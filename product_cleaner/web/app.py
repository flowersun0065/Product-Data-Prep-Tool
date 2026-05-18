#!/usr/bin/env python3
"""
Web 应用主文件

整合所有模块，提供 Flask Web 服务。
"""

import os
import re
import json
import time
import hashlib
import logging
import shutil
import threading
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
import numpy as np
from flask import Flask, render_template_string, request, jsonify, send_file
from flask_cors import CORS

try:
    import google.genai as genai
    HAS_GENAI = True
except:
    HAS_GENAI = False

# 导入核心模块
from ..constants import (
    BASE_DIR, UPLOAD_FOLDER, RESULT_FOLDER, CACHE_FOLDER,
    MIN_EXCEL_SIZE, MAX_CENTRAL_DIR_SIZE, MAX_CONTENT_LENGTH
)
from ..core import (
    SpecExtractor, BrandConsistencyChecker, BrandClusterEngine,
    CategoryDetector, StandardizationEngine, CacheManager, lean_clusters,
    build_entity_dict, infer_brand_metadata
)
from ..core.ai_engine import ProductCleanerEngine
from ..core.tag_computer import compute_all_tags

# 初始化缓存管理器
cache_manager = CacheManager()

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 会话管理
sessions = {}
session_locks: Dict[str, threading.Lock] = {}
_session_global_lock = threading.Lock()

def _get_session_lock(sid: str) -> threading.Lock:
    """获取 session 级别的锁，用于保护单个 session 的读-改-写操作"""
    if sid not in session_locks:
        with _session_global_lock:
            if sid not in session_locks:
                session_locks[sid] = threading.Lock()
    return session_locks[sid]

SNAPSHOT_DIR = CACHE_FOLDER / 'session_snapshots'
# Session 快照保留天数，超过此期限的旧 session 启动时自动清理
MAX_SESSION_DAYS = 1

# Electron mode data directory (set by run_server.py --electron)
_electron_data_dir = None

def set_electron_data_dir(path: str):
    global _electron_data_dir
    _electron_data_dir = path
# 诊断超时：processing 状态超过此时间视为失效，重新诊断
SESSION_PROCESSING_TIMEOUT = timedelta(minutes=30)

def _serialize_session(sess: Dict) -> Dict:
    """提取 session 中需要持久化的字段"""
    return {
        'file_path': sess.get('file_path'),
        'col_mapping': sess.get('col_mapping'),
        'status': sess.get('status'),
        'created': sess.get('created').isoformat() if isinstance(sess.get('created'), datetime) else sess.get('created'),
        'brand_rules': sess.get('brand_rules', {}),
        'new_brands': sess.get('new_brands', []),
        'confirmed_brands': sess.get('confirmed_brands', []),
        'diagnosis_status': sess.get('diagnosis_status'),
        'diagnosis_stats': sess.get('diagnosis_stats'),
        'diagnosis_result': sess.get('diagnosis_result')
    }

def _snapshot_path(group_id: str, file_hash: str) -> Path:
    if not group_id:
        logger.warning("_snapshot_path called with empty group_id")
    d = SNAPSHOT_DIR / group_id
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{file_hash}.json"

def save_session_snapshots(sid: str = None):
    """
    增量保存 session 快照。
    如果 sid 指定，只保存该 session 的独立文件；
    如果 sid 为 None，遍历 _dirty_sessions 保存所有变更过的 session。
    """
    try:
        SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

        if sid is not None:
            # 立即保存单个 session
            if sid in sessions:
                sess = sessions[sid]
                data = _serialize_session(sess)
                gid = sess.get('group_id', '')
                fh = sess.get('file_hash', '')
                if gid and fh:
                    path = _snapshot_path(gid, fh)
                    tmp = path.with_suffix('.tmp')
                    with open(tmp, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    os.replace(str(tmp), str(path))
            with _dirty_sessions_lock:
                _dirty_sessions.discard(sid)
            return

        # 后台刷写：遍历 dirty set
        with _dirty_sessions_lock:
            dirty = set(_dirty_sessions)
            _dirty_sessions.clear()
        for d_sid in dirty:
            if d_sid in sessions:
                sess = sessions[d_sid]
                data = _serialize_session(sess)
                gid = sess.get('group_id', '')
                fh = sess.get('file_hash', '')
                if gid and fh:
                    path = _snapshot_path(gid, fh)
                    tmp = path.with_suffix('.tmp')
                    with open(tmp, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    os.replace(str(tmp), str(path))
    except Exception as e:
        logger.error(f"Save snapshots failed: {e}")

_dirty_sessions: set = set()
_dirty_sessions_lock = threading.Lock()

def mark_snapshot_dirty(sid: str = None):
    """标记 session 为 dirty，后台 flusher 会在 30s 内刷写"""
    with _dirty_sessions_lock:
        if sid is None:
            # 标记所有 session 为 dirty（兜底）
            for s in sessions:
                _dirty_sessions.add(s)
        else:
            _dirty_sessions.add(sid)

def _snapshot_flusher():
    """后台定时刷写 dirty sessions，避免高频 IO"""
    while True:
        time.sleep(30)
        with _dirty_sessions_lock:
            dirty = bool(_dirty_sessions)
        if dirty:
            save_session_snapshots()

_snapshot_flusher_thread = threading.Thread(target=_snapshot_flusher, daemon=True)
_snapshot_flusher_thread.start()

def _get_session_created(sess: Dict) -> Optional[datetime]:
    """获取 session 的创建时间，兼容 datetime 对象和 ISO 字符串"""
    val = sess.get('created')
    if isinstance(val, datetime):
        return val
    if isinstance(val, str):
        try:
            return datetime.fromisoformat(val)
        except Exception:
            return None
    return None

def _remove_session(sid: str):
    """从内存和磁盘中移除指定 session"""
    sess = sessions.get(sid, {})
    gid = sess.get('group_id', '')
    fh = sess.get('file_hash', '')
    sessions.pop(sid, None)
    if gid and fh:
        snap_path = _snapshot_path(gid, fh)
        try:
            if snap_path.exists():
                snap_path.unlink()
        except Exception:
            pass

def _migrate_old_snapshot():
    """将旧版单文件 session_snapshots.json 迁移为独立文件"""
    old_file = CACHE_FOLDER / 'session_snapshots.json'
    if not old_file.exists():
        return
    try:
        old_file.rename(old_file.with_suffix('.json.bak'))
        logger.info("Renamed old session_snapshots.json (no longer needed)")
    except Exception as e:
        logger.error(f"Migration failed: {e}")

def _cleanup_old_snapshots():
    """清理过期 session 快照和旧版迁移残留"""
    try:
        # 删除迁移残留的 .bak 文件
        bak = CACHE_FOLDER / 'session_snapshots.json.bak'
        if bak.exists():
            bak_size = bak.stat().st_size
            bak.unlink()
            logger.info(f"Deleted migration backup: {bak.name} ({bak_size / 1024 / 1024:.0f}MB)")

        # 清理超过 MAX_SESSION_DAYS 的 session 文件（按 group_id 分目录）
        if not SNAPSHOT_DIR.exists():
            return
        now = datetime.now()
        cutoff = now - timedelta(days=MAX_SESSION_DAYS)
        removed = 0
        for group_dir in SNAPSHOT_DIR.iterdir():
            if not group_dir.is_dir():
                continue
            for f in group_dir.iterdir():
                if f.suffix == '.json':
                    try:
                        mtime = datetime.fromtimestamp(f.stat().st_mtime)
                        if mtime < cutoff:
                            f.unlink()
                            removed += 1
                    except Exception:
                        pass
            # 清理空目录
            try:
                if not any(group_dir.iterdir()):
                    group_dir.rmdir()
            except Exception:
                pass
        if removed:
            logger.info(f"Cleaned up {removed} expired session snapshots (>{MAX_SESSION_DAYS}d old)")
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")

def load_session_snapshots():
    """从独立文件恢复所有会话（按 group_id 分目录）"""
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    loaded = 0
    for group_dir in sorted(SNAPSHOT_DIR.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if not group_dir.is_dir():
            continue
        for f in sorted(group_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
            if f.suffix == '.json':
                try:
                    with open(f, 'r', encoding='utf-8') as fh:
                        sess_data = json.load(fh)
                    sid = sess_data.get('session_id', f.stem)
                    sessions[sid] = sess_data
                    loaded += 1
                except Exception as e:
                    logger.error(f"Load {f.name} failed: {e}")
    logger.info(f"Loaded {loaded} session snapshots")

# 启动时迁移旧格式 → 清理过期 → 加载
_migrate_old_snapshot()
_cleanup_old_snapshots()
load_session_snapshots()


def create_app():
    """创建 Flask 应用实例"""
    app = Flask(__name__, static_folder='../static', static_url_path='/static')
    CORS(app)
    app.config['UPLOAD_FOLDER'] = str(UPLOAD_FOLDER)
    app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

    # 注册路由
    register_routes(app)

    return app


def validate_excel_file(filepath: Path) -> Tuple[bool, str]:
    """
    验证 Excel 文件的完整性

    Returns:
        (is_valid, error_message)
    """
    try:
        file_size = filepath.stat().st_size

        # 检查文件大小
        if file_size == 0:
            return False, "文件为空，请重新上传"

        if file_size < MIN_EXCEL_SIZE:
            return False, f"文件大小异常（{file_size} 字节），可能是上传不完整，请重新上传"

        # 读取文件头检查 ZIP 签名（Excel 2007+ 是 ZIP 格式）
        with open(filepath, 'rb') as f:
            header = f.read(4)

            # 检查 ZIP 文件签名
            if header != b'PK\x03\x04':
                # 不是 ZIP 格式，可能是旧版 Excel (.xls) 或其他格式
                # 尝试读取更多内容检查
                f.seek(0)
                content = f.read(8)
                # 旧版 Excel (.xls) 签名
                if content[:2] == b'\xd0\xcf':
                    return True, ""  # 旧版 Excel 格式
                return False, "文件格式不是有效的 Excel 文件，请上传 .xlsx 或 .xls 格式文件"

            # 对于 ZIP 格式（.xlsx），检查文件是否完整
            # 读取文件末尾检查中央目录
            f.seek(-MAX_CENTRAL_DIR_SIZE, 2)  # 从文件末尾向前读取
            tail = f.read()

            # 检查是否包含完整的中央目录标记
            if tail.count(b'PK\x01\x02') > 0:
                # 找到中央目录，但需要确保文件有足够的数据
                if file_size < 5000:  # 小于 5KB 的 xlsx 文件很可能损坏
                    return False, f"文件可能损坏或上传不完整（大小: {file_size} 字节），请重新上传原始文件"

        return True, ""

    except Exception as e:
        return False, f"文件验证失败: {str(e)}"


def diagnose_async(session_id: str, file_path: str, col_mapping: Dict):
    """后台异步执行诊断"""
    session = sessions[session_id]
    session['diagnosis_status'] = 'processing'
    session['diagnosis_progress'] = 0
    session['diagnosis_logs'] = []
    session['step_times'] = {}
    step_times = session['step_times']
    import time as _time

    session['current_step'] = 'reading'
    session['current_step_start'] = _time.time()

    try:
        filepath = Path(file_path)

        step_times['reading_start'] = _time.time()
        # 检查文件是否存在
        if not filepath.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        # 验证文件完整性
        is_valid, error_msg = validate_excel_file(filepath)
        if not is_valid:
            raise ValueError(error_msg)

        file_size = filepath.stat().st_size
        session['diagnosis_logs'].append(f"文件大小: {file_size / 1024:.1f} KB")

        # 尝试不同的引擎读取 Excel
        df = None
        last_error = None
        for engine in ['openpyxl', 'xlrd']:
            try:
                df = pd.read_excel(file_path, engine=engine)
                session['diagnosis_logs'].append(f"使用引擎: {engine}")
                break
            except Exception as e:
                last_error = str(e)
                session['diagnosis_logs'].append(f"引擎 {engine} 失败: {e}")
                continue

        # 如果指定引擎都失败，尝试自动检测
        if df is None:
            try:
                df = pd.read_excel(file_path)
                session['diagnosis_logs'].append("使用引擎: auto")
            except Exception as e:
                last_error = str(e)
                session['diagnosis_logs'].append(f"引擎 auto 失败: {e}")

        if df is None:
            error_detail = f"\n最后错误: {last_error}" if last_error else ""
            raise ValueError(f"无法读取 Excel 文件，请检查文件是否损坏或格式是否正确。{error_detail}")

        df = df.replace({np.nan: None})
        step_times['reading_end'] = _time.time()

        session['diagnosis_progress'] = 10
        session['diagnosis_logs'].append("正在读取文件...")

        session['current_step'] = 'brands'
        session['current_step_start'] = _time.time()
        step_times['brands_start'] = _time.time()
        session['diagnosis_progress'] = 20
        session['diagnosis_logs'].append("正在分析品牌与分类（预计 40 秒）...")
        code_col = col_mapping.get('org_spu_code')
        brand_clusters = BrandClusterEngine.cluster(df, col_mapping['org_spu_name'], col_mapping.get('brand_name'), code_col, col_mapping)
        step_times['brands_end'] = _time.time()

        # 加载持久化的确认规则，注入 session
        from ..brands.database import load_corrected_products
        if 'brand_rules' not in session:
            session['brand_rules'] = {}
        confirmed_rules = load_corrected_products(_get_group_id(session_id))
        for code, rule in confirmed_rules.items():
            if code not in session['brand_rules']:
                session['brand_rules'][code] = rule

        # 将已修正的分类注入分类规则缓存
        cat_rules_changed = False
        cache_rules = cache_manager.get_rules(_get_group_id(session_id), session_id) or {}
        cat_rules = cache_rules.get('categories', {})
        for code, info in confirmed_rules.items():
            if info.get('category') and code not in cat_rules:
                cat_rules[code] = {'action': 'confirm', 'replacement': info['category']}
                cat_rules_changed = True
        if cat_rules_changed:
            cache_manager.set_rules(_get_group_id(session_id), session_id, {**cache_rules, 'categories': cat_rules})

        # 加载修正记录，改善建议值
        from ..brands.database import load_corrected_brands, find_any_brand, load_dismissed_brands
        corrected_brands = load_corrected_brands()

        # === 自动提取新品牌候选者 (带智能推断) ===
        auto_new_brands = []
        seen_new_brands = set()
        for cluster in brand_clusters:
            for item in cluster.get('items', []):
                if item.get('issue_type') == 'new_brand_candidate':
                    b_name = item['brand']
                    item_code = str(item.get('code', '')).strip()
                    if item_code in confirmed_rules:
                        continue
                    if b_name and b_name not in seen_new_brands:
                        # 查修正记录：如果历史上有过同类修正
                        if b_name in corrected_brands:
                            entry = corrected_brands[b_name]
                            corrected_to = entry['corrected_to']
                            if find_any_brand(corrected_to)['found']:
                                # 修正后的品牌已在库中 → 跳过，不进入新品牌待确认
                                item['corrected_from_history'] = True
                                item['corrected_brand'] = corrected_to
                                continue
                            else:
                                # 修正后的品牌也不在库中 → 用修正后的名字
                                b_name = corrected_to
                                item['corrected_from_history'] = True
                                item['corrected_brand'] = corrected_to
                        if not find_any_brand(b_name)['found']:
                            if b_name in load_dismissed_brands():
                                continue
                            metadata = infer_brand_metadata(item['name'], item.get('category_path', ''))

                            auto_new_brands.append({
                                'name': b_name,
                                'aliases': [b_name],
                                'type': metadata['type'],
                                'country': metadata['country'],
                                'suggested_name': metadata['suggested_name'],
                                'sample_product': item['name'],
                                'sample_category': item.get('category_path', ''),
                                'confirmed': False,
                                'is_slash_brand': '/' in (metadata['suggested_name'] or b_name)
                            })
                            seen_new_brands.add(b_name)

        # 品牌列为空时，从 missing 聚类中提取新品牌候选
        for cluster in brand_clusters:
            if cluster.get('type') != 'missing':
                continue
            b_name = cluster.get('suggested_standard')
            if not b_name or b_name in seen_new_brands:
                continue
            if b_name in corrected_brands:
                entry = corrected_brands[b_name]
                corrected_to = entry['corrected_to']
                if find_any_brand(corrected_to)['found']:
                    continue
                b_name = corrected_to
            if not find_any_brand(b_name)['found']:
                if b_name in load_dismissed_brands():
                    continue
                sample = (cluster.get('items') or [{}])[0]
                metadata = infer_brand_metadata(sample.get('name', ''), sample.get('category_path', ''))
                auto_new_brands.append({
                    'name': b_name,
                    'aliases': [b_name],
                    'type': metadata['type'],
                    'country': metadata['country'],
                    'suggested_name': metadata['suggested_name'],
                    'sample_product': sample.get('name', ''),
                    'sample_category': sample.get('category_path', ''),
                    'confirmed': False,
                    'is_slash_brand': '/' in (metadata['suggested_name'] or b_name)
                })
                seen_new_brands.add(b_name)

        session['new_brands'] = auto_new_brands

        session['diagnosis_progress'] = 80
        session['diagnosis_logs'].append("正在分析分类（Code 归集逻辑）...")
        session['current_step'] = 'categories'
        session['current_step_start'] = _time.time()
        step_times['categories_start'] = _time.time()
        name_col = col_mapping.get('org_spu_name')
        entity_dict = build_entity_dict(df[name_col].dropna().astype(str).tolist()) if name_col else {}
        category_result = CategoryDetector.analyze(df, col_mapping, entity_dict)
        step_times['categories_end'] = _time.time()

        # 应用分类修正记录
        from ..brands.database import load_corrected_categories
        corrected_cats = load_corrected_categories()
        if corrected_cats and entity_dict:
            for group_key in ['missing_items', 'conflict_groups', 'marketing_groups', 'standard_groups']:
                for group in category_result.get(group_key, []):
                    for gitem in group.get('items', []):
                        factors = gitem.get('factors', {}) or {}
                        entity = factors.get('entity')
                        if entity and entity in corrected_cats:
                            entry = corrected_cats[entity]
                            if entry.get('brand_type') == factors.get('brand_type'):
                                gitem['corrected_from_history'] = True
                                if entry.get('corrected_path'):
                                    gitem['suggested_path'] = [entry['corrected_path']]
            # 同步到 all_codes
            for ac in category_result.get('all_codes', []):
                ac_factors = ac.get('factors', {}) or {}
                ac_entity = ac_factors.get('entity')
                if ac_entity and ac_entity in corrected_cats:
                    entry = corrected_cats[ac_entity]
                    if entry.get('brand_type') == ac_factors.get('brand_type'):
                        ac['corrected_from_history'] = True
                        if entry.get('corrected_path'):
                            ac['suggested_path'] = [entry['corrected_path']]
        
        
        session['diagnosis_progress'] = 90
        session['diagnosis_logs'].append("正在精简数据...")
        lean_clusters_data = lean_clusters(brand_clusters)

        stats = category_result['stats']
        total = len(df)
        brand_missing_count = sum([c.get('count', 0) for c in brand_clusters if c.get('type') == 'missing'])
        brand_mismatch_count = sum([c.get('count', 0) for c in brand_clusters if c.get('type') == 'mismatch'])
        need_ai = brand_missing_count + brand_mismatch_count + stats['missing_count']

        diagnosis_result = {
            'brand_clusters': lean_clusters_data,
            'conflict_groups': category_result['conflict_groups'],
            'marketing_groups': category_result['marketing_groups'],
            'standard_groups': category_result['standard_groups'],
            'missing_items': category_result['missing_items'],
            'all_codes': category_result.get('all_codes', []),
            'cleaned_paths': category_result.get('cleaned_paths', {}),
            'path_classifications': category_result.get('path_classifications', {}),
            'category_options': category_result['category_options']
        }
        diagnosis_stats = {
            'total': int(total),
            'valid': int(total - need_ai),
            'brand_missing': int(brand_missing_count),
            'brand_mismatch': int(brand_mismatch_count),
            'marketing': int(stats['pure_marketing_count'] + stats['conflict_count']),
            'need_ai': int(need_ai)
        }

        with _get_session_lock(session_id):
            session['diagnosis_progress'] = 100
            session['diagnosis_result'] = diagnosis_result
            session['diagnosis_stats'] = diagnosis_stats
            session['current_step'] = ''
            session['diagnosis_logs'].append("诊断完成!")
            session['diagnosis_status'] = 'completed'

        save_session_snapshots(session_id)

    except Exception as e:
        logger.error(f"Diagnosis error: {e}")
        session['diagnosis_status'] = 'error'
        session['diagnosis_error'] = str(e)
        session['diagnosis_logs'].append(f"错误: {e}")


def _find_optional_column(df, *patterns) -> Optional[str]:
    """在 df.columns 中按关键词匹配列名，返回第一个匹配到的列名。"""
    for col in df.columns:
        col_lower = col.lower()
        for p in patterns:
            if p in col_lower:
                return col
    return None


def _input_fingerprint(item: dict) -> str:
    """计算输入数据指纹，用于检测新文件中同一 code 的数据是否变化。"""
    raw = f"{item.get('name', '')}|{item.get('brand', '')}|{item.get('category', '')}"
    return hashlib.md5(raw.encode('utf-8')).hexdigest()[:12]


def _build_result_entry(item, brand_info=None, cat_info=None) -> dict:
    """
    构建单条结果 entry（只含 code + AI新增列 + 标签）。

    Args:
        item: all_items 中的条目（含 _org_prom_price, _org_recommend_tag 等）
        brand_info: AI 返回的 brand dict，None 表示跳过/本地模式
        cat_info: AI 返回的 category dict，None 表示跳过/本地模式

    Returns:
        dict，只含新增列，不含原始df已有列
    """
    if brand_info:
        brand_name = brand_info.get('value', '')
    else:
        brand_name = item.get('brand', '')

    spec_from_name = SpecExtractor.extract(item['name'])[1] or ''

    tags = compute_all_tags(
        brand_name=brand_name,
        org_prom_price=item.get('_org_prom_price', ''),
        org_recommend_tag=item.get('_org_recommend_tag', ''),
        category_path=item.get('category', ''),
    )

    entry = {
        'code': item['code'],
        'brand_ai': brand_name,
        'brand_type': brand_info.get('brand_type', '') if brand_info else '',
        'brand_confidence': brand_info.get('confidence', 0) if brand_info else 0,
        'brand_status': brand_info.get('status', '') if brand_info else '',
        'brand_reason': brand_info.get('reason', '') if brand_info else '',
        'spec_from_name': spec_from_name,
        'category_ai': cat_info.get('path', '') if cat_info else '',
        'category_confidence': cat_info.get('confidence', 0) if cat_info else 0,
        'category_method': cat_info.get('method', '') if cat_info else '',
        'category_reason': cat_info.get('reason', '') if cat_info else '',
        'category_status': cat_info.get('status', '') if cat_info else '',
        'category_entity': (cat_info.get('factors', {}).get('entity', '') if cat_info else ''),
        'category_modifiers': ', '.join(cat_info.get('factors', {}).get('modifiers', []) or []) if cat_info else '',
        **tags,
    }

    if brand_info is not None or cat_info is not None:
        entry['needs_review'] = (
            brand_info.get('needs_review', False) or
            cat_info.get('needs_review', False)
        )
    else:
        entry['needs_review'] = item.get('_needs_review', False)

    entry['review_status'] = '已确认' if not entry['needs_review'] else '待复核'

    return entry


def process_file_async(session_id: str, providers: List[Dict] = None,
                       batch_size: int = 20,
                       ai_provider: str = None,
                       api_key: str = None,
                       model_id: str = None,
                       force_reanalyze: bool = False):
    """后台异步处理文件 - 支持 AI 按字段处理"""
    session = sessions[session_id]
    session['status'] = 'processing'
    session['logs'] = []
    session['ai_logs'] = []  # 增量日志（consumed by /api/ai_logs）
    session['processed'] = 0
    session['ai_total'] = 0
    session['ai_skipped'] = 0
    session['review_pending'] = []
    session['start_time'] = datetime.now()

    try:
        df = pd.read_excel(session['file_path'])
        df = df.replace({np.nan: None})

        rules = cache_manager.get_rules(_get_group_id(session_id), session_id)
        df = StandardizationEngine.apply_rules(df, session['col_mapping'], rules)

        # 保留一份原始 df 引用，供后续 left join 使用（避免每次 batch 重复读磁盘）
        original_df = df.copy()

        name_col = session['col_mapping'].get('org_spu_name')
        brand_col = session['col_mapping'].get('brand_name')
        spec_col = session['col_mapping'].get('spu_spec')
        code_col = session['col_mapping'].get('org_spu_code')
        cate1_col = session['col_mapping'].get('cate_level1_name')
        cate2_col = session['col_mapping'].get('cate_level2_name')
        cate3_col = session['col_mapping'].get('cate_level3_name')

        # 检测标签计算所需的可选原始列
        org_prom_price_col = _find_optional_column(df, 'prom_price', '促销价')
        org_recommend_tag_col = _find_optional_column(df, 'recommend_tag', '推荐标签')

        brand_rules = session.get('brand_rules', {})
        cat_rules = rules.get('categories', {})

        # 从诊断结果的 brand_clusters 构建 code→suggested_brand 索引
        diagnosis_result = session.get('diagnosis_result', {})
        code_suggestion = {}
        for cluster in diagnosis_result.get('brand_clusters', []):
            for item in cluster.get('items', []):
                c = item.get('code', '')
                if c:
                    sb = item.get('suggested_brand')
                    if sb:
                        code_suggestion[c] = sb

        # 构建所有商品的判断列表（按 code 去重）
        all_items = []
        seen_codes = set()
        for idx, row in df.iterrows():
            code = str(row.get(code_col, '')).strip() if code_col else f"row_{idx}"
            if code_col and code in seen_codes:
                continue  # 已处理过的商品 code 跳过
            seen_codes.add(code)
            name = str(row.get(name_col, '')).strip() if name_col else ''
            brand = str(row.get(brand_col, '')).strip() if brand_col and row.get(brand_col) else ''
            spec = str(row.get(spec_col, '')).strip() if spec_col and row.get(spec_col) else ''
            cate1 = str(row.get(cate1_col, '')).strip() if cate1_col and row.get(cate1_col) else ''
            cate2 = str(row.get(cate2_col, '')).strip() if cate2_col and row.get(cate2_col) else ''
            cate3 = str(row.get(cate3_col, '')).strip() if cate3_col and row.get(cate3_col) else ''
            category = f"{cate1} > {cate2} > {cate3}" if cate3 else ''

            # 标签计算所需的原始行值
            _org_prom_price = str(row.get(org_prom_price_col, '')).strip() if org_prom_price_col else ''
            _org_recommend_tag = str(row.get(org_recommend_tag_col, '')).strip() if org_recommend_tag_col else ''

            if not name:
                continue

            # 判断品牌是否需要 AI
            brand_rule = brand_rules.get(code, {})
            needs_brand_ai = False
            if brand_rule.get('skipped'):
                needs_brand_ai = True  # 用户跳过的
            elif not brand_rule and (not brand or brand == 'nan'):
                needs_brand_ai = True  # 未处理且品牌缺失

            # 判断分类是否需要 AI（只要用户没人工确认过的都送 AI）
            cat_rule = cat_rules.get(code, {})
            needs_category_ai = cat_rule.get('action') not in ('confirm', 'replace')

            all_items.append({
                'code': code,
                'name': name,
                'brand': brand,
                'spec': spec,
                'category': category,
                'needs_brand_ai': needs_brand_ai,
                'needs_category_ai': needs_category_ai,
                'has_brand_confirmed': bool(brand_rule) and not brand_rule.get('skipped'),
                'has_category_confirmed': cat_rule.get('action') in ('confirm', 'replace'),
                'existing_suggestion': code_suggestion.get(code, ''),  # 诊断阶段的品牌建议
                '_org_prom_price': _org_prom_price,
                '_org_recommend_tag': _org_recommend_tag,
            })

        # 统计（分字段）
        need_ai_items = [it for it in all_items if it['needs_brand_ai'] or it['needs_category_ai']]
        skip_items = [it for it in all_items if not it['needs_brand_ai'] and not it['needs_category_ai']]
        total_brand_ai = sum(1 for it in all_items if it['needs_brand_ai'])
        total_cat_ai = sum(1 for it in all_items if it['needs_category_ai'])
        skipped_brand = sum(1 for it in all_items if it['has_brand_confirmed'])
        skipped_cat = sum(1 for it in all_items if it['has_category_confirmed'])
        session['ai_total'] = len(need_ai_items)
        session['ai_skipped'] = len(skip_items)
        session['ai_total_brand'] = total_brand_ai
        session['ai_total_category'] = total_cat_ai
        session['ai_skipped_brand'] = skipped_brand
        session['ai_skipped_category'] = skipped_cat
        session['total'] = len(all_items)
        session['logs'].append(
            f"[{datetime.now().strftime('%H:%M:%S')}] 总计{len(all_items)}个商品 | "
            f"品牌待AI:{total_brand_ai} 分类待AI:{total_cat_ai} | "
            f"品牌已确认:{skipped_brand} 分类已确认:{skipped_cat}"
        )

        # 已确认的商品写入日志（让用户看到跳过了哪些）
        for item in skip_items:
            session['ai_logs'].append({
                'name': item['name'],
                'code': item['code'],
                'brand': {
                    'status': 'skipped',
                    'value': item['brand'],
                    'confirmed': True,
                    'confidence': 1.0
                },
                'category': {
                    'status': 'skipped',
                    'path': item['category'],
                    'confirmed': True,
                    'confidence': 1.0
                },
                'needs_review': False
            })

        # 处理需要 AI 的条目
        all_results = []
        has_ai_engine = False
        engine = None

        if need_ai_items and ai_provider and api_key:
            try:
                engine = ProductCleanerEngine(
                    api_key=api_key,
                    provider=ai_provider,
                    model_id=model_id
                )
                has_ai_engine = True
                session['logs'].append(
                    f"[{datetime.now().strftime('%H:%M:%S')}] AI 引擎初始化成功: {ai_provider}/{model_id or '默认'}"
                )
            except Exception as e:
                logger.warning(f"AI 引擎初始化失败，使用本地模式: {e}")
                session['logs'].append(f"[{datetime.now().strftime('%H:%M:%S')}] AI 引擎初始化失败: {e}，将使用本地模式")
                session['ai_logs'].append({
                    'name': '(系统)',
                    'code': '',
                    'brand': {'status': 'skipped', 'value': '', 'confidence': 1.0},
                    'category': {'status': 'skipped', 'path': '', 'confidence': 1.0},
                    'needs_review': False,
                    '_system_message': f'⚠️ AI 引擎初始化失败: {e}，将使用本地模式'
                })

        # 构建 entity_dict 供分类使用（复用诊断阶段的逻辑）
        entity_dict = build_entity_dict(
            [it['name'] for it in all_items if it['name']]
        ) if has_ai_engine else {}

        # 从诊断结果获取分类相关数据（diagnosis_result 已在上面定义）
        category_options = diagnosis_result.get('category_options', {})
        cleaned_paths = diagnosis_result.get('cleaned_paths', {})

        # AI 缓存：先查缓存，命中则跳过 AI（force_reanalyze 时跳过缓存）
        # 缓存已是同组共享，带输入指纹检测数据变化
        cache_key_suffix = f"{ai_provider or 'local'}:{model_id or 'default'}"
        group_id = _get_group_id(session_id)
        uncached_items = []
        for item in need_ai_items:
            cache_key = f"ai:{item['code']}:{cache_key_suffix}"
            fingerprint = _input_fingerprint(item) if has_ai_engine else ''
            cached = None
            if has_ai_engine and not force_reanalyze:
                cached = cache_manager.get_ai_cache(group_id, cache_key, fingerprint)
            if cached:
                entry = _build_result_entry(
                    item,
                    brand_info=cached.get('brand', {}),
                    cat_info=cached.get('category', {}),
                )
                # 日志
                session['ai_logs'].append({
                    'name': item['name'],
                    'code': item['code'],
                    'brand': cached.get('brand', {}),
                    'category': cached.get('category', {}),
                    'factors': cached.get('category', {}).get('factors', {}),
                    'needs_review': cached.get('needs_review', False),
                    '_cached': True,
                })
                all_results.append(entry)
                if entry.get('needs_review'):
                    session['review_pending'].append(entry)
            else:
                uncached_items.append(item)

        cached_count = len(need_ai_items) - len(uncached_items)
        if uncached_items:
            session['logs'].append(
                f"[{datetime.now().strftime('%H:%M:%S')}] "
                f"缓存命中 {cached_count} 条，"
                f"待 AI 处理 {len(uncached_items)} 条"
            )

        # 分批处理需要 AI 的条目（仅未缓存的）
        for batch_idx in range(0, len(uncached_items), batch_size):
            # 检查是否被取消
            if session.get('cancel_requested'):
                session['status'] = 'cancelled'
                session['message'] = f'用户取消，已处理 {len(all_results)} 条'
                session['logs'].append(f"[{datetime.now().strftime('%H:%M:%S')}] 用户取消处理")
                break

            batch = uncached_items[batch_idx:batch_idx + batch_size]
            batch_results = []

            if has_ai_engine:
                # AI 模式
                ai_results = engine.process_batch(
                    batch,
                    fields=['brand', 'category'],
                    entity_dict=entity_dict,
                    cleaned_paths=cleaned_paths,
                    category_options=category_options,
                )
                for item, ai_res in zip(batch, ai_results):
                    # 写入缓存（带输入指纹，同组共享）
                    cache_key = f"ai:{item['code']}:{cache_key_suffix}"
                    fp = _input_fingerprint(item)
                    cache_manager.set_ai_cache(group_id, cache_key, ai_res, fp)

                    entry = _build_result_entry(
                        item,
                        brand_info=ai_res.get('brand', {}),
                        cat_info=ai_res.get('category', {}),
                    )
                    batch_results.append(entry)
                    # 写入增量日志（含完整 factors / reason）
                    factors = ai_res.get('category', {}).get('factors', {})
                    log_entry = {
                        'name': item['name'],
                        'code': item['code'],
                        'brand': ai_res['brand'],
                        'category': ai_res['category'],
                        'factors': {
                            'entity': factors.get('entity', ''),
                            'modifiers': factors.get('modifiers', []),
                            'brand_type': factors.get('brand_type', ''),
                        },
                        'needs_review': ai_res.get('needs_review', False)
                    }
                    session['ai_logs'].append(log_entry)
                    if entry.get('needs_review'):
                        session['review_pending'].append(entry)
            else:
                # 本地提取模式（fallback）
                for item in batch:
                    entry = _build_result_entry(item)
                    # 本地模式覆盖：从商品名提取品牌
                    extracted_brand = BrandConsistencyChecker._extract_from_name(item['name']) or ''
                    entry['brand_ai'] = extracted_brand or item['brand']
                    entry['brand_confidence'] = 0.8 if extracted_brand else 0.5
                    entry['brand_status'] = 'local'
                    entry['needs_review'] = not extracted_brand
                    entry['review_status'] = '待复核' if entry['needs_review'] else '已确认'
                    batch_results.append(entry)
                    log_entry = {
                        'name': item['name'],
                        'code': item['code'],
                        'brand': {'status': 'local', 'value': entry['brand_ai'], 'confidence': entry['brand_confidence']},
                        'category': {'status': 'skipped', 'path': '', 'confidence': 0.0},
                        'needs_review': entry['needs_review']
                    }
                    session['ai_logs'].append(log_entry)
                    if entry.get('needs_review'):
                        session['review_pending'].append(entry)

            all_results.extend(batch_results)
            session['processed'] = len(all_results)
            session['progress'] = int(session['processed'] / len(need_ai_items) * 100) if need_ai_items else 100

            # 写入中间结果
            combined = []
            for item in skip_items:
                entry = _build_result_entry(item)
                entry['brand_confidence'] = 1.0
                entry['brand_status'] = 'skipped'
                combined.append(entry)
            combined.extend(all_results)
            if combined:
                ai_df = pd.DataFrame(combined)
                # left join 到原始 df：保留全部原始列 + AI 新增列
                if code_col and code_col in original_df.columns:
                    original_df[code_col] = original_df[code_col].astype(str)
                    ai_df['code'] = ai_df['code'].astype(str)
                    result_df = original_df.merge(ai_df, left_on=code_col, right_on='code', how='left')
                else:
                    result_df = ai_df
                result_file = RESULT_FOLDER / f"{session_id}_result.xlsx"
                result_df.to_excel(str(result_file), index=False)
                session['result_file'] = str(result_file)

                # 生成 review_file
                review_df = result_df[result_df['needs_review'] == True] if 'needs_review' in result_df.columns else pd.DataFrame()
                if not review_df.empty:
                    review_file = RESULT_FOLDER / f"{session_id}_review_{uuid.uuid4().hex[:6]}.xlsx"
                    review_df.to_excel(str(review_file), index=False)
                    session['review_file'] = str(review_file)

            time.sleep(0.2)

        # 如果没有需要 AI 处理的数据
        if not need_ai_items:
            session['logs'].append(
                f"[{datetime.now().strftime('%H:%M:%S')}] 所有商品均已完成确认，无需 AI 处理"
            )
            session['ai_logs'].append({
                'name': '(系统)',
                'code': '',
                'brand': {'status': 'skipped', 'value': '', 'confidence': 1.0},
                'category': {'status': 'skipped', 'path': '', 'confidence': 1.0},
                'needs_review': False,
                '_system_message': '所有商品均已完成确认，无需 AI 处理'
            })

        # 添加快跳到结果列表
        combined = []
        for item in skip_items:
            entry = _build_result_entry(item)
            entry['brand_confidence'] = 1.0
            entry['brand_status'] = 'skipped'
            combined.append(entry)
        combined.extend(all_results)

        if combined:
            ai_df = pd.DataFrame(combined)
            if code_col and code_col in original_df.columns:
                original_df[code_col] = original_df[code_col].astype(str)
                ai_df['code'] = ai_df['code'].astype(str)
                result_df = original_df.merge(ai_df, left_on=code_col, right_on='code', how='left')
            else:
                result_df = ai_df
            result_file = RESULT_FOLDER / f"{session_id}_result.xlsx"
            result_df.to_excel(str(result_file), index=False)
            session['result_file'] = str(result_file)

            review_df = result_df[result_df['needs_review'] == True] if 'needs_review' in result_df.columns else pd.DataFrame()
            if not review_df.empty:
                review_file = RESULT_FOLDER / f"{session_id}_review_{uuid.uuid4().hex[:6]}.xlsx"
                review_df.to_excel(str(review_file), index=False)
                session['review_file'] = str(review_file)

        # 如果被取消，不要覆盖 cancelled 状态
        if session.get('status') != 'cancelled':
            session['status'] = 'completed'
            session['progress'] = 100
            session['message'] = (
                f'处理完成! AI处理{len(uncached_items)}条, '
                f'缓存复用{cached_count}条, '
                f'跳过{len(skip_items)}条, '
                f'需复核{len(session["review_pending"])}条'
            )
            session['end_time'] = datetime.now()
            session['logs'].append(f"[{datetime.now().strftime('%H:%M:%S')}] 处理完成")
            logger.info(f"Session {session_id} completed. {session['message']}")

    except Exception as e:
        logger.error(f"Processing error: {e}")
        session['status'] = 'error'
        session['message'] = str(e)
        session['end_time'] = datetime.now()
        session['logs'].append(f"[{datetime.now().strftime('%H:%M:%S')}] 错误: {e}")
        session['logs'].append(f"[{datetime.now().strftime('%H:%M:%S')}] 错误: {e}")


# === 分组管理 ===

GROUPS_FILE = CACHE_FOLDER / 'groups.json'
_groups_cache: Dict[str, Dict] = {}

def _load_groups() -> Dict:
    """加载分组数据"""
    if GROUPS_FILE.exists():
        try:
            return json.load(open(GROUPS_FILE, 'r', encoding='utf-8'))
        except Exception:
            return {}
    return {}

def _save_groups(data: Dict):
    """保存分组数据（原子写入）"""
    tmp = GROUPS_FILE.with_suffix('.tmp')
    json.dump(data, open(tmp, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    os.replace(str(tmp), str(GROUPS_FILE))

def _ensure_group_dir(group_id: str):
    """确保某个分组的目录存在"""
    (CACHE_FOLDER / 'ai_cache' / group_id).mkdir(parents=True, exist_ok=True)
    (CACHE_FOLDER / 'session_snapshots' / group_id).mkdir(parents=True, exist_ok=True)
    (CACHE_FOLDER / 'rules_cache' / group_id).mkdir(parents=True, exist_ok=True)
    (CACHE_FOLDER / 'review_cache' / group_id).mkdir(parents=True, exist_ok=True)
    (BASE_DIR.parent / 'corrections' / group_id).mkdir(parents=True, exist_ok=True)

def _get_group_id(session_id: str) -> str:
    """从 session 中获取 group_id"""
    sess = sessions.get(session_id, {})
    gid = sess.get('group_id', '')
    if not gid:
        logger.warning(f"_get_group_id({session_id}): empty group_id, session exists={session_id in sessions}")
    return gid

# 启动时加载分组
_groups_cache = _load_groups()


def register_routes(app):

    @app.route('/')
    def index():
        from ..templates.html_templates import HTML_TEMPLATE
        return render_template_string(HTML_TEMPLATE)

    @app.route('/review')
    def review_page():
        from ..templates.html_templates import REVIEW_TEMPLATE
        return render_template_string(REVIEW_TEMPLATE)

    @app.route('/electron')
    def electron_app():
        """Serve the Electron-specific layout."""
        from ..templates.html_templates import ELECTRON_LAYOUT
        return render_template_string(ELECTRON_LAYOUT)

    @app.route('/api/shutdown', methods=['POST'])
    def shutdown():
        """Gracefully shut down the Flask server (called by Electron on quit)."""
        import os as _os
        import signal
        _os.kill(_os.getpid(), signal.SIGTERM)
        return jsonify({'success': True})

    @app.route('/api/settings', methods=['GET'])
    def get_settings():
        """Return current settings."""
        settings_file = Path(_electron_data_dir) / 'settings.json' if _electron_data_dir else None
        defaults = {
            'ai_provider': 'gemini',
            'model_id': 'gemini-2.0-flash',
            'api_key': '',
            'batch_size': 20,
            'detail_mode': 'sidebar',
            'theme': 'system',
            'language': 'zh',
            'startup_action': 'upload',
        }
        if settings_file and settings_file.exists():
            saved = json.load(open(settings_file))
            defaults.update(saved)
        return jsonify(defaults)

    @app.route('/api/settings', methods=['PUT'])
    def save_settings():
        """Save settings."""
        if not _electron_data_dir:
            return jsonify({'error': 'No data directory configured'}), 500
        settings_file = Path(_electron_data_dir) / 'settings.json'
        with open(settings_file, 'w') as f:
            json.dump(request.json, f, ensure_ascii=False, indent=2)
        return jsonify({'success': True})

    @app.route('/api/venv-status')
    def venv_status():
        """Check if Python virtual environment is ready."""
        import sys
        return jsonify({
            'ready': True,
            'python_version': sys.version,
            'data_dir': str(_electron_data_dir) if _electron_data_dir else '',
        })

    @app.route('/api/upload', methods=['POST'])
    def upload_file():
        """同步上传（小文件 < 1000 行）"""
        if 'file' not in request.files:
            return jsonify({'error': '没有文件'}), 400

        group_id = (request.form.get('group_id') or '').strip()
        if not group_id or group_id not in _groups_cache:
            return jsonify({'error': '请选择有效的分组'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': '文件名为空'}), 400

        try:
            # 对于大文件，先保存再读取，避免文件流被消耗
            original_filename = file.filename
            if not original_filename.lower().endswith(('.xlsx', '.xls')):
                original_filename += '.xlsx'

            temp_filename = f"temp_{int(time.time())}_{original_filename}"
            temp_filepath = UPLOAD_FOLDER / temp_filename

            # 保存文件
            file.save(temp_filepath)

            # 验证文件完整性
            is_valid, error_msg = validate_excel_file(temp_filepath)
            if not is_valid:
                try:
                    temp_filepath.unlink()
                except:
                    pass
                return jsonify({'error': error_msg}), 400

            # 从保存的文件读取
            df = pd.read_excel(temp_filepath, engine='openpyxl')
            df = df.replace({np.nan: None})

            # 小文件使用同步模式
            if len(df) < 1000:
                return _process_sync_upload(df, temp_filepath, original_filename, group_id)
            else:
                # 大文件使用异步模式
                return _process_async_upload(df, temp_filepath, original_filename, group_id)

        except Exception as e:
            logger.error(f"Upload error: {e}")
            return jsonify({'error': str(e)}), 400

    def _process_sync_upload(df, temp_filepath, original_filename, group_id):
        """同步处理小文件"""
        cols = df.columns.tolist()
        col_mapping = {}

        for col in cols:
            col_lower = col.lower()
            if 'spu_name' in col_lower or '商品名' in col_lower:
                col_mapping['org_spu_name'] = col
            elif 'brand' in col_lower or '品牌' in col_lower:
                col_mapping['brand_name'] = col
            elif 'spec' in col_lower or '规格' in col_lower:
                col_mapping['spu_spec'] = col
            elif 'cate_level1' in col_lower or '一级分类' in col_lower:
                col_mapping['cate_level1_name'] = col
            elif 'cate_level2' in col_lower or '二级分类' in col_lower:
                col_mapping['cate_level2_name'] = col
            elif 'cate_level3' in col_lower or '三级分类' in col_lower:
                col_mapping['cate_level3_name'] = col
            elif 'org_image_url' in col_lower or '商品图' in col_lower or '图片' in col_lower:
                col_mapping['org_image_url'] = col

        if 'org_spu_name' not in col_mapping:
            try:
                temp_filepath.unlink()
            except:
                pass
            return jsonify({'error': '缺少商品名称列'}), 400

        session_id = f"session_{int(time.time())}_{uuid.uuid4().hex[:6]}"

        # 将临时文件重命名为正式文件名
        filename = f"{session_id}_{original_filename}"
        filepath = UPLOAD_FOLDER / filename
        temp_filepath.rename(filepath)

        # 自动识别商品code列
        code_col = None
        for col in cols:
            col_lower = col.lower()
            if 'spu_code' in col_lower or 'code' in col_lower or '商品code' in col_lower or '编码' in col_lower:
                code_col = col
                col_mapping['org_spu_code'] = col
                break

        brand_clusters = BrandClusterEngine.cluster(df, col_mapping['org_spu_name'], col_mapping.get('brand_name'), code_col, col_mapping)
        name_col = col_mapping.get('org_spu_name')
        entity_dict = build_entity_dict(df[name_col].dropna().astype(str).tolist()) if name_col else {}
        category_result = CategoryDetector.analyze(df, col_mapping, entity_dict)

        # 加载持久化的确认和修正规则
        from ..brands.database import load_corrected_products, load_corrected_brands, load_corrected_categories, find_any_brand, load_dismissed_brands
        confirmed_rules = load_corrected_products(group_id)
        corrected_brands = load_corrected_brands()
        corrected_cats = load_corrected_categories()

        # 将已修正的分类注入分类规则缓存
        cat_rules_changed = False
        cache_rules = cache_manager.get_rules(group_id, session_id) or {}
        cat_rules = cache_rules.get('categories', {})
        for code, info in confirmed_rules.items():
            if info.get('category') and code not in cat_rules:
                cat_rules[code] = {'action': 'confirm', 'replacement': info['category']}
                cat_rules_changed = True
        if cat_rules_changed:
            cache_manager.set_rules(group_id, session_id, {**cache_rules, 'categories': cat_rules})

        # === 自动提取新品牌候选者 (带智能推断) ===
        auto_new_brands = []
        seen_new_brands = set()
        for cluster in brand_clusters:
            for item in cluster.get('items', []):
                if item.get('issue_type') == 'new_brand_candidate':
                    item_code = str(item.get('code', '')).strip()
                    if item_code in confirmed_rules:
                        continue
                    b_name = item['brand']
                    if b_name and b_name not in seen_new_brands:
                        if b_name in corrected_brands:
                            entry = corrected_brands[b_name]
                            corrected_to = entry['corrected_to']
                            if find_any_brand(corrected_to)['found']:
                                item['corrected_from_history'] = True
                                item['corrected_brand'] = corrected_to
                                continue
                            else:
                                b_name = corrected_to
                                item['corrected_from_history'] = True
                                item['corrected_brand'] = corrected_to
                        if not find_any_brand(b_name)['found']:
                            if b_name in load_dismissed_brands():
                                continue
                            metadata = infer_brand_metadata(item['name'], item.get('category_path', ''))

                            auto_new_brands.append({
                                'name': b_name,
                                'aliases': [b_name],
                                'type': metadata['type'],
                                'country': metadata['country'],
                                'suggested_name': metadata['suggested_name'],
                                'sample_product': item['name'],
                                'sample_category': item.get('category_path', ''),
                                'confirmed': False,
                                'is_slash_brand': '/' in (metadata['suggested_name'] or b_name)
                            })
                            seen_new_brands.add(b_name)

        # 品牌列为空时，从 missing 聚类中提取新品牌候选
        for cluster in brand_clusters:
            if cluster.get('type') != 'missing':
                continue
            b_name = cluster.get('suggested_standard')
            if not b_name or b_name in seen_new_brands:
                continue
            if b_name in corrected_brands:
                entry = corrected_brands[b_name]
                corrected_to = entry['corrected_to']
                if find_any_brand(corrected_to)['found']:
                    continue
                b_name = corrected_to
            if not find_any_brand(b_name)['found']:
                if b_name in load_dismissed_brands():
                    continue
                sample = (cluster.get('items') or [{}])[0]
                metadata = infer_brand_metadata(sample.get('name', ''), sample.get('category_path', ''))
                auto_new_brands.append({
                    'name': b_name,
                    'aliases': [b_name],
                    'type': metadata['type'],
                    'country': metadata['country'],
                    'suggested_name': metadata['suggested_name'],
                    'sample_product': sample.get('name', ''),
                    'sample_category': sample.get('category_path', ''),
                    'confirmed': False,
                    'is_slash_brand': '/' in (metadata['suggested_name'] or b_name)
                })
                seen_new_brands.add(b_name)

        # 应用分类修正记录
        if corrected_cats and entity_dict:
            for group_key in ['missing_items', 'conflict_groups', 'marketing_groups', 'standard_groups']:
                for group in category_result.get(group_key, []):
                    for gitem in group.get('items', []):
                        factors = gitem.get('factors', {}) or {}
                        entity = factors.get('entity')
                        if entity and entity in corrected_cats:
                            entry = corrected_cats[entity]
                            if entry.get('brand_type') == factors.get('brand_type'):
                                gitem['corrected_from_history'] = True
                                if entry.get('corrected_path'):
                                    gitem['suggested_path'] = [entry['corrected_path']]
            for ac in category_result.get('all_codes', []):
                ac_factors = ac.get('factors', {}) or {}
                ac_entity = ac_factors.get('entity')
                if ac_entity and ac_entity in corrected_cats:
                    entry = corrected_cats[ac_entity]
                    if entry.get('brand_type') == ac_factors.get('brand_type'):
                        ac['corrected_from_history'] = True
                        if entry.get('corrected_path'):
                            ac['suggested_path'] = [entry['corrected_path']]

        stats = category_result['stats']
        total = len(df)
        brand_missing_count = sum([c.get('count', 0) for c in brand_clusters if c.get('type') == 'missing'])
        brand_mismatch_count = sum([c.get('count', 0) for c in brand_clusters if c.get('type') == 'mismatch'])
        need_ai = brand_missing_count + brand_mismatch_count + stats['missing_count']

        lean_clusters_data = lean_clusters(brand_clusters)

        try:
            with open(filepath, 'rb') as f:
                file_hash = hashlib.md5(f.read()).hexdigest()[:12]
        except Exception as e:
            logger.error(f"Failed to compute file hash: {e}")
            file_hash = 'unknown'

        sessions[session_id] = {
            'session_id': session_id,
            'group_id': group_id,
            'file_hash': file_hash,
            'file_path': str(filepath),
            'col_mapping': col_mapping,
            'status': 'uploaded',
            'created': datetime.now(),
            'brand_rules': {},
            'new_brands': auto_new_brands,
            'confirmed_brands': [],
            'diagnosis_status': 'completed',
            'diagnosis_result': {
                'brand_clusters': lean_clusters_data,
                'conflict_groups': category_result['conflict_groups'],
                'marketing_groups': category_result['marketing_groups'],
                'standard_groups': category_result['standard_groups'],
                'missing_items': category_result['missing_items'],
                'all_codes': category_result.get('all_codes', []),
                'cleaned_paths': category_result.get('cleaned_paths', {}),
                'path_classifications': category_result.get('path_classifications', {}),
                'category_options': category_result['category_options']
            },
            'diagnosis_stats': {
                'total': int(total),
                'valid': int(total - need_ai),
                'brand_missing': int(brand_missing_count),
                'brand_mismatch': int(brand_mismatch_count),
                'marketing': int(stats['pure_marketing_count'] + stats['conflict_count']),
                'need_ai': int(need_ai)
            }
        }

        save_session_snapshots(session_id)

        return jsonify({
            'success': True,
            'session_id': session_id,
            'diagnosis': {
                'brand_clusters': brand_clusters,
                'conflict_groups': category_result['conflict_groups'],
                'marketing_groups': category_result['marketing_groups'],
                'standard_groups': category_result['standard_groups'],
                'missing_items': category_result['missing_items'],
                'all_codes': category_result.get('all_codes', []),
                'cleaned_paths': category_result.get('cleaned_paths', {}),
                'path_classifications': category_result.get('path_classifications', {}),
                'category_options': category_result['category_options']
            },
            'stats': {
                'total': int(total),
                'valid': int(total - need_ai),
                'brand_missing': int(brand_missing_count),
                'brand_mismatch': int(brand_mismatch_count),
                'marketing': int(stats['pure_marketing_count'] + stats['conflict_count']),
                'need_ai': int(need_ai)
            },
            'category_options': category_result['category_options']
        })

    def _process_async_upload(df, temp_filepath, original_filename, group_id):
        """异步处理大文件"""
        session_id = f"session_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        try:
            with open(temp_filepath, 'rb') as f:
                file_hash = hashlib.md5(f.read()).hexdigest()[:12]
        except Exception as e:
            logger.error(f"Failed to compute file hash: {e}")
            file_hash = 'unknown'

        # 将临时文件重命名为正式文件名
        filename = f"{session_id}_{original_filename}"
        filepath = UPLOAD_FOLDER / filename
        temp_filepath.rename(filepath)

        # 检查文件是否保存成功
        if not filepath.exists():
            return jsonify({'error': '文件保存失败'}), 500

        file_size = filepath.stat().st_size
        if file_size == 0:
            return jsonify({'error': '保存的文件为空'}), 500

        # 验证文件完整性
        is_valid, error_msg = validate_excel_file(filepath)
        if not is_valid:
            try:
                filepath.unlink()
            except:
                pass
            return jsonify({'error': error_msg}), 400

        cols = df.columns.tolist()
        col_mapping = {}

        for col in cols:
            col_lower = col.lower()
            if 'spu_name' in col_lower or '商品名' in col_lower:
                col_mapping['org_spu_name'] = col
            elif 'brand' in col_lower or '品牌' in col_lower:
                col_mapping['brand_name'] = col
            elif 'spec' in col_lower or '规格' in col_lower:
                col_mapping['spu_spec'] = col
            elif 'cate_level1' in col_lower or '一级分类' in col_lower:
                col_mapping['cate_level1_name'] = col
            elif 'cate_level2' in col_lower or '二级分类' in col_lower:
                col_mapping['cate_level2_name'] = col
            elif 'cate_level3' in col_lower or '三级分类' in col_lower:
                col_mapping['cate_level3_name'] = col
            elif 'spu_code' in col_lower or '商品code' in col_lower or ('code' in col_lower and '商品' in col):
                col_mapping['org_spu_code'] = col
            elif 'org_image_url' in col_lower or '商品图' in col_lower or '图片' in col_lower:
                col_mapping['org_image_url'] = col

        if 'org_spu_name' not in col_mapping:
            return jsonify({'error': '缺少商品名称列'}), 400

        sessions[session_id] = {
            'session_id': session_id,
            'group_id': group_id,
            'file_hash': file_hash,
            'file_path': str(filepath),
            'col_mapping': col_mapping,
            'status': 'uploaded',
            'diagnosis_status': 'pending',
            'diagnosis_progress': 0,
            'diagnosis_logs': [],
            'created': datetime.now(),
            'brand_rules': {},
            'new_brands': [],
            'confirmed_brands': []
        }

        thread = threading.Thread(
            target=diagnose_async,
            args=(session_id, str(filepath), col_mapping)
        )
        thread.start()

        return jsonify({
            'success': True,
            'session_id': session_id,
            'async': True,
            'message': f'大文件诊断中（{file_size / 1024 / 1024:.1f}MB），请轮询 /api/diagnosis_status 获取进度'
        })

    @app.route('/api/upload_by_path', methods=['POST'])
    def upload_by_path():
        """Upload via file path (Electron native dialog)."""
        file_path = request.form.get('file_path')
        group_id = request.form.get('group_id', '')
        if not file_path or not Path(file_path).exists():
            return jsonify({'error': '文件不存在'}), 400

        original_filename = Path(file_path).name
        session_id = f"session_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        dest = UPLOAD_FOLDER / f"{session_id}_{original_filename}"
        shutil.copy2(file_path, dest)

        try:
            df = pd.read_excel(dest, engine='openpyxl')
            df = df.replace({np.nan: None})
        except Exception as e:
            try: dest.unlink()
            except: pass
            return jsonify({'error': f'文件读取失败: {str(e)}'}), 400

        # Reuse the same logic as upload_file
        cols = df.columns.tolist()
        col_mapping = {}
        for col in cols:
            col_lower = col.lower()
            if 'spu_name' in col_lower or '商品名' in col_lower:
                col_mapping['org_spu_name'] = col
            elif 'brand' in col_lower or '品牌' in col_lower:
                col_mapping['brand_name'] = col
            elif 'spec' in col_lower or '规格' in col_lower:
                col_mapping['spu_spec'] = col
            elif 'cate_level1' in col_lower or '一级分类' in col_lower:
                col_mapping['cate_level1_name'] = col
            elif 'cate_level2' in col_lower or '二级分类' in col_lower:
                col_mapping['cate_level2_name'] = col
            elif 'cate_level3' in col_lower or '三级分类' in col_lower:
                col_mapping['cate_level3_name'] = col
            elif 'org_image_url' in col_lower or '商品图' in col_lower or '图片' in col_lower:
                col_mapping['org_image_url'] = col

        if 'org_spu_name' not in col_mapping:
            try: dest.unlink()
            except: pass
            return jsonify({'error': '缺少商品名称列'}), 400

        file_size = dest.stat().st_size
        if len(df) > 1000 or (file_size > 10 * 1024 * 1024 and len(df) > 100):
            # Large file: async
            sessions[None] = None  # placeholder
            session_id = f"session_{int(time.time())}_{uuid.uuid4().hex[:6]}"
            del sessions[None]

            sessions[session_id] = {
                'session_id': session_id,
                'group_id': group_id,
                'file_path': str(dest),
                'col_mapping': col_mapping,
                'status': 'uploaded',
                'diagnosis_status': 'pending',
                'diagnosis_progress': 0,
                'diagnosis_logs': [],
                'created': datetime.now(),
                'brand_rules': {},
                'new_brands': [],
                'confirmed_brands': [],
                'review_pending': [],
                'logs': [],
                'ai_logs': [],
            }

            try:
                with open(dest, 'rb') as f:
                    file_hash = hashlib.md5(f.read()).hexdigest()[:12]
            except Exception:
                file_hash = 'unknown'
            sessions[session_id]['file_hash'] = file_hash

            thread = threading.Thread(
                target=diagnose_async,
                args=(session_id, str(dest), col_mapping)
            )
            thread.start()

            return jsonify({
                'success': True,
                'session_id': session_id,
                'async': True,
                'message': f'大文件诊断中（{file_size / 1024 / 1024:.1f}MB）',
            })
        else:
            # Small file: trigger async diagnosis then return
            session_id = f"session_{int(time.time())}_{uuid.uuid4().hex[:6]}"
            try:
                with open(dest, 'rb') as f:
                    file_hash = hashlib.md5(f.read()).hexdigest()[:12]
            except Exception:
                file_hash = 'unknown'

            sessions[session_id] = {
                'session_id': session_id,
                'group_id': group_id,
                'file_hash': file_hash,
                'file_path': str(dest),
                'col_mapping': col_mapping,
                'status': 'uploaded',
                'diagnosis_status': 'pending',
                'diagnosis_progress': 0,
                'diagnosis_logs': [],
                'created': datetime.now(),
                'brand_rules': {},
                'new_brands': [],
                'confirmed_brands': [],
                'review_pending': [],
                'logs': [],
                'ai_logs': [],
            }

            thread = threading.Thread(
                target=diagnose_async,
                args=(session_id, str(dest), col_mapping)
            )
            thread.start()

            return jsonify({
                'success': True,
                'session_id': session_id,
                'async': True,
                'message': '文件已上传，正在诊断中...'
            })

    @app.route('/api/recent_files')
    def get_recent_files():
        """获取最近上传的文件"""
        # 构建 file_path → group_name 映射（从活跃 session）
        file_group = {}
        for sid, sess in sessions.items():
            fp = sess.get('file_path', '')
            if fp:
                file_group[Path(fp).name] = sess.get('group_id', '')

        files = []
        if UPLOAD_FOLDER.exists():
            for f in UPLOAD_FOLDER.iterdir():
                if f.is_file() and f.suffix.lower() in ['.xlsx', '.xls']:
                    gid = file_group.get(f.name, '')
                    group_name = _groups_cache.get(gid, {}).get('name', '') if gid else ''
                    files.append({
                        'id': f.name,
                        'name': f.name.split('_', 1)[1] if '_' in f.name else f.name,
                        'time': datetime.fromtimestamp(f.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                        'mtime': f.stat().st_mtime,
                        'group_name': group_name
                    })
        files.sort(key=lambda x: x['mtime'], reverse=True)
        return jsonify(files[:5])

    @app.route('/api/import_recent', methods=['POST'])
    def import_recent_file():
        """从已有文件导入"""
        data = request.json
        file_id = data.get('file_id')
        if not file_id:
            return jsonify({'error': '缺少 file_id'}), 400
        
        filepath = UPLOAD_FOLDER / file_id
        if not filepath.exists():
            return jsonify({'error': '文件不存在'}), 404
        
        try:
            # 简单读取以确认列
            df = pd.read_excel(filepath, engine='openpyxl')
            cols = df.columns.tolist()
            col_mapping = {}
            for col in cols:
                col_lower = col.lower()
                if 'spu_name' in col_lower or '商品名' in col_lower:
                    col_mapping['org_spu_name'] = col
                elif 'brand' in col_lower or '品牌' in col_lower:
                    col_mapping['brand_name'] = col
                elif 'spec' in col_lower or '规格' in col_lower:
                    col_mapping['spu_spec'] = col
                elif 'cate_level1' in col_lower or '一级分类' in col_lower:
                    col_mapping['cate_level1_name'] = col
                elif 'cate_level2' in col_lower or '二级分类' in col_lower:
                    col_mapping['cate_level2_name'] = col
                elif 'cate_level3' in col_lower or '三级分类' in col_lower:
                    col_mapping['cate_level3_name'] = col
                elif 'spu_code' in col_lower or 'code' in col_lower:
                    col_mapping['org_spu_code'] = col
                elif 'org_image_url' in col_lower or '商品图' in col_lower or '图片' in col_lower:
                    col_mapping['org_image_url'] = col

            if 'org_spu_name' not in col_mapping:
                return jsonify({'error': '缺少商品名称列'}), 400

            # 检查是否已有该文件的进行中诊断，避免重复触发
            for sid, sess in list(sessions.items()):
                if sess.get('file_path') == str(filepath) and sess.get('diagnosis_status') == 'processing':
                    created = _get_session_created(sess)
                    if created and (datetime.now() - created) > SESSION_PROCESSING_TIMEOUT:
                        # 诊断超时，视为失效，清理后重新诊断
                        logger.warning(f"Session {sid} processing timed out, re-diagnosing")
                        _remove_session(sid)
                        break
                    return jsonify({
                        'success': True,
                        'session_id': sid,
                        'async': True,
                        'message': '该文件正在诊断中，复用已有 session'
                    })

            # 走异步诊断流程
            session_id = f"session_{int(time.time())}_{uuid.uuid4().hex[:6]}"
            try:
                with open(filepath, 'rb') as f:
                    file_hash = hashlib.md5(f.read()).hexdigest()[:12]
            except Exception as e:
                logger.error(f"Failed to compute file hash for import: {e}")
                file_hash = 'unknown'
            # 优先使用请求中的 group_id，其次复用已有 session 的 group_id
            req_group_id = data.get('group_id', '')
            imp_group_id = req_group_id or (existing.get('group_id', '') if existing else '')
            sessions[session_id] = {
                'session_id': session_id,
                'group_id': imp_group_id,
                'file_hash': file_hash,
                'file_path': str(filepath),
                'col_mapping': col_mapping,
                'status': 'uploaded',
                'diagnosis_status': 'pending',
                'diagnosis_progress': 0,
                'diagnosis_logs': [],
                'created': datetime.now(),
                'brand_rules': {},
                'new_brands': [],
                'confirmed_brands': []
            }
            
            thread = threading.Thread(
                target=diagnose_async,
                args=(session_id, str(filepath), col_mapping)
            )
            thread.start()
            
            return jsonify({
                'success': True,
                'session_id': session_id,
                'async': True,
                'message': '正在重新分析历史文件...'
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 400

    @app.route('/api/diagnosis_status')
    def get_diagnosis_status():
        """获取诊断进度"""
        session_id = request.args.get('sid')

        if session_id not in sessions:
            return jsonify({'error': '会话不存在'}), 404

        session = sessions[session_id]

        from datetime import datetime
        start_time = session.get('start_time')
        elapsed = round((datetime.now() - start_time).total_seconds(), 1) if start_time else 0

        return jsonify({
            'status': session.get('diagnosis_status', 'pending'),
            'progress': session.get('diagnosis_progress', 0),
            'logs': session.get('diagnosis_logs', []),
            'message': session.get('diagnosis_logs', [''])[-1] if session.get('diagnosis_logs') else '准备中...',
            'step_times': session.get('step_times', {}),
            'elapsed': elapsed,
            'current_step': session.get('current_step', ''),
            'current_step_start': session.get('current_step_start', 0)
        })

    @app.route('/api/diagnosis_result')
    def get_diagnosis_result():
        """获取诊断结果"""
        session_id = request.args.get('sid')

        if session_id not in sessions:
            return jsonify({'error': '会话不存在'}), 404

        session = sessions[session_id]

        if session.get('diagnosis_status') != 'completed':
            return jsonify({'error': '诊断未完成'}), 400

        logger.info(f"get_diagnosis_result [{session_id}]: session keys={list(session.keys())}, has diagnosis_result={'diagnosis_result' in session}")

        diagnosis_result = session.get('diagnosis_result')
        if not diagnosis_result:
            return jsonify({'error': '诊断结果数据不完整，请重新诊断'}), 400

        return jsonify({
            'success': True,
            'diagnosis': diagnosis_result,
            'stats': session.get('diagnosis_stats', {}),
            'category_options': diagnosis_result.get('category_options', {})
        })

    @app.route('/api/rules/save', methods=['POST'])
    def save_rules():
        data = request.json
        session_id = data.get('session_id')
        rules = data.get('rules', {})

        # 合并保存品牌规则和分类规则
        cache_manager.set_rules(_get_group_id(session_id), session_id, rules)

        # 持久化分类确认到全局 corrected_products.json
        from ..brands.database import batch_save_corrected_products
        categories = rules.get('categories', {})
        cat_updates = {}
        for code, rule in categories.items():
            if rule.get('action') == 'confirm' and rule.get('replacement'):
                cat_updates[code] = {'category': rule['replacement']}
        if cat_updates:
            batch_save_corrected_products(_get_group_id(session_id), cat_updates)

        # 如果有营销标记，同步到 Session
        if session_id in sessions and 'marketing_tags' in rules:
            sessions[session_id]['marketing_tags'] = rules['marketing_tags']

        mark_snapshot_dirty(session_id)
        return jsonify({'success': True})

    @app.route('/api/rules/get')
    def get_rules():
        """获取已保存的分类规则"""
        session_id = request.args.get('sid')
        if not session_id:
            return jsonify({'categories': {}, 'marketing_tags': {}})
        rules = cache_manager.get_rules(_get_group_id(session_id), session_id)
        return jsonify({
            'categories': rules.get('categories', {}),
            'marketing_tags': rules.get('marketing_tags', {})
        })

    # ── 分组管理 API ──

    @app.route('/api/groups', methods=['GET'])
    def list_groups():
        return jsonify({'groups': _groups_cache})

    @app.route('/api/groups', methods=['POST'])
    def create_group():
        data = request.json
        name = (data.get('name') or '').strip()
        if not name:
            return jsonify({'error': '分组名称不能为空'}), 400
        group_id = uuid.uuid4().hex[:8]
        _groups_cache[group_id] = {
            'name': name,
            'created': datetime.now().isoformat(),
            'description': (data.get('description') or '').strip()
        }
        _save_groups(_groups_cache)
        _ensure_group_dir(group_id)
        return jsonify({'success': True, 'group_id': group_id, 'name': name})

    @app.route('/api/groups/<group_id>', methods=['PUT'])
    def update_group(group_id):
        if group_id not in _groups_cache:
            return jsonify({'error': '分组不存在'}), 404
        data = request.json
        if 'name' in data:
            _groups_cache[group_id]['name'] = data['name'].strip()
        if 'description' in data:
            _groups_cache[group_id]['description'] = (data.get('description') or '').strip()
        _save_groups(_groups_cache)
        return jsonify({'success': True})

    @app.route('/api/groups/<group_id>', methods=['DELETE'])
    def delete_group(group_id):
        if group_id not in _groups_cache:
            return jsonify({'error': '分组不存在'}), 404
        del _groups_cache[group_id]
        _save_groups(_groups_cache)
        return jsonify({'success': True})

    # ── Session 快照 ──

    @app.route('/api/session/snapshot')
    def api_session_snapshot():
        """强制触发 Session 镜像保存"""
        save_session_snapshots()
        return jsonify({'success': True})

    @app.route('/api/brand_rules/save', methods=['POST'])
    def save_brand_rules():
        """保存品牌编辑规则"""
        data = request.json
        session_id = data.get('session_id')
        code = data.get('code')
        rule_type = data.get('type')  # 'set_brand', 'no_brand', 'skip', 'confirm_valid'
        brand = data.get('brand')

        # 将别名解析为标准品牌名
        if brand:
            from ..brands.database import find_any_brand
            resolved = find_any_brand(brand)
            if resolved['found']:
                brand = resolved['standard_name']

        if session_id not in sessions:
            return jsonify({'error': '会话不存在'}), 404

        session = sessions[session_id]

        if 'brand_rules' not in session:
            session['brand_rules'] = {}

        if rule_type == 'set_brand':
            session['brand_rules'][code] = {'brand': brand, 'no_brand': False, 'skipped': False}
        elif rule_type == 'no_brand':
            session['brand_rules'][code] = {'brand': None, 'no_brand': True, 'skipped': False}
        elif rule_type == 'skip':
            session['brand_rules'][code] = {'brand': None, 'no_brand': False, 'skipped': True}
        elif rule_type == 'confirm_valid':
            session['brand_rules'][code] = {'brand': brand, 'confirmed': True, 'skipped': False}

        # 持久化所有规则到 corrected_products.json
        from ..brands.database import save_corrected_product
        save_corrected_product(_get_group_id(session_id), code, session['brand_rules'][code])

        mark_snapshot_dirty(session_id)
        return jsonify({'success': True, 'code': code, 'rule': session['brand_rules'][code]})

    @app.route('/api/brand_rules/batch_save', methods=['POST'])
    def batch_save_brand_rules():
        """批量保存品牌编辑规则"""
        data = request.json
        session_id = data.get('session_id')
        rules = data.get('rules', [])  # [{code, type, brand}, ...]

        if session_id not in sessions:
            return jsonify({'error': '会话不存在'}), 404

        session = sessions[session_id]

        if 'brand_rules' not in session:
            session['brand_rules'] = {}

        from ..brands.database import batch_save_corrected_products, find_any_brand
        batch_updates = {}
        for rule in rules:
            code = rule.get('code')
            rule_type = rule.get('type')
            brand = rule.get('brand')

            # 将别名解析为标准品牌名
            if brand:
                resolved = find_any_brand(brand)
                if resolved['found']:
                    brand = resolved['standard_name']

            if rule_type == 'set_brand':
                session['brand_rules'][code] = {'brand': brand, 'no_brand': False, 'skipped': False}
                batch_updates[code] = {'brand': brand, 'no_brand': False, 'skipped': False}
            elif rule_type == 'no_brand':
                session['brand_rules'][code] = {'brand': None, 'no_brand': True, 'skipped': False}
                batch_updates[code] = {'brand': None, 'no_brand': True, 'skipped': False}
            elif rule_type == 'skip':
                session['brand_rules'][code] = {'brand': None, 'no_brand': False, 'skipped': True}
                batch_updates[code] = {'brand': None, 'no_brand': False, 'skipped': True}
            elif rule_type == 'confirm_valid':
                session['brand_rules'][code] = {'brand': brand, 'confirmed': True, 'skipped': False}
                batch_updates[code] = {'brand': brand, 'confirmed': True, 'skipped': False}

        if batch_updates:
            batch_save_corrected_products(_get_group_id(session_id), batch_updates)

        mark_snapshot_dirty(session_id)
        return jsonify({'success': True, 'count': len(rules)})

    @app.route('/api/brand_rules/get')
    def get_brand_rules():
        """获取品牌编辑规则（含跨 session 持久化的规则）"""
        session_id = request.args.get('sid')

        if session_id not in sessions:
            return jsonify({'error': '会话不存在'}), 404

        session = sessions[session_id]
        from ..brands.database import load_corrected_products
        brand_rules = dict(session.get('brand_rules', {}))
        confirmed = load_corrected_products(_get_group_id(session_id))
        for code, rule in confirmed.items():
            if code not in brand_rules:
                brand_rules[code] = rule

        return jsonify({
            'brand_rules': brand_rules,
            'new_brands': [b for b in session.get('new_brands', []) if not b.get('confirmed')],
            'confirmed_brands': session.get('confirmed_brands', [])
        })

    @app.route('/api/brands/check', methods=['POST'])
    def check_brand_exists():
        """检查品牌是否已在品牌库中"""
        brand_name = request.json.get('brand_name', '').strip()
        if not brand_name:
            return jsonify({'exists': False})
        from ..brands.database import find_any_brand, BRAND_DATABASE_V6
        result = find_any_brand(brand_name)
        if result['found']:
            info = BRAND_DATABASE_V6.get(result['standard_name'], {})
            return jsonify({
                'exists': True,
                'standard_name': result['standard_name'],
                'existing_aliases': info.get('aliases', []),
                'match_type': result['match_type']
            })
        return jsonify({'exists': False})

    @app.route('/api/brands/add', methods=['POST'])
    def add_new_brand():
        """添加或更新新品牌（支持保留元数据和改名）"""
        import re
        data = request.json
        session_id = data.get('session_id')
        brand_name = data.get('brand_name')
        old_name = data.get('old_name') # 可选：用于改名逻辑
        aliases = data.get('aliases', [])
        brand_type = data.get('brand_type', '未知')
        country = data.get('country', 'CN')
        confirm_to_library = data.get('confirm_to_library', False)
        parent_brand = data.get('parent_brand', '')
        relation_type = data.get('relation_type', '')

        if session_id and session_id in sessions:
            session = sessions[session_id]
        else:
            session = {'new_brands': []}
            if session_id: sessions[session_id] = session

        if 'new_brands' not in session:
            session['new_brands'] = []

        # 查找现有条目
        target_brand = None
        
        # 1. 优先尝试用 old_name 匹配（改名场景）
        if old_name:
            for b in session['new_brands']:
                if b['name'] == old_name:
                    target_brand = b
                    break
        
        # 2. 否则按当前名字匹配（更新场景）
        if not target_brand:
            for b in session['new_brands']:
                if b['name'] == brand_name:
                    target_brand = b
                    break

        # === 斜杠品牌自动处理 ===
        original_brand_name = brand_name
        is_slash_brand = '/' in brand_name or '／' in brand_name
        
        if is_slash_brand:
            parts = re.split(r'[/／]', brand_name)
            english_part = parts[0].strip()
            chinese_part = parts[1].strip() if len(parts) > 1 else english_part
            brand_name = chinese_part
            auto_aliases = list(set([chinese_part, english_part, original_brand_name]))
            aliases = list(set(auto_aliases + aliases))
            from ..brands.patterns import add_slash_pattern
            add_slash_pattern(original_brand_name, chinese_part, english_part)

        if target_brand:
            target_brand.update({
                'name': brand_name,
                'aliases': aliases,
                'type': brand_type,
                'country': country,
                'parent_brand': parent_brand,
                'relation_type': relation_type,
                'confirmed': confirm_to_library or target_brand.get('confirmed', False),
                'is_slash_brand': is_slash_brand
            })
            if target_brand.get('suggested_name') == brand_name:
                target_brand['suggested_name'] = None
            brand_info = target_brand
        else:
            brand_info = {
                'name': brand_name,
                'aliases': aliases,
                'type': brand_type,
                'country': country,
                'parent_brand': parent_brand,
                'relation_type': relation_type,
                'confirmed': confirm_to_library,
                'is_slash_brand': is_slash_brand
            }
            session['new_brands'].append(brand_info)

        # 入库逻辑
        if confirm_to_library:
            from ..brands.database import add_brand, find_any_brand
            already_exists = find_any_brand(brand_name)['found']
            if not already_exists or parent_brand:
                add_brand(brand_name, aliases, brand_type, country,
                          parent_brand=parent_brand, relation_type=relation_type)
        else:
            already_exists = False

        mark_snapshot_dirty(session_id)
        return jsonify({'success': True, 'brand': brand_info, 'already_exists': already_exists})

    @app.route('/api/new_brands/dismiss', methods=['POST'])
    def dismiss_new_brand():
        """从待确认列表中移除标记为「不是品牌」的项"""
        data = request.json
        session_id = data.get('session_id')
        brand_name = data.get('brand_name')

        if session_id and session_id in sessions:
            session = sessions[session_id]
            session['new_brands'] = [b for b in session.get('new_brands', []) if b.get('name') != brand_name]

        # 持久化已忽略品牌
        from ..brands.database import save_dismissed_brand
        save_dismissed_brand(brand_name)

        mark_snapshot_dirty(session_id)
        return jsonify({'success': True})

    @app.route('/api/dismissed_brands', methods=['GET'])
    def get_dismissed_brands():
        """获取已忽略品牌列表"""
        from ..brands.database import load_dismissed_brands
        return jsonify({'dismissed_brands': load_dismissed_brands()})

    @app.route('/api/classify/path', methods=['POST'])
    def classify_path():
        """标记分类路径为 marketing/standard"""
        data = request.json
        path = data.get('path', '').strip()
        label = data.get('label', '')
        if not path or label not in ('marketing', 'standard'):
            return jsonify({'error': '参数无效'}), 400
        from ..categories.classified_paths import save_classified_path
        save_classified_path(path, label)
        return jsonify({'success': True})

    @app.route('/api/classify/path', methods=['DELETE'])
    def delete_classify_path():
        """移除路径标记"""
        data = request.json
        path = data.get('path', '').strip()
        if not path:
            return jsonify({'error': '参数无效'}), 400
        from ..categories.classified_paths import delete_classified_path
        delete_classified_path(path)
        return jsonify({'success': True})

    @app.route('/api/classify/path/batch', methods=['POST'])
    def batch_classify_paths():
        """批量标记分类路径为 marketing/standard"""
        data = request.json
        paths = data.get('paths', [])
        label = data.get('label', '')
        if not paths or label not in ('marketing', 'standard'):
            return jsonify({'error': '参数无效'}), 400
        from ..categories.classified_paths import save_classified_path
        for path in paths:
            save_classified_path(path, label)
        return jsonify({'success': True, 'count': len(paths)})

    @app.route('/api/classified_paths', methods=['GET'])
    def get_classified_paths():
        """获取所有已分类路径标记"""
        from ..categories.classified_paths import load_classified_paths
        return jsonify({'classified_paths': load_classified_paths()})

    @app.route('/api/classify/reclassify', methods=['POST'])
    def reclassify_missing_items():
        """剔除已标记营销的分类路径，重新为缺失商品建议分类"""
        from ..categories.classified_paths import load_classified_paths
        session_obj = sessions.get(request.json.get('session_id', ''))
        if not session_obj or 'diagnosis_result' not in session_obj:
            return jsonify({'error': '会话不存在'}), 400

        diagnosis = session_obj['diagnosis_result']
        missing_items = diagnosis.get('missing_items', [])
        category_options = diagnosis.get('category_options', {})
        cleaned_paths = diagnosis.get('cleaned_paths', {})

        # 构建 entity_dict
        names = [item.get('name', '') for item in diagnosis.get('all_codes', []) if item.get('name')]
        entity_dict = build_entity_dict(names)

        updated = 0
        for item in missing_items:
            suggested, confidence, factors = CategoryDetector.suggest_category(
                item.get('name', ''), category_options,
                cleaned_paths, entity_dict
            )
            if suggested and suggested != ((item.get('suggested_path') or [''])[0]):
                item['suggested_path'] = [suggested]
                item['suggested_confidence'] = confidence
                item['factors'] = factors
                updated += 1

        # 同步更新 all_codes
        missing_codes = {item['code'] for item in missing_items}
        for item in diagnosis.get('all_codes', []):
            if item['code'] in missing_codes:
                for mi in missing_items:
                    if mi['code'] == item['code']:
                        item['suggested_path'] = mi['suggested_path']
                        break

        return jsonify({
            'success': True,
            'updated_count': updated,
            'missing_items': missing_items,
            'all_codes': diagnosis.get('all_codes', [])
        })

    @app.route('/api/suggest_category', methods=['POST'])
    def suggest_missing_category():
        """为缺失分类商品推荐分类路径"""
        data = request.json
        name = data.get('name', '')
        brand_type = data.get('brand_type', '')
        options = data.get('options', {})
        from ..core.category_detector import CategoryDetector
        from ..core.lexicon import NOT_BRAND_CATEGORIES

        # 收集品种词库
        variety_words = set()
        for cat, words in NOT_BRAND_CATEGORIES.get('variety', {}).items():
            if isinstance(words, dict):
                for sub, wlist in words.items():
                    for w in (wlist if isinstance(wlist, list) else [wlist]):
                        if isinstance(w, str):
                            variety_words.add(w)
                    if isinstance(wlist, dict):
                        for sw, swlist in wlist.items():
                            for w in (swlist if isinstance(swlist, list) else [swlist]):
                                if isinstance(w, str):
                                    variety_words.add(w)
            elif isinstance(words, list):
                variety_words.update(w for w in words if isinstance(w, str))

        # 商品所在code的标准路径商品数统计（从当前诊断数据）
        from collections import Counter
        path_counter = Counter()
        for code, items in data.get('all_codes', {}).items():
            for p in items.get('standard_paths', []):
                path_counter[p] += 1

        suggested, confidence, factors = CategoryDetector.suggest_category(name, options, path_counter, brand_type, list(variety_words))
        return jsonify({'suggested': suggested, 'confidence': confidence, 'factors': factors})

    @app.route('/api/brands/list')
    def get_brands_list():
        """获取品牌列表（返回完整信息，包含斜杠模式，统一排序）"""
        from ..brands.database import BRAND_DATABASE_V6, get_all_brands
        from ..brands.patterns import get_slash_pattern_by_chinese
        
        brands = []
        for name in get_all_brands():
            info = BRAND_DATABASE_V6[name]
            slash_pattern = get_slash_pattern_by_chinese(name)
            
            # 预计算显示名称：优先使用斜杠模式的第一个完整名，否则使用主名
            display_name = slash_pattern[0] if slash_pattern else name
            
            brands.append({
                'name': name,
                'display_name': display_name,
                'type': info.get('type', '未知'),
                'country': info.get('country', 'CN'),
                'aliases': info.get('aliases', []),
                'slash_pattern': list(slash_pattern) if slash_pattern else None,
                'has_sub_brands': 'sub_brands' in info,
                'sub_brands': list(info.get('sub_brands', {}).keys())
            })
        
        # 统一按 display_name 排序，不再偏袒斜杠品牌
        brands.sort(key=lambda b: b['display_name'].lower())
        
        return jsonify({
            'brands': brands,
            'count': len(brands)
        })

    @app.route('/api/brands/config')
    def get_brand_config():
        """获取品牌配置（类型列表+国家列表）"""
        from ..brands.database import get_brand_config as load_config
        try:
            return jsonify(load_config())
        except Exception as e:
            return jsonify({'brand_types': ['食品','饮料','零食'], 'countries': [{'code':'CN','name':'中国'}], 'error': str(e)})

    @app.route('/api/brands/config/type', methods=['POST'])
    def add_brand_type():
        """新增品牌类型"""
        from ..brands.database import add_brand_type as add_type
        data = request.json
        type_name = data.get('type', '').strip()
        if not type_name:
            return jsonify({'success': False, 'error': '类型名称不能为空'})
        ok = add_type(type_name)
        return jsonify({'success': ok})

    @app.route('/api/brands/config/type', methods=['DELETE'])
    def delete_brand_type():
        """删除品牌类型"""
        from ..brands.database import delete_brand_type as del_type
        data = request.json
        type_name = data.get('type', '').strip()
        del_type(type_name)
        return jsonify({'success': True})

    @app.route('/api/brands/config/country', methods=['POST'])
    def add_country():
        """新增国家"""
        from ..brands.database import add_country as add_country_fn
        data = request.json
        code = data.get('code', '').strip().upper()
        name = data.get('name', '').strip()
        if not code or not name:
            return jsonify({'success': False, 'error': '国家代码和名称不能为空'})
        ok = add_country_fn(code, name)
        return jsonify({'success': ok})

    @app.route('/api/brands/config/country', methods=['DELETE'])
    def delete_country():
        """删除国家"""
        from ..brands.database import delete_country as del_country_fn
        data = request.json
        code = data.get('code', '').strip().upper()
        del_country_fn(code)
        return jsonify({'success': True})

    @app.route('/api/correction/brand', methods=['POST'])
    def save_brand_correction():
        """保存品牌建议修正记录"""
        data = request.json
        suggested = data.get('suggested', '').strip()
        corrected_to = data.get('corrected_to', '').strip()
        sample = data.get('sample', {})
        if suggested and corrected_to:
            from ..brands.database import save_corrected_brand
            save_corrected_brand(suggested, corrected_to, sample)
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': '参数不完整'}), 400

    @app.route('/api/correction/category', methods=['POST'])
    def save_category_correction():
        """保存分类建议修正记录"""
        data = request.json
        record = {
            'entity': data.get('entity', ''),
            'brand_type': data.get('brand_type', ''),
            'modifiers': data.get('modifiers', []),
            'suggested_path': data.get('suggested_path', ''),
            'corrected_path': data.get('corrected_path', ''),
            'samples': data.get('samples', []),
            'count': 1,
            'corrected_at': __import__('datetime').datetime.now().isoformat()
        }
        entity = record['entity']
        if entity and record['corrected_path']:
            from ..brands.database import save_corrected_category
            save_corrected_category(entity, record)
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': '参数不完整'}), 400

    @app.route('/api/correction/product', methods=['POST'])
    def save_product_correction():
        """保存商品修正记录（品牌/分类）到 corrected_products.json"""
        data = request.json
        code = data.get('code', '').strip()
        if not code:
            return jsonify({'success': False, 'error': '缺少 code'}), 400
        from ..brands.database import save_corrected_product
        rule = {}
        if data.get('name'):
            rule['name'] = data['name']
        if data.get('category'):
            rule['category'] = data['category']
        if data.get('brand'):
            rule['brand'] = data['brand']
        if rule:
            save_corrected_product(_get_group_id(session_id), code, rule)
        return jsonify({'success': True})

    @app.route('/api/brands/export-to-library', methods=['POST'])
    def export_brands_to_library():
        """将动态品牌合并到 database.py"""
        data = request.json or {}
        sid = data.get('session_id')

        # 立即持久化到磁盘（防止写数据库代码导致数据丢失）
        save_session_snapshots(sid)

        from ..brands.database import export_to_database_py
        count = export_to_database_py()
        if count >= 0:
            return jsonify({'success': True, 'count': count})
        else:
            return jsonify({'success': False, 'error': '导出失败'})

    @app.route('/api/brands/dynamic', methods=['GET'])
    def get_dynamic_brands():
        """获取所有动态品牌（过滤掉已在源码中的）"""
        import re
        from pathlib import Path
        from ..brands.database import get_all_dynamic_brands
        dyn = get_all_dynamic_brands()
        if not dyn:
            return jsonify({'brands': {}})
        # 读取 database.py 源码中的品牌名
        db_file = Path(__file__).parent.parent / 'brands' / 'database.py'
        content = db_file.read_text(encoding='utf-8')
        end_marker = '\n}\n\n\n# === 动态品牌持久化 ==='
        insert_pos = content.find(end_marker)
        if insert_pos == -1:
            return jsonify({'brands': dyn})
        static_part = content[:insert_pos]
        existing_names = set(re.findall(r"'([^']+)':\s*\{", static_part))
        existing_names.update(re.findall(r'"([^"]+)":\s*\{', static_part))
        new_only = {k: v for k, v in dyn.items() if k not in existing_names}
        return jsonify({'brands': new_only})

    @app.route('/api/preview')
    def get_preview():
        session_id = request.args.get('sid')

        if session_id not in sessions:
            return jsonify({'error': '会话不存在'}), 404

        session = sessions[session_id]

        try:
            df = pd.read_excel(session['file_path'])
            df = df.replace({np.nan: None})

            rules = cache_manager.get_rules(_get_group_id(session_id), session_id)
            df = StandardizationEngine.apply_rules(df, session['col_mapping'], rules)

            name_col = session['col_mapping'].get('org_spu_name')
            brand_col = session['col_mapping'].get('brand_name')
            spec_col = session['col_mapping'].get('spu_spec')
            cate1_col = session['col_mapping'].get('cate_level1_name')
            cate2_col = session['col_mapping'].get('cate_level2_name')
            cate3_col = session['col_mapping'].get('cate_level3_name')
            code_col = session['col_mapping'].get('org_spu_code')

            brand_rules = session.get('brand_rules', {})

            preview = []
            counts = {'standardized': 0, 'valid': 0, 'need_ai': 0, 'error': 0}

            for idx, row in df.iterrows():
                name = str(row.get(name_col, '')).strip()
                brand = str(row.get(brand_col, '')).strip() if brand_col and row.get(brand_col) else ''
                spec = str(row.get(spec_col, '')).strip() if spec_col and row.get(spec_col) else ''
                cate1 = str(row.get(cate1_col, '')).strip() if cate1_col and row.get(cate1_col) else ''
                cate2 = str(row.get(cate2_col, '')).strip() if cate2_col and row.get(cate2_col) else ''
                cate3 = str(row.get(cate3_col, '')).strip() if cate3_col and row.get(cate3_col) else ''
                code = str(row.get(code_col, '')).strip() if code_col else ''

                if code and code in brand_rules:
                    rule = brand_rules[code]
                    if rule.get('no_brand'):
                        brand = ''
                    elif rule.get('brand'):
                        brand = rule['brand']

                check_result = BrandConsistencyChecker.check(name, brand)

                status = 'valid'
                status_text = '数据完整'

                if not brand or brand == 'nan':
                    status = 'need_ai'
                    status_text = '待AI处理(品牌缺失)'
                    counts['need_ai'] += 1
                elif not check_result['is_valid']:
                    status = 'brand_error'
                    status_text = f'品牌错误: {check_result["message"]}'
                    counts['error'] += 1
                elif not spec or spec == 'nan':
                    status = 'need_ai'
                    status_text = '待AI处理(规格缺失)'
                    counts['need_ai'] += 1
                else:
                    counts['valid'] += 1

                preview.append({
                    'row': idx + 2,
                    'name': name[:30],
                    'brand': brand,
                    'spec': spec,
                    'category': f'{cate1} > {cate2} > {cate3}',
                    'status': status,
                    'status_text': status_text
                })

            return jsonify({
                'preview': preview[:500],
                'standardized': int(counts['standardized']),
                'valid': int(counts['valid']),
                'need_ai': int(counts['need_ai']),
                'error': int(counts['error']),
                'total': int(len(df))
            })

        except Exception as e:
            return jsonify({'error': str(e)}), 400

    @app.route('/api/process', methods=['POST'])
    def start_process():
        data = request.json
        session_id = data.get('session_id')
        providers = data.get('providers', [])
        batch_size = data.get('batch_size', 20)
        ai_provider = data.get('provider')  # gemini / claude / openai / deepseek
        api_key = data.get('api_key')
        model_id = data.get('model_id')
        force_reanalyze = data.get('force_reanalyze', False)

        if session_id not in sessions:
            return jsonify({'error': '会话不存在'}), 404

        thread = threading.Thread(
            target=process_file_async,
            args=(session_id, providers, batch_size, ai_provider, api_key, model_id, force_reanalyze)
        )
        thread.start()

        return jsonify({'success': True})

    @app.route('/api/process/cancel', methods=['POST'])
    def cancel_process():
        """取消 AI 处理（仅设标志，状态由线程自行切换）"""
        data = request.json
        session_id = data.get('session_id')
        if session_id in sessions:
            sessions[session_id]['cancel_requested'] = True
        return jsonify({'success': True})

    @app.route('/api/ai_logs')
    def get_ai_logs():
        """获取 AI 处理增量日志（consumed 模式）"""
        session_id = request.args.get('sid')
        if session_id not in sessions:
            return jsonify({'logs': []})

        session = sessions[session_id]
        logs = list(session.get('ai_logs', []))
        session['ai_logs'] = []  # 消费后清空
        return jsonify({'logs': logs})

    @app.route('/api/status')
    def get_status():
        session_id = request.args.get('sid')

        if session_id not in sessions:
            return jsonify({'error': '会话不存在'}), 404

        session = sessions[session_id]

        return jsonify({
            'status': session.get('status', 'uploaded'),
            'progress': session.get('progress', 0),
            'total': session.get('total', 0),
            'ai_total': session.get('ai_total', 0),
            'ai_skipped': session.get('ai_skipped', 0),
            'ai_total_brand': session.get('ai_total_brand', 0),
            'ai_total_category': session.get('ai_total_category', 0),
            'ai_skipped_brand': session.get('ai_skipped_brand', 0),
            'ai_skipped_category': session.get('ai_skipped_category', 0),
            'processed': session.get('processed', 0),
            'message': session.get('message', ''),
            'logs': session.get('logs', []),
            'review_pending': len(session.get('review_pending', [])),
            'review_file': session.get('review_file'),
            'result_file': session.get('result_file')
        })

    @app.route('/api/download')
    def download_file():
        session_id = request.args.get('sid')
        file_type = request.args.get('type')

        if session_id not in sessions:
            return jsonify({'error': '会话不存在'}), 404

        session = sessions[session_id]

        if file_type == 'result':
            filepath = session.get('result_file')
        elif file_type == 'review':
            filepath = session.get('review_file')
        elif file_type == 'complete':
            filepath = RESULT_FOLDER / f"{session_id}_complete.xlsx"
        else:
            return jsonify({'error': '无效类型'}), 400

        if not filepath or not Path(filepath).exists():
            return jsonify({'error': '文件不存在'}), 404

        return send_file(filepath, as_attachment=True)

    @app.route('/api/review/data')
    def get_review_data():
        session_id = request.args.get('sid')

        if session_id not in sessions:
            return jsonify({'data': []})

        session = sessions[session_id]
        review_file = session.get('review_file')

        if not review_file or not Path(review_file).exists():
            return jsonify({'data': []})

        try:
            df = pd.read_excel(review_file)
            df = df.replace({np.nan: None})

            # 返回字段映射: JSON key → Excel 列名（按优先级查找）
            FIELD_MAP = [
                ('code', ['code']),
                ('name', ['name', 'org_spu_name']),
                ('original_brand', ['brand_name']),
                ('brand_ai', ['brand_ai']),
                ('brand_type', ['brand_type']),
                ('brand_confidence', ['brand_confidence']),
                ('brand_status', ['brand_status']),
                ('brand_reason', ['brand_reason']),
                ('spec_original', ['spu_spec']),
                ('spec_from_name', ['spec_from_name']),
                ('original_category', ['category_original']),
                ('category_ai', ['category_ai']),
                ('category_confidence', ['category_confidence']),
                ('category_status', ['category_status']),
                ('category_method', ['category_method']),
                ('category_reason', ['category_reason']),
                ('category_entity', ['category_entity']),
                ('category_modifiers', ['category_modifiers']),
                ('promo_tag', ['promo_tag']),
                ('recommend_tag', ['recommend_tag']),
                ('self_operated_tag', ['self_operated_tag']),
                ('import_tag', ['import_tag']),
                ('needs_review', ['needs_review']),
                ('review_status', ['review_status']),
                # 原始标签列透传
                ('org_prom_spu_tag', ['org_prom_spu_tag']),
                ('org_new_spu_tag', ['org_new_spu_tag']),
                ('org_billboard_top', ['org_billboard_top']),
                ('org_recommend_tag', ['org_recommend_tag']),
                ('org_prom_price', ['org_prom_price']),
                ('org_image_url', ['org_image_url']),
            ]

            def _safe_get(row, col_names, default=''):
                for c in col_names:
                    if c in row.index:
                        val = row.get(c)
                        if pd.isna(val):
                            return default
                        if isinstance(val, float):
                            return val
                        return str(val) if val is not None else default
                return default

            data = []
            for _, row in df.iterrows():
                item = {}
                for json_key, col_names in FIELD_MAP:
                    if json_key in ('brand_confidence', 'category_confidence'):
                        item[json_key] = float(_safe_get(row, col_names, 0)) if _safe_get(row, col_names, 0) != '' else 0
                    elif json_key == 'needs_review':
                        item[json_key] = bool(row.get(col_names[0], True)) if col_names[0] in row.index else True
                    else:
                        item[json_key] = _safe_get(row, col_names)
                data.append(item)

            return jsonify({'data': data})
        except Exception:
            return jsonify({'data': []})

    @app.route('/api/review/decision', methods=['POST'])
    def save_review_decision():
        data = request.json
        session_id = data.get('session_id')
        code = data.get('code', data.get('idx'))
        action = data.get('action', data.get('type'))
        changes = data.get('changes', data.get('data', {}))

        # 原有 cache_manager 逻辑保留
        cache_manager.add_review(_get_group_id(session_id), session_id, code, {'action': action, 'changes': changes})

        # 更新 result_df 中的 review_status
        session = sessions.get(session_id)
        if session:
            result_file = session.get('result_file')
            if result_file and Path(result_file).exists():
                df = pd.read_excel(result_file)
                code_col = session.get('col_mapping', {}).get('org_spu_code')
                if code_col and code_col in df.columns:
                    mask = df[code_col].astype(str) == str(code)
                    if action == 'confirm':
                        df.loc[mask, 'review_status'] = '已确认'
                    elif action == 'modify':
                        df.loc[mask, 'review_status'] = '已修改'
                        for field, value in (changes or {}).items():
                            if field in df.columns:
                                df.loc[mask, field] = value
                    # 同步更新 review_file
                    review_file = session.get('review_file')
                    if review_file and Path(review_file).exists():
                        rdf = pd.read_excel(review_file)
                        if code_col and code_col in rdf.columns:
                            rmask = rdf[code_col].astype(str) == str(code)
                            if action == 'confirm':
                                rdf.loc[rmask, 'review_status'] = '已确认'
                            elif action == 'modify':
                                rdf.loc[rmask, 'review_status'] = '已修改'
                                for field, value in (changes or {}).items():
                                    if field in rdf.columns:
                                        rdf.loc[rmask, field] = value
                        rdf.to_excel(str(review_file), index=False)
                df.to_excel(str(result_file), index=False)

        return jsonify({'success': True})

    @app.route('/api/review/export')
    def export_review_final():
        session_id = request.args.get('sid')

        if not session_id:
            return jsonify({'error': '缺少session_id'}), 400

        review_cache = cache_manager.get_review(_get_group_id(session_id), session_id)

        if not review_cache:
            return jsonify({'error': '没有复核数据'}), 400

        data = []
        for idx_str, decision in review_cache.items():
            data.append({
                'idx': int(idx_str),
                'type': decision['type'],
                'name': decision['data'].get('name', ''),
                'brand': decision['data'].get('brand', ''),
                'spec': decision['data'].get('spec', ''),
                'confidence': decision['data'].get('confidence', 0.8)
            })

        df = pd.DataFrame(data)
        output_path = RESULT_FOLDER / f"{session_id}_review_final.xlsx"
        tmp_path = RESULT_FOLDER / f"{session_id}_review_final_tmp.xlsx"
        df.to_excel(str(tmp_path), index=False)
        os.replace(str(tmp_path), str(output_path))

        return send_file(output_path, as_attachment=True)

    @app.route('/api/export/custom', methods=['POST'])
    def export_custom():
        data = request.json
        session_id = data.get('sid')
        columns = data.get('columns', [])
        filter_status = data.get('filter', {}).get('review_status')

        if session_id not in sessions:
            return jsonify({'error': 'session 不存在'}), 400

        session = sessions[session_id]
        result_file = session.get('result_file')
        if not result_file or not Path(result_file).exists():
            return jsonify({'error': '结果文件不存在'}), 400

        df = pd.read_excel(result_file)

        if filter_status and 'review_status' in df.columns:
            df = df[df['review_status'] == filter_status]

        if columns:
            available = [c for c in columns if c in df.columns]
            df = df[available]

        tmp_path = RESULT_FOLDER / f"{session_id}_export_{uuid.uuid4().hex[:6]}.xlsx"
        df.to_excel(str(tmp_path), index=False)
        return send_file(str(tmp_path), as_attachment=True,
                         download_name=f"export_{session_id}.xlsx")


# 创建应用实例
app = create_app()


if __name__ == '__main__':
    print("\n" + "="*70)
    print("商品数据清理系统 V4")
    print("="*70)
    print("\n核心改进:")
    print("  ✓ 品牌聚类（去规格，包含关系不聚类）")
    print("  ✓ 品牌一致性检测（商品名不含品牌 → 错误）")
    print("  ✓ 标准化规则一次性确认，批量应用")
    print("  ✓ 三级联动分类下拉 + 搜索 + 营销标记")
    print("  ✓ 全量数据预览（含无需处理数据）")
    print("  ✓ AI结果置信度分级确认")
    print("="*70)
    print(f"\n主页: http://localhost:5001")
    print(f"复核: http://localhost:5001/review")
    print("="*70 + "\n")

    app.run(host='0.0.0.0', port=5001, debug=False, threaded=True)
