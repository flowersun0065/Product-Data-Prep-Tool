# TypeScript 模块化 + 工作流引擎改造计划

## 背景

Electron 前端当前是原生 JS，所有函数/变量挂在 `window` 全局，无模块化、无状态管理、无类型定义。工作流步骤硬编码在 HTML 里。Agent 只能拿到 `{ type, name }` 的简单上下文，不知道用户在哪个步骤、能做什么操作。

### 目标
1. TypeScript 模块化 — 新代码用 TS 写，逐步替换老 JS
2. 集中状态管理 — 替代散落的全局变量
3. 工作流引擎 — 步骤可配置、状态可查询、Agent 可感知
4. 保持现有功能不变 — 每步验证，零回归

### 已完成
- **Phase 1: Vite + TS 基础设施** ✅
  - `vite.config.ts` + `tsconfig.json` 已创建
  - `src/main.ts` 输出 `product_cleaner/static/dist/bundle.js`
  - `index.html` 已加载 bundle，Console 可见 `[TS] bundle loaded`
  - `npm run build:ts` / `npm run dev:ts` 可用

---

## Phase 2: state.ts — 集中状态

### 目标
把 `static/js/common.js` 的 14 个全局变量搬到 `src/state.ts`，定义 TypeScript 接口，通过 `window` 桥接让老 JS 无感知。

### 当前 common.js 内容（product_cleaner/static/js/common.js）

```javascript
var sessionId = null;
var diagnosisData = null;
var brandRules = {};        // {code: {brand, no_brand, skipped}}
let categoryRules = {};     // {code: {action, replacement}}
let marketingTags = {};     // {code: [paths]}
let categoryOptions = { level1: [], level2_by_level1: {}, level3_by_level2: {} };
var newBrands = [];
let currentPanelData = null;
let currentPanelPage = 1;
let currentPanelFilter = '';
const ITEMS_PER_PAGE = 20;
var brandDatabase = [];
let groupPagination = { missing: {page:1,perPage:10}, mismatch: {page:1,perPage:10}, valid: {page:1,perPage:10}, unbranded: {page:1,perPage:10} };
// + previewImage() 函数
// + toggleSection() 函数
```

### 步骤

#### Step 1: 创建 `src/types.ts` — 定义核心数据接口

```typescript
export interface CodeItem {
  code: string;
  name: string;
  row?: number;
  org_image_url?: string;
  suggested_path?: string[];
  all_paths?: string[];
  marketing_paths?: string[];
  standard_paths?: string[];
  _section?: 'standard' | 'conflict' | 'marketing' | 'missing';
  factors?: Record<string, any>;
}

export interface BrandCluster {
  cluster_id: string;
  brands: string[];
  suggested_standard: string;
  count: number;
  has_issue: boolean;
  issue_type: string;
  type: string;
  items: CodeItem[];
}

export interface CategoryOptions {
  level1: string[];
  level2_by_level1: Record<string, string[]>;
  level3_by_level2: Record<string, string[]>;
}

export interface DiagnosisData {
  brand_clusters: BrandCluster[];
  all_codes: CodeItem[];
  category_options: CategoryOptions;
  cleaned_paths: Record<string, string[]>;
  path_classifications: Record<string, { label: string }>;
  conflict_groups: any[];
  marketing_groups: any[];
  standard_groups: any[];
  missing_items: any[];
}

export interface GroupPagination {
  missing: { page: number; perPage: number };
  mismatch: { page: number; perPage: number };
  valid: { page: number; perPage: number };
  unbranded: { page: number; perPage: number };
}
```

#### Step 2: 创建 `src/state.ts` — 集中状态 + window 桥接

```typescript
import type { DiagnosisData, CategoryOptions, GroupPagination } from './types';

export const state = {
  sessionId: null as string | null,
  diagnosisData: null as DiagnosisData | null,
  brandRules: {} as Record<string, any>,
  categoryRules: {} as Record<string, any>,
  marketingTags: {} as Record<string, string[]>,
  categoryOptions: { level1: [], level2_by_level1: {}, level3_by_level2: {} } as CategoryOptions,
  newBrands: [] as any[],
  currentPanelData: null as any,
  currentPanelPage: 1,
  currentPanelFilter: '',
  ITEMS_PER_PAGE: 20,
  brandDatabase: [] as any[],
  groupPagination: {
    missing: { page: 1, perPage: 10 },
    mismatch: { page: 1, perPage: 10 },
    valid: { page: 1, perPage: 10 },
    unbranded: { page: 1, perPage: 10 },
  } as GroupPagination,
};

// 桥接到 window — 老 JS 读写 window.xxx 时自动同步到 state
Object.keys(state).forEach((key) => {
  Object.defineProperty(window, key, {
    get: () => (state as any)[key],
    set: (v: any) => { (state as any)[key] = v; },
    configurable: true,
  });
});
```

#### Step 3: 修改 `src/main.ts`

```typescript
import './state';
console.log('[TS] bundle loaded, state initialized');
```

#### Step 4: 修改 `static/js/common.js` — 删掉变量声明，只保留函数

删掉第 1-22 行的变量声明。保留 `previewImage()` 和 `toggleSection()` 函数。

注意：bundle.js 在所有 JS 之后加载（index.html 末尾），但 common.js 在最前面。所以需要调整 bundle.js 的加载位置到 common.js 之后、其他 JS 之前。

具体：在 `index.html` 中把 `<script src="/static/dist/bundle.js">` 从末尾移到 `<script src="/static/js/common.js">` 之后。

### 验证
1. `npm run build:ts`
2. 重启 Flask，刷新页面
3. Console 无报错，`[TS] bundle loaded, state initialized` 可见
4. 上传文件 → 诊断 → 品牌审核 → 分类审核 → 全部功能正常
5. 在 Console 输入 `state`（import 的模块不可直接访问），但 `window.diagnosisData` 应该正常返回数据

### 风险
- `Object.defineProperty` 在 common.js 加载前就设置了 getter/setter，所以 common.js 的变量声明会被 setter 拦截
- 如果 common.js 用 `var` 声明同名变量，可能导致冲突 — 需要删掉 common.js 的声明

---

## Phase 3: workflow.ts — 工作流引擎

### 目标
定义工作流描述结构，跟踪当前步骤和上下文，暴露给 Agent。

### 步骤

#### Step 1: 创建 `src/workflow/types.ts`

```typescript
export interface WorkflowStep {
  id: string;
  name: string;
  tools: string[];           // 该步骤可用的工具名
  dataKey?: string;           // 该步骤关联的 state key（如 'brandRules'）
}

export interface WorkflowDefinition {
  id: string;
  name: string;
  steps: WorkflowStep[];
}

export interface WorkflowContext {
  workflow: string;
  step: string;
  stepName: string;
  tools: string[];
  selected: any | null;
  session: { id: string | null; fileName: string };
  pending?: number;
}
```

#### Step 2: 创建 `src/workflow/engine.ts`

```typescript
import type { WorkflowDefinition, WorkflowContext, WorkflowStep } from './types';
import { state } from '../state';

let _currentWorkflow: WorkflowDefinition | null = null;
let _currentStepId: string = '';
let _selectedContext: any = null;

export function registerWorkflow(def: WorkflowDefinition) {
  _currentWorkflow = def;
  _currentStepId = def.steps[0]?.id || '';
}

export function goToStep(stepId: string) {
  if (!_currentWorkflow) return;
  const step = _currentWorkflow.steps.find(s => s.id === stepId);
  if (step) _currentStepId = stepId;
}

export function setSelected(ctx: any) {
  _selectedContext = ctx;
}

export function clearSelected() {
  _selectedContext = null;
}

export function getContext(): WorkflowContext {
  const step = _currentWorkflow?.steps.find(s => s.id === _currentStepId);
  return {
    workflow: _currentWorkflow?.name || '',
    step: _currentStepId,
    stepName: step?.name || '',
    tools: step?.tools || [],
    selected: _selectedContext,
    session: {
      id: state.sessionId,
      fileName: '',  // 从 session 数据获取
    },
  };
}

// 桥接：替代 window._selectedContext
Object.defineProperty(window, '_workflowContext', {
  get: () => getContext(),
});
```

#### Step 3: 创建 `src/workflow/product-cleaning.ts` — 当前工作流定义

```typescript
import type { WorkflowDefinition } from './types';

export const productCleaningWorkflow: WorkflowDefinition = {
  id: 'product-cleaning',
  name: '商品数据清洗',
  steps: [
    {
      id: 'upload',
      name: '上传 & 诊断',
      tools: ['upload_file', 'run_diagnosis'],
    },
    {
      id: 'brand-review',
      name: '品牌审核',
      tools: ['set_brand', 'skip_brand', 'add_brand', 'batch_apply_suggestion'],
      dataKey: 'brandRules',
    },
    {
      id: 'category-review',
      name: '分类审核',
      tools: ['set_category', 'skip_category', 'mark_marketing', 'batch_confirm'],
      dataKey: 'categoryRules',
    },
    {
      id: 'ai-process',
      name: 'AI 处理',
      tools: ['start_ai', 'cancel_ai', 'select_config'],
    },
    {
      id: 'review',
      name: '复核',
      tools: ['confirm_item', 'modify_item', 'export_custom'],
    },
    {
      id: 'export',
      name: '导出',
      tools: ['export_result', 'export_to_library'],
    },
  ],
};
```

#### Step 4: 修改 `src/main.ts`

```typescript
import './state';
import { registerWorkflow, goToStep, setSelected, clearSelected } from './workflow/engine';
import { productCleaningWorkflow } from './workflow/product-cleaning';

registerWorkflow(productCleaningWorkflow);

// 桥接：让老 JS 的 navigateToStep 同步到工作流引擎
const _origNavigate = (window as any).navigateToStep;
if (_origNavigate) {
  (window as any).navigateToStep = function(step: string) {
    goToStep(step);
    _origNavigate(step);
  };
}

// 桥接：卡片选择同步
(window as any)._setWorkflowSelected = setSelected;
(window as any)._clearWorkflowSelected = clearSelected;

console.log('[TS] workflow engine initialized');
```

#### Step 5: 修改 index.html 卡片选择处理器

在 `window._selectedContext = ctx;` 之后加一行：
```javascript
if (typeof _setWorkflowSelected === 'function') _setWorkflowSelected(ctx);
```

在 `window._selectedContext = null;` 之后加一行：
```javascript
if (typeof _clearWorkflowSelected === 'function') _clearWorkflowSelected();
```

#### Step 6: 修改 agent.js — 传完整上下文给后端

```javascript
// 原来：context: window._selectedContext || null
// 改为：
context: window._workflowContext || window._selectedContext || null
```

### 验证
1. `npm run build:ts`
2. 刷新页面，切换步骤
3. Console 输入 `window._workflowContext`，确认返回完整上下文
4. 在品牌审核页选中一个卡片，再查 `window._workflowContext`，确认 selected 有值
5. Agent 对话，检查后端收到的 context 是否完整

---

## Phase 4: Agent 感知工作流

### 目标
后端 Agent 读取工作流上下文，自动知道当前步骤和可用工具。

### 步骤
修改 `product_cleaner/agent/agent_loop.py`，在处理用户消息时读取 `context.workflow`、`context.step`、`context.tools`，动态过滤可用工具。

这一步等 Phase 3 完成并验证后再详细设计。

---

## 后续迁移路线

Phase 2-4 完成后，可以逐步迁移老 JS 文件到 TS 模块：

| 优先级 | 文件 | 说明 |
|:---:|------|------|
| 1 | `common.js` | Phase 2 已处理 |
| 2 | `timeline.js` + `timeline_utils.js` | Electron 专属，无共享依赖 |
| 3 | `category-tree.js` + `category_review_electron.js` | Electron 专属 |
| 4 | `brand-library.js` + `variety_words.js` | Electron 专属，独立页面 |
| 5 | `brand_editor_electron.js` | 最大的文件，依赖 brand_editor.js 的核心函数 |
| 6 | `ai_process_electron.js` | 依赖 ai_process.js 的核心流程 |
| 7 | `review_electron.js` | 依赖 detail-panel.js |
| 8 | `settings.js` + `agent.js` + `task_panel.js` | 相对独立 |

每个文件迁移模式相同：
1. 在 `src/` 创建 `.ts` 模块
2. 从老 JS 抽取逻辑到 TS
3. 通过 window 桥接保持兼容
4. 验证功能正常
5. 从 index.html 移除老 `<script>` 标签

---

## 文件结构（最终目标）

```
src/
  main.ts                    ← 入口
  types.ts                   ← 全局类型定义
  state.ts                   ← 集中状态 + window 桥接
  workflow/
    types.ts                 ← 工作流类型
    engine.ts                ← 工作流引擎
    product-cleaning.ts      ← 当前工作流定义
  modules/                   ← 迁移后的页面模块（后续）
    timeline.ts
    brand-review.ts
    category-review.ts
    ai-process.ts
    review.ts
    ...
```

---

## 关键约束

- **每步一个 commit**，可独立回退
- **先加后删** — 新模块先通过 window 桥接工作，验证后再删老文件
- **不改 Python 后端**（Phase 4 之前）
- **不引入 React/Vue** — 保持原生 DOM 操作
- **中文注释**
