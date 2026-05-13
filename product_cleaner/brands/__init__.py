#!/usr/bin/env python3
"""
品牌库模块

此模块包含品牌数据库、斜杠品牌模式等数据，
可以独立维护更新。
"""

from .database import BRAND_DATABASE_V6
from .patterns import SLASH_BRAND_PATTERNS

__all__ = ['BRAND_DATABASE_V6', 'SLASH_BRAND_PATTERNS']
