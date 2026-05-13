#!/usr/bin/env python3
"""
品牌一致性检测器 V6 - 三层提取 + 置信度评分

用于检测品牌名称是否与商品名称匹配，以及从商品名称中提取品牌。
"""

import re
from functools import lru_cache
from typing import Dict, Tuple, Optional

from ..brands.database import BRAND_DATABASE_V6, find_any_brand
from ..brands.patterns import SLASH_BRAND_PATTERNS
from .product_parser import SpecExtractor, similarity


class BrandConsistencyChecker:
    """品牌一致性检测器 V6 - 三层提取 + 置信度评分"""

    @staticmethod
    def check(product_name: str, brand_name: str) -> Dict:
        """
        检查品牌名与商品名是否一致（V6 增强版）

        决策树概述（按优先级）：
          A. 品牌列为空 → 从商品名提取品牌，标记缺失
          B. 斜杠品牌 → 解析出中文名后走后续逻辑
          C. 品牌在库中 → 但仍需校验是否与商品名一致（避免库中有但商品名无关）
          D. 品牌不在库中 + 品牌列值不在商品名中 → 品牌列错误
          E. 品牌不在库中 + 品牌列值在商品名中 → 自证清白（但可能误判产地/加工词）
          F. 1-2 字品牌 → 与商品名提取结果核对
          G. 提取到品牌 → 相似度判断
          H. 兜底 → 无法确认
        """
        # ========== A. 品牌列为空 ==========
        # 品牌列没填值 → 尝试从商品名提取，无论如何都标记为缺失
        if not brand_name or brand_name.strip() == '' or brand_name == 'nan':
            extracted, conf = BrandConsistencyChecker._extract_from_name_v6(product_name)
            if extracted:
                return {
                    'is_valid': False,
                    'issue_type': 'missing',
                    'extracted_brand': extracted,
                    'confidence': conf,
                    'message': f'品牌缺失，已从商品名提取（置信度 {conf:.0%}）'
                }
            else:
                return {
                    'is_valid': False,
                    'issue_type': 'missing',
                    'extracted_brand': None,
                    'confidence': 0.3,
                    'message': '品牌缺失，无法从商品名提取'
                }

        brand_clean = brand_name.strip()

        # ========== B. 斜杠品牌处理（如"Lay's/乐事"）==========
        # 将斜杠形式的品牌解析为中文标准名，继续走后续判断
        if '/' in brand_clean or '／' in brand_clean:
            parts = re.split(r'[/／]', brand_clean)
            english_part = parts[0].strip()
            chinese_part = parts[1].strip() if len(parts) > 1 else None

            pattern = None
            for p in SLASH_BRAND_PATTERNS:
                if p[0] == brand_clean or (chinese_part and p[1] == chinese_part) or (english_part and p[2] == english_part):
                    pattern = p
                    break

            if pattern:
                chinese_brand = pattern[1]
                if chinese_brand in BRAND_DATABASE_V6:
                    return {
                        'is_valid': True,
                        'issue_type': 'valid',
                        'extracted_brand': chinese_brand,
                        'confidence': 0.95,
                        'message': f'斜杠品牌"{brand_clean}"是"{chinese_brand}"的标准形式'
                    }
                brand_clean = chinese_brand
            else:
                brand_clean = chinese_part if chinese_part else english_part

        # ========== C. 品牌在库中 ==========
        # 【关键路径】品牌在库中 → 但不代表一定匹配当前商品
        # 需要验证：品牌名或其别名是否出现在商品名中
        # 如果不出现在商品名中，说明可能是错误赋值（如"正洋"在库中但与"智利冻帝王蟹"无关）
        result = find_any_brand(brand_clean)
        if result['found']:
            if result['match_type'] == 'sub_brand':
                # 子品牌匹配：品牌列值是某个品牌的子品牌
                return {
                    'is_valid': True,
                    'issue_type': 'valid_sub_brand',
                    'extracted_brand': result['sub_brand_name'],
                    'confidence': 0.95,
                    'message': f'品牌"{brand_clean}"是"{result["standard_name"]}"的子品牌'
                }
            # 主品牌/别名匹配 → 还需核对商品名中是否出现该品牌
            std_name = result['standard_name']
            info = BRAND_DATABASE_V6.get(std_name, {})
            brand_aliases = [std_name.lower()] + [a.lower() for a in info.get('aliases', []) if isinstance(a, str)]
            name_lower = product_name.lower()
            # 如果品牌（主名+别名）不出现在商品名中，怀疑是品牌列错误
            if not any(alias in name_lower for alias in brand_aliases):
                extracted, _ = BrandConsistencyChecker._extract_from_name_v6(product_name)
                return {
                    'is_valid': False,
                    'issue_type': 'mismatch',
                    'extracted_brand': extracted,
                    'confidence': 0.60,
                    'message': f'品牌列"{brand_clean}"是已知品牌但不在商品名中'
                }
            # 品牌在库中且出现在商品名中 → 有效
            issue_type = 'valid' if result['match_type'] == 'main' else 'valid_alias'
            return {
                'is_valid': True,
                'issue_type': issue_type,
                'extracted_brand': std_name,
                'confidence': 0.95,
                'message': f'品牌"{brand_clean}"是"{std_name}"的标准名'
            }

        # ========== D. 品牌不在库中 + 不在商品名中 ==========
        # 品牌列值既不是已知品牌，也不在商品名中出现 → 错误
        if len(brand_clean) >= 2 and brand_clean.lower() not in product_name.lower():
            extracted, ext_conf = BrandConsistencyChecker._extract_from_name_v6(product_name)
            return {
                'is_valid': False,
                'issue_type': 'mismatch',
                'extracted_brand': extracted,
                'confidence': 0.60,
                'message': f'品牌列"{brand_clean}"不在商品名中'
            }

        # ========== E. 品牌不在库中 + 在商品名中 → 自证清白 ==========
        # 品牌列值在商品名中出现，但可能不是真品牌（如"智利"是产地而非品牌）
        # 此处仅做碎片验证（品牌列是否为已知品牌的碎片），不做非品牌词校验
        if len(brand_clean) >= 2 and brand_clean.lower() in product_name.lower():
            extracted, conf = BrandConsistencyChecker._extract_from_name_v6(product_name)
            # 交叉验证：提取到的品牌是否与品牌列值有包含关系
            if extracted and conf >= 0.95 and extracted.lower() != brand_clean.lower():
                if (extracted.lower() in brand_clean.lower() or
                    brand_clean.lower() in extracted.lower()):
                    return {
                        'is_valid': False,
                        'issue_type': 'mismatch',
                        'extracted_brand': extracted,
                        'confidence': 0.60,
                        'message': f'品牌列"{brand_clean}"可能是"{extracted}"的碎片'
                    }
            # 自证清白通过 → 作为新品牌候选（待后续人工确认是否真是品牌）
            return {
                'is_valid': True,
                'issue_type': 'new_brand_candidate',
                'extracted_brand': brand_clean,
                'confidence': 0.85,
                'factors': {'source': 'product_name_match', 'matched_text': brand_clean, 'product_name': product_name},
                'message': '品牌名在商品名中存在（自证清白）'
            }

        # ========== F. 1-2 字品牌：与提取结果核对 ==========
        # 短品牌名（1-2字）无法用"是否在商品名中"判断（易误判）
        # 改用提取器是否从商品名中提取到相同品牌来判断
        extracted, ext_conf = BrandConsistencyChecker._extract_from_name_v6(product_name)
        if extracted and extracted.lower() == brand_clean.lower():
            return {
                'is_valid': True,
                'issue_type': 'new_brand_candidate',
                'extracted_brand': brand_clean,
                'confidence': 0.90,
                'factors': {'source': 'extraction_match', 'matched_text': brand_clean, 'product_name': product_name},
                'message': f'品牌"{brand_clean}"与商品名提取一致'
            }

        # ========== G. 提取到品牌 → 相似度判断 ==========
        if extracted:
            sim_val = similarity(extracted, brand_clean)
            if sim_val > 0.8:
                return {
                    'is_valid': True,
                    'issue_type': 'similar',
                    'extracted_brand': extracted,
                    'confidence': 0.85,
                    'message': f'品牌"{brand_clean}"与商品名中的"{extracted}"相似'
                }
            else:
                return {
                    'is_valid': False,
                    'issue_type': 'mismatch',
                    'extracted_brand': extracted,
                    'confidence': 0.60,
                    'message': f'品牌不匹配：商品名暗示"{extracted}"，但提供"{brand_clean}"'
                }

        # ========== H. 兜底 ==========
        return {
            'is_valid': False,
            'issue_type': 'unknown',
            'extracted_brand': None,
            'confidence': 0.50,
            'message': f'无法确认品牌"{brand_clean}"是否有效'
        }

    @staticmethod
    @lru_cache(maxsize=2048)
    def _extract_from_name_v6(name: str) -> Tuple[Optional[str], float]:
        """
        V6 三层品牌提取（优化版 - 使用哈希索引）：
        1. 精准匹配（已知品牌别名）→ 0.95
        2. 位置启发式（开头 2-8 字）→ 0.85
        3. 模糊匹配（相似度）→ 0.80

        Args:
            name: 商品名称

        Returns:
            tuple: (提取的品牌名, 置信度)
        """
        if not name or len(str(name).strip()) == 0:
            return None, 0.0

        name = str(name).strip()
        name_clean, spec = SpecExtractor.extract(name)
        name_clean = re.sub(r'[（(][^）)]*[）)]?', '', name_clean).strip()
        name_clean = re.sub(r'【[^】]*】', '', name_clean).strip()
        name_lower = name_clean.lower()

        # 第 1 层：精准匹配（使用哈希索引加速）
        # 先尝试用常见分隔符切分，快速匹配
        for sep in [' ', '/', '／', '(', '（', '【', '[', '】', ']']:
            if sep in name_clean:
                parts = name_clean.split(sep)
                for part in parts:
                    prefix = part.strip()
                    if len(prefix) >= 2:
                        br = find_any_brand(prefix)
                        if br['found']:
                            return br['sub_brand_name'] if br['match_type'] == 'sub_brand' else br['standard_name'], 0.95
        
        # 检查括号内的品牌
        for bracket_pair in [('(', ')'), ('（', '）'), ('【', '】'), ('[', ']')]:
            start = name_clean.find(bracket_pair[0])
            if start != -1:
                end = name_clean.find(bracket_pair[1], start)
                if end != -1:
                    inner = name_clean[start+1:end].strip()
                    if len(inner) >= 2:
                        br = find_any_brand(inner)
                        if br['found']:
                            return br['sub_brand_name'] if br['match_type'] == 'sub_brand' else br['standard_name'], 0.90

        # 检查子品牌（整体匹配 + 前缀匹配）
        br = find_any_brand(name_clean)
        if br['found'] and br['match_type'] == 'sub_brand':
            return br['sub_brand_name'], 0.95
        for sep in [' ', '/', '／']:
            if sep in name_clean:
                prefix = name_clean.split(sep)[0].strip()
                br = find_any_brand(prefix)
                if br['found'] and br['match_type'] == 'sub_brand':
                    return br['sub_brand_name'], 0.95

        # 第 2 层：位置启发式（开头 2-8 字）
        patterns = [
            r'^([A-Za-z\u4e00-\u9fff]{2,8})\s+',
            r'^([A-Za-z\u4e00-\u9fff]{2,8})[/／]',
            r'^([A-Za-z\u4e00-\u9fff]{2,8})[\(\（]',
        ]

        for pattern in patterns:
            match = re.match(pattern, name_clean)
            if match:
                candidate = match.group(1).strip()
                if BrandConsistencyChecker._is_valid_brand_candidate(candidate):
                    br = find_any_brand(candidate)
                    if br['found']:
                        return br['sub_brand_name'] if br['match_type'] == 'sub_brand' else br['standard_name'], 0.85
                    return candidate, 0.85

        # 第 3 层：模糊匹配（使用哈希索引加速）
        # 只检查品牌标准名，不遍历所有别名
        for std_brand in BRAND_DATABASE_V6.keys():
            if std_brand.lower() in name_lower:
                return std_brand, 0.80

        return None, 0.0

    @staticmethod
    def _is_valid_brand_candidate(candidate: str) -> bool:
        """验证候选品牌是否有效"""
        if not candidate or len(candidate) < 2 or len(candidate) > 10:
            return False
        if all(c.isdigit() for c in candidate):
            return False
        if ' ' in candidate.strip():
            return False
        invalid_words = ['规格', '大小', '尺寸', '颜色', '数量', '克', '毫升', '米']
        if any(word in candidate for word in invalid_words):
            return False
        return True

    @staticmethod
    def _extract_from_name(name: str) -> Optional[str]:
        """从商品名提取品牌（兼容旧版）"""
        result, _ = BrandConsistencyChecker._extract_from_name_v6(name)
        return result

