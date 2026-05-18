#!/usr/bin/env python3
"""标签计算模块 — 促销/推荐/自营/进口标签的纯函数计算"""

from ..brands.database import find_any_brand, BRAND_DATABASE_V6

PROMO_KEYWORDS = ['折扣', '买赠', '换购', '前几件打折', '满赠', '满减', '特价', '限时']


def compute_promo_tag(org_prom_price='', org_recommend_tag='') -> str:
    """促销标签。org_prom_price有值→促销价；org_recommend_tag含关键词→取原文关键词。"""
    if org_prom_price:
        v = str(org_prom_price).strip()
        if v and v != '0' and v.lower() != 'nan':
            return '促销价'

    if org_recommend_tag:
        text = str(org_recommend_tag)
        for kw in PROMO_KEYWORDS:
            if kw in text:
                return kw

    return ''


def compute_recommend_tag(category_path='') -> str:
    """推荐标签。分类路径含'推荐'即打标。"""
    if category_path and '推荐' in str(category_path):
        return '推荐'
    return ''


def compute_self_operated_tag(brand_name='') -> str:
    """
    自营标签。三重判断：
    1. 品牌type=='自有品牌'
    2. 子品牌所属父品牌type=='自有品牌'
    3. 品牌为空
    """
    if not brand_name or not str(brand_name).strip():
        return '自营'

    result = find_any_brand(str(brand_name).strip())
    if not result['found']:
        return ''

    std_name = result['standard_name']
    brand_info = BRAND_DATABASE_V6.get(std_name, {})
    if brand_info.get('type') == '自有品牌':
        return '自营'

    if result['match_type'] == 'sub_brand':
        parent_info = BRAND_DATABASE_V6.get(std_name, {})
        if parent_info.get('type') == '自有品牌':
            return '自营'

    return ''


def compute_import_tag(brand_name='') -> str:
    """进口/国产标签。查品牌库country字段，非CN→进口，CN→国产。未知默认国产。"""
    if not brand_name or not str(brand_name).strip():
        return ''

    result = find_any_brand(str(brand_name).strip())
    if result['found']:
        std_name = result['standard_name']
        brand_info = BRAND_DATABASE_V6.get(std_name, {})
        country = brand_info.get('country', 'CN')
        if country and country != 'CN':
            return '进口'
        return '国产'

    return '国产'


def compute_all_tags(*, brand_name='', org_prom_price='', org_recommend_tag='',
                     category_path='') -> dict:
    """一次调用返回四个标签。brand_name为已确定的最终品牌名。"""
    return {
        'promo_tag': compute_promo_tag(org_prom_price, org_recommend_tag),
        'recommend_tag': compute_recommend_tag(category_path),
        'self_operated_tag': compute_self_operated_tag(brand_name),
        'import_tag': compute_import_tag(brand_name),
    }
