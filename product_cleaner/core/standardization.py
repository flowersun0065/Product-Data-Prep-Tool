#!/usr/bin/env python3
"""
标准化引擎

用于应用品牌和分类的标准化规则。
"""

from typing import Dict

import pandas as pd
import numpy as np



class StandardizationEngine:
    """标准化引擎"""

    # 已知品牌别名映射（用于自动填充缺失品牌）
    KNOWN_BRAND_ALIASES = {
        '可口可乐': ['可口可乐', 'Coca-Cola', 'Coca Cola', 'cocacola'],
        '百事可乐': ['百事可乐', 'Pepsi', '百事'],
        '农夫山泉': ['农夫山泉', 'NONGFU SPRING'],
        '伊利': ['伊利', 'Yili', '伊利集团'],
        '蒙牛': ['蒙牛', 'Mengniu', '蒙牛集团'],
        '光明': ['光明', '光明乳业'],
    }

    @staticmethod
    def apply_rules(df: pd.DataFrame, col_mapping: Dict, rules: Dict) -> pd.DataFrame:
        """
        应用标准化规则 (Code 归集优化版)
        """
        df = df.copy()
        df = df.replace({np.nan: None})

        name_col = col_mapping.get('org_spu_name')
        brand_col = col_mapping.get('brand_name')
        code_col = col_mapping.get('org_spu_code')
        cate1_col = col_mapping.get('cate_level1_name')
        cate2_col = col_mapping.get('cate_level2_name')
        cate3_col = col_mapping.get('cate_level3_name')

        # 预先添加“营销标记”列
        df['marketing_tag'] = None

        # 1. 应用品牌编辑规则 (按 code)
        brand_rules = rules.get('brand_rules', {})
        if brand_rules and code_col:
            for idx, row in df.iterrows():
                code = str(row.get(code_col, '')).strip()
                if code in brand_rules:
                    rule = brand_rules[code]
                    if rule.get('no_brand'):
                        df.at[idx, brand_col] = None
                    elif rule.get('brand'):
                        df.at[idx, brand_col] = rule['brand']

        # 2. 应用分类规则 (按 code 或按 路径)
        category_rules = rules.get('categories', {}) # {code_or_path: {action, replacement}}
        marketing_tags_rule = rules.get('marketing_tags', {}) # {code: [paths]}

        for idx, row in df.iterrows():
            code = str(row.get(code_col, '')).strip()
            cate1 = str(row.get(cate1_col, "")).strip() if cate1_col else ""
            cate2 = str(row.get(cate2_col, "")).strip() if cate2_col else ""
            cate3 = str(row.get(cate3_col, "")).strip() if cate3_col else ""
            current_path = f"{cate1} > {cate2} > {cate3}" if cate1 else ""

            # 处理营销标记 (Tags)
            if code in marketing_tags_rule:
                df.at[idx, 'marketing_tag'] = " | ".join(marketing_tags_rule[code])

            # 处理分类决策
            # A. 优先查找 Code 级别的决策
            if code in category_rules:
                rule = category_rules[code]
                if rule.get('action') == 'confirm' or rule.get('action') == 'replace':
                    replacement = rule.get('replacement')
                    if replacement:
                        parts = replacement.split(' > ')
                        df.at[idx, cate1_col] = parts[0] if len(parts) > 0 else None
                        df.at[idx, cate2_col] = parts[1] if len(parts) > 1 else None
                        df.at[idx, cate3_col] = parts[2] if len(parts) > 2 else None
            
            # B. 其次查找路径级别的批量决策
            elif current_path in category_rules:
                rule = category_rules[current_path]
                if rule.get('action') == 'remove':
                    df.at[idx, cate1_col] = None
                    df.at[idx, cate2_col] = None
                    df.at[idx, cate3_col] = None
                elif rule.get('action') == 'replace':
                    replacement = rule.get('replacement')
                    if replacement:
                        parts = replacement.split(' > ')
                        df.at[idx, cate1_col] = parts[0] if len(parts) > 0 else None
                        df.at[idx, cate2_col] = parts[1] if len(parts) > 1 else None
                        df.at[idx, cate3_col] = parts[2] if len(parts) > 2 else None

        return df


    @staticmethod
    def add_brand_alias(brand_name: str, aliases: list):
        """
        添加品牌别名映射

        Args:
            brand_name: 品牌标准名称
            aliases: 别名列表
        """
        if brand_name not in StandardizationEngine.KNOWN_BRAND_ALIASES:
            StandardizationEngine.KNOWN_BRAND_ALIASES[brand_name] = aliases
        else:
            # 合并别名
            existing = set(StandardizationEngine.KNOWN_BRAND_ALIASES[brand_name])
            existing.update(aliases)
            StandardizationEngine.KNOWN_BRAND_ALIASES[brand_name] = list(existing)
