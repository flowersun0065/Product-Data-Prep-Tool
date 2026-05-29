#!/usr/bin/env python3
"""标签计算模块 — 促销/推荐/自营/进口标签的纯函数计算"""

import re

from ..brands.database import find_any_brand, BRAND_DATABASE_V6

# org_recommend_tag 中促销内容嵌在描述文本里，按格式提取
_RECOMMEND_PROMO_RE = re.compile(
    r'满\d+(?:元)?[减赠]\d+(?:元)?'            # 满49减10, 满29元赠菠萝
    r'|买[一二][赠一]'                           # 买一赠一
    r'|任选\d+件\d+\.?\d*折'                    # 任选2件9折, 任选3件8.5折
    r'|(?<!\d)\d+\.?\d*折(?!\d)'                # 8.9折（独立数字）
    r'|首件[价减]\d*(?:元)?'                     # 首件价, 首件减1元
    r'|换购'                                      # 换购
    r'|领券'                                      # 领券
    r'|新人首单价'                                # 新人首单价
    r'|前\d+件[丨｜]\s*每件省\d+(?:\.\d+)?'     # 前4件｜每件省1元
    r'|任选\d+件\d+元'                           # 任选3件79元
    r'|(?:商品)?限时特价\d+(?:\.\d+)?元'         # 限时特价26.9元, 商品限时特价199元
    r'|预售'                                      # 预售
)


# org_prom_spu_tag 非促销类关键词（排除用）
_NOT_PROMO_SPU_KEYWORDS = [
    '人回购', '人好评', '好评率',                 # 评价数据
    '近期销量',                                    # 销量趋势
    '库存紧张',                                    # 库存
    '历史低价',                                    # 历史低价
    '月回头客',                                    # 复购率
]

# org_prom_spu_tag 促销类关键词（命中即促销）
_PROMO_SPU_KEYWORDS = [
    '折,',                                         # 折扣前缀
    '减,',                                         # 满减前缀
    '赠,',                                         # 买赠前缀
    '领券',                                        # 领券
    '换购',                                        # 换购
    '首件',                                        # 首件优惠
    '新人首单价',                                  # 新人价
    '每件省',                                      # 前N件省
    '降价超',                                      # 降价
    '较昨日降',                                    # 较昨日降价
    '限时特价',                                    # 限时特价
    '送赠品',                                      # 送赠品
    '预售',                                        # 预售
]

# org_prom_spu_tag 促销类后缀/格式判断（need endswith or specific pattern）
# 这些在关键词匹配不到时作为补充判断


def _split_spu_tags(value: str) -> list:
    """将 org_prom_spu_tag 拆分为单个标签（逗号或空格分隔）"""
    parts = []
    for part in value.replace(',', ' ').split():
        part = part.strip().strip(',').strip()
        if part:
            parts.append(part)
    return parts


def _is_promo_spu_tag(tag: str) -> bool:
    """判断 org_prom_spu_tag 中的单个标签是否为促销"""
    # 排除非促销
    for kw in _NOT_PROMO_SPU_KEYWORDS:
        if kw in tag:
            return False
    if tag.startswith('月') and '人已下单' in tag:
        return False
    if tag.startswith('近') and ('天低价' in tag or '天最低价' in tag):
        return False

    # 关键词匹配促销
    for kw in _PROMO_SPU_KEYWORDS:
        if kw in tag:
            return True

    # 后缀/格式判断（关键词命中不到的情况）
    if tag.endswith('折'):
        return True
    if tag in ('减', '赠'):
        return True  # 从"减,"/"赠,"拆分后的独立标签
    if tag.startswith('每') and ('减' in tag or '赠' in tag):
        return True
    if tag.startswith('买') and '赠' in tag:
        return True
    if '第' in tag and '件' in tag and '折' in tag:
        return True
    if '满' in tag and ('减' in tag or '赠' in tag):
        return True  # 满49减10, 满29元赠菠萝
    if tag[0:1].isdigit() and '减' in tag:
        return True  # 139减40
    if '任选' in tag:
        return True  # 任选3件79元, 任选2件9折

    return False


def compute_promo_tag(org_prom_price='', org_recommend_tag='', org_prom_spu_tag='') -> str:
    """促销标签。优先级：org_prom_price数值→org_recommend_tag正则→org_prom_spu_tag分类。"""
    # 1. org_prom_price 有数值 → 促销价
    if org_prom_price:
        v = str(org_prom_price).strip()
        if v and v != '0' and v.lower() != 'nan':
            try:
                float(v)
                return '促销价'
            except ValueError:
                pass

    # 2. org_recommend_tag 正则匹配捉取促销文本
    if org_recommend_tag:
        m = _RECOMMEND_PROMO_RE.search(str(org_recommend_tag))
        if m:
            return m.group()

    # 3. org_prom_spu_tag 拆开逐标签分类判断
    if org_prom_spu_tag:
        for tag in _split_spu_tags(str(org_prom_spu_tag)):
            if _is_promo_spu_tag(tag):
                return tag

    return ''


def compute_recommend_tag(category_path='') -> str:
    """推荐标签。分类路径含'推荐'即打标。"""
    if category_path and '推荐' in str(category_path):
        return '推荐'
    return ''


def compute_self_operated_tag(brand_name='') -> str:
    """自营标签。品牌type==自有品牌 或 品牌为空。"""
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


def compute_import_tag(brand_name='', product_name='') -> str:
    """进口/国产标签。查品牌库country字段；品牌未知则检查品名。"""
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

    # 品牌库未知时检查品名
    if product_name and '进口' in str(product_name):
        return '进口'
    return '国产'


def compute_all_tags(*, brand_name='', org_prom_price='', org_recommend_tag='',
                     org_prom_spu_tag='', category_path='', product_name='') -> dict:
    """一次调用返回四个标签。brand_name为已确定的最终品牌名。"""
    return {
        'promo_tag': compute_promo_tag(org_prom_price, org_recommend_tag, org_prom_spu_tag),
        'recommend_tag': compute_recommend_tag(category_path),
        'self_operated_tag': compute_self_operated_tag(brand_name),
        'import_tag': compute_import_tag(brand_name, product_name),
    }
