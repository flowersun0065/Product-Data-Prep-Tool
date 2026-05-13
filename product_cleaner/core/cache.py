#!/usr/bin/env python3
"""
缓存管理器

用于管理 AI 处理缓存、复核决策缓存和规则缓存。
"""

import json
import os
import threading
from pathlib import Path
from typing import Dict, Optional

from ..constants import CACHE_FOLDER


class CacheManager:
    """缓存管理器"""

    def __init__(self):
        self.ai_cache_file = CACHE_FOLDER / 'ai_cache_v4.json'
        self.review_cache_file = CACHE_FOLDER / 'review_cache_v4.json'
        self.rules_cache_file = CACHE_FOLDER / 'rules_cache_v4.json'

        self.ai_cache = self._load(self.ai_cache_file)
        self.review_cache = self._load(self.review_cache_file)
        self.rules_cache = self._load(self.rules_cache_file)

        self.lock = threading.Lock()

    def _load(self, path: Path) -> Dict:
        """从文件加载缓存"""
        if path.exists():
            try:
                return json.load(open(path, 'r', encoding='utf-8'))
            except:
                return {}
        return {}

    def _save(self, path: Path, data: Dict):
        """保存缓存到文件（原子写入）"""
        try:
            tmp = path.with_suffix('.tmp')
            json.dump(data, open(tmp, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
            os.replace(str(tmp), str(path))
        except Exception as e:
            print(f"Cache save error: {e}")

    def get_ai_cache(self, key: str) -> Optional[Dict]:
        """获取 AI 处理缓存"""
        return self.ai_cache.get(key)

    def set_ai_cache(self, key: str, value: Dict):
        """设置 AI 处理缓存"""
        with self.lock:
            self.ai_cache[key] = value
            self._save(self.ai_cache_file, self.ai_cache)

    def get_rules(self, session_id: str) -> Dict:
        """获取规则缓存"""
        return self.rules_cache.get(session_id, {})

    def set_rules(self, session_id: str, rules: Dict):
        """设置规则缓存"""
        with self.lock:
            self.rules_cache[session_id] = rules
            self._save(self.rules_cache_file, self.rules_cache)

    def get_review(self, session_id: str) -> Dict:
        """获取复核决策缓存"""
        return self.review_cache.get(session_id, {})

    def add_review(self, session_id: str, idx: int, decision: Dict):
        """添加复核决策"""
        with self.lock:
            if session_id not in self.review_cache:
                self.review_cache[session_id] = {}
            self.review_cache[session_id][str(idx)] = decision
            self._save(self.review_cache_file, self.review_cache)

    def clear_session(self, session_id: str):
        """清除会话相关缓存"""
        with self.lock:
            if session_id in self.rules_cache:
                del self.rules_cache[session_id]
                self._save(self.rules_cache_file, self.rules_cache)
            if session_id in self.review_cache:
                del self.review_cache[session_id]
                self._save(self.review_cache_file, self.review_cache)


# 全局缓存管理器实例
cache_manager = CacheManager()
