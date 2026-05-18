#!/usr/bin/env python3
"""
缓存管理器

用于管理 AI 处理缓存、复核决策缓存和规则缓存。
所有缓存按 group_id 隔离，不同分组数据互不干扰。
"""

import json
import os
import threading
from pathlib import Path
from typing import Dict, Optional

from ..constants import CACHE_FOLDER


class CacheManager:
    """缓存管理器（按 group_id 隔离）"""

    def __init__(self):
        self._ai_caches: Dict[str, Dict] = {}       # key = group_id
        self._rules_caches: Dict[str, Dict] = {}    # key = group_id
        self._review_caches: Dict[str, Dict] = {}   # key = group_id

        self.lock = threading.Lock()

    def _ai_cache_dir(self, group_id: str) -> Path:
        d = CACHE_FOLDER / 'ai_cache' / group_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _rules_cache_dir(self, group_id: str) -> Path:
        d = CACHE_FOLDER / 'rules_cache' / group_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _review_cache_dir(self, group_id: str) -> Path:
        d = CACHE_FOLDER / 'review_cache' / group_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _ai_cache_path(self, group_id: str) -> Path:
        return self._ai_cache_dir(group_id) / 'cache.json'

    def _rules_cache_path(self, group_id: str) -> Path:
        return self._rules_cache_dir(group_id) / 'rules.json'

    def _review_cache_path(self, group_id: str) -> Path:
        return self._review_cache_dir(group_id) / 'review.json'

    def _load(self, path: Path) -> Dict:
        if path.exists():
            try:
                return json.load(open(path, 'r', encoding='utf-8'))
            except Exception:
                return {}
        return {}

    def _save(self, path: Path, data: Dict):
        try:
            tmp = path.with_suffix('.tmp')
            json.dump(data, open(tmp, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
            os.replace(str(tmp), str(path))
        except Exception as e:
            print(f"Cache save error: {e}")

    # ── AI 缓存 ──

    def _load_ai_cache(self, group_id: str) -> Dict:
        if group_id not in self._ai_caches:
            path = self._ai_cache_path(group_id)
            self._ai_caches[group_id] = self._load(path)
        return self._ai_caches[group_id]

    def get_ai_cache(self, group_id: str, key: str, input_fingerprint: str = '') -> Optional[Dict]:
        """读取 AI 缓存。input_fingerprint 用于检测输入数据是否变化，不匹配则视为未命中。"""
        cache = self._load_ai_cache(group_id)
        entry = cache.get(key)
        if not entry:
            return None
        cached_fp = entry.get('_fingerprint', '')
        if input_fingerprint and cached_fp and cached_fp != input_fingerprint:
            return None  # 输入数据变了，缓存失效
        return entry.get('_data')

    def set_ai_cache(self, group_id: str, key: str, value: Dict, input_fingerprint: str = ''):
        """写入 AI 缓存，附带输入数据指纹。"""
        with self.lock:
            cache = self._load_ai_cache(group_id)
            cache[key] = {'_data': value, '_fingerprint': input_fingerprint}
            self._save(self._ai_cache_path(group_id), cache)

    # ── 规则缓存 ──

    def _load_rules_cache(self, group_id: str) -> Dict:
        if group_id not in self._rules_caches:
            path = self._rules_cache_path(group_id)
            self._rules_caches[group_id] = self._load(path)
        return self._rules_caches[group_id]

    def get_rules(self, group_id: str, session_id: str) -> Dict:
        cache = self._load_rules_cache(group_id)
        return cache.get(session_id, {})

    def set_rules(self, group_id: str, session_id: str, rules: Dict):
        with self.lock:
            cache = self._load_rules_cache(group_id)
            cache[session_id] = rules
            self._save(self._rules_cache_path(group_id), cache)

    # ── 复核缓存 ──

    def _load_review_cache(self, group_id: str) -> Dict:
        if group_id not in self._review_caches:
            path = self._review_cache_path(group_id)
            self._review_caches[group_id] = self._load(path)
        return self._review_caches[group_id]

    def get_review(self, group_id: str, session_id: str) -> Dict:
        cache = self._load_review_cache(group_id)
        return cache.get(session_id, {})

    def add_review(self, group_id: str, session_id: str, idx: int, decision: Dict):
        with self.lock:
            cache = self._load_review_cache(group_id)
            if session_id not in cache:
                cache[session_id] = {}
            cache[session_id][str(idx)] = decision
            self._save(self._review_cache_path(group_id), cache)

    # ── 清理 ──

    def clear_session(self, group_id: str, session_id: str):
        with self.lock:
            if group_id in self._rules_caches and session_id in self._rules_caches[group_id]:
                cache = self._rules_caches[group_id]
                del cache[session_id]
                self._save(self._rules_cache_path(group_id), cache)
            if group_id in self._review_caches and session_id in self._review_caches[group_id]:
                cache = self._review_caches[group_id]
                del cache[session_id]
                self._save(self._review_cache_path(group_id), cache)


# 全局缓存管理器实例
cache_manager = CacheManager()
