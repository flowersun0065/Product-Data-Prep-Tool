#!/usr/bin/env python3
"""
营销关键词库

用于识别营销性质的分类，这些分类通常需要被剔除或替换。
可以根据业务需求随时添加新的关键词。
"""

# 营销关键词列表
# 用于识别包含营销性质的分类路径
MARKETING_KEYWORDS = [
    # 促销活动类
    '热卖', '推荐', '新品', '特价', '促销', '限时', '爆款', '热销',
    '人气', '精选', '优惠', '折扣', '团购', '秒杀', '抢购', '直降',
    '满减', '特卖', '大促', '活动', '专场', '会场', '预售',

    # 节日节气类
    '端午', '年菜', '家宴', '招牌', '中秋', '春节', '圣诞',
    '上新', '最新', '团圆', '年货', '元宵',

    # 季节类
    '清凉', '一夏', '冬日', '暖冬', '夏日', '春季',

    # 主题营销类
    '无肉', '不欢', '养生', '健身', '减肥', '美容', '团圆',
    '本周', '本月', '今年', '今日', '热门', '必备', '首选', '经典', '周年庆','十周年',

    # 补充常用营销词
    '会员', '特惠', '福利', '省心',

    # 补充常用营销词
    '会员', '特惠', '福利', '省心',
]


def add_marketing_keyword(keyword: str):
    """
    添加新的营销关键词

    Args:
        keyword: 要添加的营销关键词
    """
    if keyword not in MARKETING_KEYWORDS:
        MARKETING_KEYWORDS.append(keyword)


def remove_marketing_keyword(keyword: str):
    """
    移除营销关键词

    Args:
        keyword: 要移除的营销关键词
    """
    if keyword in MARKETING_KEYWORDS:
        MARKETING_KEYWORDS.remove(keyword)


def is_marketing_keyword(text: str) -> bool:
    """
    检查文本是否包含营销关键词

    Args:
        text: 要检查的文本

    Returns:
        如果包含营销关键词返回 True，否则返回 False
    """
    return any(kw in text for kw in MARKETING_KEYWORDS)


def get_marketing_keywords() -> list:
    """获取所有营销关键词列表"""
    return MARKETING_KEYWORDS.copy()


def get_matching_keywords(text: str) -> list:
    """
    获取文本中匹配的所有营销关键词

    Args:
        text: 要检查的文本

    Returns:
        匹配的营销关键词列表
    """
    return [kw for kw in MARKETING_KEYWORDS if kw in text]
