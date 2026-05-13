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
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
import numpy as np
from flask import Flask, render_template_string, request, jsonify, send_file
from flask_cors import CORS

try:
    import google.generativeai as genai
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
    build_entity_dict
)
from ..core.ai_engine import ProductCleanerEngine

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

SNAPSHOT_FILE = CACHE_FOLDER / 'session_snapshots.json'

def save_session_snapshots():
    """将所有会话元数据镜像到磁盘"""
    try:
        # 保存关键元数据和诊断结果，确保重启后 session 可完整恢复
        snapshots = {}
        for sid, sess in sessions.items():
            snapshots[sid] = {
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
        tmp = SNAPSHOT_FILE.with_suffix('.tmp')
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(snapshots, f, ensure_ascii=False, indent=2)
        os.replace(str(tmp), str(SNAPSHOT_FILE))
    except Exception as e:
        logger.error(f"Save snapshots failed: {e}")

_snapshot_dirty = False
_snapshot_dirty_lock = threading.Lock()

def mark_snapshot_dirty():
    """标记 snapshot 需要刷新（轻量操作，不阻塞请求线程）"""
    global _snapshot_dirty
    with _snapshot_dirty_lock:
        _snapshot_dirty = True

def _snapshot_flusher():
    """后台定时刷写 snapshot，避免高频 IO"""
    global _snapshot_dirty
    while True:
        time.sleep(30)
        with _snapshot_dirty_lock:
            dirty = _snapshot_dirty
            _snapshot_dirty = False
        if dirty:
            save_session_snapshots()

_snapshot_flusher_thread = threading.Thread(target=_snapshot_flusher, daemon=True)
_snapshot_flusher_thread.start()

def load_session_snapshots():
    """从磁盘恢复会话"""
    if SNAPSHOT_FILE.exists():
        try:
            with open(SNAPSHOT_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for sid, sess_data in data.items():
                    sessions[sid] = sess_data
        except Exception as e:
            logger.error(f"Load snapshots failed: {e}")

# 启动时加载
load_session_snapshots()


def infer_brand_metadata(product_name: str, category_path: str) -> Dict:
    """智能推断品牌元数据"""
    metadata = {
        'type': '未知',
        'country': 'CN',
        'suggested_name': None
    }
    
    name_clean = str(product_name)
    path_clean = str(category_path).lower()
    
    # 1. 探测斜杠模式 (EN/CN 或 CN/EN)
    # 匹配开头如 "Tempo/得宝", "乐事/Lay's", "UCC/悠诗诗"
    slash_match = re.search(r'^([a-zA-Z0-9\s\'\.\&\-]+)[/／]([\u4e00-\u9fff\s]+)', name_clean)
    if not slash_match:
        slash_match = re.search(r'^([\u4e00-\u9fff\s]+)[/／]([a-zA-Z0-9\s\'\.\&\-]+)', name_clean)
    
    if slash_match:
        metadata['suggested_name'] = slash_match.group(0).strip()
    
    # 2. 推断类型 (根据分类路径关键词)
    type_map = {
        '零食': ['零食', '饼干', '膨化', '糖果', '坚果', '肉干'],
        '饮料': ['饮料', '汽水', '果汁', '饮用水', '茶饮料'],
        '乳品': ['乳品', '牛奶', '酸奶', '奶粉', '黄油', '奶酪'],
        '生鲜': ['生鲜', '水果', '蔬菜', '肉禽', '水产', '蛋'],
        '日化': ['日化', '清洁', '洗涤', '牙膏', '纸巾', '洗发', '沐浴'],
        '美妆': ['美妆', '护肤', '彩妆', '面膜', '面部'],
        '母婴': ['母婴', '婴儿', '尿裤', '童装', '玩具'],
        '酒类': ['酒', '啤酒', '红酒', '白酒', '洋酒'],
        '调味': ['调味', '酱油', '醋', '调料', '火锅底料'],
        '电器': ['电器', '生活电器', '厨房电器'],
        '电子': ['电子', '数码', '手机', '电脑'],
        '宠物': ['宠物', '猫粮', '狗粮', '宠物用品']
    }
    
    best_type = '未知'
    best_score = 0
    for b_type, keywords in type_map.items():
        score = sum(1 for kw in keywords if kw in path_clean)
        if score > best_score:
            best_score = score
            best_type = b_type
    metadata['type'] = best_type
            
    # 3. 推断国家 (根据商品名关键词)
    country_map = {
        'JP': ['日本', '日产', '进口日', '源自日本'],
        'KR': ['韩国', '韩产', '进口韩'],
        'US': ['美国', '美产', '进口美'],
        'DE': ['德国', '德产', '进口德'],
        'FR': ['法国', '法产', '进口法'],
        'AU': ['澳洲', '澳大利亚'],
        'NZ': ['新西兰'],
        'TH': ['泰国'],
        'IT': ['意大利'],
        'GB': ['英国'],
    }
    
    for code, keywords in country_map.items():
        if any(kw in name_clean for kw in keywords):
            metadata['country'] = code
            break
            
    return metadata


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
        confirmed_rules = load_corrected_products()
        for code, rule in confirmed_rules.items():
            if code not in session['brand_rules']:
                session['brand_rules'][code] = rule

        # 将已修正的分类注入分类规则缓存
        cat_rules_changed = False
        cache_rules = cache_manager.get_rules(session_id) or {}
        cat_rules = cache_rules.get('categories', {})
        for code, info in confirmed_rules.items():
            if info.get('category') and code not in cat_rules:
                cat_rules[code] = {'action': 'confirm', 'replacement': info['category']}
                cat_rules_changed = True
        if cat_rules_changed:
            cache_manager.set_rules(session_id, {**cache_rules, 'categories': cat_rules})

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
        
        save_session_snapshots()

    except Exception as e:
        logger.error(f"Diagnosis error: {e}")
        session['diagnosis_status'] = 'error'
        session['diagnosis_error'] = str(e)
        session['diagnosis_logs'].append(f"错误: {e}")


def process_file_async(session_id: str, providers: List[Dict] = None,
                       batch_size: int = 20,
                       ai_provider: str = None,
                       api_key: str = None,
                       model_id: str = None):
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

        rules = cache_manager.get_rules(session_id)
        df = StandardizationEngine.apply_rules(df, session['col_mapping'], rules)

        name_col = session['col_mapping'].get('org_spu_name')
        brand_col = session['col_mapping'].get('brand_name')
        spec_col = session['col_mapping'].get('spu_spec')
        code_col = session['col_mapping'].get('org_spu_code')
        cate1_col = session['col_mapping'].get('cate_level1_name')
        cate2_col = session['col_mapping'].get('cate_level2_name')
        cate3_col = session['col_mapping'].get('cate_level3_name')

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
                'existing_suggestion': code_suggestion.get(code, '')  # 诊断阶段的品牌建议
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

        # 分批处理需要 AI 的条目
        for batch_idx in range(0, len(need_ai_items), batch_size):
            # 检查是否被取消
            if session.get('cancel_requested'):
                session['status'] = 'cancelled'
                session['message'] = f'用户取消，已处理 {len(all_results)} 条'
                session['logs'].append(f"[{datetime.now().strftime('%H:%M:%S')}] 用户取消处理")
                break

            batch = need_ai_items[batch_idx:batch_idx + batch_size]
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
                    entry = {
                        'code': item['code'],
                        'name': item['name'],
                        'brand': ai_res['brand']['value'],
                        'spec': item['spec'],
                        'confidence': ai_res['brand']['confidence'],
                        'needs_review': ai_res.get('needs_review', False)
                    }
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
                    name = item['name']
                    extracted_spec = SpecExtractor.extract(name)[1] if spec_col else ''
                    extracted_brand = BrandConsistencyChecker._extract_from_name(name) or ''

                    entry = {
                        'code': item['code'],
                        'name': name,
                        'brand': extracted_brand or item['brand'],
                        'spec': extracted_spec or item['spec'],
                        'confidence': 0.8 if extracted_brand else 0.5,
                        'needs_review': not extracted_brand
                    }
                    batch_results.append(entry)
                    log_entry = {
                        'name': name,
                        'code': item['code'],
                        'brand': {'status': 'local', 'value': entry['brand'], 'confidence': entry['confidence']},
                        'category': {'status': 'skipped', 'path': '', 'confidence': 0.0},
                        'needs_review': entry['needs_review']
                    }
                    session['ai_logs'].append(log_entry)
                    if entry.get('needs_review'):
                        session['review_pending'].append(entry)

            all_results.extend(batch_results)
            session['processed'] = int(batch_idx + len(batch))
            session['progress'] = int(session['processed'] / len(need_ai_items) * 100) if need_ai_items else 100

            # 写入中间结果
            combined = []
            for item in skip_items:
                combined.append({
                    'code': item['code'],
                    'name': item['name'],
                    'brand': item['brand'],
                    'spec': item['spec'],
                    'confidence': 1.0,
                    'needs_review': False
                })
            combined.extend(all_results)
            if combined:
                result_df = pd.DataFrame(combined)
                result_file = RESULT_FOLDER / f"{session_id}_result.xlsx"
                result_df.to_excel(str(result_file), index=False)
                session['result_file'] = str(result_file)

            if session['review_pending']:
                review_df = pd.DataFrame(session['review_pending'])
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
            combined.append({
                'code': item['code'],
                'name': item['name'],
                'brand': item['brand'],
                'spec': item['spec'],
                'confidence': 1.0,
                'needs_review': False
            })
        combined.extend(all_results)

        # 如果被取消，不要覆盖 cancelled 状态
        if session.get('status') != 'cancelled':
            session['status'] = 'completed'
            session['progress'] = 100
            session['message'] = (
                f'处理完成! AI处理{len(need_ai_items)}条, '
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


def register_routes(app):
    """注册所有路由"""

    @app.route('/')
    def index():
        from ..templates.html_templates import HTML_TEMPLATE
        return render_template_string(HTML_TEMPLATE)

    @app.route('/review')
    def review_page():
        from ..templates.html_templates import REVIEW_TEMPLATE
        return render_template_string(REVIEW_TEMPLATE)

    @app.route('/api/upload', methods=['POST'])
    def upload_file():
        """同步上传（小文件 < 1000 行）"""
        if 'file' not in request.files:
            return jsonify({'error': '没有文件'}), 400

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
                return _process_sync_upload(df, temp_filepath, original_filename)
            else:
                # 大文件使用异步模式
                return _process_async_upload(df, temp_filepath, original_filename)

        except Exception as e:
            logger.error(f"Upload error: {e}")
            return jsonify({'error': str(e)}), 400

    def _process_sync_upload(df, temp_filepath, original_filename):
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
        confirmed_rules = load_corrected_products()
        corrected_brands = load_corrected_brands()
        corrected_cats = load_corrected_categories()

        # 将已修正的分类注入分类规则缓存
        cat_rules_changed = False
        cache_rules = cache_manager.get_rules(session_id) or {}
        cat_rules = cache_rules.get('categories', {})
        for code, info in confirmed_rules.items():
            if info.get('category') and code not in cat_rules:
                cat_rules[code] = {'action': 'confirm', 'replacement': info['category']}
                cat_rules_changed = True
        if cat_rules_changed:
            cache_manager.set_rules(session_id, {**cache_rules, 'categories': cat_rules})

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

        sessions[session_id] = {
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

        save_session_snapshots()

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

    def _process_async_upload(df, temp_filepath, original_filename):
        """异步处理大文件"""
        session_id = f"session_{int(time.time())}_{uuid.uuid4().hex[:6]}"

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

    @app.route('/api/recent_files')
    def get_recent_files():
        """获取最近上传的文件"""
        files = []
        if UPLOAD_FOLDER.exists():
            for f in UPLOAD_FOLDER.iterdir():
                if f.is_file() and f.suffix.lower() in ['.xlsx', '.xls']:
                    files.append({
                        'id': f.name,
                        'name': f.name.split('_', 1)[1] if '_' in f.name else f.name,
                        'time': datetime.fromtimestamp(f.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                        'mtime': f.stat().st_mtime
                    })
        # 按时间倒序排序
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
            for sid, sess in sessions.items():
                if sess.get('file_path') == str(filepath) and sess.get('diagnosis_status') == 'processing':
                    return jsonify({
                        'success': True,
                        'session_id': sid,
                        'async': True,
                        'message': '该文件正在诊断中，复用已有 session'
                    })

            # 走异步诊断流程
            session_id = f"session_{int(time.time())}_{uuid.uuid4().hex[:6]}"
            sessions[session_id] = {
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
        cache_manager.set_rules(session_id, rules)

        # 持久化分类确认到全局 corrected_products.json
        from ..brands.database import batch_save_corrected_products
        categories = rules.get('categories', {})
        cat_updates = {}
        for code, rule in categories.items():
            if rule.get('action') == 'confirm' and rule.get('replacement'):
                cat_updates[code] = {'category': rule['replacement']}
        if cat_updates:
            batch_save_corrected_products(cat_updates)

        # 如果有营销标记，同步到 Session
        if session_id in sessions and 'marketing_tags' in rules:
            sessions[session_id]['marketing_tags'] = rules['marketing_tags']

        mark_snapshot_dirty()
        return jsonify({'success': True})

    @app.route('/api/rules/get')
    def get_rules():
        """获取已保存的分类规则"""
        session_id = request.args.get('sid')
        if not session_id:
            return jsonify({'categories': {}, 'marketing_tags': {}})
        rules = cache_manager.get_rules(session_id)
        return jsonify({
            'categories': rules.get('categories', {}),
            'marketing_tags': rules.get('marketing_tags', {})
        })

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
        save_corrected_product(code, session['brand_rules'][code])

        mark_snapshot_dirty()
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
            batch_save_corrected_products(batch_updates)

        mark_snapshot_dirty()
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
        confirmed = load_corrected_products()
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

        mark_snapshot_dirty()
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

        mark_snapshot_dirty()
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
            save_corrected_product(code, rule)
        return jsonify({'success': True})

    @app.route('/api/brands/export-to-library', methods=['POST'])
    def export_brands_to_library():
        """将动态品牌合并到 database.py"""
        data = request.json or {}
        sid = data.get('session_id')

        # 立即持久化到磁盘（防止写数据库代码导致数据丢失）
        save_session_snapshots()

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

            rules = cache_manager.get_rules(session_id)
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

        if session_id not in sessions:
            return jsonify({'error': '会话不存在'}), 404

        thread = threading.Thread(
            target=process_file_async,
            args=(session_id, providers, batch_size, ai_provider, api_key, model_id)
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

            data = []
            for idx, row in df.iterrows():
                data.append({
                    'name': str(row.get('name', '')),
                    'brand': str(row.get('brand', '')),
                    'spec': str(row.get('spec', '')),
                    'confidence': float(row.get('confidence', 0.8)),
                    'needs_review': bool(row.get('needs_review', True))
                })

            return jsonify({'data': data})
        except:
            return jsonify({'data': []})

    @app.route('/api/review/decision', methods=['POST'])
    def save_review_decision():
        data = request.json
        session_id = data.get('session_id')
        idx = data.get('idx')
        type_ = data.get('type')
        item_data = data.get('data')

        cache_manager.add_review(session_id, idx, {'type': type_, 'data': item_data})

        return jsonify({'success': True})

    @app.route('/api/review/export')
    def export_review_final():
        session_id = request.args.get('sid')

        if not session_id:
            return jsonify({'error': '缺少session_id'}), 400

        review_cache = cache_manager.get_review(session_id)

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
