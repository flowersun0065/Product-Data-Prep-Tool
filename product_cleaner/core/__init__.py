#!/usr/bin/env python3
"""
核心业务逻辑模块

包含所有商品数据清理的核心算法和引擎。
"""

from .product_parser import SpecExtractor, build_entity_dict, extract_modifiers, infer_brand_metadata
from .brand_checker import BrandConsistencyChecker
from .brand_cluster import BrandClusterEngine, lean_clusters
from .category_detector import CategoryDetector
from .standardization import StandardizationEngine
from .cache import CacheManager

__all__ = [
    'SpecExtractor',
    'BrandConsistencyChecker',
    'BrandClusterEngine',
    'CategoryDetector',
    'StandardizationEngine',
    'CacheManager',
    'lean_clusters',
    'build_entity_dict',
    'extract_modifiers',
    'infer_brand_metadata',
]
