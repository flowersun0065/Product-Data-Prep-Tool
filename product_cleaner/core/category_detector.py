#!/usr/bin/env python3
"""
分类检测引擎

用于分析分类问题：层级关系、营销标记、冲突检测等。
"""

from typing import Dict
from collections import defaultdict, Counter

import pandas as pd
import numpy as np

from ..categories.marketing_keywords import MARKETING_KEYWORDS

# 导入分类路径清洗器
from ..categories.path_cleaner import clean_paths, build_raw_paths, is_marketing

# 品种分组 → L1 关键词映射
from .lexicon import VARIETY_GROUP_L1, CATEGORY_GROUP_CN
from .product_parser import clean_product_name, clean_product_name_strict, find_entity, classify_word, SpecExtractor, extract_modifiers

class CategoryDetector:
    """分类检测引擎"""

    @staticmethod
    def _level_has_marketing(level_text: str) -> bool:
        if not level_text or level_text.strip().lower() in ('none', '', 'null'):
            return True  # None 缺失值视为无效
        return any(kw in level_text.lower() for kw in MARKETING_KEYWORDS)

    @staticmethod
    def _is_clean_standard(path: str) -> bool:
        """路径所有级都无营销词才是clean标准"""
        levels = [l.strip().lower() for l in path.split(' > ')]
        return not any(CategoryDetector._level_has_marketing(l) for l in levels)

    @staticmethod
    def _is_pure_marketing_path(path: str) -> bool:
        """逐级判断路径是否纯营销（所有级都含营销词才判营销）—— 纯算法，不读持久化标记
        与 _classify_code_paths 的逐级逻辑一致。
        注意：对外语义判断请用 is_marketing_category（优先读人工标记）"""
        if not path:
            return False
        levels = [l.strip().lower() for l in path.split(' > ')]
        return all(CategoryDetector._level_has_marketing(l) for l in levels)

    @staticmethod
    def _classify_code_paths(paths: list) -> tuple:
        """从末级逐级向上找标准路径
        每级保留非营销的候选；若该级无保留则继承上一级候选。
        从未被过滤（所有级都营销）的路径被丢弃为营销。
        返回: (standard_paths, marketing_paths)
        """
        if not paths:
            return [], []

        candidates = list(paths)
        parts_list = [p.split(' > ') for p in paths]
        max_levels = max(len(p) for p in parts_list)
        ever_filtered = False

        for level_idx in range(max_levels - 1, -1, -1):  # L3 → L2 → L1
            non_mkt = []
            for i, parts in enumerate(parts_list):
                if level_idx < len(parts):
                    if not CategoryDetector._level_has_marketing(parts[level_idx]):
                        non_mkt.append(paths[i])
            if non_mkt:
                candidates = non_mkt
                ever_filtered = True
            # 若该级无候选则继承上一级

        if not ever_filtered:
            candidates = []  # 从未被过滤 → 全部丢弃

        # 读取持久化标记，覆盖关键词判断结果
        try:
            from ..categories.classified_paths import load_classified_paths
            classified = load_classified_paths()
            for p in list(candidates):
                if p in classified and classified[p] == 'marketing':
                    candidates.remove(p)
            for p in paths:
                if p not in candidates and p in classified and classified[p] == 'standard':
                    candidates.append(p)
        except Exception:
            pass

        standard = list(candidates)
        marketing = [p for p in paths if p not in standard]
        return standard, marketing

    @staticmethod
    def analyze(df: pd.DataFrame, col_mapping: Dict, entity_dict: dict = None) -> Dict:
        """
        分析分类问题（集成 path_cleaner）
        
        逻辑:
           1. 先跑 path_cleaner.clean_paths() 得到每条code的清洗后标准路径
           2. 有清洗路径的code → 直接作为建议路径，无冲突/分裂
           3. 仅有营销路径的code → 归入 marketing_only
           4. 无任何路径的code → 归入 missing
           5. 对缺失商品，基于 entity + brand_type + 修饰词推荐路径
        """
        df = df.replace({np.nan: None})

        cate1_col = col_mapping.get('cate_level1_name')
        cate2_col = col_mapping.get('cate_level2_name')
        cate3_col = col_mapping.get('cate_level3_name')
        name_col = col_mapping.get('org_spu_name')
        code_col = col_mapping.get('org_spu_code')

        # ── 0. 构建原始路径数据 ──
        code_data = defaultdict(lambda: {
            'name': '', 'paths': set(), 'rows': [],
            'marketing_paths': set(), 'standard_paths': set(),
            'org_image_url': ''
        })
        hierarchy = defaultdict(set)
        image_col = col_mapping.get('org_image_url', '')

        for idx, row in df.iterrows():
            code = str(row.get(code_col, f"row_{idx}")).strip()
            name = str(row.get(name_col, "")).strip()
            c1 = str(row.get(cate1_col, "")).strip() if cate1_col else ""
            c2 = str(row.get(cate2_col, "")).strip() if cate2_col else ""
            c3 = str(row.get(cate3_col, "")).strip() if cate3_col else ""
            path = f"{c1} > {c2} > {c3}" if c1 and c1 != "None" else None
            
            entry = code_data[code]
            if not entry['name']: entry['name'] = name
            if not entry['org_image_url'] and image_col:
                entry['org_image_url'] = str(row.get(image_col, '')).strip()
            entry['rows'].append(idx + 2)
            if path:
                entry['paths'].add(path)
                hierarchy['level1'].add(c1)
                if c2:
                    hierarchy[c1].add(c2)
                    hierarchy[f"{c1} > {c2}"].add(c3 if c3 else "")

        # ── 1. 运行 path_cleaner 得到清洗后路径 ──
        raw_paths = build_raw_paths(df, code_col, col_mapping.get('date_code', 'date_code'),
                                     cate1_col, cate2_col, cate3_col)
        cleaned_paths = clean_paths(raw_paths)  # {path: [code1, code2, ...]}

        # 额外过滤：剔除已标记为 marketing 的路径
        # 防止 path_cleaner 模块缓存未刷新导致已标记营销的路径仍被建议
        # 统一走 load_classified_paths() 访问器（与 _classify_code_paths 一致），避免重复手写文件读取
        try:
            from ..categories.classified_paths import load_classified_paths
            classified = load_classified_paths()
            for path in list(cleaned_paths.keys()):
                if classified.get(path) == 'marketing':
                    del cleaned_paths[path]
        except Exception:
            pass

        # 反转: path→codes → code→path
        code_to_path = {}
        for path, codes in cleaned_paths.items():
            for code in codes:
                code_to_path[code] = path

        # 标记：哪些code有清洗路径（有标准路径）
        has_cleaned = set(code_to_path.keys())

        # ── 2. 区分原始路径中的营销/标准（供参考） ──
        for code, entry in code_data.items():
            for p in entry['paths']:
                if is_marketing(p):
                    entry['marketing_paths'].add(p)
                else:
                    entry['standard_paths'].add(p)

        # ── 3. 构建清洗后路径统计 ──
        cleaned_counter = Counter()
        for path, codes in cleaned_paths.items():
            cleaned_counter[path] = len(codes)

        # ── 4. 品种词库展平 ──
        variety_flat = set()
        variety_groups = {}
        try:
            from ..core.lexicon import NOT_BRAND_CATEGORIES
            raw = NOT_BRAND_CATEGORIES.get('variety', {})
            for group_name, group_words in raw.items():
                words = set()
                if isinstance(group_words, set):
                    words.update(w for w in group_words if isinstance(w, str) and len(w) >= 2)
                elif isinstance(group_words, (list, tuple)):
                    words.update(w for w in group_words if isinstance(w, str) and len(w) >= 2)
                elif isinstance(group_words, dict):
                    for sv in group_words.values():
                        if isinstance(sv, set):
                            words.update(w for w in sv if isinstance(w, str) and len(w) >= 2)
                if words:
                    variety_groups[group_name] = words
                    variety_flat.update(words)
        except Exception:
            pass

        # ── 5. 归集分类 ──
        standard_codes = []
        pure_marketing_codes = []
        missing_codes = []
        conflict_codes = []  # 保留字段，清洗后应为0

        for code, info in code_data.items():
            cleaned_path = code_to_path.get(code)
            item = {
                'code': code, 'name': info['name'],
                'all_paths': list(info['paths']),
                'marketing_paths': list(info['marketing_paths']),
                'standard_paths': list(info['standard_paths']),
                'row': info['rows'][0],
                'org_image_url': info.get('org_image_url', '')
            }

            if not info['paths']:
                missing_codes.append(item)
                continue

            if cleaned_path:
                # 有清洗路径 → 直接作为建议路径
                item['suggested_path'] = [cleaned_path]
                item['suggested_confidence'] = 1.0

                # 检查原始数据中是否既有营销又有非营销路径（仅用于参考标记）
                if info['marketing_paths'] and info['standard_paths']:
                    item['variant_paths'] = list(info['marketing_paths'])
                    conflict_codes.append(item)
                else:
                    standard_codes.append(item)
            else:
                # 无清洗路径 → 全部是营销
                item['suggested_path'] = []
                item['suggested_confidence'] = 0.0
                pure_marketing_codes.append(item)

        # ── 6. 聚类 ──
        path_to_items = defaultdict(list)
        for code, path in code_to_path.items():
            info = code_data[code]
            sec = 'standard'
            if code_data[code]['marketing_paths'] and code_data[code]['standard_paths']:
                sec = 'conflict'
            path_to_items[path].append({
                'code': code, 'name': info['name'],
                'all_paths': list(info['paths']),
                'marketing_paths': list(info['marketing_paths']),
                'standard_paths': list(info['standard_paths']),
                'suggested_path': [path],
                '_section': sec,
                'row': info['rows'][0],
                'org_image_url': info.get('org_image_url', '')
            })

        def cluster_by_path(items, path_attr='suggested_path'):
            clusters = defaultdict(list)
            for itm in items:
                paths = itm.get(path_attr, [])
                p = paths[0] if paths else "未知"
                clusters[p].append(itm)
            return sorted([{'path': p, 'count': len(v), 'items': v}
                           for p, v in clusters.items()], key=lambda x: -x['count'])

        # ── 7. 构建输出 ──
        category_options = {
            'level1': sorted(list(hierarchy['level1'])),
            'level2_by_level1': {k: sorted(list(v)) for k, v in hierarchy.items()
                                 if k != 'level1' and '>' not in k},
            'level3_by_level2': {k: sorted([v for v in v_set if v]) for k, v_set in hierarchy.items()
                                 if '>' in k}
        }

        # 基于清洗后路径构建树选项
        cleaned_hierarchy = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
        for path, cnt in cleaned_counter.items():
            parts = path.split(' > ')
            if len(parts) == 3:
                cleaned_hierarchy[parts[0]][parts[1]][parts[2]] = cnt

        cleaned_tree = {
            'level1': sorted(cleaned_hierarchy.keys()),
            'level2_by_level1': {l1: sorted(l2s.keys()) for l1, l2s in cleaned_hierarchy.items()},
            'level3_by_level2': {f'{l1} > {l2}': sorted(l3s.keys())
                                 for l1, l2s in cleaned_hierarchy.items()
                                 for l2, l3s in l2s.items()}
        }

        path_classifications = {}
        for code, entry in code_data.items():
            for p in entry['paths']:
                if p not in path_classifications:
                    path_classifications[p] = CategoryDetector.auto_classify(p)

        all_codes = []
        for code, info in code_data.items():
            cleaned_path = code_to_path.get(code)
            sec = 'missing'
            if cleaned_path:
                sec = 'conflict' if (info['marketing_paths'] and info['standard_paths']) else 'standard'
            elif info['paths']:
                sec = 'marketing'

            item = {
                'code': code, 'name': info['name'],
                'all_paths': list(info['paths']),
                'suggested_path': [cleaned_path] if cleaned_path else [],
                'marketing_paths': list(info['marketing_paths']),
                'standard_paths': list(info['standard_paths']),
                '_section': sec,
                'row': info['rows'][0],
                'org_image_url': info.get('org_image_url', '')
            }
            if info['marketing_paths'] and info['standard_paths']:
                item['variant_paths'] = list(info['marketing_paths'])
            all_codes.append(item)

        # ── 8. 为缺失商品和纯营销商品智能推荐分类（纯营销 = 无有效标准路径） ──
        need_recommend = []
        for item in missing_codes + pure_marketing_codes:
            if item.get('name'):
                need_recommend.append(item)
        if entity_dict and need_recommend:
            for item in need_recommend:
                suggested, confidence, factors = CategoryDetector.suggest_category(
                    item.get('name', ''), cleaned_tree,
                    cleaned_paths, entity_dict
                )
                if suggested:
                    item['suggested_path'] = [suggested]
                    item['suggested_confidence'] = confidence
                    item['factors'] = factors
            # 同步到 all_codes
            recommend_codes = {m['code'] for m in need_recommend if m.get('suggested_path')}
            for ac in all_codes:
                if ac['code'] in recommend_codes:
                    for mi in need_recommend:
                        if mi['code'] == ac['code'] and mi.get('suggested_path'):
                            ac['suggested_path'] = mi['suggested_path']
                            ac['suggested_confidence'] = mi.get('suggested_confidence', 0)
                            ac['factors'] = mi.get('factors')
                            break

        # 提取 factors（用于前端展示）
        if entity_dict:
            from ..core.brand_checker import BrandConsistencyChecker
            from ..core.lexicon import NOT_BRAND_CATEGORIES as NBC
            from ..brands.database import BRAND_DATABASE_V6
            _all_items = []
            for cl in [missing_codes, conflict_codes, pure_marketing_codes, standard_codes]:
                _all_items.extend(cl)
            _code_to_factors = {}
            for item in _all_items:
                if item.get('factors') or item.get('code') in _code_to_factors:
                    continue
                name = item.get('name', '')
                if not name:
                    continue
                cleaned_name = clean_product_name(name)
                chars = ''.join(c for c in cleaned_name if '\u4e00' <= c <= '\u9fff')
                if not chars:
                    continue
                # 从原始标准路径提取 L3 token 辅助 entity 排序
                known_tokens = set()
                for p in item.get('standard_paths', []):
                    l3 = p.split(' > ')[-1]
                    known_tokens.update(t for t in l3.split('/') if len(t) >= 2)
                entity, _ = find_entity(chars, entity_dict, known_tokens or None)
                brand, _ = BrandConsistencyChecker._extract_from_name_v6(name)
                brand_type = ''
                if brand:
                    binfo = BRAND_DATABASE_V6.get(brand, {})
                    if isinstance(binfo, dict):
                        brand_type = binfo.get('type', '')
                remaining = chars
                if entity:
                    remaining = remaining.replace(entity, '', 1)
                if brand:
                    brand_chars = ''.join(c for c in brand if '\u4e00' <= c <= '\u9fff')
                    if brand_chars:
                        remaining = remaining.replace(brand_chars, '', 1)
                modifiers, modifier_detail = extract_modifiers(remaining, NBC)

                entity_type = ''
                entity_subtype = ''
                if entity:
                    gk, sk = classify_word(entity, NBC)
                    entity_type = CATEGORY_GROUP_CN.get(gk, '')
                    entity_subtype = sk if sk and sk != gk else ''

                spec_weight = SpecExtractor.extract_weight_spec(name) or ''
                spec_pack = SpecExtractor.extract_pack_spec(name) or ''

                _code_to_factors[item['code']] = {
                    'entity': entity or '',
                    'entity_type': entity_type,
                    'entity_subtype': entity_subtype,
                    'brand_type': brand_type,
                    'modifiers': modifiers,
                    'modifier_detail': modifier_detail,
                    'spec_weight': spec_weight,
                    'spec_pack': spec_pack,
                }
            for cl in _all_items:
                if not cl.get('factors'):
                    f = _code_to_factors.get(cl.get('code'))
                    if f:
                        cl['factors'] = f
            for ac in all_codes:
                if not ac.get('factors'):
                    f = _code_to_factors.get(ac.get('code'))
                    if f:
                        ac['factors'] = f

        return {
            'conflict_groups': cluster_by_path([c for c in conflict_codes]),
            'marketing_groups': cluster_by_path(pure_marketing_codes, 'marketing_paths'),
            'standard_groups': cluster_by_path(standard_codes),
            'missing_items': missing_codes,
            'all_codes': all_codes,
            'cleaned_paths': dict(cleaned_paths),
            'path_classifications': path_classifications,
            'category_options': cleaned_tree,
            'stats': {
                'total_codes': len(code_data),
                'conflict_count': len(conflict_codes),
                'pure_marketing_count': len(pure_marketing_codes),
                'standard_count': len(standard_codes),
                'missing_count': len(missing_codes)
            }
        }


    @staticmethod
    def is_marketing_category(path: str) -> bool:
        """逐级判断路径是否为营销（优先读持久化标记）"""
        if not path:
            return False
        try:
            from ..categories.classified_paths import load_classified_paths
            classified = load_classified_paths()
            if path in classified:
                return classified[path] == 'marketing'
        except Exception:
            pass
        _, mkt = CategoryDetector._classify_code_paths([path])
        return len(mkt) > 0

    @staticmethod
    def auto_classify(path: str) -> dict:
        """返回路径分类信息: {label, reason, is_confirmed}
        label: 'marketing'|'standard'
        reason: 算法依据描述
        is_confirmed: 是否已有人工标记"""
        result = {'path': path, 'label': 'standard', 'reason': '', 'is_confirmed': False}
        try:
            from ..categories.classified_paths import load_classified_paths
            classified = load_classified_paths()
            if path in classified:
                result['label'] = classified[path]
                result['is_confirmed'] = True
                return result
        except Exception:
            pass
        levels = [l.strip().lower() for l in path.split(' > ')]
        mkt_levels = [l for l in levels if CategoryDetector._level_has_marketing(l)]
        if mkt_levels:
            result['label'] = 'marketing'
            result['reason'] = f'含营销词: {", ".join(mkt_levels)}'
            _, discarded = CategoryDetector._classify_code_paths([path])
            if not discarded:
                result['reason'] += ' (有标准级, 可保留)'
        return result

    @staticmethod
    def get_marketing_keywords_in_path(path: str) -> list:
        """获取分类路径中匹配的所有营销关键词"""
        return [kw for kw in MARKETING_KEYWORDS if kw in path]

    @staticmethod
    def suggest_category(product_name: str, category_options: dict,
                         cleaned_paths: dict, entity_dict: dict) -> tuple:
        """基于 entity + brand_type + 修饰词，为缺失商品推荐标准路径
        返回: (best_path, confidence, factors)
        """
        if not product_name:
            return '', 0.0, {}

        name = clean_product_name_strict(product_name)
        if not name:
            return '', 0.0, {}

        chars = ''.join(c for c in name if '\u4e00' <= c <= '\u9fff')
        if not chars:
            return '', 0.0, {}

        import re
        from ..core.brand_cluster import BrandClusterEngine
        from ..core.lexicon import NOT_BRAND_CATEGORIES as NBC
        from ..core.brand_checker import BrandConsistencyChecker
        from ..brands.database import BRAND_DATABASE_V6

        # ── Step 1: 提取 entity ──
        entity, _ = find_entity(chars, entity_dict)

        # ── Step 2: 提取 brand + brand_type ──
        brand, _ = BrandConsistencyChecker._extract_from_name_v6(product_name)
        brand_type = ''
        if brand:
            brand_info = BRAND_DATABASE_V6.get(brand, {})
            if isinstance(brand_info, dict):
                brand_type = brand_info.get('type', '')

        # ── Step 3: 提取修饰词（商品名中去除 entity 和 brand 后剩下的词） ──
        remaining = chars
        if entity:
            remaining = remaining.replace(entity, '', 1)
        if brand:
            brand_chars = ''.join(c for c in brand if '\u4e00' <= c <= '\u9fff')
            if brand_chars:
                remaining = remaining.replace(brand_chars, '', 1)
        modifiers = set()
        modifier_detail = []
        if remaining:
            mods, detail = extract_modifiers(remaining, NBC)
            modifiers = set(mods)
            modifier_detail = detail

        entity_type = ''
        entity_subtype = ''
        if entity:
            gk, sk = classify_word(entity, NBC)
            entity_type = CATEGORY_GROUP_CN.get(gk, '')
            entity_subtype = sk if sk and sk != gk else ''

        spec_weight = SpecExtractor.extract_weight_spec(product_name) or ''
        spec_pack = SpecExtractor.extract_pack_spec(product_name) or ''

        # ── Step 4: 构建候选路径（从全量分类树） ──
        candidates = []
        for l1 in category_options.get('level1', []):
            for l2 in category_options.get('level2_by_level1', {}).get(l1, []):
                for l3 in category_options.get('level3_by_level2', {}).get(f"{l1} > {l2}", []):
                    path = f"{l1} > {l2} > {l3}"
                    pop = sum(len(codes) for p, codes in cleaned_paths.items() if p == path)
                    candidates.append((path, l1, l2, l3, pop))

        if not candidates:
            return '', 0.0, {}

        # ── Step 5: 构建品种分组反向索引（涵盖所有品类词） ──
        variety_groups = {}
        for cat_key in ['variety', 'dairy_egg', 'meat', 'product_type']:
            cat_data = NBC.get(cat_key, {})
            if isinstance(cat_data, dict):
                for group_name, words in cat_data.items():
                    words_set = set()
                    if isinstance(words, (set, list)):
                        words_set.update(w for w in words if isinstance(w, str) and len(w) >= 2)
                    elif isinstance(words, dict):
                        for sub in words.values():
                            if isinstance(sub, (set, list)):
                                words_set.update(w for w in sub if isinstance(w, str) and len(w) >= 2)
                    for w in words_set:
                        variety_groups[w] = group_name
            elif isinstance(cat_data, (set, list)):
                for w in cat_data:
                    if isinstance(w, str) and len(w) >= 2:
                        variety_groups[w] = cat_key

        # ── Step 6: 综合评分 ──
        WEIGHT_ENTITY_L3 = 50
        WEIGHT_ENTITY_L2 = 30
        WEIGHT_ENTITY_L1 = 20
        WEIGHT_BRAND_L1 = 15
        WEIGHT_MOD_L3 = 5

        best_score = 0
        best_path = ''

        for path, l1, l2, l3, pop in candidates:
            score = 0

            # entity 匹配
            if entity:
                if entity in l3 or l3 in entity:
                    score += WEIGHT_ENTITY_L3
                entity_group = variety_groups.get(entity)
                if entity_group and entity_group in l2:
                    score += WEIGHT_ENTITY_L2
                elif entity in l2:
                    score += WEIGHT_ENTITY_L2 * 0.5
                if entity_group and entity_group in VARIETY_GROUP_L1:
                    mapped_l1 = VARIETY_GROUP_L1[entity_group]
                    if mapped_l1 in l1:
                        score += WEIGHT_ENTITY_L1
                elif entity in l1:
                    score += WEIGHT_ENTITY_L1 * 0.5

            # brand_type 匹配
            if brand_type:
                if brand_type in l1:
                    score += WEIGHT_BRAND_L1

            # 修饰词辅助匹配（仅 L3）
            for mod in modifiers:
                if mod in l3:
                    score += WEIGHT_MOD_L3

            # 路径热门加权
            if pop > 0:
                import math
                score = score * (1 + math.log(pop + 1) / 5)

            if score > best_score:
                best_score = score
                best_path = path

        if best_score <= 0:
            return '', 0.0, {}

        # ── 置信度 ──
        if entity and best_path:
            _, bl1, bl2, bl3, _ = next(
                (c for c in candidates if c[0] == best_path),
                ('', '', '', '', 0)
            )
            hits = 0
            total = 0
            if bl1: total += 1
            if bl2: total += 1
            if bl3: total += 1
            entity_group = variety_groups.get(entity) if entity else None
            if entity_group and entity_group in VARIETY_GROUP_L1 and VARIETY_GROUP_L1[entity_group] in bl1:
                hits += 1
            if entity_group and entity_group in bl2:
                hits += 1
            if entity in bl3 or bl3 in entity:
                hits += 1

            if hits == total and brand_type and brand_type in bl1:
                confidence = 1.0
            elif hits == total:
                confidence = 0.8
            elif hits >= 2:
                confidence = 0.5
            elif hits >= 1:
                confidence = 0.3
            else:
                confidence = 0.1
        else:
            confidence = 0.1

        factors = {}
        if entity or brand_type or modifiers:
            factors = {
                'entity': entity,
                'entity_type': entity_type,
                'entity_subtype': entity_subtype,
                'brand_type': brand_type,
                'modifiers': sorted(list(modifiers)) if modifiers else [],
                'modifier_detail': modifier_detail,
                'spec_weight': spec_weight,
                'spec_pack': spec_pack,
                'score': best_score,
                'scores_detail': {
                    'entity': WEIGHT_ENTITY_L3 if entity and (entity in l3 or l3 in entity) else 0,
                    'brand_type': WEIGHT_BRAND_L1 if brand_type and brand_type in l1 else 0,
                    'modifiers': sum(WEIGHT_MOD_L3 for m in modifiers if m in l3),
                }
            }
        return best_path, confidence, factors

