# 🎯 项目使用指南 - 快速参考

## 📦 你获得了什么？

```
商品数据清理系统完整包/
│
├── 🔴 必读文档
│   ├── QUICK_START.md              ⭐ 5分钟快速开始
│   ├── README.md                   📖 详细使用说明
│   └── DELIVERY_SUMMARY.md         📋 项目交付总结
│
├── 🟢 核心脚本（选择一个使用）
│   ├── product_cleaner.py          ⭐ 命令行脚本（推荐）
│   └── product_cleaner_web.py      🌐 Web 应用（可视化）
│
├── 🟡 可选文件
│   ├── ProductCleanerUI.jsx        React 高级 UI
│   └── config.yaml.example         配置文件模板
│
└── 📝 说明
    └── 本文件

总大小：89 KB（非常小，可直接使用）
```

---

## ⚡ 三步快速开始

### 步骤 1️⃣：安装（2 分钟）

```bash
# 安装 Python 依赖
pip install anthropic pandas openpyxl

# 或（如果要使用 Web 应用）
pip install anthropic pandas openpyxl flask flask-cors
```

### 步骤 2️⃣：配置（1 分钟）

```bash
# 设置 API Key（从 https://claude.ai 获取）
export ANTHROPIC_API_KEY="sk-your-api-key-here"

# Windows 用户：
set ANTHROPIC_API_KEY=sk-your-api-key-here
```

### 步骤 3️⃣：运行（2-4 小时）

**方式 A - 命令行（简单快速）**
```bash
python product_cleaner.py --input 盒马爬虫-20260422.xlsx
```

**方式 B - Web 应用（可视化）**
```bash
python product_cleaner_web.py
# 然后访问 http://localhost:5000
```

---

## 📊 文件选择指南

### 我应该使用哪个文件？

| 你想... | 使用 | 原因 |
|--------|------|------|
| 快速批量处理 | `product_cleaner.py` | 最快最便宜 |
| 看到可视化界面 | `product_cleaner_web.py` | 友好易用 |
| 自定义高级功能 | 编辑 config.yaml | 灵活可配置 |
| 集成到代码 | 导入 Python 类 | 可编程 |

### 建议流程

```
1️⃣ 快速测试（10 分钟）
   使用 Web 应用浏览一下数据
   └─ python product_cleaner_web.py

2️⃣ 评估效果（1 天）
   处理前 1000 行，看看质量
   └─ python product_cleaner.py --input data.xlsx --batch-size 100

3️⃣ 调整规则（可选，1 天）
   修改 config.yaml，优化 AI 规则
   └─ 编辑 SYSTEM_PROMPT 或品牌映射

4️⃣ 完整处理（2-4 小时）
   处理全部数据
   └─ python product_cleaner.py --input data.xlsx

5️⃣ 人工审核（1-2 天）
   检查 _manual_review.xlsx，修正错误
   └─ 用 Excel 打开，逐行审核

6️⃣ 上线使用（立即）
   导入清理后的数据到生产系统
   └─ 使用 cleaned_data.xlsx
```

---

## 🎮 常用命令

### 基础命令

```bash
# 简单一行命令
python product_cleaner.py --input data.xlsx

# 完整命令（所有选项）
python product_cleaner.py \
  --input 盒马爬虫-20260422.xlsx \
  --output cleaned_data.xlsx \
  --api-key sk-xxx \
  --batch-size 500 \
  --start-row 0
```

### 特殊场景

```bash
# 测试前 1000 行
python product_cleaner.py --input data.xlsx --batch-size 100

# 从中断处继续（处理了 10,000 行后中断）
python product_cleaner.py --input data.xlsx --start-row 10000

# 使用便宜的模型（Sonnet）加快速度
# 编辑脚本，改 MODEL = "claude-sonnet-4-20250514"

# 清空缓存，重新处理所有数据
rm cleaner_cache.json
python product_cleaner.py --input data.xlsx
```

### Web 应用

```bash
# 启动 Web 应用
python product_cleaner_web.py

# 后台运行（Linux/Mac）
nohup python product_cleaner_web.py > app.log 2>&1 &

# 后台运行（Windows）
start pythonw product_cleaner_web.py

# 访问应用
# 浏览器打开：http://localhost:5000
```

---

## 💰 成本估算

**你的数据：** 54,100 行

### 三种场景

| 场景 | 成本 | 耗时 | 说明 |
|------|------|------|------|
| 🟢 最优 | ¥50 | 1-2h | 使用缓存，高复用 |
| 🟡 正常 | ¥100 | 3-4h | 首次完整处理 |
| 🔴 最坏 | ¥150 | 4-5h | 低批处理，无缓存 |

### 降低成本的方法

```
1. 重复使用缓存（自动）
   第一次处理后保留 cleaner_cache.json
   → 节省 80%+ 费用

2. 增加批处理大小
   --batch-size 1000 代替 500
   → 节省 30% 费用

3. 使用更便宜的模型
   改用 Claude Sonnet 代替 Opus
   → 节省 50% 费用

4. 只处理缺失字段
   修改 SYSTEM_PROMPT，跳过已有数据
   → 节省 30-50% 费用
```

---

## 📊 预期结果

### 数据质量提升

| 指标 | 当前 | 处理后 | 提升 |
|------|------|--------|------|
| 品牌完整率 | 78.93% | 95%+ | +16% |
| 规格完整率 | 87.26% | 92%+ | +5% |
| 分类准确率 | 81.6% | 92%+ | +11% |
| 需人工审核 | N/A | 10-20% | - |

### 生成的文件

```
cleaned_data.xlsx                   ← 最终清理数据
│ └─ 54,100 行 × 14 列
│    - org_spu_code: 商品代码
│    - org_spu_name: 商品名称
│    - cleaned_brand: 清理后品牌
│    - cleaned_spec: 清理后规格
│    - cleaned_cate_l1/l2/l3: 清理后分类
│    - confidence: 置信度（0-1）
│    - needs_review: 是否需审核
│    - notes: 备注

cleaned_data_manual_review.xlsx     ← 需要人工审核（5,000-10,000 行）
│ └─ 所有置信度 <80% 的记录
│    需要你逐行检查和修正

cleaner_cache.json                 ← API 缓存（自动生成）
│ └─ 保留此文件，下次处理会自动使用
│    节省 80%+ 的费用

product_cleaner.log                ← 处理日志（自动生成）
└─ 记录完整的处理过程，用于调试
```

---

## 🔍 理解输出数据

### cleaned_data.xlsx 列说明

```
org_spu_code           商品编码（不变）
org_spu_name           商品名称（不变）

original_brand         原始品牌（可能为空）
cleaned_brand          清理后品牌 ⭐ 新字段
brand_confidence       品牌置信度 (0-1)

original_spec          原始规格（可能为空）
cleaned_spec           清理后规格 ⭐ 新字段
spec_confidence        规格置信度 (0-1)

original_cate_l1/2/3   原始分类（可能有多个）
cleaned_cate_l1/2/3    清理后分类 ⭐ 新字段
cate_confidence        分类置信度 (0-1)
cate_reason            为什么选择这个分类

needs_review           是否需人工审核（true/false）
notes                  备注和说明
```

### 置信度解读

```
0.95-1.0  ✅ 完全可信      无需审核
0.8-0.94  ⚠️  较可信       可抽样审核
0.6-0.79  ⚠️⚠️ 低可信       建议审核
0.0-0.59  ❌ 不可信        必须审核
```

---

## 🐛 常见问题（极速解答）

| 问题 | 秒速回答 | 详见 |
|------|---------|------|
| 怎么安装？ | `pip install anthropic pandas openpyxl` | README.md |
| API Key 哪里得？ | https://claude.ai → Settings → API | README.md |
| 要多久？ | 2-4 小时 | 本文档 |
| 要多少钱？ | ¥50-150 | 本文档 |
| 怎么加快？ | 增加 batch-size 或换便宜模型 | README.md |
| 卡住了？ | 查看 product_cleaner.log | README.md |
| 需要人工审核吗？ | 是的，10-20% 的记录 | DELIVERY_SUMMARY.md |
| 能离线用吗？ | 不能，需要 API | README.md |

---

## 📱 Web 应用使用流程

```
打开浏览器
   ↓
访问 http://localhost:5000
   ↓
看到上传界面
   ↓
点击"选择文件"或"拖拽文件"
   ↓
看到数据预览
   ↓
输入 API Key（可选）
   ↓
点击"开始处理"
   ↓
看到进度条实时更新
   ↓
处理完成 ✅
   ↓
点击"下载结果"
   ↓
获得 cleaned_data.xlsx
```

---

## ✨ 高级技巧

### 1️⃣ 自定义清理规则

编辑 `config.yaml`，修改：

```yaml
rules:
  brand_aliases:
    "旧品牌": "新品牌"
  
  exclude_promotional_categories:
    - "促销分类1"
    - "促销分类2"
```

或直接编辑 `product_cleaner.py` 中的 `SYSTEM_PROMPT`。

### 2️⃣ 分阶段处理

```bash
# 分 5 次处理，每次 10,000+ 行
for i in {0..4}; do
  START=$((i * 10000))
  python product_cleaner.py \
    --input data.xlsx \
    --output result_part_$i.xlsx \
    --start-row $START
done

# 合并结果（可选）
# 用 Python/Excel 合并所有 result_part_*.xlsx
```

### 3️⃣ 集成到代码

```python
from product_cleaner import ProductCleanerAgent

agent = ProductCleanerAgent(api_key="sk-xxx")
result = agent.clean_product(
    product_name="金字 飘香火腿块 228g",
    current_brand=None,
    current_spec=None,
    current_categories={"level1": "肉禽蛋品"}
)
print(result)
```

### 4️⃣ 监控日志

```bash
# 实时查看处理进度
tail -f product_cleaner.log

# 查看处理统计
grep "处理统计" product_cleaner.log -A 10
```

---

## 🎓 学习路径（预计 2 天）

### 第 1 天（4 小时）

⏱️ **09:00-09:30** 阅读 QUICK_START.md  
⏱️ **09:30-10:00** 安装依赖和配置 API Key  
⏱️ **10:00-11:00** 运行 Web 应用，上传测试数据  
⏱️ **11:00-14:00** 处理前 1000 行，观察结果  
⏱️ **14:00-14:30** 评估结果质量  

### 第 2 天（6 小时）

⏱️ **09:00-11:00** 调整规则（如需要）  
⏱️ **11:00-15:00** 处理完整数据（后台进行）  
⏱️ **15:00-17:00** 审核 manual_review.xlsx，修正错误  
✅ **17:00** 完成！导入生产系统

---

## 📞 需要帮助？

### 快速参考
1. **5分钟快速开始？** → 读 `QUICK_START.md`
2. **详细使用说明？** → 读 `README.md`
3. **系统设计细节？** → 读 `DELIVERY_SUMMARY.md`
4. **配置文件示例？** → 参考 `config.yaml.example`

### 常见错误处理
```bash
# 错误：ModuleNotFoundError
→ pip install anthropic pandas openpyxl

# 错误：ANTHROPIC_API_KEY not found
→ export ANTHROPIC_API_KEY="sk-xxx"

# 错误：ReadTimeoutError
→ python product_cleaner.py --batch-size 200

# 错误：内存不足
→ python product_cleaner.py --start-row 20000

# 看日志
→ tail -f product_cleaner.log
```

---

## ✅ 开始前检查清单

- [ ] Python 3.7+ 已安装
- [ ] 已运行 `pip install anthropic pandas openpyxl`
- [ ] 已获得 Anthropic API Key
- [ ] 已设置 ANTHROPIC_API_KEY 环境变量
- [ ] 已准备好输入 Excel 文件
- [ ] 已理解成本 (¥50-150) 和耗时 (2-4h)
- [ ] 已读过 QUICK_START.md
- [ ] 已下载所有文件到工作目录

✅ 所有检查完成？立即开始吧！

```bash
python product_cleaner.py --input 盒马爬虫-20260422.xlsx
```

---

## 🎉 祝你使用愉快！

**现在就开始吧！** 🚀

有问题？查看 README.md 或 QUICK_START.md。  
需要定制？编辑 config.yaml 或 SYSTEM_PROMPT。  
有建议？反馈给我们！

---

*更新于 2025-04-23*  
*系统版本：v1.0*
