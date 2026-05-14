#!/usr/bin/env python3
"""
HTML 模板 V2 - 支持品牌编辑功能
"""

# 主页面 HTML 模板
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>商品数据清理系统 </title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        .marketing-tag { background: #dc2626; color: white; padding: 2px 6px; border-radius: 4px; font-size: 12px; }
        .valid-tag { background: #16a34a; color: white; padding: 2px 6px; border-radius: 4px; font-size: 12px; }
        .missing-tag { background: #f59e0b; color: white; padding: 2px 6px; border-radius: 4px; font-size: 12px; }
        .mismatch-tag { background: #ef4444; color: white; padding: 2px 6px; border-radius: 4px; font-size: 12px; }
        .process-tag { background: #3b82f6; color: white; padding: 2px 6px; border-radius: 4px; font-size: 12px; }
        /* 修复暗色模式下极其刺眼的粉色高亮，改为柔和的深红底加边框 */
        .highlight-marketing { background-color: rgba(153, 27, 27, 0.2) !important; border-left: 2px solid #ef4444 !important; }

        .side-panel { position: fixed; top: 0; right: -600px; width: 600px; height: 100vh; background: #1e293b; transition: right 0.3s ease; z-index: 1000; overflow-y: auto; box-shadow: -4px 0 20px rgba(0,0,0,0.5); }
        .side-panel.open { right: 0; }
        .side-panel-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 999; display: none; }
        .side-panel-overlay.open { display: block; }

        /* 统一使用 Tailwind 间距，移除冗余的 margin/padding，增加容器感 */
        .group-card { background: #1e293b; padding: 16px; border: 1px solid rgba(71,85,105,0.5); border-radius: 8px; margin-bottom: 16px; border-left: 4px solid; box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05); }
        .group-card.missing { border-left-color: #f59e0b; }
        .group-card.mismatch { border-left-color: #ef4444; }
        .group-card.valid { border-left-color: #3b82f6; }
        .group-card.collapsed { padding: 12px 16px; }
        .group-card.collapsed .group-details { display: none; }
        .group-toggle { cursor: pointer; user-select: none; }
        .group-toggle::before { content: '\25bc '; font-size: 10px; color: #94a3b8; margin-right: 4px; display: inline-block; transition: transform 0.2s;}
        .group-card.collapsed .group-toggle::before { transform: rotate(-90deg); }

        /* 行对齐优化 */
        .item-row { background: rgba(15, 23, 42, 0.4); border: 1px solid rgba(71,85,105,0.3); border-radius: 6px; padding: 10px 12px; margin-bottom: 8px; }
        .item-row.processed { opacity: 0.6; border-left: 3px solid #10b981; }
        .item-row.skipped { border-left: 3px solid #6b7280; }

        #missingGroupsSection.collapsed #missingGroups, #mismatchGroupsSection.collapsed #mismatchGroups, #validGroupsSection.collapsed #validGroups,
        #unbrandedSection.collapsed #unbrandedGroups, #categoryConflictSection.collapsed #categoryConflictGroups,
        #categoryMarketingSection.collapsed #categoryMarketingGroups, #categoryStandardSection.collapsed #categoryStandardGroups,
        #categoryMissingSection.collapsed #categoryMissingGroups { display: none; }

        #missingGroupsSection.collapsed .mt-4, #mismatchGroupsSection.collapsed .mt-4,
        #validGroupsSection.collapsed .mt-4, #unbrandedSection.collapsed .mt-4 { display: none; }

        .brand-dropdown-wrapper { position: relative; display: inline-block; min-width: 180px; }
        .brand-dropdown-input { width: 100%; padding: 6px 10px; background: #475569; border: 1px solid #64748b; border-radius: 6px; color: white; font-size: 13px; cursor: pointer; }
        .brand-dropdown-input:focus { outline: none; border-color: #3b82f6; }
        .brand-dropdown-list { position: absolute; top: 100%; left: 0; right: 0; max-height: 300px; overflow-y: auto; background: #1e293b; border: 1px solid #475569; border-radius: 6px; z-index: 1001; display: none; box-shadow: 0 8px 16px rgba(0,0,0,0.4); }
        .brand-dropdown-list.open { display: block; }
        .brand-dropdown-item { padding: 8px 12px; cursor: pointer; border-bottom: 1px solid #334155; }
        .brand-dropdown-item:hover { background: #334155; }
        .brand-dropdown-item.selected { background: #1d4ed8; }

        .export-modal { position: fixed; inset: 0; z-index: 1002; display: none; }
        .export-modal.open { display: block; }
        .export-modal-overlay { position: absolute; inset: 0; background: rgba(0,0,0,0.6); }
        .export-modal-content { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); background: #1e293b; border-radius: 12px; padding: 24px; width: 600px; max-height: 70vh; overflow: hidden; box-shadow: 0 20px 40px rgba(0,0,0,0.5); }

        .new-brands-sidebar { position: fixed; top: 80px; right: 20px; width: 340px; max-height: calc(100vh - 100px); background: rgba(30,41,59,0.95); backdrop-filter: blur(10px); border: 1px solid rgba(71,85,105,0.5); border-radius: 12px; padding: 16px; z-index: 900; display: flex; flex-direction: column; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.3); overflow: hidden; }
        .new-brands-sidebar.hidden { display: none; }
        .sidebar-list { overflow-y: auto; flex: 1; margin-top: 12px; min-height: 0; }
    </style>
</head>
<body class="bg-slate-900 min-h-screen text-white antialiased">

<!-- 顶部导航栏，稳定页面骨架 -->
<header class="bg-slate-800 border-b border-slate-700/50 sticky top-0 z-50 h-16">
    <div class="max-w-[1600px] mx-auto px-6 h-full flex items-center justify-between">
        <h1 class="text-lg font-bold text-slate-100 flex items-center gap-2 tracking-tight">
            商品数据清理系统
        </h1>
        <div class="flex items-center gap-4 text-sm text-slate-400">
            <span class="text-slate-400"> 导入 → 诊断 → 标准化 → 预览 → AI处理 → 确认</span>
            <div id="saveIndicator" class="flex items-center text-xs text-emerald-400 bg-emerald-400/10 px-2 py-1 rounded opacity-0 transition-opacity duration-300">
                <span class="flex h-2 w-2 rounded-full bg-emerald-500 mr-2 animate-pulse"></span>
                自动保存中...
            </div>
            <div id="aiHeaderStatus" class="flex items-center text-xs text-cyan-400 bg-cyan-400/10 px-2 py-1 rounded hidden">
                <span class="flex h-2 w-2 rounded-full bg-cyan-500 mr-2 animate-pulse"></span>
                <span id="aiHeaderStatusText">AI处理中...</span>
            </div>
            <button onclick="exitDiagnosis()" class="px-3 py-1.5 bg-slate-700 hover:bg-red-600 rounded text-sm text-slate-300 hover:text-white whitespace-nowrap transition-colors">
                退出诊断
            </button>
        </div>
    </div>
</header>

<div id="app" style="display:flex;gap:24px;max-width:1600px;margin:0 auto;padding:24px">
<div style="flex:1;min-width:0">

    <!-- 上传区域 -->
    <div id="uploadSection" class="bg-slate-800 rounded-xl p-6 mb-6 border border-slate-700/50 shadow-sm">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div class="text-center border-r border-slate-700/50 pr-8">
                <h2 class="font-bold mb-4 text-lg text-slate-200">数据接入</h2>
                <input type="file" id="fileInput" accept=".xlsx,.xls" class="hidden">
                <div id="dropZone" class="border-2 border-dashed border-slate-600 rounded-xl p-8 cursor-pointer hover:border-cyan-500 hover:bg-slate-700/30 transition flex flex-col items-center justify-center" onclick="document.getElementById('fileInput').click()">
                    <svg class="w-8 h-8 text-slate-400 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
                    <p class="text-slate-300 font-medium mb-1">拖拽文件到此处，或点击选择文件</p>
                    <p class="text-xs text-slate-500">支持 .xlsx 和 .xls 格式</p>
                </div>
                <div id="fileName" class="mt-3 text-sm text-cyan-400 hidden"></div>
                <div id="uploadMsg" class="mt-2 text-sm text-slate-400"></div>
                <button id="uploadBtn" onclick="uploadFile()" class="mt-4 px-6 py-2 bg-cyan-600 hover:bg-cyan-500 rounded-lg font-bold text-sm transition disabled:opacity-50 shadow-sm" disabled>开始诊断</button>
                <ul class="space-y-2 text-sm text-slate-400">
                    <li class="flex items-center gap-2"><svg class="w-4 h-4 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>品牌缺失 / 品牌错误 / 品牌正确检测</li>
                    <li class="flex items-center gap-2"><svg class="w-4 h-4 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>新品牌自动发现与确认入库</li>
                    <li class="flex items-center gap-2"><svg class="w-4 h-4 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>营销分类识别与标准分类归集</li>
                    <li class="flex items-center gap-2"><svg class="w-4 h-4 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>AI 智能辅助分类（可选）</li>
                    <li class="flex items-center gap-2"><svg class="w-4 h-4 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>一键导出标准化结果</li>
                </ul>
            </div>
            <div class="flex flex-col justify-center pl-8">
                <h3 class="font-bold text-slate-200 text-sm mb-4 border-b border-slate-700 pb-2">最近上传</h3>
                
                <div id="recentFiles" class="mt-6 space-y-2 text-sm"></div>
            </div>
        </div>
    </div>

    <!-- 进度区域 -->
    <div id="progressSection" class="bg-slate-800 rounded-xl px-6 py-4 mb-6 hidden border border-slate-700/50 shadow-sm">
        <div class="flex items-center gap-4">
            <h3 class="font-bold text-cyan-400 text-sm whitespace-nowrap">正在诊断...</h3>
            <div class="flex-1 bg-slate-700 rounded-full h-2">
                <div id="progressBar" class="bg-cyan-500 h-2 rounded-full transition-all duration-500" style="width:0%"></div>
            </div>
            <span class="text-sm text-slate-400 whitespace-nowrap"><span id="progressPercent">0</span>%</span>
            <span id="progressText" class="text-sm text-cyan-400 truncate"></span>
        </div>
        <div id="progressSteps" class="text-[10px] text-slate-500 mt-2 text-left hidden">
            <span id="stepReading">读取文件: --</span>
            <span class="mx-1">|</span>
            <span id="stepBrands">分析品牌: --</span>
            <span class="mx-1">|</span>
            <span id="stepCategories">分析分类: --</span>
            <span class="mx-2">|</span>
            <span id="totalTime">总计: --</span>
        </div>
        <div id="progressLogs" class="text-sm text-slate-400 mt-3 overflow-y-auto max-h-40 bg-slate-900/50 rounded p-2 border border-slate-700/30">
            <div>等待开始...</div>
        </div>
    </div>

    <!-- 统计区域 -->
    <div id="statsSection" class="grid grid-cols-2 md:grid-cols-6 gap-4 mb-6 hidden">
        <div class="bg-slate-800 rounded-xl p-4 text-center border border-slate-700/50 shadow-sm"><div class="text-2xl font-bold text-slate-100" id="statTotal">-</div><div class="text-xs text-slate-400 mt-1">总商品数</div></div>
        <div class="bg-slate-800 rounded-xl p-4 text-center border border-slate-700/50 border-b-2 border-b-emerald-500/50 shadow-sm"><div class="text-2xl font-bold text-emerald-400" id="statValid">-</div><div class="text-xs text-slate-400 mt-1">正确</div></div>
        <div class="bg-slate-800 rounded-xl p-4 text-center border border-slate-700/50 border-b-2 border-b-amber-500/50 shadow-sm"><div class="text-2xl font-bold text-amber-400" id="statBrandMissing">-</div><div class="text-xs text-slate-400 mt-1">品牌缺失</div></div>
        <div class="bg-slate-800 rounded-xl p-4 text-center border border-slate-700/50 border-b-2 border-b-red-500/50 shadow-sm"><div class="text-2xl font-bold text-red-400" id="statBrandMismatch">-</div><div class="text-xs text-slate-400 mt-1">品牌错误</div></div>
        <div class="bg-slate-800 rounded-xl p-4 text-center border border-slate-700/50 border-b-2 border-b-purple-500/50 shadow-sm"><div class="text-2xl font-bold text-purple-400" id="statMarketing">-</div><div class="text-xs text-slate-400 mt-1">营销分类</div></div>
        <div class="bg-slate-800 rounded-xl p-4 text-center border border-slate-700/50 border-b-2 border-b-cyan-500/50 shadow-sm"><div class="text-2xl font-bold text-cyan-400" id="statNeedAI">-</div><div class="text-xs text-slate-400 mt-1">待AI处理</div></div>
    </div>

    <!-- 诊断结果区域 -->
    <div id="diagnosisSection" class="hidden">

        <!-- 全局品牌列表 -->
        <div id="brandPanel" class="bg-slate-800 rounded-xl p-6 mb-6 border border-slate-700/50 shadow-sm">
            <div class="flex items-center gap-2 mb-3 cursor-pointer opacity-80 hover:opacity-100 transition-opacity" onclick="globalBrandListOpen=!globalBrandListOpen;document.getElementById('globalBrandBody').classList.toggle('hidden');document.getElementById('globalBrandArrow').style.transform=globalBrandListOpen?'rotate(0deg)':'rotate(-90deg)'">
                <span id="globalBrandArrow" class="transition-transform" style="font-size:10px">▶</span>
                <span class="text-sm font-bold text-slate-200">快速定品牌列表</span>
            </div>
            <div id="globalBrandBody" class="hidden">
                <input type="text" id="globalBrandSearch" placeholder="搜索品牌..." class="w-full px-3 py-1.5 bg-slate-800 rounded text-sm mb-3" oninput="filterGlobalBrandList(this.value)">
                <div id="globalBrandListContainer" class="max-h-72 overflow-y-auto text-sm"></div>
            </div>
        </div>



        <!-- 品牌分组 -->
        <div id="mainContent" class="grid grid-cols-1 gap-6 mb-6">
            <div id="missingGroupsSection" class="bg-slate-800 rounded-xl p-6 border border-slate-700/50 shadow-sm collapsed">
                <h3 class="font-bold text-amber-500 mb-4 flex items-center cursor-pointer" onclick="toggleSection('missingGroupsSection')">
                    <span id="missingGroupsSectionArrow" class="mr-2 transition-transform opacity-70">▶</span>
                    品牌缺失 <span id="missingCount" class="text-sm text-slate-400 font-normal ml-2">(0个商品code)</span>
                </h3>
                <div id="missingGroups" class="space-y-4"></div>
            </div>
            <div id="mismatchGroupsSection" class="bg-slate-800 rounded-xl p-6 border border-slate-700/50 shadow-sm collapsed">
                <h3 class="font-bold text-red-500 mb-4 flex items-center cursor-pointer" onclick="toggleSection('mismatchGroupsSection')">
                    <span id="mismatchGroupsSectionArrow" class="mr-2 transition-transform opacity-70">▶</span>
                    品牌错误 <span id="mismatchCount" class="text-sm text-slate-400 font-normal ml-2">(0个商品code)</span>
                </h3>
                <div id="mismatchGroups" class="space-y-4"></div>
           
            </div>
            <div id="validGroupsSection" class="bg-slate-800 rounded-xl p-6 border border-slate-700/50 shadow-sm collapsed">
                <h3 class="font-bold text-blue-500 mb-4 flex items-center cursor-pointer" onclick="toggleSection('validGroupsSection')">
                    <span id="validGroupsSectionArrow" class="mr-2 transition-transform opacity-70">▶</span>
                    待确认品牌 <span id="validCount" class="text-sm text-slate-400 font-normal ml-2">(0个商品code)</span>
                </h3>
                <div id="validGroups" class="space-y-4"></div>

            </div>
            <div id="unbrandedSection" class="bg-slate-800 rounded-xl p-6 border border-slate-700/50 shadow-sm collapsed">
                <h3 class="font-bold text-emerald-500 mb-4 flex items-center cursor-pointer" onclick="toggleSection('unbrandedSection')">
                    <span id="unbrandedSectionArrow" class="mr-2 transition-transform opacity-70">▶</span>
                    无品牌候选 <span id="unbrandedCount" class="text-sm text-slate-400 font-normal ml-2">(0个商品code)</span>
                </h3>
                <div id="unbrandedGroups" class="space-y-4"></div>
            </div>
        </div>



        <!-- 分类树 -->
        <div id="categoryPanel" class="bg-slate-800 rounded-xl p-6 mb-6 border border-slate-700/50 shadow-sm">
            <h3 class="font-bold text-slate-200 mb-6 flex items-center justify-between border-b border-slate-700 pb-3">
                <span class="flex items-center gap-2"><svg class="w-4 h-4 text-orange-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"></path></svg>分类标准化规则确认</span>
                <span class="flex items-center gap-2">
                    <span id="cateCount" class="text-sm text-slate-400 font-normal">正在准备分类数据...</span>
                    <button id="reclassifyBtn" onclick="reclassifyExcludeMarketing()"
                            class="px-3 py-1 bg-red-700 hover:bg-red-600 rounded text-xs font-bold text-white whitespace-nowrap opacity-80 hover:opacity-100 transition-opacity">
                        剔除营销并重分类
                    </button>
                </span>
            </h3>
            <div class="mb-6">
                <div class="flex items-center gap-2 mb-3 cursor-pointer opacity-80 hover:opacity-100 transition-opacity" onclick="globalCateTreeOpen=!globalCateTreeOpen;document.getElementById('cateTreeBody').classList.toggle('hidden',!globalCateTreeOpen);document.getElementById('cateTreeArrow').style.transform=globalCateTreeOpen?'rotate(0deg)':'rotate(-90deg)'">
                    <span id="cateTreeArrow" class="transition-transform" style="font-size:10px">▶</span>
                    <span class="text-sm font-bold text-slate-200">分类树</span>
                    <button onclick="event.stopPropagation();toggleMarketingInTree()"
                            class="px-2 py-0.5 bg-slate-700 hover:bg-slate-600 rounded text-xs text-slate-300 whitespace-nowrap ml-2">
                        隐藏营销分类
                    </button>
                </div>
                <div id="cateTreeBody" class="hidden">
                    <input type="text" id="cateTreeSearch" placeholder="搜索分类路径..." class="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm mb-2 focus:outline-none focus:border-cyan-500" oninput="filterCategoryTree(this.value)">
                    <input type="text" id="productSearch" placeholder="搜商品名/编码，快速定位清洗路径..." class="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm mb-3 focus:outline-none focus:border-cyan-500" oninput="searchProduct(this.value)">
                    <div id="productSearchResults" class="hidden mb-2 max-h-40 overflow-y-auto text-sm bg-slate-900/50 rounded p-1"></div>
                    <div id="cateTreeContainer" class="max-h-96 overflow-y-auto text-sm bg-slate-900/30 p-2 rounded"></div>
                </div>
            </div>
            <div id="categoryMissingSection" class="mb-2">
                <h4 class="font-semibold text-amber-500 mb-3 flex items-center cursor-pointer hover:opacity-80" onclick="toggleSection('categoryMissingSection')">
                    <span id="categoryMissingSectionArrow" class="mr-2 transition-transform opacity-70">▼</span>
                    重点补全：分类缺失或待定义的商品
                </h4>
                <div id="categoryMissingGroups" class="space-y-3"></div>
                <div id="missingPagination" class="flex justify-center items-center gap-2 mt-4 pt-2 border-t border-slate-700/50 hidden">
                    <button id="missingPrevPage" onclick="changeMissingPage(-1)" class="px-3 py-1 bg-slate-700 hover:bg-slate-600 rounded text-sm text-slate-300 disabled:opacity-50">上一页</button>
                    <span id="missingPageInfo" class="text-sm text-slate-400"></span>
                    <button id="missingNextPage" onclick="changeMissingPage(1)" class="px-3 py-1 bg-slate-700 hover:bg-slate-600 rounded text-sm text-slate-300 disabled:opacity-50">下一页</button>
                </div>
            </div>
        </div>

        <!-- AI 配置 -->
        <div id="aiConfigPanel" class="bg-slate-800 rounded-xl p-6 mb-6 border border-brand-500/30 shadow-sm">
            <h3 class="font-bold text-brand-400 mb-4 flex items-center gap-2">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
                AI 服务配置
            </h3>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div>
                    <label class="block text-sm text-slate-400 mb-2">服务商</label>
                    <select id="aiProvider" class="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white focus:border-brand-500 outline-none text-sm">
                        <option value="gemini">Google Gemini</option>
                        <option value="deepseek">DeepSeek</option>
                        <option value="openai">OpenAI</option>
                        <option value="claude">Claude</option>
                    </select>
                </div>
                <div>
                    <label class="block text-sm text-slate-400 mb-2">API Key</label>
                    <input type="password" id="aiApiKey" class="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white focus:border-brand-500 outline-none text-sm" placeholder="输入 API Key">
                </div>
                <div>
                    <label class="block text-sm text-slate-400 mb-2">模型</label>
                    <select id="aiModel" class="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white focus:border-brand-500 outline-none text-sm">
                        <option value="gemini-2.0-flash">Gemini 2.0 Flash</option>
                        <option value="deepseek-chat">DeepSeek Chat</option>
                        <option value="gpt-4o">GPT-4o</option>
                        <option value="claude-3-haiku">Claude 3 Haiku</option>
                    </select>
                </div>
            </div>
            <div class="flex gap-3 mt-6">
                <button onclick="saveAIConfig()" class="px-6 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-sm font-medium text-white transition-colors border border-slate-600">保存配置</button>
                <button onclick="startAIProcessing()" class="px-6 py-2 bg-brand-600 hover:bg-brand-500 rounded-lg text-sm font-medium text-white transition-colors shadow-sm flex items-center gap-2">
                    交给AI处理
                </button>
            </div>
        </div>

        <!-- AI 处理进度 -->
        <div id="aiProgressSection" class="bg-slate-800 rounded-xl p-6 mb-6 border border-slate-700/50 shadow-sm hidden">
            <div class="flex items-center justify-between mb-4">
                <h3 class="font-bold text-cyan-400 flex items-center gap-2">
                    <span class="flex h-3 w-3 rounded-full bg-green-500 animate-pulse" id="aiStatusDot"></span>
                    <span id="aiStatusTitle">AI 正在处理未确认的商品...</span>
                </h3>
                <button id="aiCancelBtn" onclick="cancelAI()" class="px-3 py-1.5 bg-slate-700 hover:bg-red-600 rounded text-sm text-slate-300 hover:text-white transition-colors">
                    取消处理
                </button>
            </div>
            <div class="mb-4">
                <div class="flex items-center gap-4 mb-2">
                    <div class="flex-1 bg-slate-700 rounded-full h-3">
                        <div id="aiProgressBar" class="bg-cyan-500 h-3 rounded-full transition-all duration-500" style="width:0%"></div>
                    </div>
                    <span class="text-sm text-slate-400 whitespace-nowrap"><span id="aiProgressPercent">0</span>%</span>
                </div>
                <div id="aiProgressDetail" class="text-xs text-slate-400">准备中...</div>
            </div>

            <!-- 实时日志 -->
            <div class="bg-slate-900/80 rounded-xl border border-slate-700 overflow-hidden">
                <div class="bg-slate-800 px-4 py-2 border-b border-slate-700 flex justify-between items-center">
                    <span class="text-xs font-bold text-slate-400 uppercase tracking-wider">处理日志</span>
                    <span class="flex h-2 w-2 rounded-full bg-green-500 animate-pulse" id="aiLogDot"></span>
                </div>
                <div id="aiLogContainer" class="h-64 overflow-y-auto p-3 font-mono text-xs space-y-1 scroll-smooth">
                    <div class="text-slate-500 italic">等待处理数据...</div>
                </div>
            </div>

            <!-- 完成操作 -->
            <div id="aiCompleteActions" class="hidden mt-4 flex gap-3">
                <button id="aiDownloadBtn" class="px-5 py-2 bg-emerald-600 hover:bg-emerald-500 rounded-lg text-sm font-bold text-white transition-colors">
                    ⬇ 下载结果
                </button>
                <button id="aiReviewBtn" onclick="window.open('/review?sid=' + sessionId, '_blank')" class="px-5 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg text-sm font-bold text-white transition-colors">
                    📋 前往复核
                </button>
            </div>

            <!-- 错误信息 -->
            <div id="aiErrorMessage" class="hidden mt-4 p-3 bg-red-900/30 border border-red-700/50 rounded-lg text-sm text-red-300">
                <div class="flex items-center gap-2">
                    <span>❌</span>
                    <span id="aiErrorText" class="flex-1"></span>
                </div>
                <div class="flex gap-2 mt-2 justify-end">
                    <button onclick="retryAI()" class="px-3 py-1 bg-red-700 hover:bg-red-600 rounded text-xs font-bold text-white">重试</button>
                    <button onclick="cancelAI()" class="px-3 py-1 bg-slate-700 hover:bg-slate-600 rounded text-xs text-slate-300">取消</button>
                </div>
            </div>
        </div>

    </div>

    <!-- 侧边弹窗 -->
    <div id="sidePanelOverlay" class="side-panel-overlay" onclick="closeSidePanel()"></div>
    <div id="sidePanel" class="side-panel">
        <div class="p-6">
            <div class="flex justify-between items-center mb-4">
                <h3 id="sidePanelTitle" class="text-lg font-bold text-cyan-400">商品详情</h3>
                <button onclick="closeSidePanel()" class="text-slate-400 hover:text-white text-xl font-bold px-2">✕</button>
            </div>
            <div id="panelItemsList" class="space-y-3"></div>
            <div id="panelPagination" class="flex justify-center items-center gap-2 mt-4"></div>
            <div id="panelBatchActions" class="flex gap-2 mt-4 pt-4 border-t border-slate-700/50 flex-wrap"></div>
        </div>
    </div>

</div>

</div>

    <!-- 新品牌侧边栏 -->
    <div id="newBrandsSidebar" class="new-brands-sidebar hidden shadow-lg shadow-black/20">
        <div class="flex items-start justify-between mb-2">
            <span class="font-bold text-slate-100 text-sm flex items-center gap-2">新品牌发现</span>
                        <span id="newBrandsCount" class="text-sm text-slate-400 font-normal ml-1"></span>
            <div class="flex items-center gap-1.5 flex-shrink-0">
                <span id="newBrandsCount" class="text-xs text-slate-500"></span>
                <button onclick="showExportPreview()" class="px-3 py-1.5 bg-brand-600 hover:bg-brand-500 rounded text-xs font-medium text-white whitespace-nowrap shadow-sm">导入品牌库</button>
            </div>
        </div>
        <div id="newBrandsList" class="sidebar-list space-y-2 mt-4"></div>
    </div>

<!-- 导出预览弹窗 -->
<div id="exportPreviewModal" class="export-modal">
    <div class="export-modal-overlay" onclick="closeExportPreview()"></div>
    <div class="export-modal-content bg-slate-800 border border-slate-700">
        <h3 class="text-lg font-bold text-slate-100 mb-4 flex items-center gap-2">导出到品牌库</h3>
        <p class="text-sm text-slate-400 mb-3">以下 <span id="exportCount" class="text-brand-400 font-bold">0</span> 个品牌将合并到品牌库：</p>
        <div class="overflow-y-auto max-h-[40vh] mb-4 bg-slate-900 rounded-lg p-3 border border-slate-700/50" id="exportPreviewList"></div>
        <div class="flex justify-end gap-2">
            <button onclick="closeExportPreview()" class="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded text-sm text-slate-200">取消</button>
            <button onclick="confirmExportToLibrary()" class="px-4 py-2 bg-brand-600 hover:bg-brand-500 rounded text-sm font-medium text-white shadow-sm">确认导出</button>
        </div>
    </div>
</div>

<!-- 添加品牌弹窗 -->
<div id="addBrandModal" class="export-modal">
    <div class="export-modal-overlay" onclick="closeAddBrandModal()"></div>
    <div class="export-modal-content" style="width: 450px;">
        <h3 class="text-lg font-bold text-cyan-400 mb-4">➕ 添加/编辑品牌</h3>
        <div class="space-y-4">
            <div>
                <label class="block text-sm text-slate-400 mb-1">品牌名称 (必填)</label>
                <input type="text" id="modalBrandName" class="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-white focus:border-cyan-500 outline-none" placeholder="例如: 乐事/Lay's">
            </div>
            <div>
                <label class="block text-sm text-slate-400 mb-1">品牌类型</label>
                <div class="flex gap-1">
                    <div id="modalBrandTypeContainer" class="flex-1" style="position:relative">
                        <input type="text" id="modalBrandType" class="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-white text-sm" placeholder="加载中..." autocomplete="off">
                        <div id="modalBrandTypeList" class="brand-dropdown-list" style="width:100%"></div>
                    </div>
                    <button onclick="manageBrandTypes()" class="px-2 py-1 bg-slate-600 hover:bg-slate-500 rounded text-sm" title="管理类型">⚙️</button>
                </div>
            </div>
            <div>
                <label class="block text-sm text-slate-400 mb-1">国家/地区</label>
                <div class="flex gap-1">
                    <div id="modalBrandCountryContainer" class="flex-1" style="position:relative">
                        <input type="text" id="modalBrandCountry" class="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-white text-sm" placeholder="加载中..." autocomplete="off">
                        <div id="modalBrandCountryList" class="brand-dropdown-list" style="width:100%"></div>
                    </div>
                    <button onclick="manageCountries()" class="px-2 py-1 bg-slate-600 hover:bg-slate-500 rounded text-sm" title="管理国家">⚙️</button>
                </div>
            </div>
            <div id="modalParentBrandRow">
                <label class="block text-sm text-slate-400 mb-1">关联主品牌（可选）</label>
                <div id="modalParentBrandContainer" style="position:relative">
                    <input type="text" id="modalParentBrand" class="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-white text-sm" placeholder="不关联..." autocomplete="off">
                    <div id="modalParentBrandList" class="brand-dropdown-list" style="width:100%; display:none;"></div>
                </div>
                <div id="modalRelationType" class="flex gap-4 mt-1.5" style="display:none;">
                    <label class="text-sm text-slate-400 flex items-center gap-1.5 cursor-pointer" onclick="document.getElementById('relationSubBrand').checked=true">
                        <input type="radio" name="relation" id="relationSubBrand" value="sub_brand" checked class="accent-cyan-500"> 子品牌
                    </label>
                    <label class="text-sm text-slate-400 flex items-center gap-1.5 cursor-pointer" onclick="document.getElementById('relationAlias').checked=true">
                        <input type="radio" name="relation" id="relationAlias" value="alias" class="accent-cyan-500"> 别名
                    </label>
                </div>
            </div>
            <div class="flex gap-2 pt-2">
                <button onclick="closeAddBrandModal()" class="flex-1 py-2 bg-slate-600 hover:bg-slate-500 rounded font-bold">取消</button>
                <button onclick="submitNewBrandFromModal()" class="flex-1 py-2 bg-cyan-600 hover:bg-cyan-500 rounded font-bold">确认添加</button>
            </div>
        </div>
    </div>
</div>

<!-- 品牌配置管理弹窗 -->
<div id="brandConfigModal" class="export-modal">
    <div class="export-modal-overlay" onclick="closeBrandConfigModal()"></div>
    <div class="export-modal-content" style="width: 500px;">
        <h3 id="brandConfigModalTitle" class="text-lg font-bold text-cyan-400 mb-4">⚙️ 管理</h3>
        <div id="brandConfigList" class="max-h-60 overflow-y-auto mb-4 space-y-1 text-sm"></div>
        <div class="flex gap-2">
            <input type="text" id="brandConfigNewInput" class="flex-1 bg-slate-700 border border-slate-600 rounded px-3 py-2 text-white text-sm" placeholder="输入新类型名称...">
            <button onclick="submitBrandConfigNew()" class="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 rounded text-sm font-bold">+ 新增</button>
        </div>
    </div>
</div>

<!-- 统一分类选择弹窗 -->
<div id="categoryPickerModal" class="export-modal">
    <div class="export-modal-overlay" onclick="closePickerModal()"></div>
    <div class="export-modal-content" style="width: 500px;">
        <h3 class="text-lg font-bold text-cyan-400 mb-4">📂 设置分类</h3>
        <input type="text" id="pickerSearch" placeholder="搜索分类..." class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded text-sm mb-3" oninput="filterPickerTree(this.value)" autocomplete="off">
        <div id="pickerTreeContainer" class="max-h-64 overflow-y-auto border border-slate-700/50 rounded p-2 mb-3"></div>
        <div id="pickerSelectedDisplay" class="text-xs text-slate-400 mb-3 min-h-[20px]"></div>
        <div class="flex gap-2 justify-end">
            <button onclick="closePickerModal()" class="px-4 py-2 bg-slate-600 hover:bg-slate-500 rounded text-sm">取消</button>
            <button id="pickerConfirmBtn" onclick="confirmPickerSelection()" class="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 rounded text-sm font-bold" disabled>确认</button>
        </div>
    </div>
</div>

<script src="/static/js/common.js"></script>
<script src="/static/js/upload.js"></script>
<script src="/static/js/diagnosis.js"></script>
<script src="/static/js/brand_editor.js"></script>
<script src="/static/js/export.js"></script>
<script src="/static/js/ai_process.js"></script>
</body>
</html>
'''

# 复核页面 HTML 模板
REVIEW_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="utf-8">
    <title>人工复核 - 商品数据清理系统 V4</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 min-h-screen text-white">
<div class="max-w-5xl mx-auto px-6 py-8">
    <div class="text-center mb-6">
        <h1 class="text-2xl font-bold">人工复核界面</h1>
        <p class="text-slate-400 text-sm">自动监听处理进度，增量加载待复核数据</p>
    </div>
    <div class="bg-slate-800/50 rounded-xl p-6 mb-6">
        <h3 class="font-bold">待复核列表</h3>
        <div id="loadingMsg" class="text-center text-slate-400 py-8">
            <div class="animate-pulse">正在监听处理进度...</div>
        </div>
    </div>
</div>
</body>
</html>
'''
