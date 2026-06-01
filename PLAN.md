# 完整方案:能力地图驱动的工作流 + Agent 感知与执行

## Context

### 用户的真实需求
1. 不要再造不可扩展的功能。状态机/多角色/条件分支是未来方向,现在的架构不能挡路。
2. Agent 必须能"看懂"——知道用户在哪个面板、选中哪种卡片、那张卡片能做什么。
3. Agent 要能"分析建议 + 确认后执行",分析逻辑可能需要现写(动态计算)。
4. 领域地图一次建全:6 个工作流步骤 + 5 个管理页 + 所有卡片类型 + 跨面板资源联动。
5. 顺手修掉遗留 bug。

### 系统真实结构(已勘查)
```
工作流步骤(6)         独立管理页(5)        共享资源(联动核心)
├ upload 上传&诊断    ├ brand-database     brand-library  (全局)
├ brand-review ──┐   ├ brand-corrections  lexicon        (全局)
│  4卡片:        │   ├ variety-words ──┐  brand-rules    (组级)
│  missing/      │   ├ category-tree   │  category-rules (组级)
│  mismatch/     └──→├ category-classify│  classified-paths(全局)
│  valid/unbranded   │                  │  corrections   (全局)
├ category-review    │                  │
│  4卡片:            │   新增品牌 ───────┘→ 写入 brand-library
│  conflict/marketing/standard/missing
├ ai-process  词库改动 ──→ 影响下次诊断识别
├ review
└ export
```

### 关键勘查结论
- 卡片 DOM **已带真实 ID**:`data-cluster-id`(brand_editor.js:254)、`data-code`(:585)。当前 `_selectedContext` 只读标题文字没读 ID,补读即可。
- 每种卡片的操作都已定位到具体 `window` 函数 + API 端点(见下方能力地图)。
- 后端 Agent 已有 `execute_brand_actions`、`execute_python` 等工具,执行能力有基础。

---

## 重大设计问题(勘查中发现,需纳入改造)

### 设计问题 #1:复核与 AI 绑死(要害,本轮处理)

**现状:** `process_file_async`(app.py,即"AI处理"函数)耦合了两件本该分开的事:
1. 跑 AI — 只处理 `need_ai_items`
2. **生成复核数据** — 合并所有商品(含已确认的 skip_items)、算 4 个标签、产出 `result_df`/`review_file`(app.py:1224-1262)

第 2 件是确定性的、不需要 AI,却被埋在 AI 函数里。后果:用户即使全部手工确认完(`need_ai_items` 为空),也被迫进 AI 步骤才能拿到复核数据。**"复核"不该是"跑完AI",而该是"所有需确认的都确认完即可进入"。**

**改造:**
- 抽出 `finalize_results(session)` — 把 app.py:1224-1262 的"combined→result_df→review_file"逻辑独立成纯函数,零 AI 依赖(复用现有 `_build_result_entry`,它已含 `compute_all_tags`)
- `process_file_async` 重构为:**可选** AI 填充 `need_ai_items` → 调 `finalize_results`
- 新增"进入复核"操作/路由,直接调 `finalize_results`,不经过 AI
- AI 处理从"必经步骤"降级为"仅处理需 AI 子集的可选步骤"
- 工作流逻辑:`need_ai=0` → 直接 finalize → 复核;`need_ai>0` → 可选跑 AI 或手工确认 → finalize → 复核

这与能力地图的资源建模一致:复核读 `ai-results`,而 `ai-results` 应由 `finalize` 产出,AI 只是其中一个可选填充来源。

### 设计问题 #2:改词库/品牌库后当前诊断不刷新(无"重新诊断")

`diagnose_async` 仅在上传/导入/超时触发。编辑词库或品牌库后当前 session 诊断不更新,须重新上传。**线性工作流装不下"管理页→诊断"的反馈环。** 本轮先记录,作为反馈环打通的后续项(能力地图的 `feeds` 已建模此联动)。

### 设计问题 #3/#4/#5(记录,后续清理)

- #3 品牌入库 3 个入口(brand-review modal / 新品牌侧边栏 / 导出),职责重叠
- #4 品牌修正记录只读不可删,错误修正永久污染
- #5 统计口径混算(marketing = 纯营销+冲突;valid 为派生值)

---

## 架构核心:能力地图(Capability Map)= 单一事实源

一份 `capability-map.json`,**前端(TS)和后端(Python Agent)同时读取**,描述:
- **resources** — 共享数据存储 + 联动关系(谁喂给谁)
- **steps/pages** — 面板,每个面板声明它读/写哪些资源
- **cardTypes** — 每个面板内的卡片类型
- **operations** — 每种卡片上的操作(名称 / 前端函数 / API / 写入哪个资源)

这是纯数据 + JSON-serializable,所以:
- 未来加 `roles`、`guard`、`transitions` 不改引擎代码
- 未来可做可视化配置界面(直接编辑 JSON)
- 前后端永远同步(单一来源)

### Schema

```typescript
interface ResourceDef {
  id: string;            // 'brand-library'
  name: string;          // '品牌库'
  scope: 'global' | 'group' | 'session';   // 对应三层隔离
  feeds?: string[];      // 此资源变化会影响哪些 step/resource
}

interface OperationDef {
  id: string;            // 'set_brand'
  name: string;          // '设置品牌'
  fn?: string;           // 前端函数名 'setItemBrand'
  api?: string;          // 'POST /api/brand_rules/save'
  writes?: string[];     // 改动哪些资源 ['brand-rules']
  scope?: 'item' | 'group';  // 单条 or 整组
}

interface CardTypeDef {
  id: string;            // 'missing'
  name: string;          // '品牌缺失'
  meaning: string;       // 给 Agent 看的语义说明
  operations: OperationDef[];
}

interface StepDef {
  id: string;
  name: string;
  kind: 'workflow' | 'page';
  reads?: string[];      // 读哪些资源
  cardTypes?: Record<string, CardTypeDef>;
  tools?: string[];
  transitions?: Record<string, string>;  // 未来用
  roles?: string[];      // 未来用
}

interface CapabilityMap {
  resources: ResourceDef[];
  steps: StepDef[];
}
```

---

## 文件结构

```
src/
  workflow/
    capability-map.json   ← 单一事实源(前后端共读)
    types.ts              ← Schema 接口
    engine.ts             ← 状态机:当前步骤 + 选中卡片 + getContext
  main.ts                 ← 加载 map + 桥接 window

product_cleaner/agent/
  capability_map.py       ← 读同一份 JSON,供 Agent 用
  agent_loop.py           ← 注入工作流上下文到 system prompt
```

---

## 交付顺序(三批,逐批验证)

```
第1批  Phase 0(修bug) + Phase R(复核解耦AI)   ──► 单独验证 ──► commit/push
        ↑ 后端核心改动,先做先验,确认流程对
第2批  Phase A+B+C(能力地图+引擎+前端上下文)   ──► 验证 ──► commit/push
第3批  Phase D(Agent 感知+执行)                ──► 验证 ──► commit/push
```

用户决定:Phase R(复核解耦)**独立先做、单独验证**,因为它重构后端核心流程 `process_file_async`,风险最高。

---

## 实施阶段

### Phase R:复核解耦 AI(第1批,独立验证)

**目标:** 复核不再被 AI 绑死。所有需确认项确认完即可直接进复核。

**步骤:**
1. **抽 `finalize_results(session)`** — 从 `process_file_async`(app.py:1224-1262)抽出"combined→result_df→review_file"逻辑为独立纯函数。输入:session(含 all_items、已有 AI 结果或空)。输出:result_file + review_file。零 AI 依赖,复用 `_build_result_entry`(已含 `compute_all_tags`)。
2. **重构 `process_file_async`** — 改为:(可选)AI 填充 `need_ai_items` → 调 `finalize_results`。保持现有"有 AI"路径行为不变。
3. **新增进入复核路由** — `POST /api/finalize`(或复用复核入口):直接调 `finalize_results`,不经过 AI。前端"进入复核"按钮指向它。
4. **前端衔接** — `review.js`/`ai_process` 流程:`need_ai=0` 时"进入复核"直接 finalize;`need_ai>0` 时提示用户"X 条需 AI,可跑 AI 或手工确认后直接复核"。

**验证(单独):**
- 全部手工确认 → 点"进入复核" → 不触发 AI,直接出复核数据、标签齐全
- 部分需 AI → 跑 AI 后 finalize,行为与改造前一致
- result_df/review_file 内容与改造前对比无回归

---

### Phase 0:修 Bug(第1批,与 Phase R 一起)

| # | 文件 | 问题 | 修法 |
|---|------|------|------|
| 0-0 | `static/js/common.js` | `categorySectionPagination` 未初始化,点分页崩溃(ReferenceError) | 加 `if(typeof window.categorySectionPagination==='undefined') window.categorySectionPagination={};` |
| 0-1 | `core/category_detector.py` | `is_marketing_category()` 重复定义(L39/L441),后者覆盖前者 | L39 改名 `_is_pure_marketing_path()`,同步调用处 |
| 0-2 | `core/cache.py` L63 + `core/ai_engine.py` L631 | `open()` 未关闭句柄 | 改 `with open(...) as f:` |
| 0-3 | `core/category_detector.py` L186 | 正则 `[^\一-龥]` 无效转义 | 改 `[^一-龥]` |
| 0-4 | `core/brand_cluster.py` L526 | 重复 return 死代码 | 删第二行 |
| 0-5 | `core/category_detector.py` | 营销路径过滤逻辑重复两处 | 提取 `_load_marketing_classified_paths()` |
| 0-6 | `CLAUDE.md` | `agent/` 模块未记录、`static/js/` 列表不全 | 补文档 |

**不在本轮**:app.py 拆分(2-3天专项)、brand_cluster O(n²) 优化(数据量小暂不需要)。

---

### Phase A:构建能力地图 `capability-map.json`

按勘查结果,完整填充所有面板。摘录(品牌审核部分):

```jsonc
{
  "resources": [
    {"id":"brand-library","name":"品牌库","scope":"global","feeds":["upload","brand-review","ai-process"]},
    {"id":"lexicon","name":"词库","scope":"global","feeds":["upload"]},
    {"id":"brand-rules","name":"品牌规则","scope":"group","feeds":["ai-process","export"]},
    {"id":"category-rules","name":"分类规则","scope":"group","feeds":["ai-process","export"]},
    {"id":"classified-paths","name":"路径分类标记","scope":"global","feeds":["category-review"]},
    {"id":"corrections","name":"修正记录","scope":"global","feeds":["ai-process"]},
    {"id":"ai-cache","name":"AI结果缓存","scope":"group","feeds":["ai-process"]},
    {"id":"ai-results","name":"AI结果+计算标签","scope":"session","feeds":["review","export"],
      "note":"由 ai-process 的 process_file_async 生成:brand_ai/category_ai/confidence + 4个计算标签(promo/recommend/self_operated/import,compute_all_tags @ app.py:683)。review 只展示编辑,不重算标签"}
  ],
  "steps": [
    {
      "id":"brand-review","name":"品牌审核","kind":"workflow",
      "reads":["brand-library","lexicon"],
      "cardTypes":{
        "missing":{"name":"品牌缺失","meaning":"商品无品牌标签,系统按聚类+词库推荐",
          "operations":[
            {"id":"set_brand","name":"设置品牌","fn":"setItemBrand","api":"POST /api/brand_rules/save","writes":["brand-rules"],"scope":"item"},
            {"id":"batch_set_brand","name":"整组设品牌","fn":"batchSetBrand","api":"POST /api/brand_rules/batch_save","writes":["brand-rules"],"scope":"group"},
            {"id":"add_new_brand","name":"新增品牌","fn":"openAddBrandModal","api":"POST /api/brands/add","writes":["brand-library"],"scope":"item"},
            {"id":"skip","name":"跳过","fn":"skipItem","api":"POST /api/brand_rules/save","writes":["brand-rules"],"scope":"item"}
          ]},
        "mismatch":{"name":"品牌错误","meaning":"已有品牌与建议不符",
          "operations":[
            {"id":"confirm_suggested","name":"改为建议品牌","fn":"applyDropdownBrand","api":"POST /api/brand_rules/batch_save","writes":["brand-rules"],"scope":"group"},
            {"id":"set_brand","name":"设置品牌","fn":"setItemBrand","api":"POST /api/brand_rules/save","writes":["brand-rules"],"scope":"item"},
            {"id":"skip","name":"跳过","fn":"skipGroup","api":"POST /api/brand_rules/batch_save","writes":["brand-rules"],"scope":"group"}
          ]},
        "valid":{"name":"待确认正确","meaning":"识别品牌与标签一致,待确认",
          "operations":[
            {"id":"confirm_valid","name":"确认正确","fn":"confirmValidGroup","api":"POST /api/brand_rules/batch_save","writes":["brand-rules"],"scope":"group"},
            {"id":"skip","name":"跳过","fn":"skipGroup","api":"POST /api/brand_rules/batch_save","writes":["brand-rules"],"scope":"group"}
          ]},
        "unbranded":{"name":"天然无品牌","meaning":"如生鲜,天然无品牌属性",
          "operations":[
            {"id":"confirm_no_brand","name":"确认无品牌","fn":"confirmUnbrandedGroup","api":"POST /api/brand_rules/batch_save","writes":["brand-rules"],"scope":"group"},
            {"id":"skip","name":"跳过","fn":"skipGroup","api":"POST /api/brand_rules/batch_save","writes":["brand-rules"],"scope":"group"}
          ]},
        "new_brand_candidate":{"name":"新品牌候选","meaning":"识别出的新品牌,待人工确认入库(newBrandsSidebar)",
          "operations":[
            {"id":"confirm_to_library","name":"确认入库","fn":"confirmBrandToLibrary","api":"POST /api/brands/add (confirm_to_library=true)","writes":["brand-library","corrections"],"scope":"item"},
            {"id":"edit_then_add","name":"编辑后入库","fn":"openAddBrandModalFromSidebar→submitNewBrandFromModal","api":"POST /api/brands/add","writes":["brand-library"],"scope":"item"},
            {"id":"apply_slash_suggestion","name":"应用斜杠建议名","fn":"applySlashSuggestion","api":"POST /api/brands/add","writes":["brand-library"],"scope":"item"},
            {"id":"dismiss","name":"不是品牌","fn":"dismissNewBrand","api":"POST /api/new_brands/dismiss","writes":["brand-library","brand-rules"],"scope":"item"},
            {"id":"clear_confirmed","name":"清除已入库","fn":"clearConfirmedBrands","writes":[],"scope":"group"}
          ]}
      },
      "transitions":{"BRAND_DONE":"category-review"}
    },
    {
      "id":"ai-process","name":"AI处理","kind":"workflow",
      "reads":["brand-rules","category-rules","brand-library","corrections","ai-cache"],
      "meaning":"把品牌缺失/分类未确认的商品批量交给 AI 单条处理,生成 brand_ai/category_ai + 4个计算标签,结果写入 ai-results 与 ai-cache",
      "operations":[
        {"id":"load_config","name":"加载AI配置","fn":"loadAIConfig","api":"GET /api/settings(electron) | localStorage(web)"},
        {"id":"save_config","name":"保存AI配置","fn":"saveAIConfig","api":"PUT /api/settings(electron) | localStorage(web)"},
        {"id":"start_ai","name":"启动批处理","fn":"startAIProcessing","api":"POST /api/process","writes":["ai-results","ai-cache"],"params":["provider/config_name","model_id","batch_size=20","force_reanalyze"]},
        {"id":"cancel_ai","name":"取消处理","fn":"cancelAI","api":"POST /api/process/cancel"},
        {"id":"poll_progress","name":"进度轮询(被动)","fn":"pollAIProgress","api":"GET /api/status"},
        {"id":"poll_logs","name":"日志轮询(被动)","fn":"pollAILogs","api":"GET /api/ai_logs"}
      ],
      "transitions":{"AI_DONE":"review"}
    },
    {
      "id":"review","name":"复核","kind":"workflow",
      "reads":["ai-results"],
      "meaning":"单条复核 AI 结果。展示 brand_ai/category_ai/规格/4个计算标签/原始标签。标签在 ai-process 已算好,此处只展示与编辑",
      "cardTypes":{
        "review_item":{"name":"复核项","meaning":"单条商品的 AI 结果待复核",
          "operations":[
            {"id":"confirm_item","name":"确认","fn":"confirmItem","api":"POST /api/review/decision (action=confirm)","writes":["ai-results"],"scope":"item"},
            {"id":"modify_item","name":"修改品牌/分类","fn":"editItem→saveEdit","api":"POST /api/review/decision (action=modify)","writes":["ai-results"],"scope":"item"},
            {"id":"export_custom","name":"导出筛选结果","fn":"exportCustom","api":"POST /api/export/custom","scope":"group"},
            {"id":"export_all","name":"导出全部决策","fn":"_reviewExportAll","api":"GET /api/review/export","scope":"group"}
          ]}
      },
      "transitions":{"REVIEW_DONE":"export"}
    },
    {
      "id":"upload","name":"上传&诊断","kind":"workflow",
      "reads":["brand-library","lexicon","classified-paths"],
      "meaning":"上传Excel(必选分组)→后端 diagnose_async 依次:读文件→品牌聚类(BrandClusterEngine.cluster)→分类分析(CategoryDetector.analyze+path_cleaner)→统计聚合。产出 diagnosis_result + 6项统计",
      "operations":[
        {"id":"upload_file","name":"上传文件","fn":"doUpload→triggerFileSelect","api":"POST /api/upload (web) | POST /api/upload_by_path (electron)"},
        {"id":"import_recent","name":"导入最近文件","fn":"importRecentFile","api":"POST /api/import_recent"},
        {"id":"select_group","name":"选择分组","fn":"loadGroups/createGroup/deleteGroup","api":"GET/POST /api/groups, DELETE /api/groups/{id}"},
        {"id":"poll_diag","name":"诊断进度轮询(被动)","fn":"pollDiagnosisStatus","api":"GET /api/diagnosis_status"},
        {"id":"fetch_result","name":"获取诊断结果(被动)","fn":"fetchDiagnosisResult→showDiagnosis","api":"GET /api/diagnosis_result"}
      ],
      "stats":["total","valid","brand_missing","brand_mismatch","marketing","need_ai"],
      "transitions":{"UPLOAD_DONE":"brand-review"}
    },
    {
      "id":"export","name":"导出","kind":"workflow",
      "reads":["ai-results","brand-rules","category-rules"],
      "meaning":"导出结果Excel / 自定义筛选导出 / 把会话识别的动态品牌合并入品牌库",
      "operations":[
        {"id":"export_custom","name":"自定义筛选导出","fn":"exportCustom","api":"POST /api/export/custom","scope":"group"},
        {"id":"preview_to_library","name":"预览导出到品牌库","fn":"showExportPreview","api":"GET /api/brands/dynamic"},
        {"id":"confirm_to_library","name":"确认合并入品牌库","fn":"confirmExportToLibrary","api":"POST /api/brands/export-to-library","writes":["brand-library"],"scope":"group"}
      ]
    },
    {
      "id":"brand-database","name":"品牌库管理","kind":"page","reads":["brand-library"],
      "operations":[
        {"id":"list","name":"加载品牌列表","fn":"renderBrandDatabase","api":"GET /api/brands/list"},
        {"id":"add","name":"新增品牌","fn":"addBrand→openAddBrandModal","api":"POST /api/brands/add","writes":["brand-library"]},
        {"id":"edit","name":"编辑品牌","fn":"editBrand","api":"POST /api/brands/config/type","writes":["brand-library"]},
        {"id":"delete","name":"删除品牌","fn":"deleteBrand","api":"DELETE /api/brands/config","writes":["brand-library"]},
        {"id":"manage_config","name":"管理类型/国家","fn":"manageBrandTypes/manageCountries","api":"POST/DELETE /api/brands/config/type|country","writes":["brand-library"]}
      ]
    },
    {
      "id":"brand-corrections","name":"品牌修正记录","kind":"page","reads":["corrections"],
      "operations":[
        {"id":"list","name":"查看修正记录(只读)","fn":"_renderBrandCorrectionsPage","api":"GET /api/correction/brand"}
      ]
    },
    {
      "id":"variety-words","name":"词库管理","kind":"page","reads":["lexicon"],
      "meaning":"三层:类别→分组→词条。词库变化影响下次诊断的品牌/品种识别",
      "operations":[
        {"id":"add_word","name":"添加词条","fn":"_doAddWord","api":"POST /api/lexicon_words/add_word","writes":["lexicon"]},
        {"id":"delete_word","name":"删除词条","fn":"deleteLexiconWord","api":"POST /api/lexicon_words/delete_word","writes":["lexicon"]},
        {"id":"rename_word","name":"重命名词条","fn":"editLexiconWord","api":"POST /api/lexicon_words/rename_word","writes":["lexicon"]},
        {"id":"add_subgroup","name":"新增分组","fn":"addLexiconSubgroup","api":"POST /api/lexicon_words/add_subgroup","writes":["lexicon"]},
        {"id":"delete_subgroup","name":"删除分组","fn":"deleteLexiconSubgroup","api":"POST /api/lexicon_words/delete_subgroup","writes":["lexicon"]},
        {"id":"rename_subgroup","name":"重命名分组","fn":"renameLexiconSubgroup","api":"POST /api/lexicon_words/rename_subgroup","writes":["lexicon"]}
      ]
    },
    {
      "id":"category-tree","name":"分类路径树","kind":"page","reads":["classified-paths"],
      "operations":[
        {"id":"render_tree","name":"展示三级树","fn":"renderCategoryTreePage","api":"GET /api/classified_paths"},
        {"id":"search_product","name":"搜索商品","fn":"searchProductPage","scope":"local"},
        {"id":"open_product_panel","name":"查看路径下商品","fn":"_openCategoryProductPanel"},
        {"id":"toggle_marketing","name":"切换营销显示","fn":"toggleMarketingPage"}
      ]
    },
    {
      "id":"category-classify","name":"路径分类标记","kind":"page","reads":["classified-paths"],
      "meaning":"标记路径为营销/标准,影响诊断时分类清洗",
      "operations":[
        {"id":"classify_path","name":"标记单路径","fn":"classifyPathPage","api":"POST /api/classify/path","writes":["classified-paths"]},
        {"id":"batch_classify","name":"批量标记(L1/L2)","fn":"batchClassifyPathPage","api":"POST /api/classify/path/batch","writes":["classified-paths"]},
        {"id":"delete_classify","name":"删除标记","fn":"_deleteClassifyPage","api":"DELETE /api/classify/path","writes":["classified-paths"]},
        {"id":"reclassify","name":"剔除营销重分类","fn":"reclassifyExcludeMarketing","api":"GET /api/classify/reclassify","writes":["classified-paths"]}
      ]
    }
  ]
}
```

完整版包含全部 11 个面板的 cardTypes 与 operations,均已逐个 grep 核对函数名/端点。

**诊断流程说明(写入地图,供 Agent 理解):** `diagnose_async`(app.py:351)依次执行 reading→brands(BrandClusterEngine.cluster,产出 missing/mismatch/valid/unbranded 4类聚类+新品牌候选)→categories(CategoryDetector.analyze+path_cleaner,产出 conflict/marketing/standard/missing)→finalizing(统计)。6项统计:total/valid/brand_missing/brand_mismatch/marketing/need_ai。

**标签计算说明(写入地图注释,供 Agent 理解):** 4 个标签由 `tag_computer.compute_all_tags()` 在 AI 处理阶段(`app.py:683`,生成 result_df 时)计算,不在复核阶段重算。促销标签 3 级优先级、自营/进口依赖品牌库 type/country 字段。

---

### Phase B:TS 引擎 `engine.ts` + `types.ts`

`WorkflowEngine` class(约 90 行):
- `constructor(map)` 载入能力地图
- `send(event)` 切换步骤(无 transitions 时降级为直接切 stepId)
- `setSelected(ctx)` / `clearSelected()`
- `getContext()` 返回:当前步骤 + 该步骤 cardTypes + 选中卡片(含真实 ID)+ 该卡片可用 operations + 涉及资源
- `subscribe(fn)` 变化订阅(未来 Agent/React 用)
- 所有"未来扩展"(roles/guard/history-undo)都是在 map 数据或 engine 加方法,不推翻

---

### Phase C:`main.ts` 桥接 + 选中上下文补 ID

`main.ts`:
- 实例化 engine,读 `S.currentStep` 初始化
- 桥接 `window._workflowContext`(getter)、`_wfSend`、`_wfSetSelected`、`_wfClearSelected`

`index.html` 卡片选中处(brand_editor.js 内联段,~1414行附近)增强:
- 在构造 `ctx` 时,补读真实 ID:
  ```javascript
  var idEl = card.closest('[data-cluster-id]') || card.querySelector('[data-cluster-id]');
  if (idEl) ctx.clusterId = idEl.dataset.clusterId;
  var codeEl = card.closest('[data-code]') || card.querySelector('[data-code]');
  if (codeEl) ctx.code = codeEl.dataset.code;
  ```
- 选中后调 `window._wfSetSelected?.(ctx)`,取消时调 `window._wfClearSelected?.()`

侧边栏步骤切换处加 `window._wfSend?.(stepId)`。

---

### Phase D:Agent 感知 + 分析→确认→执行

**D-1 `capability_map.py`**:读同一份 `capability-map.json`,提供 `get_step(id)`、`get_operations(step, cardType)`、`get_resource_links()`。

**D-2 `agent.js`(前端发送)**:
```javascript
context: window._workflowContext || window._selectedContext || null
```

**D-3 `agent_loop.py`(注入上下文)**:
SYSTEM_PROMPT 增加动态段,从 ui_context 读取并说明:
- 当前步骤/面板
- 选中卡片类型 + 其语义 + 真实 ID(clusterId/code)
- 该卡片**可用操作清单**(名称 + 作用 + 写入哪个资源)
- 相关**资源联动**(如"新增品牌会写入品牌库,影响后续识别")

**D-4 执行链路(分析→确认→执行)**:
- 分析:Agent 用现有 `read_*` 工具 + `execute_python`(现写分析逻辑)产出分析报告
- 建议:Agent 用自然语言提出建议操作(引用能力地图里的 operation id)
- 确认:Agent 必须先问用户确认(system prompt 已要求)
- 执行:确认后,Agent 调后端执行工具命中对应 API。复用现有 `execute_brand_actions`;缺口操作(分类规则保存、路径分类等)新增对应执行工具,每个工具内部调用能力地图里 operation 声明的 API 端点逻辑。

---

## 关键文件汇总

| 文件 | 操作 |
|------|------|
| `core/category_detector.py` `cache.py` `ai_engine.py` `brand_cluster.py` `static/js/common.js` `CLAUDE.md` | Phase 0 修 bug |
| `src/workflow/capability-map.json` | 新建(全 11 面板) |
| `src/workflow/types.ts` | 新建 |
| `src/workflow/engine.ts` | 新建 |
| `src/main.ts` | 修改(桥接) |
| `product_cleaner/electron/index.html` | 修改(选中补 ID + send) |
| `product_cleaner/electron/js/agent.js` | 修改(发送 workflow context) |
| `product_cleaner/agent/capability_map.py` | 新建(读同一 JSON) |
| `product_cleaner/agent/agent_loop.py` | 修改(注入上下文) |
| `product_cleaner/agent/tools/tool_execute_*.py` | 按缺口新增执行工具 |

---

## 未来扩展(不推翻引擎)

| 需求 | 怎么加 |
|------|--------|
| 条件分支 | map 的 transitions 加映射 + guard 注册表 |
| 多角色审批 | StepDef/OperationDef 加 roles,执行前校验 |
| Undo/redo | engine 加 history 栈 + undo() |
| 持久化 | getContext() 序列化存 localStorage |
| 可视化配置 | 直接编辑 capability-map.json |
| 新面板/新卡片/新操作 | 只改 JSON,前后端自动同步 |

---

## 验证

1. `npm run build:ts` — 编译通过
2. `python run_server.py` — 启动
3. Console:`window._workflowContext` → 返回 step + cardTypes + selected(含 clusterId/code)+ operations
4. 品牌审核页选中一个 missing 卡片 → context.selected.clusterId 有值、operations 含 set_brand/add_new_brand
5. 切到分类审核 → context.step 变化、cardTypes 变为 conflict/marketing/standard/missing
6. 对 Agent 说"分析我选中的这组品牌" → Agent 回复识别出正确卡片类型、可用操作、并给出分析
7. 对 Agent 说"帮我把这组都设成建议品牌" → Agent 先确认,确认后执行,前端刷新看到结果
8. Python:`from product_cleaner.agent.capability_map import get_operations` 能读到与前端一致的操作清单
