#!/usr/bin/env python3
"""
分类路径清洗算法

检测框架: 场景判定 + 散布判定 + 合并检测 + 污染纠正 → 裁定 → 循环收敛

核心流程:
  0. 营销剔除（关键词 + 模式匹配 + 已知营销L1）
  1. 场景L1判定（永久标记）
  2. 循环收敛:
     a. L1合并（合并映射表 + 字符包含）  
     b. 散布判定（≥4个L1且最大≤60%）
     c. depth primary分配（L3深度差距≥2）
     d. 场景拆解（场景L1下所有L2分配到标准L1）
     e. 散布收敛（散布L2全部纠正到depth primary）
     f. 污染纠正（depth_primary > std L1 > 合并表 > 散布）
  3. 最终选路
  4. 小L1处理（≤30条用token兜底）
  5. 近似合并（token共享/字符包含）
  6. 输出结构树

外部依赖:
  - pandas
  - marketing_keywords.py（本目录下）
"""

import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import json

import pandas as pd

# 引入营销关键词库和手动标记
PARENT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PARENT_DIR.parent))
sys.path.insert(0, str(PARENT_DIR))
from categories.marketing_keywords import MARKETING_KEYWORDS

# 手动标记的路径（来自 classified_paths.json）
CLASSIFIED_PATHS = {}
CLASSIFIED_PATHS_FILE = Path(__file__).parent / 'classified_paths.json'
if CLASSIFIED_PATHS_FILE.exists():
    try:
        with open(CLASSIFIED_PATHS_FILE, 'r', encoding='utf-8') as f:
            CLASSIFIED_PATHS = json.load(f)
    except Exception:
        pass


# =========================================================================
# 配置
# =========================================================================

# 营销关键词列表（来自 marketing_keywords.py）
MKT_KEYWORDS = MARKETING_KEYWORDS

# 已知营销入口L1（全营销，不参与分类）
MKT_L1 = {'年货大街', '十周年', '尝春鲜', '清凉一夏', '端午食俗'}

# 营销模式匹配（正则）
MKT_PATTERNS = [
    re.compile(r'\d+件\s*\d*\.?\d*折'),  # 2件85折
    re.compile(r'满\d+'),                  # 满29
    re.compile(r'减\d+'),                  # 减10
]

# L1同义词映射（由 clean_paths() 中的算法生成，运行时填充）
L1_SYNONYM_MAP = {}


# =========================================================================
# 工具函数
# =========================================================================

def sort_tokens(name: str) -> str:
    """将 '/' 分隔的 token 排序归一，用于比较和显示"""
    return '/'.join(sorted(name.split('/')))


def token_set(name: str) -> set:
    """将 '/' 分隔的名称转为 token 集合"""
    return set(name.split('/'))


def get_l2_depth(l2_name: str, code_paths: dict) -> dict:
    """
    返回一个 L2 在各级别 L1 下的 L3 深度。
    返回 {L1: 去重L3数量}
    """
    depth = defaultdict(set)
    for _, paths in code_paths.items():
        for path in paths:
            parts = path.split(' > ')
            if len(parts) == 3 and parts[1] == l2_name:
                depth[parts[0]].add(parts[2])
    return {l1: len(l3s) for l1, l3s in depth.items()}


def merge_l1(l1_name: str) -> str:
    """执行 L1 合并，返回合并后的 L1 名（由 clean_paths 中的算法生成 L1_SYNONYM_MAP）"""
    return L1_SYNONYM_MAP.get(l1_name, l1_name)


def merge_l1_match(l2_name: str) -> None:
    """已废弃：L1_MERGE_MAP 已删除，所有调用点由现有兜底逻辑处理"""
    return None


def is_marketing(path: str) -> bool:
    """
    检查路径是否含有营销标记。
    检测优先级:
      1. 手动标记（classified_paths.json）
      2. 已知营销L1
      3. 关键词匹配
      4. 模式匹配（件折、满、减）
    """
    # 1. 手动标记优先
    if path in CLASSIFIED_PATHS:
        return CLASSIFIED_PATHS[path] == 'marketing'
    # 2. 已知营销L1
    parts = path.lower().split(' > ')
    if parts[0].strip() in MKT_L1:
        return True
    # 3. 关键词匹配
    for level in parts:
        for kw in MKT_KEYWORDS:
            if kw in level:
                return True
    # 4. 模式匹配
    for level in parts:
        for pat in MKT_PATTERNS:
            if pat.search(level):
                return True
    return False


def read_data(filepath: str) -> dict:
    """
    从 Excel 读取商品数据，返回 {code: {path: date}} 字典。
    同一个code的同一路径只保留最新日期。
    """
    df = pd.read_excel(filepath, dtype=str)
    return build_raw_paths(df, 'org_spu_code', 'date_code',
                           'cate_level1_name', 'cate_level2_name', 'cate_level3_name')


def build_raw_paths(df: pd.DataFrame, code_col: str = 'org_spu_code',
                     date_col: str = 'date_code',
                     c1_col: str = 'cate_level1_name',
                     c2_col: str = 'cate_level2_name',
                     c3_col: str = 'cate_level3_name') -> dict:
    """
    从 DataFrame 构建原始路径字典。
    返回 {code: {path: date}}，同code同路径只保留最新日期。
    
    参数:
        df: 原始数据
        code_col: 商品编码列名
        date_col: 日期列名
        c1_col / c2_col / c3_col: 三级分类列名
    """
    code_paths = defaultdict(lambda: defaultdict(str))
    for _, row in df.iterrows():
        code = str(row.get(code_col, '')).strip()
        c1 = str(row.get(c1_col, '')).strip() if pd.notna(row.get(c1_col)) else ''
        c2 = str(row.get(c2_col, '')).strip() if pd.notna(row.get(c2_col)) else ''
        c3 = str(row.get(c3_col, '')).strip() if pd.notna(row.get(c3_col)) else ''
        date = str(row.get(date_col, '')).strip()
        if c1 and c2 and c3:
            path = f'{c1} > {c2} > {c3}'
            existing = code_paths[code].get(path, '')
            if not date or date > existing:
                code_paths[code][path] = date
    return {c: dict(ps) for c, ps in code_paths.items()}


# =========================================================================
# 场景判定
# =========================================================================

def detect_scene_l1s(code_paths: dict, all_l1: set) -> set:
    """
    检测场景化 L1。
    标准: L1 的 L2 中含其他标准L1名占比 >20% 且 ≥2种。
    返回场景 L1 集合（含已知营销L1）。
    """
    # 构建 L1→L2 映射
    l1_l2 = defaultdict(set)
    for _, paths in code_paths.items():
        for path in paths:
            parts = path.split(' > ')
            if len(parts) == 3:
                l1_l2[parts[0]].add(parts[1])
    
    all_l1_list = sorted(all_l1)
    scene_l1s = set()
    
    for l1 in l1_l2:
        # 统计 L2 中包含的其他 L1 名
        other_l1_count = {}
        for _, paths in code_paths.items():
            for path in paths:
                parts = path.split(' > ')
                if len(parts) == 3 and parts[0] == l1:
                    l2 = parts[1]
                    if l2 in all_l1 and l2 != l1:
                        other_l1_count[l2] = other_l1_count.get(l2, 0) + 1
        
        if other_l1_count:
            total = sum(1 for _, ps in code_paths.items()
                        for p in ps if p.split(' > ')[0] == l1)
            if total and sum(other_l1_count.values()) / total * 100 > 20 \
                    and len(other_l1_count) >= 2:
                scene_l1s.add(l1)
    
    scene_l1s |= MKT_L1
    return scene_l1s


# =========================================================================
# 路径去重 / 最终选路
# =========================================================================

def _path_score(path: str) -> int:
    """
    L3 具体性评分（用于日期相同时的排序回退）。
    越高越具体：
      - L3 != L2 → +1000（真正的子分类）
      - L3 纯字数（不含/） → +10/字
      - L3 含 '/' → +50（复合品类）
      - L1 == L2 → -800（收敛步骤的产物，L2 不是真实子分类）
    """
    parts = path.split(' > ')
    if len(parts) < 3:
        return 0
    l1, l2, l3 = parts[0], parts[1], parts[2]
    score = len(l3.replace('/', '')) * 10
    if l3 != l2:
        score += 1000
    if l1 == l2:
        score -= 800
    if '/' in l3:
        score += 50
    return score


def pick_final_path(paths: dict, scene_l1s: set) -> str:
    """
    从多个路径中选取最终的分类路径。
    优先选非场景L1的路径，然后选日期最新，日期相同时选 L3 更具体的。
    """
    non_scene = {p: d for p, d in paths.items()
                 if p.split(' > ')[0] not in scene_l1s}
    if non_scene:
        return max(non_scene.items(),
                   key=lambda x: (int(x[1]) if x[1] else 0, _path_score(x[0])))[0]
    if paths:
        return max(paths.items(),
                   key=lambda x: (int(x[1]) if x[1] else 0, _path_score(x[0])))[0]
    return ''


# =========================================================================
# L1 同义词检测（替换 L1_MERGE_MAP）
# =========================================================================

def build_l1_synonym_map(code_paths: dict, all_l1: set) -> dict:
    """
    检测 L1 同义词，返回 {同义词L1: 标准L1} 映射。

    判断条件（满足任一即视为同义词）:
      1. L2 集包含度 >= 0.7（子集/高度重叠）
      2. L2 集包含度 >= 0.4 + L1名共享token（同源不同名）

    合并规则: 商品数少的 L1 归入商品数多的 L1
    """
    from collections import Counter, defaultdict

    l1_l2 = defaultdict(set)
    l1_count = Counter()
    for _, paths in code_paths.items():
        for path in paths:
            parts = path.split(' > ')
            if len(parts) == 3:
                l1_l2[parts[0]].add(parts[1])
                l1_count[parts[0]] += 1

    l1_synonym = {}
    all_l1_list = sorted(l1 for l1 in all_l1 if l1 in l1_l2)

    for i in range(len(all_l1_list)):
        for j in range(i + 1, len(all_l1_list)):
            a, b = all_l1_list[i], all_l1_list[j]
            # 仅对两个都 >30条 且 ≥3个L2 的 L1 做同义词检测
            # 小 L1（≤30条）由 Phase 4 的 token 匹配处理
            if l1_count[a] <= 30 or l1_count[b] <= 30:
                continue
            if len(l1_l2[a]) < 3 or len(l1_l2[b]) < 3:
                continue
            s_a, s_b = l1_l2[a], l1_l2[b]
            inter = len(s_a & s_b)
            union = len(s_a | s_b)
            smaller = min(len(s_a), len(s_b))

            if union == 0 or smaller == 0:
                continue

            containment = inter / smaller

            # 条件 1: 高包含度
            if containment >= 0.7:
                pass
            elif containment >= 0.4:
                # 条件 2: 包含度 + L1名共享token
                tokens_a = set(a.replace('/', ' ').split(' '))
                tokens_b = set(b.replace('/', ' ').split(' '))
                if not (tokens_a & tokens_b):
                    continue
            else:
                continue

            # 合并: 小归大
            if l1_count[a] < l1_count[b]:
                l1_synonym[a] = b
            else:
                l1_synonym[b] = a

    return l1_synonym


# =========================================================================
# 主清洗函数
# =========================================================================

def clean_paths(code_paths: dict) -> dict:
    """
    分类路径清洗主入口。
    
    参数:
        code_paths: {code: {path: date}}
    
    返回:
        {code: final_path} 每个code唯一的标准分类路径
    """
    # ---- 0. 营销剔除 ----
    non_mkt = {}
    for code, paths in code_paths.items():
        clean = {p: d for p, d in paths.items() if not is_marketing(p)}
        if clean:
            non_mkt[code] = clean
    
    # 全量 L1 集合（用于场景判定）
    all_l1 = set()
    for _, paths in code_paths.items():
        for path in paths:
            parts = path.split(' > ')
            if parts:
                all_l1.add(parts[0])
    # ---- 1. 场景L1判定 ----
    scene_l1s = detect_scene_l1s(non_mkt, all_l1)

    # 算法生成 L1 同义词映射（替换硬编码 L1_MERGE_MAP）
    L1_SYNONYM_MAP.clear()
    L1_SYNONYM_MAP.update(build_l1_synonym_map(code_paths, all_l1))

    current = {c: dict(ps) for c, ps in non_mkt.items()}
    
    # ---- 2. 循环收敛 ----
    max_cycles = 25
    for _ in range(max_cycles):
        # 2a. L1合并
        merged = {}
        for code, paths in current.items():
            new_paths = {}
            for path, date in paths.items():
                parts = path.split(' > ')
                if len(parts) == 3:
                    l1 = merge_l1(parts[0])
                    new_paths[f'{l1} > {parts[1]} > {parts[2]}'] = date
                else:
                    new_paths[path] = date
            merged[code] = new_paths
        current = merged
        
        # 重建分层数据
        l2_l1_count = defaultdict(lambda: defaultdict(int))
        for _, paths in current.items():
            for path in paths:
                parts = path.split(' > ')
                if len(parts) == 3:
                    l2_l1_count[parts[1]][parts[0]] += 1
        
        # 2b. 散布判定 + depth primary分配
        depth_primary = {}
        scattered = set()
        for l2, l1s in l2_l1_count.items():
            l1s_merged = defaultdict(int)
            for l1, cnt in l1s.items():
                m = merge_l1(l1)
                if m not in scene_l1s:
                    l1s_merged[m] += cnt
            total = sum(l1s_merged.values())
            
            # 散布: ≥4个L1 且 最大≤60%
            if len(l1s_merged) >= 4 and max(l1s_merged.values()) / total <= 0.60:
                scattered.add(l2)
            
            # depth primary: L3深度差距≥2
            depths = get_l2_depth(l2, current)
            filtered = {l: d for l, d in depths.items() if l not in scene_l1s}
            if len(filtered) >= 2:
                sorted_d = sorted(filtered.items(), key=lambda x: -x[1])
                if sorted_d[0][1] - sorted_d[1][1] >= 2:
                    depth_primary[l2] = sorted_d[0][0]
            elif len(filtered) == 1:
                depth_primary[l2] = list(filtered.keys())[0]
        
        # 2d-2f. 裁定: 场景拆解 + 散布收敛 + 污染纠正
        actions = 0
        new_current = {}
        for code, paths in current.items():
            new_paths = {}
            for path, date in paths.items():
                parts = path.split(' > ')
                if len(parts) == 3:
                    l1, l2, l3 = parts
                    target = None
                    
                    if l1 in scene_l1s and l1 not in MKT_L1:
                        # 场景拆解
                        m = merge_l1_match(l2)
                        if m:
                            target = (m, l2, sort_tokens(l3))
                        elif l2 in (all_l1 - scene_l1s):
                            target = (l2, l2, sort_tokens(l3))
                    else:
                        # ① depth primary优先
                        if l2 in depth_primary and depth_primary[l2] != l1:
                            dep = get_l2_depth(l2, current)
                            fd = {l: d for l, d in dep.items()
                                  if l not in scene_l1s}
                            sd = sorted(fd.items(), key=lambda x: -x[1])
                            if len(sd) >= 2 and sd[0][1] - sd[1][1] >= 2:
                                target = (depth_primary[l2], l2, sort_tokens(l3))
                        # ② L2是标准L1
                        if not target and l2 in (all_l1 - scene_l1s) and l2 != l1:
                            target = (l2, l2, sort_tokens(l3))
                        # ③ 合并映射表
                        if not target:
                            m = merge_l1_match(l2)
                            if m and m != l1:
                                target = (m, l2, sort_tokens(l3))
                        # ④ 散布收敛到depth primary
                        if not target and l2 in scattered and l2 in depth_primary \
                                and depth_primary[l2] != l1:
                            target = (depth_primary[l2], l2, sort_tokens(l3))
                    
                    if target:
                        new_paths[f'{target[0]} > {target[1]} > {target[2]}'] = date
                        actions += 1
                    else:
                        new_paths[path] = date
                else:
                    new_paths[path] = date
            new_current[code] = new_paths
        
        if actions == 0:
            break
        current = new_current
    
    # ---- 3. 最终选路 ----
    final = {}
    for code, paths in current.items():
        picked = pick_final_path(paths, scene_l1s)
        if picked:
            final[code] = picked
    
    # ---- 4. 小L1处理（≤30条，token兜底） ----
    l1_counts = Counter(p.split(' > ')[0] for p in final.values())
    for l1, cnt in list(l1_counts.items()):
        if cnt > 30 or l1 in scene_l1s or l1 not in all_l1:
            continue
        targets = set()
        for code, path in list(final.items()):
            parts = path.split(' > ')
            if len(parts) == 3 and parts[0] == l1:
                l2 = parts[1]
                m = merge_l1_match(l2)
                if m:
                    targets.add(m)
                for sl in all_l1:
                    if sl in scene_l1s or sl == l1:
                        continue
                    if token_set(l2) & token_set(sl):
                        targets.add(sl)
        if targets:
            best = max(targets, key=lambda x: l1_counts.get(x, 0))
            for code in list(final.keys()):
                parts = final[code].split(' > ')
                if len(parts) == 3 and parts[0] == l1:
                    final[code] = f'{best} > {" > ".join(parts[1:])}'
    
    # ---- 5. 近似合并 ----
    path_counts = Counter()
    for code, path in final.items():
        parts = path.split(' > ')
        if len(parts) == 3:
            l1 = merge_l1(parts[0])
            path_counts[f'{l1} > {parts[1]} > {parts[2]}'] += 1
    
    # 按L1分组 → 共享token/字符包含 → 少归多
    l1_groups = defaultdict(list)
    for path, cnt in path_counts.items():
        parts = path.split(' > ')
        if len(parts) == 3 and parts[2]:
            l1_groups[parts[0]].append((path, parts[1], parts[2], cnt))
    
    # 并查集结构（自带传递性 + 按 count 大小合并）
    parent = {}
    for _, entries in l1_groups.items():
        for path, _, _, _ in entries:
            parent[path] = path

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        rx, ry = find(x), find(y)
        if rx == ry:
            return
        cx, cy = path_counts.get(rx, 0), path_counts.get(ry, 0)
        if cx < cy:
            parent[rx] = ry
        else:
            parent[ry] = rx

    # 按 L1 分组做近似合并，用 L2 token 倒排索引避免 O(n²)
    for l1, entries in l1_groups.items():
        token_to_entries = defaultdict(set)
        for idx, (_, l2, _, _) in enumerate(entries):
            for token in token_set(l2):
                token_to_entries[token].add(idx)

        for i, (p_a, l2a, l3a, _) in enumerate(entries):
            candidates = set()
            for token in token_set(l2a):
                candidates |= token_to_entries[token]

            for j in candidates:
                if j <= i:
                    continue
                p_b, l2b, l3b, _ = entries[j]
                l2_ok = (token_set(l2a) & token_set(l2b)
                         or l2a in l2b or l2b in l2a)
                if l2_ok:
                    union(p_a, p_b)

        # 子串兜底：补 token 索引覆盖不到的（L2 无 "/" 时）
        l2_to_indices = defaultdict(list)
        for idx, (_, l2, _, _) in enumerate(entries):
            l2_to_indices[l2].append(idx)
        all_l2s = list(l2_to_indices.keys())
        for i in range(len(all_l2s)):
            for j in range(i + 1, len(all_l2s)):
                l2a, l2b = all_l2s[i], all_l2s[j]
                if l2a in l2b or l2b in l2a:
                    for ia in l2_to_indices[l2a]:
                        for ib in l2_to_indices[l2b]:
                            if ia < ib:
                                union(entries[ia][0], entries[ib][0])

    # 应用近似合并到结果（L1+L2 归一化到 root，相同 L3 去重归并）
    cluster_groups = defaultdict(lambda: defaultdict(list))
    for code, path in final.items():
        parts = path.split(' > ')
        if len(parts) == 3:
            l1 = merge_l1(parts[0])
            root = find(f'{l1} > {parts[1]} > {parts[2]}')
            root_l1_l2 = ' > '.join(root.split(' > ')[:2])
            cluster_groups[root_l1_l2][parts[2]].append(code)

    final_paths = defaultdict(list)
    for cluster_key, l3_groups in cluster_groups.items():
        sorted_l3s = sorted(l3_groups.items(), key=lambda x: -len(x[1]))
        l3_dedup = {}
        for i in range(len(sorted_l3s)):
            l3_a = sorted_l3s[i][0]
            kept = False
            for j in range(i):
                l3_b = sorted_l3s[j][0]
                merge = (l3_a == l3_b or bool(token_set(l3_a) & token_set(l3_b)))
                if not merge and (l3_a in l3_b or l3_b in l3_a):
                    merge = True
                if merge:
                    l3_dedup[l3_a] = l3_b
                    kept = True
                    break
            if not kept:
                l3_dedup[l3_a] = l3_a
        for l3, codes in l3_groups.items():
            final_paths[f'{cluster_key} > {l3_dedup[l3]}'].extend(codes)

    # 后处理: 折叠 L2==L1 的冗余路径，L3 补位 L2 保持 3 级格式
    # "蔬菜豆制品 > 蔬菜豆制品 > 叶菜/花菜" → "蔬菜豆制品 > 叶菜/花菜 > 叶菜/花菜"
    collapsed = defaultdict(list)
    for path, codes in final_paths.items():
        parts = path.split(' > ')
        if len(parts) == 3 and parts[0] == parts[1]:
            collapsed[f'{parts[0]} > {parts[2]} > {parts[2]}'].extend(codes)
        else:
            collapsed[path].extend(codes)

    return collapsed
