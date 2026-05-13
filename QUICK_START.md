# 🎯 商品数据清理系统 - 完整指南

## 📚 目录
1. [系统概览](#系统概览)
2. [快速开始（5分钟）](#快速开始5分钟)
3. [两种使用方式](#两种使用方式)
4. [系统架构](#系统架构)
5. [常见问题](#常见问题)
6. [进阶配置](#进阶配置)

---

## 🏗️ 系统概览

### 你现在拥有什么？

```
商品数据清理系统/
├── product_cleaner.py           ← Python 脚本（本地处理）
├── product_cleaner_web.py       ← Web 应用（可视化界面）
├── ProductCleanerUI.jsx         ← React 组件（高级UI）
├── cleaner_cache.json           ← 缓存文件（自动生成）
├── README.md                    ← 详细使用说明
└── product_cleaner.log          ← 处理日志（自动生成）
```

### 核心能力

| 功能 | Python 脚本 | Web 应用 |
|------|-----------|--------|
| 批量处理 5 万行数据 | ✅ | ✅ |
| 品牌自动补全 | ✅ | ✅ |
| 规格自动提取 | ✅ | ✅ |
| 分类规范化 | ✅ | ✅ |
| 智能缓存 | ✅ | ✅ |
| 断点续传 | ✅ | ❌ |
| 可视化预览 | ❌ | ✅ |
| 对比显示 | ❌ | ✅ |
| 手动编辑 | ❌ | ✅ |

---

## 🚀 快速开始（5分钟）

### 方式一：直接运行 Python 脚本（推荐用于批量处理）

```bash
# 1️⃣ 安装依赖
pip install anthropic google-generativeai pandas openpyxl

# 2️⃣ 设置 API Key (选择其一)
export GEMINI_API_KEY="your-gemini-key"      # 推荐，如果你没有 Claude API
# 或
export ANTHROPIC_API_KEY="sk-your-key-here"  # 原始方案

# 3️⃣ 运行脚本
# 使用 Gemini (推荐):
python product_cleaner.py --input 盒马爬虫-20260422.xlsx --output result.xlsx --provider gemini

# 使用 Claude:
python product_cleaner.py --input 盒马爬虫-20260422.xlsx --output result.xlsx --provider anthropic

# 4️⃣ 等待完成
# 处理完成后生成：
# - result.xlsx                    ← 清理后的数据
# - result_manual_review.xlsx      ← 需要审核的记录
# - cleaner_cache.json             ← 缓存（用于后续快速处理）
```

### 方式二：Web 应用（推荐用于可视化审核）

```bash
# 1️⃣ 安装依赖
pip install flask flask-cors anthropic pandas openpyxl

# 2️⃣ 设置 API Key
export ANTHROPIC_API_KEY="sk-your-key-here"

# 3️⃣ 启动应用
python product_cleaner_web.py

# 4️⃣ 打开浏览器
# 访问 http://localhost:5000
# 然后：
#   1. 上传 Excel 文件
#   2. 预览数据
#   3. 输入 API Key（可选）
#   4. 点击"开始处理"
#   5. 等待完成后下载结果
```

---

## 📋 两种使用方式详解

### 使用方式 A：Python 脚本（完全本地控制）

#### 优点
✅ 更快（没有网络往返开销）
✅ 断点续传支持
✅ 完整的日志和缓存
✅ 可自定义脚本逻辑
✅ 适合 CI/CD 集成

#### 缺点
❌ 没有可视化界面
❌ 需要命令行操作

#### 典型场景
- 定期批量处理（每周/每月）
- 大规模数据集（10万+ 行）
- 与其他系统集成
- 需要完整的审计日志

#### 高级用法

```bash
# 只处理前 1000 行测试
python product_cleaner.py \
  --input data.xlsx \
  --output test_result.xlsx \
  --batch-size 100

# 从中断处继续
python product_cleaner.py \
  --input data.xlsx \
  --output result.xlsx \
  --start-row 5000

# 自定义批处理大小（减少成本）
python product_cleaner.py \
  --input data.xlsx \
  --output result.xlsx \
  --batch-size 1000
```

---

### 使用方式 B：Web 应用（可视化交互）

#### 优点
✅ 上传即用，友好界面
✅ 实时预览数据
✅ 对比原数据和清理后数据
✅ 进度实时显示
✅ 一键下载

#### 缺点
❌ 每次都从头处理（不利用缓存）
❌ 支持的数据量相对较小

#### 典型场景
- 首次测试和演示
- 小数据集（<10,000 行）
- 需要看到处理效果
- 团队协作演示

#### Web 应用工作流

```
上传 Excel
    ↓
预览前 10 行（检查数据）
    ↓
输入 API Key（可选）
    ↓
点击"开始处理"
    ↓
后台线程处理，前端显示进度
    ↓
完成后，下载结果 Excel
```

---

## 🏛️ 系统架构

### 高层架构图

```
┌─────────────────────────────────────────────────────────┐
│                    用户输入                              │
│  (Excel 文件 / 参数配置)                                 │
└──────────────────┬──────────────────────────────────────┘
                   │
        ┌──────────┴──────────┐
        │                     │
        ▼                     ▼
   ┌─────────────┐      ┌──────────────┐
   │ 脚本入口    │      │ Flask Web    │
   │ product_    │      │ 应用         │
   │ cleaner.py  │      │              │
   └──────┬──────┘      └──────┬───────┘
          │                    │
          └──────────┬─────────┘
                     ▼
          ┌──────────────────────┐
          │   数据加载模块       │
          │ (pandas Excel 读取)  │
          └──────────┬───────────┘
                     ▼
          ┌──────────────────────┐
          │   缓存管理模块       │
          │  (避免重复调用 API) │
          └──────────┬───────────┘
                     ▼
          ┌──────────────────────┐
          │  ProductCleanerAgent │
          │  (AI 驱动的清理引擎) │
          │                      │
          │  - 品牌识别          │
          │  - 规格提取          │
          │  - 分类优化          │
          │  - 置信度评分        │
          └──────────┬───────────┘
                     │
          ┌──────────▼───────────┐
          │  Anthropic API       │
          │  (Claude Opus 4)     │
          └──────────┬───────────┘
                     ▼
          ┌──────────────────────┐
          │   结果处理模块       │
          │  - 标记需审核项      │
          │  - 生成审计日志      │
          │  - 保存缓存          │
          └──────────┬───────────┘
                     ▼
          ┌──────────────────────┐
          │    输出结果          │
          │                      │
          │ - cleaned_data.xlsx  │
          │ - manual_review.xlsx │
          │ - cleaner_cache.json │
          │ - product_cleaner.   │
          │   log               │
          └──────────────────────┘
```

### 数据流

```
原始 Excel 数据
   ↓
分批读取（500行/批）
   ↓
检查缓存 ──是→ 使用缓存结果
   ↓ 否
调用 Claude API
   ↓
解析 JSON 响应
   ↓
标记置信度和需审核项
   ↓
保存到缓存
   ↓
积累结果
   ↓
导出 Excel + 审核清单
```

### 成本优化策略

```
总成本 = API 调用数 × 单价

优化方式：
1. 缓存重用      → 减少 API 调用 80%
2. 批处理优化    → 减少 30% 的 token
3. 模型选择      → Sonnet 比 Opus 便宜 50%
4. 字段选择      → 只处理缺失字段
```

---

## ❓ 常见问题

### Q1: 为什么第一次处理比较慢？

**A:** 第一次需要调用 API 处理所有商品。建议：
- 使用 `--batch-size 1000` 加快速度（可能牺牲准确性）
- 或使用 Claude Sonnet 模型（速度快 50%）

### Q2: 如何使用缓存加速后续处理？

**A:** 缓存自动保存在 `cleaner_cache.json`。只要不删除此文件，下次运行会自动使用缓存。

```bash
# 这会因为使用了缓存而快得多
python product_cleaner.py --input data.xlsx --output result_v2.xlsx
```

### Q3: 如何处理 API 超时？

**A:** 
```bash
# 减少批处理大小
python product_cleaner.py --input data.xlsx --batch-size 200
```

### Q4: 如何估算成本？

**A:** 
- 商品数：5 万
- 预期 API 调用：5,000-10,000 次（取决于缺失率）
- 单次成本：约 ¥0.01-0.02
- 总成本：¥50-200

### Q5: 需要人工审核多少条？

**A:** 一般 10-20% 的记录会标记为需要审核（置信度 < 80%），这些都会输出到 `_manual_review.xlsx`。

### Q6: 能否离线运行？

**A:** 不能，需要网络连接到 Anthropic API。但你可以：
- 预先下载并缓存所有结果
- 使用本地大模型（需要修改代码）

### Q7: 大数据集（100万+ 行）怎么处理？

**A:** 分批处理：
```bash
# 分 10 次，每次处理 10 万行
for i in {0..9}; do
  START_ROW=$((i * 100000))
  python product_cleaner.py \
    --input data.xlsx \
    --output result_part_$i.xlsx \
    --start-row $START_ROW
done
```

---

## ⚙️ 进阶配置

### 修改 System Prompt（定制清理规则）

编辑 `product_cleaner.py`，找到 `SYSTEM_PROMPT` 变量：

```python
SYSTEM_PROMPT = """你是一个专业的电商商品数据清理专家。

关键原则：
1. [你的定制规则]
2. [行业特定的规则]
3. [品牌映射规则]
"""
```

### 改用 Claude Sonnet（降低成本 50%）

```python
# 在脚本中找到这一行：
MODEL = "claude-opus-4-20250805"

# 改为：
MODEL = "claude-sonnet-4-20250514"
```

### 调整置信度阈值

```python
# 找到这一行：
CONFIDENCE_THRESHOLD = 0.8  # 80%

# 改为你需要的值，例如 70%：
CONFIDENCE_THRESHOLD = 0.7
```

### 修改批处理大小

```python
# 找到这一行：
BATCH_SIZE = 500  # 每批 500 行

# 改为，例如 1000 行/批：
BATCH_SIZE = 1000
```

### 添加自定义品牌映射

在 `ProductCleanerAgent.clean_product()` 中添加：

```python
# 品牌别名映射
BRAND_ALIASES = {
    'ASAHI/朝日': '朝日',
    'AXE/斧头牌': '斧头牌',
    # ... 更多映射
}
```

---

## 📊 结果文件详解

### cleaned_data.xlsx - 清理后的完整数据

| 列名 | 含义 | 示例 |
|------|------|------|
| `org_spu_code` | 商品代码 | 20400103030 |
| `org_spu_name` | 商品名称 | 金字 飘香火腿块 228g |
| `original_brand` | 原始品牌 | (null) |
| `cleaned_brand` | 清理后品牌 | 金字 |
| `brand_confidence` | 品牌置信度 | 0.95 |
| `cleaned_spec` | 规格 | 228g |
| `spec_confidence` | 规格置信度 | 0.92 |
| `cleaned_cate_l1/l2/l3` | 分类 | 肉禽蛋品 / 火腿 / 火腿块 |
| `cate_confidence` | 分类置信度 | 0.88 |
| `needs_review` | 需要审核？ | false |

### _manual_review.xlsx - 需要人工审核

包含所有 `needs_review = true` 的记录，你需要：
1. 逐行检查
2. 修正错误的清理结果
3. 确认正确的结果
4. 保存为最终版本

### cleaner_cache.json - API 调用缓存

```json
{
  "hash_key_1": {
    "brand": "品牌",
    "spec": "规格",
    "best_category": {...},
    "confidence": 0.85
  },
  ...
}
```

**重要：保留此文件，避免重复调用 API！**

---

## 📞 技术支持

### 查看日志

```bash
# 查看最后 50 行
tail -50 product_cleaner.log

# 持续监听（实时）
tail -f product_cleaner.log

# 搜索错误
grep ERROR product_cleaner.log
```

### 常用命令

```bash
# 查看缓存大小
du -h cleaner_cache.json

# 清空缓存（会重新处理所有商品）
rm cleaner_cache.json

# 查看已处理商品数
jq 'length' cleaner_cache.json
```

---

## 🎓 学习路径

### 第 1 天：快速体验
1. 用前 1000 行测试
2. 看看效果
3. 评估准确率

### 第 2-3 天：调整优化
1. 修改 SYSTEM_PROMPT
2. 调整置信度阈值
3. 添加行业特定规则

### 第 4-5 天：完整处理
1. 处理全部数据
2. 审核 manual_review.xlsx
3. 生成最终结果

---

## 📈 预期结果

对于 5 万行的盒马数据：

| 指标 | 预期值 |
|------|--------|
| 品牌补全率 | 70-85% |
| 规格补全率 | 60-80% |
| 分类准确率 | 85-95% |
| 需审核比例 | 10-20% |
| 处理耗时 | 2-4 小时 |
| 成本 | ¥50-150 |

---

**现在就开始吧！** 🚀

有问题？查看日志文件或检查 README.md。
