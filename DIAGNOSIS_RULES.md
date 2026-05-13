# 诊断规则参考文档

> 自动生成时间: 请更新此文档时修改此时间戳
>
> 如需新增规则，修改对应源代码后同步更新本文档对应章节。

---

## 一、品牌诊断

### 1.1 品牌分类规则

| 类型 | 判定条件 | 源代码 |
|------|----------|--------|
| **缺失** (missing) | `brand` 列为空 / `None` / `NaN` | `brand_cluster.py:100` |
| **错误** (mismatch) | `brand` 列有值，但 `check(name, brand)` 返回 `is_valid: false` | `brand_cluster.py:117-120` |
| **正确** (valid) | `brand` 列有值，且 `check(name, brand)` 返回 `is_valid: true` | `brand_cluster.py:134` |

### 1.2 品牌提取算法（`_extract_from_name_v6`）

源代码: `brand_checker.py:168-247`

输入: `商品名` → 输出: `(提取的品牌名, 置信度)`

#### 第1层：精准匹配（置信度 0.95）

```
商品名 → 按分隔符 [空格, /, ／, (, （, 【, [, 】, 】] 切割
       → 每块查品牌库 find_brand_by_name_fast()
       → 命中即返回
```

额外检查：
- **括号内品牌**: 匹配 `()（【】[]` 括号内的文本
- **盒马子品牌**: `find_sub_brand_fast()` 匹配前缀

#### 第2层：位置启发式（置信度 0.85）

```
商品名 → 正则提取开头2-8字中英文
       → _is_valid_brand_candidate 校验
       → 返回候选值
```

正则模式：
| 模式 | 示例 |
|------|------|
| `^([A-Za-z\u4e00-\u9fff]{2,8})\s+` | "可口可乐 330ml" → "可口可乐" |
| `^([A-Za-z\u4e00-\u9fff]{2,8})[/／]` | "可口可乐/新品" → "可口可乐" |
| `^([A-Za-z\u4e00-\u9fff]{2,8})[\(\（]` | "可口可乐(经典)" → "可口可乐" |

#### 第3层：模糊匹配（置信度 0.80）

```
遍历 BRAND_DATABASE_V6 所有标准品牌名
→ 检查 brand.lower() in name_lower
→ 命中即返回
```

#### 候选有效性校验（`_is_valid_brand_candidate`）

源代码: `brand_checker.py:249-259`

```
合格条件:
  - 长度 2-10
  - 非纯数字
  - 不含: 规格, 大小, 尺寸, 颜色, 数量, 克, 毫升, 米
```

### 1.3 品牌一致性检测（`check`）

源代码: `brand_checker.py:21-164`

输入: `(商品名, 品牌名)` → 输出: `{is_valid, issue_type, extracted_brand, confidence, message}`

#### 6 步校验流程（优先级从高到低）

```
Step 1: 斜杠品牌处理
  → brand 含 "/" 或 "／"
  → 查 SLASH_BRAND_PATTERNS 表
  → 命中 → "得宝" 是 "Tempo/得宝" 的标准形式 (0.95)
  → 未命中 → 取中文部分作为 brand_clean

Step 2: 品牌库精确匹配
  → brand_clean in BRAND_DATABASE_V6
  → 是 → 有效 (0.95)

Step 3: 别名匹配
  → find_brand_by_alias_fast(brand_clean)
  → 有 → 有效 (0.95)，标注被标准品牌

Step 4: 盒马子品牌
  → find_sub_brand_fast(brand_clean)
  → 有 → 有效 (0.95)

Step 5: 与商品名提取结果比对
  → _extract_from_name_v6(product_name) → extracted
  → extracted == brand_clean → 新品牌候选 (0.90)
  → brand_clean in product_name → 自证清白 (0.85)
  → 相似度 > 0.8 → 相似有效 (0.85)
  → 相似度 ≤ 0.8 → 品牌错误 (0.60)

Step 6: 无法提取
  → 无法确认 (0.50)
```

### 1.4 品牌相似度算法（`_similarity`）

源代码: `brand_checker.py:268-313`

```
基于编辑距离:
  精确相等          → 1.0
  包含关系          → 0.9
  s1 in s2 或反之   → 0.9
  编辑距离 / 最大长度 → 1.0 - normalized_distance
```

示例：`"可口可乐"` vs `"可口可樂"` → 编辑距离 1，相似度 = 1 - 1/4 = 0.75

### 1.5 品牌聚类算法（`_group_similar_brands`）

源代码: `brand_cluster.py:278-332`

```
输入: 品牌名列表

第1步：分离已知/未知
  → 每个品牌调 find_brand_by_name_fast()
  → 已知：归入标准品牌名下
  → 未知：放入未知列表

第2步：已知品牌直接归组
  → 同一标准品牌下的变体归为一组

第3步：未知品牌相似度聚类（阈值 0.85）
  → 两两计算 _similarity
  → > 0.85 则归组
  → 排除直接包含关系（跳过后继计算以提升性能）
```

输出: `List[List[str]]` — 每组内品牌名被视为同一品牌的变体

### 1.6 品牌聚类后处理（`cluster` 主流程）

源代码: `brand_cluster.py:26-276`

```
品牌正确组的处理:
  → 同组内取出现次数最多的作为 suggested_standard (brand_cluster.py:189)

品牌缺失组的处理:
  → 按 suggested_brand 聚类 (brand_cluster.py:207-247)
  → 无建议品牌时触发实体提取 (brand_cluster.py:108-120)

无品牌候选（新增）:
  → 条件: V6 提取不到 且 实体提取也找不到品牌前缀
  → 或: 前缀仅为描述词（鲜活/冰鲜/原切等）
  → 来源: brand_cluster.py:125-130
  → 聚类为 type='unbranded', issue_type='unbranded_fresh'
  → 前端渲染独立区块 + "确认无品牌"批量操作
  → 无 suggest 的归入 "__无建议__" 组

品牌错误组的处理:
  → 按 suggested_brand 聚类 (brand_cluster.py:250-270)
  → 记录所有原始品牌名
```

### 1.7 实体分离提取法（`_extract_unbranded_brand`）

源代码: `brand_cluster.py:144-182`

```
输入: 商品名（V6提取失败的商品）
→ 清理（去规格、去标签、去括号）
→ 只保留中文字
→ 从末尾匹配实体词典（最长优先）
→ 取实体前的部分作为品牌前缀
→ 逐层去掉开头 NOT_BRAND_WORDS 中的描述词
→ 剩余内容 ≥ 2字 → 品牌候选
→ 无剩余内容 → 无品牌

跨实体验证 (brand_cluster.py 聚类阶段 第2阶段):
  → 同一前缀跨 ≥ 2 个不同实体 → 最终确认为品牌候选
  → 否则 → 降级为无品牌
```

实体词典构建 (`_build_entity_dictionary`, `brand_cluster.py:111-130`):
```
→ 扫描全量商品名
→ 取每个商品名末尾2-15个中文字
→ 按唯一字符串统计出现频率（suffix→set of full cleaned names）
→ 返回 dict{suffix: count}
→ _find_entity 中使用时要求 count ≥ 2（跨商品出现），避免单商品名自身被当实体
```

### 1.8 NOT_BRAND_WORDS 分类列表

源代码: `brand_cluster.py:22-107`

共 **293 个**非品牌描述词，按来源分为 10 类：

| 类别 | 数量 | 说明 | 示例 |
|------|------|------|------|
| `provenance` 产地 | 61 | 国内外产地、水域 | 澳洲、四川、千岛湖、东海、俄罗斯 |
| `processing` 加工 | 47 | 加工/处理/切分方式 | 原切、谷饲、去皮、烟熏、三去 |
| `marketing` 营销 | 26 | 促销/推荐 | 热卖、爆款、限时、首推 |
| `format` 规格 | 23 | 包装/组合形式 | 礼盒、套装、散称、家庭装 |
| `farming` 养殖 | 24 | 养殖/处理方式 | 高盐、精养、净化、吊养、船冻 |
| `seasonal` 季节 | 20 | 季节/节日主题 | 春菜、端午、烧烤季、开海季 |
| `product_type` 品类 | 19 | 泛品类词 | 海鲜、和牛、三文鱼、果切 |
| `variety` 品种 | 46 | 品种/品名特征词 | 黑金刚、红膏、梭子、波士顿 |
| `certification` 认证 | 18 | 品质/认证描述 | 精选、优品、地标、可追溯 |
| `storage` 存储 | 9 | 存储/物流方式 | 冷冻、常温、气调、真空 |

### 提取流程

```
商品名 → V6提取
  ├── V6成功 → 品牌候选 (63%)
  ├── V6失败 → 实体法
  │    ├── 有前缀且跨≥2实体 → 品牌候选 (13%)
  │    └── 无前缀或仅1实体 → 无品牌候选 (18%)
  └── 剩余: 无分类/标识异常

### 1.8 品牌后缀清理

源代码: `constants.py:27`

```python
BRAND_SUFFIXES = [
    '集团', '公司', '有限', '股份', '乳业', '食品',
    '酒业', '饮料', '科技', '产业', '生物', '制药'
]
```

聚类前用这些后缀清理品牌名：`re.sub(suffix + '$', '', brand_clean)`

### 1.8 规格提取（SpecExtractor）

源代码: `extractors.py:12-40`

```
正则: (\d+\.?\d*)\s*(ml|毫升|ML|g|克|G|kg|千克|KG|l|升|L|oz|盎司|只|个|盒|袋|瓶|罐|包|条|支|桶|箱|片|块|份|杯|mm|厘米|cm|米|m)

提取后从商品名中移除规格文本，减少对品牌提取的干扰。
```

### 1.9 斜杠品牌模式表

源代码: `brands/patterns.py`（共 289 行，约 200+ 条预定义斜杠品牌映射）

格式: `(完整名称, 中文名, 英文名)`

示例:
```
('Tempo/得宝',      '得宝',     'Tempo')
('Lay's/乐事',      '乐事',     "Lay's")
('KERASTASE/卡诗',  '卡诗',     'KERASTASE')
```

### 1.10 品牌数据库

源代码: `brands/database.py`

- `BRAND_DATABASE_V6`: 约 375 个品牌, 每个品牌含 `{name, type, country, aliases, sub_brands}`
- `BRAND_NAME_TO_STANDARD`: 品牌名/别名 → 标准品牌名 的哈希索引（约 3000+ 条目）
- 查找函数: `find_brand_by_name_fast()` / `find_brand_by_alias_fast()` / `find_sub_brand_fast()`

---

## 二、分类诊断

### 2.1 分类规则

源代码: `category_detector.py:73-104`

对于每条商品，每个分类路径先判定**路径类型**:

```python
if 路径 包含 MARKETING_KEYWORDS 中任意关键词:
    → marketing_path
else:
    → standard_path
```

然后按路径集合分入4类:

| 类型 | 判定条件 | 聚类依据 |
|------|----------|----------|
| **冲突** (conflict) | `marketing_paths` 非空 **且** `standard_paths` 非空 | `suggested_path`（第1条标准路径） |
| **纯营销** (marketing) | `marketing_paths` 非空 **且** `standard_paths` 为空 | `marketing_paths[0]` |
| **标准审计** (standard) | `standard_paths` 非空 **且** `marketing_paths` 为空 | `standard_paths[0]` |
| **分类缺失** (missing) | 无任何路径 | 不聚类，直接展示 |

### 2.2 营销关键词列表

源代码: `categories/marketing_keywords.py`

```
促销活动类: 热卖, 推荐, 新品, 特价, 促销, 限时, 爆款, 热销, 人气,
           精选, 优惠, 折扣, 团购, 秒杀, 抢购, 直降, 满减, 特卖,
           大促, 活动, 专场, 会场, 预售

节日节气类: 端午, 年菜, 家宴, 招牌, 中秋, 春节, 圣诞, 上新,
           最新, 团圆, 年货, 元宵

季节类:     清凉, 一夏, 冬日, 暖冬, 夏日

主题营销类: 无肉, 不欢, 养生, 健身, 减肥, 美容, 护肤, 本周,
           本月, 今年, 今日, 热门, 必备, 首选, 经典
```

> **新增关键词**: 直接编辑 `marketing_keywords.py` 中的 `MARKETING_KEYWORDS` 列表即可生效

### 2.3 聚类逻辑（`cluster_by_path`）

源代码: `category_detector.py:107-122`

```
对每条商品取指定路径字段（如 suggested_path / marketing_paths / standard_paths）
→ 取第1个路径作为聚类key
→ 按key将商品分组
→ 每组按数量降序排列
```

冲突组按 `suggested_path[0]` 聚类（标准路径），营销组/标准组按各自路径聚类。

### 2.4 三级分类树结构

源代码: `category_detector.py:124-128`

```python
category_options = {
    'level1': [...],                             # 所有一级分类
    'level2_by_level1': {'level1': [...], ...},  # 每个一级下的二级
    'level3_by_level2': {'l1>l2': [...], ...}    # 每个二级下的三级
}
```

数据来源：上传文件中所有商品的全部分类路径。仅包含文件中出现的分类。

### 2.5 冲突归集规则

源代码: `category_detector.py:97-99`

```
当商品同时有 marketing_paths 和 standard_paths 时:
  → suggested_path = 第1条标准路径
  → 用户可确认归集（保留标准路径，剔除营销路径）
  → 确认后写入 categoryRules: {code: {action: 'confirm', replacement: '标准路径'}}
```

### 2.6 营销剔除规则

源代码: `category_detector.py:101-102`

```
当商品只有 marketing_paths 时:
  → 进入纯营销板块
  → 用户可选择"标记为营销剔除"
  → 标记后写入 marketingTags: {code: ['营销path1', '营销path2']}
```

---

## 三、数据存储

### 3.1 前端数据状态

| 数据 | 变量名 | 存储位置 | 格式 |
|------|--------|----------|------|
| 品牌规则 | `brandRules` | `window.brandRules` | `{code: {brand, no_brand, skipped}}` |
| 新品牌 | `newBrands` | `window.newBrands` | `[{name, type, country, confirmed}]` |
| 分类规则 | `categoryRules` | `window.categoryRules` | `{code: {action, replacement}}` |
| 营销标记 | `marketingTags` | `window.marketingTags` | `{code: [path1, path2]}` |
| 诊断数据 | `diagnosisData` | `window.diagnosisData` | 完整诊断结果对象 |

### 3.2 品牌规则格式

| 操作 | `brand` | `no_brand` | `skipped` | `confirmed` |
|------|---------|------------|-----------|-------------|
| 设置品牌 | `"品牌名"` | `false` | `false` | — |
| 无品牌 | `null` | `true` | `false` | — |
| 跳过 | `null` | `false` | `true` | — |
| 确认正确 | `"品牌名"` | `false` | `false` | `true` |

### 3.3 分类规则格式

| 操作 | `action` | `replacement` |
|------|----------|---------------|
| 确认归集 | `"confirm"` | `"一级 > 二级 > 三级"` |
| 跳过给AI | `"skip"` | — |

### 3.4 后端存储位置

| 数据 | 存储位置 | 落盘时机 |
|------|----------|----------|
| 品牌规则 | `sessions[sid]['brand_rules']` (内存) + `cache_manager` | AI 处理流程 (`standardization.py`) |
| 分类规则 | `cache_manager.get_rules(sid).categories` | AI 处理流程 (`standardization.py`) |
| 营销标记 | `cache_manager.get_rules(sid).marketing_tags` | AI 处理流程 (`standardization.py`) |

### 3.5 规则应用流程（AI处理阶段）

源代码: `standardization.py:55-79`

```
1. 读取 rules.categories
   → 按 code 匹配: 若命中且 action='confirm', 将 replacement 写入分类列
   → 按 current_path 匹配: 若命中则替换分类列

2. 读取 rules.marketing_tags
   → 按 code 匹配: 将匹配的营销路径写入 marketing_tag 列（以 " | " 分隔）

3. 生成最终输出文件到 RESULT_FOLDER
```

---

## 四、更新指南

### 新增品牌
编辑 `brands/database.py` 中 `BRAND_DATABASE_V6` 字典

### 新增斜杠品牌模式
编辑 `brands/patterns.py` 中 `SLASH_BRAND_PATTERNS` 列表

### 新增营销关键词
编辑 `categories/marketing_keywords.py` 中 `MARKETING_KEYWORDS` 列表

### 修改品牌提取规则
编辑 `brand_checker.py` 中 `_extract_from_name_v6` 或 `check` 方法

### 添加非品牌描述词
编辑 `brand_cluster.py` 顶部 `NOT_BRAND_CATEGORIES` 字典中对应分类的集合（用于实体法去噪）

| 分类 | 编辑位置 | 适用场景 |
|------|----------|----------|
| `provenance` | `NOT_BRAND_CATEGORIES['provenance']` | 新产地（如"舟山"） |
| `variety` | `NOT_BRAND_CATEGORIES['variety']` | 新品种（如"马友"） |
| `farming` | `NOT_BRAND_CATEGORIES['farming']` | 新养殖方式（如"充氧"） |
| `processing` | `NOT_BRAND_CATEGORIES['processing']` | 新加工方式 |

### 修改分类判定规则
编辑 `category_detector.py` 中 `analyze` 方法的四路归集逻辑

### 修改规格提取规则
编辑 `core/extractors.py` 中 `SPEC_PATTERN` 正则
