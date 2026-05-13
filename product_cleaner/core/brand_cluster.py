#!/usr/bin/env python3
"""
品牌聚类引擎

用于将相似的品牌进行聚类，发现品牌变体和标准化机会。
支持按 org_spu_code 去重，每个code只出现一次。
"""

import re
from typing import Dict, List, Optional
from collections import defaultdict

import pandas as pd
import numpy as np

from ..brands.database import BRAND_DATABASE_V6, find_brand_by_name_fast, find_sub_brand_fast
from ..constants import BRAND_SUFFIXES
from .product_parser import (
    SpecExtractor, build_entity_dict, find_entity,
    clean_product_name, strip_not_brand_words,
    strip_size_prefix, fully_not_brand, similarity,
)
from .brand_checker import BrandConsistencyChecker
from .lexicon import (
    DUAL_MEANING_BRANDS, FOOD_CATEGORY_KEYWORDS,
    NOT_BRAND_CATEGORIES, NOT_BRAND_WORDS
)


class BrandClusterEngine:
    """品牌聚类引擎 V2 - 支持按code去重"""

    @staticmethod
    def _extract_unbranded_brand(name: str, entity_dict: dict) -> tuple:
        """
        对V6无法提取品牌的商品，用实体法提取品牌候选。
        策略：识别实体→取前缀→逐层去掉描述词→剩余内容为品牌候选。
        返回: (entity, brand_prefix) 或 (entity, None)
        """
        if not name:
            return None, None
        clean = clean_product_name(name)
        chars = re.sub(r'[^一-龥]', '', clean)
        if len(chars) < 2:
            return None, None

        entity, prefix = find_entity(chars, entity_dict)

        if not prefix or len(prefix) < 2:
            return entity, None

        # 逐层去掉开头描述词
        remaining = strip_not_brand_words(prefix)

        if remaining and len(remaining) >= 2:
            stripped = strip_size_prefix(remaining)
            if stripped != remaining:
                # 去掉了大小前缀，判断剩余是否有效
                if not stripped or len(stripped) < 2 or stripped in NOT_BRAND_WORDS:
                    return entity, None
                return entity, stripped
            return entity, remaining
        return entity, None

    @staticmethod
    def cluster(df: pd.DataFrame, name_col: str, brand_col: str, code_col: Optional[str] = None, col_mapping: Dict = {}) -> List[Dict]:
        """
        聚类品牌（按code去重版本）

        输出分组类型：
          - valid:    品牌列有值且 check() 判定有效，按相似品牌名聚类
          - missing:  品牌列为空，从商品名提取到品牌候选
          - unbranded:品牌列为空，商品名中也提取不到任何品牌
          - mismatch: 品牌列有值但 check() 判定不匹配
          - valid 下含 variant: 同一商品不同行品牌名近似但不完全一致
        """
        df = df.replace({np.nan: None})

        # ===== 阶段 0：数据准备（按 code 去重） =====
        # 多个行可能有相同 code（同一商品的多规格记录），只保留第一个 data
        if code_col is None or code_col not in df.columns:
            df['__temp_code__'] = df.index.astype(str)
            code_col = '__temp_code__'

        code_groups = defaultdict(lambda: {'rows': [], 'data': None})

        for idx, row in df.iterrows():
            code = str(row.get(code_col, '')).strip() if row.get(code_col) else f'row_{idx}'
            code_groups[code]['rows'].append(idx + 2)
            if code_groups[code]['data'] is None:
                c1 = str(row.get(col_mapping.get('cate_level1_name', ''), '')).strip() if 'cate_level1_name' in col_mapping else ''
                c2 = str(row.get(col_mapping.get('cate_level2_name', ''), '')).strip() if 'cate_level2_name' in col_mapping else ''
                c3 = str(row.get(col_mapping.get('cate_level3_name', ''), '')).strip() if 'cate_level3_name' in col_mapping else ''
                path = f"{c1} > {c2} > {c3}" if c1 else ""

                code_groups[code]['data'] = {
                    'code': code,
                    'row': idx + 2,
                    'name': str(row.get(name_col, '')).strip(),
                    'brand': str(row.get(brand_col, '')).strip() if row.get(brand_col) else None,
                    'category_path': path,
                    'org_image_url': str(row.get(col_mapping.get('org_image_url', ''), '')).strip() if col_mapping.get('org_image_url') else ''
                }

        # 初始化四个分组容器
        valid_brand_rows = defaultdict(lambda: {'rows': [], 'examples': [], 'items': []})
        missing_brand_items = []
        mismatch_items = []
        unbranded_items = []

        # 预构建实体字典（所有商品名，用于后续提取品类词）
        all_names = [g['data']['name'] for g in code_groups.values() if g['data'] and g['data']['name']]
        entity_dict = build_entity_dict(all_names)

        # entity_candidates / temp_entity_items：暂存通过实体法提取的品牌
        # 后续二阶段验证（跨商品出现≥2次才算有效）
        entity_candidates = defaultdict(set)
        temp_entity_items = []

        # ===== 阶段 1：逐商品归类 =====
        for code, group_data in code_groups.items():
            data = group_data['data']
            name = data['name']
            brand = data['brand']
            all_rows = group_data['rows']

            # ===== 分支 1：品牌列为空 =====
            # 品牌列缺失或品牌列值是非品牌词 → 尝试从商品名提取品牌
            if not brand or brand == 'nan' or brand == '' or brand in NOT_BRAND_WORDS:
                name_clean, spec = SpecExtractor.extract(name)
                extracted = BrandConsistencyChecker._extract_from_name(name)

                if extracted and len(extracted) >= 2:
                    # ===== 子分支 1a：从商品名提取到品牌候选 =====
                    db_match = find_brand_by_name_fast(extracted) or find_sub_brand_fast(extracted)
                    # 双义品牌判断：如"苹果"既是品牌又是水果，需按分类区分
                    if db_match and extracted in DUAL_MEANING_BRANDS:
                        category_path = data.get('category_path', '')
                        if any(kw in category_path for kw in FOOD_CATEGORY_KEYWORDS):
                            db_match = None  # 食品类商品，不应用品牌库匹配
                    if db_match:
                        pass  # 品牌库匹配到 → 保留 extracted
                    else:
                        # ===== 品牌库未匹配 → 从提取结果中去除非品牌词（产地、加工等）=====
                        remaining = strip_not_brand_words(extracted)
                        # 去除非品牌词后的剩余内容校验
                        if not remaining or len(remaining) < 2:
                            extracted = None
                        elif entity_dict.get(remaining, 0) >= 1:
                            extracted = None  # 剩余部分是品类实体，非品牌
                        elif fully_not_brand(remaining):
                            extracted = None
                        elif len(remaining) >= 5 and not find_brand_by_name_fast(remaining) and not find_sub_brand_fast(remaining):
                            extracted = None  # ≥5字且不在品牌库 → 大概率不是品牌
                        else:
                            rest = strip_size_prefix(remaining)
                            if rest != remaining:
                                if not rest or len(rest) < 2 or rest in NOT_BRAND_WORDS:
                                    extracted = None
                            if rest != remaining:
                                if not rest or len(rest) < 2 or rest in NOT_BRAND_WORDS:
                                    extracted = None

                item = {
                    'code': code,
                    'row': data['row'],
                    'all_rows': all_rows,
                    'name': name,
                    'name_clean': name_clean,
                    'category_path': data.get('category_path', ''),
                    'extracted_brand': extracted,
                    'suggested_brand': extracted,
                    'spec': spec,
                    'org_image_url': data.get('org_image_url', '')
                }

                if not extracted:
                    # ===== 子分支 1b：提取器未找到品牌 =====
                    # 兜底方案：商品名逐字滑动窗口匹配品牌库
                    clean_name = clean_product_name(name)
                    name_chars = re.sub(r'[^\一-龥]', '', clean_name)
                    brand_from_name = None
                    max_n = min(15, len(name_chars))
                    for start in range(max_n):
                        for end in range(start + 2, min(start + 10, max_n) + 1):
                            substr = name_chars[start:end]
                            sub = find_sub_brand_fast(substr)
                            if sub:
                                brand_from_name = sub
                                break
                            std = find_brand_by_name_fast(substr)
                            if std:
                                # 双义品牌过滤
                                if std in DUAL_MEANING_BRANDS:
                                    category_path = data.get('category_path', '')
                                    if any(kw in category_path for kw in FOOD_CATEGORY_KEYWORDS):
                                        continue  # 食品类，跳过品牌库匹配
                                brand_from_name = std
                                break
                        if brand_from_name:
                            break
                    if brand_from_name:
                        # 滑动窗口命中品牌库 → 作为品牌候选
                        item['extracted_brand'] = brand_from_name
                        item['suggested_brand'] = brand_from_name
                        item['brand_source'] = 'name_match'
                        missing_brand_items.append(item)
                        continue

                    # ===== 子分支 1c：品牌库滑动窗口也未命中 =====
                    # 用实体法：识别实体（品类词）→ 取实体前的文字作为品牌候选
                    entity, prefix = BrandClusterEngine._extract_unbranded_brand(name, entity_dict)
                    if prefix and len(prefix) >= 2:
                        # 实体法提取到品牌候选 → 暂存，待二阶段验证
                        item['extracted_brand'] = prefix
                        item['suggested_brand'] = prefix
                        item['entity'] = entity
                        item['brand_source'] = 'entity'
                        entity_candidates[prefix].add(entity)
                        temp_entity_items.append(item)
                        continue
                    else:
                        # 完全提取不到任何品牌 → 标记为无品牌
                        item['entity'] = entity
                        item['suggested_brand'] = None
                        item['brand_source'] = 'unbranded'
                        unbranded_items.append(item)
                        continue

                # 提取到品牌候选（子分支 1a）→ 入 missing 组
                missing_brand_items.append(item)
                continue

            # ===== 分支 2：品牌列有值 → 用 check() 校验 =====
            check_result = BrandConsistencyChecker.check(name, brand)

            if not check_result['is_valid']:
                # ===== 子分支 2a：check() 判定无效 =====
                extracted = check_result.get('extracted_brand')

                if check_result.get('issue_type') == 'mismatch':
                    # 品牌不匹配：品牌列值与商品名不一致
                    if extracted and fully_not_brand(extracted):
                        suggested = None  # 提取到的也是非品牌词 → 无建议
                    else:
                        suggested = extracted
                    mismatch_items.append({
                        'code': code,
                        'row': data['row'],
                        'all_rows': all_rows,
                        'name': name,
                        'brand': brand,
                        'category_path': data.get('category_path', ''),
                        'issue_type': 'mismatch',
                        'extracted_brand': extracted,
                        'suggested_brand': suggested,
                        'message': check_result.get('message', ''),
                        'org_image_url': data.get('org_image_url', '')
                    })
                elif not extracted:
                    # check() 无效且未提取到品牌 → 判断品牌列值本身是否为非品牌词
                    if fully_not_brand(brand):
                        issue_type = 'unbranded_fresh'
                        unbranded_items.append({
                            'code': code,
                            'row': data['row'],
                            'all_rows': all_rows,
                            'name': name,
                            'brand': brand,
                            'category_path': data.get('category_path', ''),
                            'suggested_brand': None,
                            'issue_type': issue_type,
                            'brand_source': 'unbranded',
                            'org_image_url': data.get('org_image_url', '')
                        })
                    else:
                        # 品牌列值非空且非非品牌词，但 check() 判定无效且无提取
                        # → 归入待确认组（unverified），作为 valid 下的子类型
                        brand_clean, spec = SpecExtractor.extract(brand)
                        for suffix in BRAND_SUFFIXES:
                            brand_clean = re.sub(suffix + '$', '', brand_clean)
                        valid_brand_rows[brand_clean]['rows'].extend(all_rows)
                        valid_brand_rows[brand_clean]['examples'].append(name[:50])
                        valid_brand_rows[brand_clean]['items'].append({
                            'code': code,
                            'row': data['row'],
                            'all_rows': all_rows,
                            'name': name,
                            'brand': brand,
                            'category_path': data.get('category_path', ''),
                            'suggested_brand': brand,
                            'issue_type': 'unverified',
                            'org_image_url': data.get('org_image_url', '')
                        })
            else:
                # ===== 子分支 2b：check() 判定有效 =====
                # 品牌有效 → 去后缀后按品牌名聚类
                brand_clean, spec = SpecExtractor.extract(brand)
                for suffix in BRAND_SUFFIXES:
                    brand_clean = re.sub(suffix + '$', '', brand_clean)

                valid_brand_rows[brand_clean]['rows'].extend(all_rows)
                valid_brand_rows[brand_clean]['examples'].append(name[:50])
                valid_brand_rows[brand_clean]['items'].append({
                    'code': code,
                    'row': data['row'],
                    'all_rows': all_rows,
                    'name': name,
                    'brand': brand,
                    'category_path': data.get('category_path', ''),
                    'suggested_brand': check_result.get('extracted_brand', brand),
                    'issue_type': check_result.get('issue_type'),
                    'factors': check_result.get('factors'),
                    'org_image_url': data.get('org_image_url', '')
                })

        # ===== 阶段 2：实体法品牌二阶段验证 =====
        # 实体法提取的品牌需要跨商品出现 ≥2 次才算有效
        # 否则归入 unbranded 组
        for item in temp_entity_items:
            prefix = item['extracted_brand']
            if prefix in DUAL_MEANING_BRANDS:
                category_path = item.get('category_path', '')
                if any(kw in category_path for kw in FOOD_CATEGORY_KEYWORDS):
                    item['suggested_brand'] = None
                    item['brand_source'] = 'unbranded'
                    unbranded_items.append(item)
                    continue
            if len(entity_candidates.get(prefix, set())) >= 2:
                missing_brand_items.append(item)
            else:
                item['suggested_brand'] = None
                item['brand_source'] = 'unbranded'
                unbranded_items.append(item)

        # ===== 阶段 3：构建输出聚类 =====
        clusters = []
        cluster_id = 0

        # ===== 3a：有效品牌聚类（valid / variant）=====
        # 按相似品牌名分组（_group_similar_brands），完全一致的单独一组
        # 同一组内出现多个近似品牌名 → issue_type='variant'，以出现最多的为标准
        grouped = BrandClusterEngine._group_similar_brands(list(valid_brand_rows.keys()))

        for group in grouped:
            if len(group) == 1:
                brand = group[0]
                data = valid_brand_rows[brand]
                clusters.append({
                    'cluster_id': cluster_id,
                    'brands': [brand],
                    'suggested_standard': brand,
                    'items': data['items'],
                    'row_indices': data['rows'],
                    'count': len(data['items']),
                    'has_issue': False,
                    'issue_type': 'valid',
                    'examples': data['examples'][:5],
                    'type': 'valid'
                })
                cluster_id += 1
            else:
                all_items = []
                all_rows = []
                all_examples = []
                counts = {}

                for brand in group:
                    data = valid_brand_rows[brand]
                    all_items.extend(data['items'])
                    all_rows.extend(data['rows'])
                    all_examples.extend(data['examples'])
                    counts[brand] = len(data['items'])

                suggested = max(counts.keys(), key=lambda b: counts[b])

                clusters.append({
                    'cluster_id': cluster_id,
                    'brands': list(group),
                    'suggested_standard': suggested,
                    'items': all_items,
                    'row_indices': all_rows,
                    'count': len(all_items),
                    'counts_per_brand': counts,
                    'has_issue': False,
                    'issue_type': 'variant',
                    'examples': all_examples[:5],
                    'type': 'valid'
                })
                cluster_id += 1

        # ===== 3b：品牌缺失（missing）=====
        # 品牌列为空但提取到品牌候选 → 按建议品牌名分组
        # 无建议品牌的归为 missing_no_suggestion
        if missing_brand_items:
            missing_by_brand = defaultdict(list)
            no_suggestion_items = []

            for item in missing_brand_items:
                if item['suggested_brand']:
                    missing_by_brand[item['suggested_brand']].append(item)
                else:
                    no_suggestion_items.append(item)

            for brand, items in missing_by_brand.items():
                clusters.append({
                    'cluster_id': cluster_id,
                    'brands': [],
                    'suggested_standard': brand,
                    'items': items,
                    'row_indices': [item['row'] for item in items],
                    'count': len(items),
                    'has_issue': True,
                    'issue_type': 'missing',
                    'examples': [item['name'][:50] for item in items[:5]],
                    'type': 'missing'
                })
                cluster_id += 1

            if no_suggestion_items:
                clusters.append({
                    'cluster_id': cluster_id,
                    'brands': [],
                    'suggested_standard': None,
                    'items': no_suggestion_items,
                    'row_indices': [item['row'] for item in no_suggestion_items],
                    'count': len(no_suggestion_items),
                    'has_issue': True,
                    'issue_type': 'missing_no_suggestion',
                    'examples': [item['name'][:50] for item in no_suggestion_items[:5]],
                    'type': 'missing'
                })
                cluster_id += 1

        # ===== 3c：无品牌（unbranded）=====
        # 品牌列为空且提取不到任何品牌（或列值是非品牌词如产地/加工）
        if unbranded_items:
            clusters.append({
                'cluster_id': cluster_id,
                'brands': [],
                'suggested_standard': None,
                'items': unbranded_items,
                'row_indices': [item['row'] for item in unbranded_items],
                'count': len(unbranded_items),
                'has_issue': True,
                'issue_type': 'unbranded_fresh',
                'examples': [item['name'][:50] for item in unbranded_items[:5]],
                'type': 'unbranded'
            })
            cluster_id += 1

        # ===== 3d：品牌不匹配（mismatch）=====
        # 品牌列有值但与商品名不一致（品牌列值不在商品名中或与提取结果冲突）
        # 按建议品牌分组
        if mismatch_items:
            mismatch_by_suggestion = defaultdict(list)

            for item in mismatch_items:
                key = item['suggested_brand'] or 'unknown'
                mismatch_by_suggestion[key].append(item)

            for suggested_brand, items in mismatch_by_suggestion.items():
                clusters.append({
                    'cluster_id': cluster_id,
                    'brands': list(set([item['brand'] for item in items])),
                    'suggested_standard': suggested_brand,
                    'items': items,
                    'row_indices': [item['row'] for item in items],
                    'count': len(items),
                    'has_issue': True,
                    'issue_type': 'mismatch',
                    'examples': [item['name'][:50] for item in items[:5]],
                    'type': 'mismatch'
                })
                cluster_id += 1

        if '__temp_code__' in df.columns:
            df.drop('__temp_code__', axis=1, inplace=True)

        return clusters

    @staticmethod
    def _group_similar_brands(brands: List[str]) -> List[List[str]]:
        """
        将相似品牌分组（V7 优化版 - 分离已知/未知品牌）
        """
        groups = []
        known_brands = {}
        unknown_brands = []

        for brand in brands:
            std_brand = find_brand_by_name_fast(brand)
            if std_brand:
                if std_brand not in known_brands:
                    known_brands[std_brand] = []
                known_brands[std_brand].append(brand)
            else:
                unknown_brands.append(brand)

        for std_brand, variants in known_brands.items():
            groups.append(variants)

        used = set()
        for brand in unknown_brands:
            if brand in used:
                continue
            group = [brand]
            used.add(brand)
            for other in unknown_brands:
                if other in used:
                    continue
                if brand.lower() in other.lower() or other.lower() in brand.lower():
                    continue
                sim = similarity(brand, other)
                if sim > 0.85:
                    group.append(other)
                    used.add(other)
            groups.append(group)

        return groups
        return groups


def lean_clusters(clusters: List[Dict]) -> List[Dict]:
    """
    精简聚类数据，用于前端展示
    保留 items 字段用于编辑
    """
    lean = []
    for c in clusters:
        lean_cluster = {
            'cluster_id': c['cluster_id'],
            'brands': c['brands'],
            'suggested_standard': c['suggested_standard'],
            'count': c['count'],
            'has_issue': c['has_issue'],
            'issue_type': c['issue_type'],
            'type': c['type'],
            'examples': c['examples'][:3] if 'examples' in c else [],
            'items': c.get('items', [])  # 保留所有 items 用于编辑
        }

        lean.append(lean_cluster)
    return lean
