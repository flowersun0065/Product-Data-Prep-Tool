#!/usr/bin/env python3
"""
基础常量和配置
"""

import os
from pathlib import Path

# 基础路径
BASE_DIR = Path(__file__).parent
UPLOAD_FOLDER = BASE_DIR / 'uploads'
RESULT_FOLDER = BASE_DIR / 'results'
CACHE_FOLDER = BASE_DIR / 'cache'

# 创建必要的目录
for folder in [UPLOAD_FOLDER, RESULT_FOLDER, CACHE_FOLDER]:
    folder.mkdir(exist_ok=True)

# 文件验证配置
MIN_EXCEL_SIZE = 1024  # 最小有效 Excel 文件大小（1KB）
MAX_CENTRAL_DIR_SIZE = 1000  # 中央目录尾部最大大小（损坏文件通常只有这部分）

# 规格匹配正则
SPEC_PATTERN = r'(\d+\.?\d*)\s*(ml|毫升|ML|g|克|G|kg|千克|KG|l|升|L|oz|盎司|只|个|盒|袋|瓶|罐|包|条|支|桶|箱|片|块|份|杯|mm|厘米|cm|米|m)'

# 品牌后缀（用于清理）
BRAND_SUFFIXES = ['集团', '公司', '有限', '股份', '乳业', '食品', '酒业', '饮料', '科技', '产业', '生物', '制药']

# AI 配置
CONFIDENCE_THRESHOLD_AUTO = 0.9

# Web 配置
MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB
