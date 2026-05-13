# 五文件调用关系总图

> 生成日期：2026-05-12（重构后）
> 范围：core/ 下的 5 个核心模块 + app.py（web 入口）

---

## 0. 架构概览

```
product_parser.py         ← 底层拆解包（零业务依赖，供所有引擎调用）
    ↓        ↓        ↓
brand_checker.py    brand_cluster.py    category_detector.py
    ↓        ↓        ↓
         app.py（web 入口）
```

**核心原则：** 底层方法 → `product_parser.py`，业务逻辑 → 各自引擎，数据常量 → `lexicon.py`

---

## 1. 整体依赖流向

```
                              ┌─────────────────────┐
                              │  brand_cluster.py   │
                              │  (品牌聚类引擎)       │
                              └────────┬────────────┘
                                       │ 依赖                       
                           ┌───────────┼──────────────────┐
                           ▼           ▼                  ▼
                    ┌──────────┐ ┌──────────┐   ┌──────────────┐
                    │product_  │ │brand_    │   │   lexicon    │
                    │parser.py │ │checker   │   │   .py        │
                    │(底层拆解) │ │.py       │   │  (数据常量)   │
                    └────┬─────┘ └────┬─────┘   └──────────────┘
                         │            │              
                         ▼            ▼
                    ┌──────────────────────────────────┐
                    │            lexicon.py             │
                    │  (数据源头，零内部依赖)             │
                    └──────────────────────────────────┘

┌──────────────┐     ┌─────────────────────┐
│   app.py     │────▶│ category_detector   │
│  (web 入口)  │     │ .py (分类检测)       │
└──────┬───────┘     └──────────┬──────────┘
       │                       │
       │              ┌────────┼────────────────┐
       ▼              ▼        ▼                ▼
  ┌──────────┐  ┌──────────┐ ┌─────────┐ ┌──────────────┐
  │brand_    │  │brand_    │ │product_ │ │   lexicon    │
  │cluster   │  │checker   │ │parser   │ │   .py        │
  │.py       │  │.py       │ │.py      │ │              │
  └──────────┘  └──────────┘ └─────────┘ └──────────────┘
```

---

## 2. 逐文件详细调用表

### 图例
- `import` = 模块级 import
- `lazy` = 函数内部 import
- `→` = 调用方向

---

### 【lexicon.py】— 纯数据，零内部依赖

```
无 import（纯常量文件）

 ── 对外输出 ──────────────────────────────────────────────
 │  SIZE_PREFIXES        → product_parser                 │
 │  SPEC_UNITS           → product_parser (via PATTERN)    │
 │  SPEC_UNITS_PATTERN   → product_parser                 │
 │  NOT_BRAND_WORDS      → product_parser                 │
 │  NOT_BRAND_CATEGORIES → brand_cluster, category_detector│
 │  DUAL_MEANING_BRANDS  → brand_cluster                  │
 │  FOOD_CATEGORY_KEYWORDS → brand_cluster                │
 │  VARIETY_GROUP_L1     → category_detector              │
 └────────────────────────────────────────────────────────┘
```

---

### 【product_parser.py】— 商品名称底层拆解器（新增，替代 extractors.py）

```
 原名 extractors.py，重构后接收了其他 3 个文件的底层方法。

 import 模块级
   SPEC_UNITS_PATTERN, NOT_BRAND_WORDS, SIZE_PREFIXES ← lexicon

 ── 内含方法 ──────────────────────────────────────────────
 │  # 商品名清理（清空档）                                  │
 │  clean_product_name(name)           ← 来自 brand_checker│
 │  clean_product_name_strict(name)    ← 来自 category_    │
 │                                         detector       │
 │  # 规格提取（原 extractors.py）                          │
 │  SpecExtractor.extract()            ← 原 extractors    │
 │  SpecExtractor.extract_all_specs()  ← 原 extractors    │
 │  SpecExtractor.has_spec()           ← 原 extractors    │
 │                                                         │
 │  # 实体识别                                              │
 │  build_entity_dict(names)           ← 原 extractors    │
 │  find_entity(chars, entity_dict)    ← 来自 brand_cluster│
 │    （含兜底：取末尾2字作为粗略实体）                      │
 │                                                         │
 │  # 去噪工具                                              │
 │  strip_not_brand_words(text)        ← 来自 brand_cluster│
 │  strip_size_prefix(text)            ← 来自 brand_cluster│
 │  fully_not_brand(text)              ← 来自 brand_cluster│
 │                                                         │
 │  # 字符串工具                                            │
 │  similarity(s1, s2)                 ← 来自 brand_checker│
 └────────────────────────────────────────────────────────┘

 被谁调用:
   SpecExtractor          → brand_checker, brand_cluster, app.py
   clean_product_name     → brand_cluster, build_entity_dict
   clean_product_name_    → category_detector
     strict
   build_entity_dict      → brand_cluster, app.py
   find_entity            → category_detector
   strip_not_brand_words  → brand_cluster
   strip_size_prefix      → brand_cluster
   fully_not_brand        → brand_cluster
   similarity             → brand_checker, brand_cluster
```

---

### 【brand_checker.py】— 品牌一致性检测

```
 import 模块级
   BRAND_DATABASE_V6, find_any_brand  ← brands.database
   SLASH_BRAND_PATTERNS               ← brands.patterns
   SpecExtractor, similarity          ← product_parser

 ── 调用关系 ──────────────────────────────────────────────
 │  BrandConsistencyChecker                              │
 │    check()                                            │
 │      └── similarity() (from product_parser)           │
 │    _extract_from_name_v6()                            │
 │      └── SpecExtractor.extract() (from product_parser)│
 └────────────────────────────────────────────────────────┘

 被谁调用:
   BrandConsistencyChecker → brand_cluster, app.py
```

**移除清单（已搬至 product_parser）：**
- `_clean_product_name` → `product_parser.clean_product_name()`
- `_similarity` → `product_parser.similarity()`
- `_extract_by_entity`（死代码删除）
- `NOT_BRAND_WORDS` 类变量（死代码删除）
- 未使用 import（`BRAND_NAME_TO_STANDARD`, `get_slash_pattern_*`）

---

### 【brand_cluster.py】— 品牌聚类引擎

```
 import 模块级
   BRAND_DATABASE_V6, find_brand_by_name_fast,  ← brands.database
     find_sub_brand_fast
   BRAND_SUFFIXES                   ← constants
   SpecExtractor, build_entity_dict,
     find_entity, clean_product_name,
     strip_not_brand_words,
     strip_size_prefix, fully_not_brand,
     similarity                     ← product_parser
   BrandConsistencyChecker          ← brand_checker
   DUAL_MEANING_BRANDS, FOOD_CATEGORY_KEYWORDS,
     NOT_BRAND_CATEGORIES, NOT_BRAND_WORDS ← lexicon

 ── 调用关系 ──────────────────────────────────────────────
 │  BrandClusterEngine.cluster()                         │
 │  BrandClusterEngine._extract_unbranded_brand()        │
 │  BrandClusterEngine._group_similar_brands()           │
 │  lean_clusters()                                      │
 └────────────────────────────────────────────────────────┘
```

**移除清单（已搬至 product_parser）：**
- `_find_entity` → `product_parser.find_entity()`
- `_strip_not_brand_words` → `product_parser.strip_not_brand_words()`
- `_strip_size_prefix` → `product_parser.strip_size_prefix()`
- `_fully_not_brand` → `product_parser.fully_not_brand()`

---

### 【category_detector.py】— 分类检测引擎

```
 import 模块级
   MARKETING_KEYWORDS           ← categories.marketing_keywords
   clean_paths, build_raw_paths ← categories.path_cleaner
   VARIETY_GROUP_L1             ← lexicon
   clean_product_name_strict,   ← product_parser
     find_entity

 lazy（函数内）
   BrandConsistencyChecker._extract_from_name_v6 ← brand_checker
   NOT_BRAND_CATEGORIES                          ← lexicon
   BRAND_DATABASE_V6                             ← brands.database
```

**移除清单（已搬至 product_parser）：**
- `_clean_name` → `product_parser.clean_product_name_strict()`
- `SPEC_UNITS_PATTERN` import（不再直接使用）

---

### 【app.py】（外部入口，只列核心）

```
 import 模块级（通过 core/__init__.py）
   SpecExtractor, BrandConsistencyChecker,
   BrandClusterEngine, CategoryDetector,
   lean_clusters, build_entity_dict, etc.

 ── 实际调用 ──────────────────────────────────────────────
 │  BrandClusterEngine.cluster()                          │
 │  build_entity_dict()                                   │
 │  CategoryDetector.analyze()                            │
 │  CategoryDetector.suggest_category()                   │
 │  lean_clusters()                                       │
 │  SpecExtractor.extract()                               │
 │  BrandConsistencyChecker._extract_from_name()          │
 │  BrandConsistencyChecker.check()                       │
 │  StandardizationEngine.apply_rules()                   │
 │  ProductCleanerEngine.process_batch()                  │
 └────────────────────────────────────────────────────────┘
```

---

## 3. 关键依赖链

### 最长的调用链（4 层）
```
app.py → BrandClusterEngine.cluster()
  → build_entity_dict() (product_parser)
    → clean_product_name() (product_parser)
      → SPEC_UNITS_PATTERN (lexicon)
```

所有路径都止于 `lexicon.py`，不再有循环依赖。

### 循环依赖追踪
```
重构前: brand_checker.py ↔ extractors.py（通过 SpecExtractor + _clean_product_name）
重构后: ❌ 已不存在
  - product_parser.py 不 import brand_checker
  - brand_checker.py import product_parser（单向）
```

### 被最多文件引用的常量
| 常量 | 来源 | 引用文件数 | 引用者 |
|---|---|---|---|
| `NOT_BRAND_WORDS` | lexicon | 2 | product_parser, brand_cluster |
| `SPEC_UNITS_PATTERN` | lexicon | 1 | product_parser |

### 被最多文件调用的方法
| 方法 | 所在 | 引用文件数 | 调用者 |
|---|---|---|---|
| `SpecExtractor.extract` | product_parser | 3 | brand_checker, brand_cluster(×3), app.py |
| `similarity` | product_parser | 2 | brand_checker, brand_cluster |
| `build_entity_dict` | product_parser | 2 | brand_cluster, app.py |

---

## 4. 重构前后对比

| 指标 | 重构前 | 重构后 |
|---|---|---|
| 底层方法分布 | 散落在 3 个文件中 | 全部在 `product_parser.py` |
| 重复的 3 层剥离算法 | 2 份（brand_cluster 内） | 1 份（product_parser） |
| 重复的 SIZE_PREFIXES 剥离 | 2 份（brand_cluster 内） | 1 份（product_parser） |
| 规格单位 regex | 3 份独立内联 | 1 份（lexicon） |
| 循环依赖 | brand_checker ↔ extractors | ❌ 无 |
| 死代码 | `_extract_by_entity` + 连带变量 | 已删除 |
| 实体识别逻辑 | 3 处分散 | 1 处（product_parser） |
| 文件数 | extractors.py（旧） | product_parser.py（新） |
| 方法总数（5 文件） | 32 个 | 28 个（删 5 + 增 1 → 净 -4） |
