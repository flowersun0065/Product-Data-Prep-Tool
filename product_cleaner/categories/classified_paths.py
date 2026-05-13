#!/usr/bin/env python3
"""
分类路径标记管理 - 持久化路径的营销/标准分类标记
"""

import json
from pathlib import Path

CLASSIFIED_PATHS_FILE = Path(__file__).parent / 'classified_paths.json'


def load_classified_paths() -> dict:
    """加载已分类的路径标记 {path: label}"""
    if CLASSIFIED_PATHS_FILE.exists():
        try:
            with open(CLASSIFIED_PATHS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_classified_path(path: str, label: str):
    """持久化路径分类标记（label: marketing/standard）"""
    data = load_classified_paths()
    data[path] = label
    with open(CLASSIFIED_PATHS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def delete_classified_path(path: str):
    """移除路径标记"""
    data = load_classified_paths()
    if path in data:
        del data[path]
    with open(CLASSIFIED_PATHS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
