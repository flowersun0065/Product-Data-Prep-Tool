#!/usr/bin/env python3
"""
商品名称底层拆解器

集中管理所有商品名称的底层拆解方法，包括：
 - 商品名清理（去规格、去标点、去括号）
 - 规格提取（容量、重量、数量等）
 - 实体识别（品类词识别：建词典 + 匹配 + 兜底）
 - 品牌/文字去噪（非品牌词剥离、大小前缀剔除、完整校验）
 - 字符串工具（编辑距离相似度）

供 brand_checker、brand_cluster、category_detector 等业务引擎使用。
不包含任何业务决策逻辑（如品牌一致性检测、品牌聚类、分类推荐）。
"""

import re
from typing import Dict, List, Tuple, Optional
from collections import defaultdict

import jieba

from .lexicon import (SPEC_UNITS_PATTERN, NOT_BRAND_WORDS, SIZE_PREFIXES,
    WEIGHT_UNITS_PATTERN, PACK_UNITS_PATTERN, CATEGORY_GROUP_CN,
    NOT_BRAND_CATEGORIES as _NBC, TYPE_MAP, COUNTRY_MAP)


def infer_brand_metadata(product_name: str, category_path: str) -> Dict:
    """从商品名和分类路径推断品牌元数据（类型、国家、斜杠模式）"""
    metadata = {
        'type': '未知',
        'country': 'CN',
        'suggested_name': None
    }

    name_clean = str(product_name)
    path_clean = str(category_path).lower()

    # 1. 探测斜杠模式 (EN/CN 或 CN/EN)
    slash_match = re.search(r'^([a-zA-Z0-9\s\'\.\&\-]+)[/／]([一-鿿\s]+)', name_clean)
    if not slash_match:
        slash_match = re.search(r'^([一-鿿\s]+)[/／]([a-zA-Z0-9\s\'\.\&\-]+)', name_clean)

    if slash_match:
        metadata['suggested_name'] = slash_match.group(0).strip()

    # 2. 推断类型（根据分类路径关键词）
    best_type = '未知'
    best_score = 0
    for b_type, keywords in TYPE_MAP.items():
        score = sum(1 for kw in keywords if kw in path_clean)
        if score > best_score:
            best_score = score
            best_type = b_type
    metadata['type'] = best_type

    # 3. 推断国家（根据商品名关键词）
    for code, keywords in COUNTRY_MAP.items():
        if any(kw in name_clean for kw in keywords):
            metadata['country'] = code
            break

    return metadata


# ====================================================================
# 常量
# ====================================================================

SPEC_PATTERN = r'(\d+\.?\d*)\s*(' + SPEC_UNITS_PATTERN + r')'
WEIGHT_SPEC_PATTERN = r'(\d+\.?\d*)\s*(' + WEIGHT_UNITS_PATTERN + r')'
PACK_SPEC_PATTERN = r'(\d+\.?\d*)\s*(' + PACK_UNITS_PATTERN + r')'


# ====================================================================
# 商品名清理
# ====================================================================

def clean_product_name(name: str) -> str:
    """清理商品名：去规格、去营销标签、去括号内容，保留中英文数字"""
    if not name:
        return ''
    name = re.sub(r'【[^】]*】', '', name)
    name = re.sub(r'[（(][^）)]*[）)]', '', name)
    name = re.sub(r'\d+\.?\d*\s*' + SPEC_UNITS_PATTERN + r'(?:[^a-zA-Z]|$)', '', name)
    name = re.sub(r'\s+', ' ', name)
    name = re.sub(r'^[\s\-_—_，,、，。]+|[\s\-_—_，,、，。]+$', '', name)
    return name.strip()


def clean_product_name_strict(name: str) -> str:
    """严格清理商品名：去规格、去标点、去数字单位，仅保留中文字"""
    if not name:
        return ''
    name = re.sub(r'[（(][^）)]*[）)]', '', name)
    name = re.sub(r'\d+\.?\d*\s*' + SPEC_UNITS_PATTERN + r'(?:[^a-zA-Z]|$)', '', name)
    name = re.sub(r'【[^】]*】', '', name)
    name = re.sub(r'[-\s_，,、，。]+', ' ', name)
    name = re.sub(r'[^一-鿿\s]', '', name)
    return name.strip().lower()


# ====================================================================
# 规格提取
# ====================================================================

class SpecExtractor:
    """规格提取器"""

    @staticmethod
    def extract(text: str) -> Tuple[str, Optional[str]]:
        """
        从文本中提取规格，返回(清理后文本, 规格)

        Args:
            text: 输入文本

        Returns:
            tuple: (清理后的文本, 提取的规格或None)
        """
        if not text:
            return text, None

        match = None
        for m in re.finditer(SPEC_PATTERN, text, re.IGNORECASE):
            match = m  # 取最后一个匹配（真实规格通常在末尾，如"260g"）
        if match:
            spec = match.group(0)
            cleaned = text.replace(spec, '').strip()
            cleaned = re.sub(r'\s+', ' ', cleaned)
            cleaned = re.sub(r'^[\s\-\_\(\)\【】]+|[\s\-\_\(\)\【】]+$', '', cleaned)
            return cleaned, spec

        return text.strip(), None

    @staticmethod
    def extract_all_specs(text: str) -> list:
        """从文本中提取所有规格信息"""
        if not text:
            return []
        matches = re.findall(SPEC_PATTERN, text, re.IGNORECASE)
        return [f"{m[0]}{m[1]}" for m in matches]

    @staticmethod
    def has_spec(text: str) -> bool:
        """检查文本是否包含规格信息"""
        if not text:
            return False
        return bool(re.search(SPEC_PATTERN, text, re.IGNORECASE))

    @staticmethod
    def extract_weight_spec(text: str) -> Optional[str]:
        """提取克重/计量规格（如 260g, 500ml, 5kg），取最后一个匹配"""
        if not text:
            return None
        match = None
        for m in re.finditer(WEIGHT_SPEC_PATTERN, text, re.IGNORECASE):
            match = m
        return match.group(0) if match else None

    @staticmethod
    def extract_pack_spec(text: str) -> Optional[str]:
        """提取计价/包装规格（如 2个, 4粒, 1盒），取最后一个匹配"""
        if not text:
            return None
        match = None
        for m in re.finditer(PACK_SPEC_PATTERN, text, re.IGNORECASE):
            match = m
        return match.group(0) if match else None


# ====================================================================
# 实体识别
# ====================================================================

def build_entity_dict(names: List[str]) -> dict:
    """
    从商品名列表中构建实体词典。

    核心思路：商品的品类词（实体）通常出现在名称末尾。
    例如"智利冻帝王蟹"的实体是"帝王蟹"，"盐磨三去鲍鱼肉"的实体是"鲍鱼肉"。

    算法：
      1. 对每个商品名，取末尾 2-15 个纯中文字符作为候选后缀
      2. 按后缀统计出现过该后缀的不同商品名数量
      3. 过滤掉非品牌词（NOT_BRAND_WORDS），如"国产"、"冷冻"等
      4. count >= 2 表示该后缀在多个商品中出现 → 很可能是品类实体

    返回 dict {suffix: count}
      - suffix: 商品名末尾的中文字串（如"帝王蟹"、"鲍鱼肉"）
      - count: 包含该后缀的（去重后）商品名数量
      - 只在一种商品名出现的后缀 count=1，可能是随机组合而非实体
    """
    suffix_to_strs = defaultdict(set)
    for n in names:
        if not n:
            continue
        clean = clean_product_name(n)
        chars = re.sub(r'[^一-龥]', '', clean)
        max_len = min(15, len(chars))
        for length in range(max_len, 1, -1):
            suffix_to_strs[chars[-length:]].add(clean)
    entity_dict = {}
    for suffix, strs in suffix_to_strs.items():
        if len(suffix) >= 2 and suffix not in NOT_BRAND_WORDS:
            entity_dict[suffix] = len(strs)
    return entity_dict


def _is_variety_entity(word: str) -> bool:
    """查词库：word 是否属于 variety（品种）"""
    gk, _ = classify_word(word, _NBC)
    return gk == 'variety'


# 预构建：词库 variety 组的展平集合（缓存避免每次重建）
_VARIETY_WORDS = None


def _get_variety_words() -> set:
    """返回 NOT_BRAND_CATEGORIES 中 variety 组的所有品类词"""
    global _VARIETY_WORDS
    if _VARIETY_WORDS is not None:
        return _VARIETY_WORDS
    _VARIETY_WORDS = set()
    vdata = _NBC.get('variety', {})
    for sub_val in vdata.values():
        if isinstance(sub_val, dict):
            for words in sub_val.values():
                if isinstance(words, (set, list)):
                    _VARIETY_WORDS.update(w for w in words if isinstance(w, str) and len(w) >= 2)
        elif isinstance(sub_val, (set, list)):
            _VARIETY_WORDS.update(w for w in sub_val if isinstance(w, str) and len(w) >= 2)
    return _VARIETY_WORDS


def _collect_variety_candidates(chars: str) -> set:
    """收集 chars 中所有被词库归为 variety 的候选词（jieba token + 词库直查）"""
    candidates = set()

    # 1. jieba token 查 classify_word
    for token in jieba.lcut(chars):
        token = token.strip()
        if len(token) >= 2:
            gk, _ = classify_word(token, _NBC)
            if gk == 'variety':
                candidates.add(token)

    # 2. 词库 variety 组中出现在 chars 内的完整词
    for w in _get_variety_words():
        if w in chars:
            candidates.add(w)

    return candidates


def find_entity(chars: str, entity_dict: dict, known_tokens: set = None) -> Tuple[Optional[str], str]:
    """
    从纯中文字符串末尾匹配实体。

    策略：
      1. 后缀频率匹配 → 所有通过 count >= 2 的候选
      2. jieba token + 词库 variety 组 → 所有品种候选
      3. 兜底：末尾 2 字
      4. 用 known_tokens + variety 属性统一排序，选最优

    Args:
        chars: 纯中文字符串
        entity_dict: 由 build_entity_dict() 预构建的实体词典
        known_tokens: 该商品原始路径 L3 的 / 分隔 token 集合（辅助排序）

    Returns:
        tuple: (entity, prefix)
    """
    if not chars or len(chars) < 2:
        return None, ''

    # ── 收集所有候选 ──
    candidates = {}  # {entity: prefix}

    # 1. 后缀频率匹配候选
    max_len = min(15, len(chars))
    for length in range(max_len, 1, -1):
        suffix = chars[-length:]
        if len(chars) > 6 and len(suffix) >= len(chars):
            continue
        if entity_dict.get(suffix, 0) >= 2:
            prefix = chars[:-length] if chars[:-length] else ''
            candidates[suffix] = prefix

    # 2. jieba + 词库品种候选
    for c in _collect_variety_candidates(chars):
        if c not in candidates:
            idx = chars.index(c)
            candidates[c] = chars[:idx] if idx > 0 else ''

    # 3. 兜底
    fallback = chars[-2:]
    if fallback not in candidates:
        candidates[fallback] = chars[:-2] if len(chars) > 2 else ''

    # ── 统一排序 ──
    def _score(entity):
        s = 0
        gk, _ = classify_word(entity, _NBC)
        if gk == 'variety':
            s += 10  # 品种词
        elif known_tokens:
            # 完整匹配
            if entity in known_tokens:
                s += 5
            # 候选是已知 token 的子串
            elif any(entity in kt for kt in known_tokens if len(kt) >= 2):
                s += 3
            # 已知 token 是候选的子串
            elif any(kt in entity for kt in known_tokens if len(kt) >= 2):
                s += 2
            # 字符重叠
            elif any(set(entity) & set(kt) for kt in known_tokens):
                s += 1
        return s

    best = max(candidates.keys(), key=lambda e: (_score(e), len(e)))
    return best, candidates[best]


# ====================================================================
# 品牌/文字去噪
# ====================================================================

def strip_not_brand_words(text: str) -> str:
    """
    从文本开头逐层剥离非品牌描述词（前缀匹配→分段前缀→子串匹配，最多15轮）

    去除策略（3层，每轮按长度降序匹配以优先去除长词）：
      第1层：前缀匹配 — text 以某 NOT_BRAND_WORD 开头则去除
      第2层：分段前缀 — 取头部 2-3 字，看是否是某非品牌词的前缀
      第3层：子串匹配 — 在 text 任意位置匹配并去除
    """
    if not text:
        return text
    remaining = text.strip()
    for _ in range(15):
        matched = False
        # 第 1 层：前缀匹配
        for dw in sorted(NOT_BRAND_WORDS, key=len, reverse=True):
            if remaining.startswith(dw):
                remaining = remaining[len(dw):].strip()
                matched = True
                break
            if 2 <= len(remaining) < len(dw) and dw.startswith(remaining):
                remaining = ''
                matched = True
                break
        if not matched:
            # 第 2 层：分段前缀（取头部 2-3 字）
            for seg_len in [3, 2]:
                if len(remaining) >= seg_len:
                    seg = remaining[:seg_len]
                    for dw in sorted(NOT_BRAND_WORDS, key=len, reverse=True):
                        if len(dw) >= seg_len and dw.startswith(seg):
                            remaining = remaining[seg_len:].strip()
                            matched = True
                            break
                if matched:
                    break
        if not matched:
            # 第 3 层：子串匹配（任何位置）
            for dw in sorted(NOT_BRAND_WORDS, key=len, reverse=True):
                if len(dw) >= 1 and dw in remaining:
                    remaining = remaining.replace(dw, '', 1).strip()
                    matched = True
                    break
            if not matched:
                break
    return remaining


def strip_size_prefix(text: str) -> str:
    """去掉开头的大小前缀词（大/小/中/高/矮...），返回剩余部分"""
    if not text or text[0] not in SIZE_PREFIXES:
        return text
    idx = 0
    while idx < len(text) and text[idx] in SIZE_PREFIXES:
        idx += 1
    return text[idx:].strip()


def fully_not_brand(text: str) -> bool:
    """检查文本是否完全由 NOT_BRAND 描述词组成（向前/向后双向匹配）"""
    if not text:
        return True
    remaining = text.strip()
    for _ in range(10):
        changed = False
        for dw in sorted(NOT_BRAND_WORDS, key=len, reverse=True):
            if remaining.startswith(dw):
                remaining = remaining[len(dw):].strip()
                changed = True
                break
            if remaining.endswith(dw):
                remaining = remaining[:-len(dw)].strip()
                changed = True
                break
        if not remaining:
            return True
        if not changed:
            return False
    return not remaining


# ====================================================================
# 字符串工具
# ====================================================================

def similarity(s1: str, s2: str) -> float:
    """
    计算字符串相似度（编辑距离）

    Args:
        s1: 字符串1
        s2: 字符串2

    Returns:
        float: 相似度分数 (0.0 - 1.0)
    """
    if not s1 or not s2:
        return 0.0

    s1 = s1.lower()
    s2 = s2.lower()

    if s1 == s2:
        return 1.0

    if s1 in s2 or s2 in s1:
        return 0.9

    m = len(s1)
    n = len(s2)

    if m == 0 or n == 0:
        return 0.0

    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if s1[i - 1] == s2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1]) + 1

    max_len = max(m, n)
    return 1.0 - dp[m][n] / max_len


def classify_word(word: str, categories: dict) -> Tuple[str, str]:
    """
    在 NOT_BRAND_CATEGORIES 中查找 word 所属的分组。

    Args:
        word: 要查找的词
        categories: NOT_BRAND_CATEGORIES 字典

    Returns:
        Tuple[str, str]: (group_key, sub_group_key)
            未找到时返回 ('', '')
    """
    if not word or len(word) < 2:
        return '', ''
    for cat_key, cat_val in categories.items():
        if isinstance(cat_val, dict):
            for sub_key, sub_val in cat_val.items():
                if isinstance(sub_val, (set, list)):
                    if word in sub_val:
                        return cat_key, sub_key
                elif isinstance(sub_val, dict):
                    for sub2_val in sub_val.values():
                        if isinstance(sub2_val, (set, list)) and word in sub2_val:
                            return cat_key, sub_key
        elif isinstance(cat_val, (set, list)):
            if word in cat_val:
                return cat_key, ''
    return '', ''


def extract_modifiers(remaining: str, categories: dict = None) -> tuple:
    """
    用 jieba 分词从 remaining 中提取修饰词。

    参数:
        remaining: 商品名去除 entity 和 brand 后的纯中文字符串
        categories: NOT_BRAND_CATEGORIES 词库（不传则 import 默认词库）

    返回:
        (modifiers, modifier_detail)
          - modifiers: list[str]，在词库中有分类的词（用于 scoring）
          - modifier_detail: list[dict]，所有 token 及分类（用于显示）
    """
    if not remaining:
        return [], []

    cat = categories if categories is not None else _NBC

    modifiers = []
    seen = set()
    modifier_detail = []

    for token in jieba.lcut(remaining):
        token = token.strip()
        if len(token) < 2 or token in seen:
            continue
        seen.add(token)
        gk, sk = classify_word(token, cat)
        if gk:
            modifiers.append(token)
            _type = CATEGORY_GROUP_CN.get(gk, '')
            if sk and sk != gk:
                _type = f"{_type}-{sk}" if _type else sk
        else:
            _type = ''
        modifier_detail.append({'value': token, 'type': _type})

    return sorted(set(modifiers)), modifier_detail
