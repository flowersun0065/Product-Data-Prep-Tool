// ═══ Bat Hover Tips Config ═══
// 集中维护蝙蝠 hover 解说文案，不在 HTML 里散落 data-bat-tip 属性。
// initDeclarativeSystem 遍历此表绑定 hover 事件。
//
// 字段：
//   tip — 蝙蝠飞到目标时显示的气泡文案
//   ox  — 水平偏移 (px)，默认 0
//   oy  — 垂直偏移 (px)，默认 -12

var BAT_TIPS = {
  // ── 上传区 ──
  '#tlDrop':   { tip: '点击或拖拽上传诊断文件，我会自动分析品牌和分类', ox: 40, oy: -45 },

  // ── 统计卡片 ──
  '#stat-total':   { tip: '本次任务清洗的数据源行数总和', ox: 0, oy: -50 },
  '#stat-ok':      { tip: '匹配成功的无歧义高内聚标准品牌总数', ox: 0, oy: -50 },
  '#stat-missing': { tip: '品牌词库中不存在、等待人工审计的品牌', ox: 0, oy: -50 },
  '#stat-clash':   { tip: '多级冲突或类目归属歧义诊断总数', ox: 0, oy: -50 },

  // ── Timeline 节点 ──
  '#tlStep1': { tip: '数据装载阶段已成功读取源文件数据', ox: 40, oy: -45 },
  '#tlStep2': { tip: '品牌库关联分析完成，筛选出高疑新品牌', ox: 40, oy: -45 },
  '#tlStep3': { tip: '多级分类归集正在执行人工确权', ox: 40, oy: -45 },
  '#tlStep4': { tip: '精简数据链路后将打包生成标准映射模型', ox: 40, oy: -45 },

  // ── 品牌审核 tab ──
  '#emBrandTabs': { tip: '在这核查和修正 AI 诊断出的品牌问题。缺失 = 找不到匹配品牌；错误 = 疑似标错品牌', ox: 80, oy: -25 },

  // ── 品牌组卡片（hover 时动态注册选择器 .brand-group-item） ──
  // 分类树节点（hover 时动态注册选择器 .tree-node-row） ──
  // 以上在 initDeclarativeSystem 中遍历容器批量绑定，不写死选择器
};
