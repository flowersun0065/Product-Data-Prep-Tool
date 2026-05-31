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
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    fontFamily: { sans: ['Inter', 'system-ui', 'sans-serif'] },
                    colors: {
                        brand: { 400: '#2dd4bf', 500: '#14b8a6', 600: '#0d9488', 700: '#0f766e' },
                    }
                }
            }
        }
    </script>
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
        select { appearance: none; background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%2394a3b8' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'%3E%3C/polyline%3E%3C/svg%3E"); background-repeat: no-repeat; background-position: right 10px center; background-size: 12px; padding-right: 30px !important; cursor: pointer; }
        select::-ms-expand { display: none; }
        select optgroup, select option { background: #1e293b; color: #e2e8f0; }

        /* ═══ Electron 侧边栏样式 ═══ */
        .electron-sidebar {
            position: fixed; top: 0; left: 0; bottom: 0; width: 220px;
            background: rgba(15, 23, 42, 0.85); backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border-right: 1px solid rgba(255,255,255,0.06);
            z-index: 60; display: flex; flex-direction: column;
            font-family: -apple-system, 'SF Pro Text', 'Inter', system-ui, sans-serif;
        }
        .electron-sidebar-group { padding: 12px; border-bottom: 1px solid rgba(255,255,255,0.06); }
        .electron-sidebar-nav { flex: 1; overflow-y: auto; padding: 8px; }
        .electron-sidebar-section-title {
            color: #86868b; font-size: 9px; font-weight: 600; text-transform: uppercase;
            letter-spacing: 0.5px; margin: 14px 4px 6px;
        }
        .electron-sidebar-item {
            display: flex; align-items: center; gap: 6px; padding: 7px 8px;
            border-radius: 5px; color: #98989d; font-size: 11px; cursor: pointer;
            transition: background 0.1s;
        }
        .electron-sidebar-item:hover { background: rgba(255,255,255,0.04); }
        .electron-sidebar-item.active { background: rgba(0,122,255,0.15); color: #fff; font-weight: 500; }
        .electron-sidebar-footer {
            padding: 8px; border-top: 1px solid rgba(255,255,255,0.06);
            font-size: 10px; color: #98989d; cursor: pointer;
        }
        .electron-main-content { margin-left: 0; transition: margin-left 0.2s; }
        .electron-main-content.electron-shifted { margin-left: 220px; }

        /* 详情面板 */
        .electron-detail-panel {
            position: fixed; top: 0; right: -380px; width: 360px; height: 100vh;
            background: rgba(15, 23, 42, 0.95); backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border-left: 1px solid rgba(255,255,255,0.06);
            padding: 16px; overflow-y: auto; z-index: 100;
            transition: right 0.25s ease;
        }
        .electron-detail-panel.open { right: 0; }
        .electron-detail-overlay {
            position: fixed; inset: 0; background: rgba(0,0,0,0.4); z-index: 99;
            display: none;
        }
        .electron-detail-overlay.open { display: block; }

        .electron-btn {
            padding: 6px 14px; border-radius: 6px; font-size: 11px; font-weight: 600;
            border: none; cursor: pointer; font-family: inherit;
        }
        .electron-btn.primary { background: #007aff; color: #fff; }
    </style>
</head>
<body class="bg-slate-900 min-h-screen text-white antialiased">

<!-- ═══ Electron 侧边栏 ═══ -->
<div id="electronSidebar" class="electron-sidebar" style="display:none;">
  <div class="electron-sidebar-group">
    <select id="electronGroupSelect" onchange="electronSwitchGroup(this.value)" class="w-full px-3 py-2 rounded-lg text-sm font-medium"
      style="background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.08);color:#f5f5f7;outline:none;">
      <option value="">-- 选择分组 --</option>
    </select>
  </div>
  <div class="electron-sidebar-nav" id="electronSidebarNav">
    <div class="electron-sidebar-section-title">当前会话</div>
    <div id="electronSessionSteps"></div>

    <div class="electron-sidebar-section-title">品牌库</div>
    <div class="electron-sidebar-item" data-nav="brand-database" onclick="electronNavTo('brand-database')">📋 品牌数据库</div>
    <div class="electron-sidebar-item" data-nav="brand-corrections" onclick="electronNavTo('brand-corrections')">✏️ 品牌修正</div>
    <div class="electron-sidebar-item" data-nav="brand-relationships" onclick="electronNavTo('brand-relationships')">🔗 品牌关系</div>

    <div class="electron-sidebar-section-title">分类体系</div>
    <div class="electron-sidebar-item" data-nav="category-tree" onclick="electronNavTo('category-tree')">🌳 分类路径树</div>
    <div class="electron-sidebar-item" data-nav="category-classify" onclick="electronNavTo('category-classify')">🏷 路径分类标记</div>

    <div class="electron-sidebar-section-title">历史会话</div>
    <div id="electronHistory"></div>
  </div>
  <div class="electron-sidebar-footer" onclick="electronOpenSettings()">⚙ 设置</div>
</div>

<!-- ═══ 主内容区（现有页面原样保留） ═══ -->
<div id="electronMainContent" class="electron-main-content">

<!-- 顶部导航栏 -->
<header class="bg-slate-800/95 border-b border-slate-700/40 sticky top-0 z-50 h-14">
    <div class="max-w-[1600px] mx-auto px-6 h-full flex items-center justify-between">
        <h1 class="text-sm font-semibold text-slate-100 flex items-center gap-2.5">
            <span class="w-6 h-6 rounded-md bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center text-[11px] font-bold text-white shadow-sm">P</span>
            商品数据清理系统
        </h1>
        <div class="flex items-center gap-3 text-[11px] text-slate-400">
            <div class="hidden lg:flex items-center gap-0.5">
                <span class="flex items-center gap-1 px-2 py-1 rounded bg-slate-700/60 text-slate-200"><svg class="w-3.5 h-3.5 text-brand-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/></svg>导入</span>
                <svg class="w-3 h-3 mx-1 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/></svg>
                <span class="flex items-center gap-1 px-2 py-1 rounded text-slate-400"><svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.25 8.511c.884.284 1.5 1.128 1.5 2.097v4.286c0 1.136-.847 2.1-1.98 2.193-.34.027-.68.052-1.02.072v3.091l-3-3c-1.354 0-2.694-.055-4.02-.163a2.115 2.115 0 01-.825-.242m9.345-8.334a2.126 2.126 0 00-.476-.095 48.64 48.64 0 00-8.048 0c-1.131.094-1.976 1.057-1.976 2.192v4.286c0 .837.46 1.58 1.155 1.951m9.345-8.334V6.637c0-1.621-1.152-3.026-2.76-3.235A48.455 48.455 0 0011.25 3c-2.115 0-4.198.137-6.24.402-1.608.209-2.76 1.614-2.76 3.235v6.226c0 1.621 1.152 3.026 2.76 3.235.577.075 1.157.14 1.74.194V21l4.155-4.155"/></svg>诊断</span>
                <svg class="w-3 h-3 mx-1 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/></svg>
                <span class="flex items-center gap-1 px-2 py-1 rounded text-slate-400"><svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>标准化</span>
                <svg class="w-3 h-3 mx-1 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/></svg>
                <span class="flex items-center gap-1 px-2 py-1 rounded text-slate-400"><svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/></svg>预览</span>
                <svg class="w-3 h-3 mx-1 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/></svg>
                <span class="flex items-center gap-1 px-2 py-1 rounded bg-brand-500/15 text-brand-400 font-medium"><svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456zM16.894 20.567L16.5 21.75l-.394-1.183a2.25 2.25 0 00-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 001.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 001.423 1.423l1.183.394-1.183.394a2.25 2.25 0 00-1.423 1.423z"/></svg>AI处理</span>
                <svg class="w-3 h-3 mx-1 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/></svg>
                <span class="flex items-center gap-1 px-2 py-1 rounded text-slate-400"><svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>确认</span>
            </div>
            <div id="saveIndicator" class="flex items-center text-[10px] text-emerald-400 bg-emerald-400/10 px-2 py-1 rounded opacity-0 transition-opacity duration-300 whitespace-nowrap">
                <span class="flex h-1.5 w-1.5 rounded-full bg-emerald-500 mr-1.5 animate-pulse"></span>
                自动保存中
            </div>
            <div id="aiHeaderStatus" class="flex items-center text-[10px] text-brand-400 bg-brand-400/10 px-2 py-1 rounded hidden whitespace-nowrap">
                <span class="flex h-1.5 w-1.5 rounded-full bg-brand-500 mr-1.5 animate-pulse"></span>
                <span id="aiHeaderStatusText">AI处理中</span>
            </div>
            <button onclick="exitDiagnosis()" class="px-2.5 py-1.5 bg-slate-700 hover:bg-red-600/80 rounded-md text-xs text-slate-300 hover:text-white transition whitespace-nowrap">
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
                <div id="dropZone" class="border-2 border-dashed border-slate-600 rounded-xl p-8 cursor-pointer hover:border-brand-500 hover:bg-slate-700/30 transition flex flex-col items-center justify-center" onclick="document.getElementById('fileInput').click()">
                    <svg class="w-8 h-8 text-slate-400 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
                    <p class="text-slate-300 font-medium mb-1">拖拽文件到此处，或点击选择文件</p>
                    <p class="text-xs text-slate-500">支持 .xlsx 和 .xls 格式</p>
                </div>
                <div id="fileName" class="mt-3 text-sm text-brand-400 hidden"></div>
                <div class="mt-3 flex items-center gap-2">
                    <select id="uploadGroup" class="flex-1 bg-slate-600 border border-slate-500 rounded-md px-2.5 py-1.5 text-white text-xs focus:border-brand-500 outline-none">
                        <option value="">-- 选择分组 --</option>
                    </select>                    <button onclick="showGroupManager()" class="px-2.5 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg transition" title="管理分组">
                        <svg class="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/></svg>
                    </button>
                </div>
                <div id="uploadMsg" class="mt-2 text-sm text-slate-400"></div>
                <button id="uploadBtn" onclick="uploadFile()" class="mt-4 px-6 py-2 bg-gradient-to-br from-brand-500 to-brand-700 hover:from-brand-400 hover:to-brand-600 rounded-lg font-bold text-sm transition disabled:opacity-50 shadow-sm" disabled>开始诊断</button>
                <ul class="space-y-2 text-sm text-slate-400">
                    <li class="flex items-center gap-2"><svg class="w-4 h-4 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>品牌缺失 / 品牌错误 / 品牌正确检测</li>
                    <li class="flex items-center gap-2"><svg class="w-4 h-4 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>新品牌自动发现与确认入库</li>
                    <li class="flex items-center gap-2"><svg class="w-4 h-4 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>营销分类识别与标准分类归集</li>
                    <li class="flex items-center gap-2"><svg class="w-4 h-4 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>AI 智能辅助分类（可选）</li>
                    <li class="flex items-center gap-2"><svg class="w-4 h-4 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>一键导出标准化结果</li>
                </ul>
            </div>
            <div class="flex flex-col pl-8" style="min-height:280px;">
                <h3 class="font-bold text-slate-200 text-sm pb-2 border-b border-slate-700 flex-shrink-0">最近上传</h3>
                <div id="recentFiles" class="mt-3 space-y-2 text-sm overflow-y-auto flex-1" style="max-height:220px;"></div>
            </div>
        </div>
    </div>

    <!-- 进度区域 -->
    <div id="progressSection" class="bg-slate-800 rounded-xl px-6 py-4 mb-6 hidden border border-slate-700/50 shadow-sm">
        <div class="flex items-center gap-4">
            <h3 class="font-bold text-brand-400 text-sm whitespace-nowrap">正在诊断...</h3>
            <div class="flex-1 bg-slate-700 rounded-full h-2">
                <div id="progressBar" class="bg-brand-500 h-2 rounded-full transition-all duration-500" style="width:0%"></div>
            </div>
            <span class="text-sm text-slate-400 whitespace-nowrap"><span id="progressPercent">0</span>%</span>
            <span id="progressText" class="text-sm text-brand-400 truncate"></span>
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
        <div class="bg-slate-800 rounded-xl p-4 text-center border border-slate-700/50 border-b-2 border-b-cyan-500/50 shadow-sm"><div class="text-2xl font-bold text-brand-400" id="statNeedAI">-</div><div class="text-xs text-slate-400 mt-1">待AI处理</div></div>
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
                    <input type="text" id="cateTreeSearch" placeholder="搜索分类路径..." class="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm mb-2 focus:outline-none focus:border-brand-500" oninput="filterCategoryTree(this.value)">
                    <input type="text" id="productSearch" placeholder="搜商品名/编码，支持空格多关键词..." class="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm mb-3 focus:outline-none focus:border-brand-500" oninput="searchProduct(this.value)">
                    <div id="productSearchResults" class="hidden mb-2 max-h-72 overflow-y-auto text-sm bg-slate-900/50 rounded p-1"></div>
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
            <div class="flex items-center gap-3 mt-6">
                <label class="flex items-center gap-2 text-sm text-slate-400 cursor-pointer">
                    <input type="checkbox" id="aiForceReanalyze" class="rounded bg-slate-700 border-slate-600">
                    强制重新分析（忽略缓存）
                </label>
                <button onclick="saveAIConfig()" class="px-6 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-sm font-medium text-white transition-colors border border-slate-600">保存配置</button>
                <button onclick="startAIProcessing()" class="px-6 py-2 bg-gradient-to-br from-brand-500 to-brand-700 hover:from-brand-400 hover:to-brand-600 rounded-lg text-sm font-medium text-white transition-colors shadow-sm flex items-center gap-2">
                    交给AI处理
                </button>
                <button onclick="finalizeWithoutAI()" title="所有需确认项已确认完，直接生成复核数据，不调用 AI" class="px-6 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-sm font-medium text-white transition-colors border border-slate-600">
                    直接进入复核(无AI)
                </button>
            </div>
        </div>

        <!-- AI 处理进度 -->
        <div id="aiProgressSection" class="bg-slate-800 rounded-xl p-6 mb-6 border border-slate-700/50 shadow-sm hidden">
            <div class="flex items-center justify-between mb-4">
                <h3 class="font-bold text-brand-400 flex items-center gap-2">
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
                        <div id="aiProgressBar" class="bg-brand-500 h-3 rounded-full transition-all duration-500" style="width:0%"></div>
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
                <h3 id="sidePanelTitle" class="text-lg font-bold text-brand-400">商品详情</h3>
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
                <button onclick="showExportPreview()" class="px-3 py-1.5 bg-gradient-to-br from-brand-500 to-brand-700 hover:from-brand-400 hover:to-brand-600 rounded text-xs font-medium text-white whitespace-nowrap shadow-sm">导入品牌库</button>
            </div>
        </div>
        <div class="relative mt-3">
            <input id="newBrandsSearch" type="text" placeholder="搜索品牌名称..."
                   oninput="updateNewBrandsDisplay()"
                   class="w-full bg-slate-800/80 border border-slate-600/50 rounded-lg px-3 py-1.5 pl-8 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-brand-600/60 focus:ring-1 focus:ring-brand-600/30 transition">
            <svg class="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-4.35-4.35M11 19a8 8 0 100-16 8 8 0 000 16z"/>
            </svg>
        </div>
        <div id="newBrandsList" class="sidebar-list space-y-2"></div>
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
            <button onclick="confirmExportToLibrary()" class="px-4 py-2 bg-gradient-to-br from-brand-500 to-brand-700 hover:from-brand-400 hover:to-brand-600 rounded text-sm font-medium text-white shadow-sm">确认导出</button>
        </div>
    </div>
</div>

<!-- 添加品牌弹窗 -->
<div id="addBrandModal" class="export-modal">
    <div class="export-modal-overlay" onclick="closeAddBrandModal()"></div>
    <div class="export-modal-content" style="width: 450px;">
        <h3 class="text-lg font-bold text-brand-400 mb-4">➕ 添加/编辑品牌</h3>
        <div class="space-y-4">
            <div>
                <label class="block text-sm text-slate-400 mb-1">品牌名称 (必填)</label>
                <input type="text" id="modalBrandName" class="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-white focus:border-brand-500 outline-none" placeholder="例如: 乐事/Lay's">
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
                        <input type="radio" name="relation" id="relationSubBrand" value="sub_brand" checked class="accent-brand-500"> 子品牌
                    </label>
                    <label class="text-sm text-slate-400 flex items-center gap-1.5 cursor-pointer" onclick="document.getElementById('relationAlias').checked=true">
                        <input type="radio" name="relation" id="relationAlias" value="alias" class="accent-brand-500"> 别名
                    </label>
                </div>
            </div>
            <div class="flex gap-2 pt-2">
                <button onclick="closeAddBrandModal()" class="flex-1 py-2 bg-slate-600 hover:bg-slate-500 rounded font-bold">取消</button>
                <button onclick="submitNewBrandFromModal()" class="flex-1 py-2 bg-gradient-to-br from-brand-500 to-brand-700 hover:from-brand-400 hover:to-brand-600 rounded font-bold">确认添加</button>
            </div>
        </div>
    </div>
</div>

<!-- 品牌配置管理弹窗 -->
<div id="brandConfigModal" class="export-modal">
    <div class="export-modal-overlay" onclick="closeBrandConfigModal()"></div>
    <div class="export-modal-content" style="width: 500px;">
        <h3 id="brandConfigModalTitle" class="text-lg font-bold text-brand-400 mb-4">⚙️ 管理</h3>
        <div id="brandConfigList" class="max-h-60 overflow-y-auto mb-4 space-y-1 text-sm"></div>
        <div class="flex gap-2">
            <input type="text" id="brandConfigNewInput" class="flex-1 bg-slate-700 border border-slate-600 rounded px-3 py-2 text-white text-sm" placeholder="输入新类型名称...">
            <button onclick="submitBrandConfigNew()" class="px-4 py-2 bg-gradient-to-br from-brand-500 to-brand-700 hover:from-brand-400 hover:to-brand-600 rounded text-sm font-bold">+ 新增</button>
        </div>
    </div>
</div>

<!-- 统一分类选择弹窗 -->
<div id="categoryPickerModal" class="export-modal">
    <div class="export-modal-overlay" onclick="closePickerModal()"></div>
    <div class="export-modal-content" style="width: 500px;">
        <h3 class="text-lg font-bold text-brand-400 mb-4">📂 设置分类</h3>
        <input type="text" id="pickerSearch" placeholder="搜索分类..." class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded text-sm mb-3" oninput="filterPickerTree(this.value)" autocomplete="off">
        <div id="pickerTreeContainer" class="max-h-64 overflow-y-auto border border-slate-700/50 rounded p-2 mb-3"></div>
        <div id="pickerSelectedDisplay" class="text-xs text-slate-400 mb-3 min-h-[20px]"></div>
        <div class="flex gap-2 justify-end">
            <button onclick="closePickerModal()" class="px-4 py-2 bg-slate-600 hover:bg-slate-500 rounded text-sm">取消</button>
            <button id="pickerConfirmBtn" onclick="confirmPickerSelection()" class="px-4 py-2 bg-gradient-to-br from-brand-500 to-brand-700 hover:from-brand-400 hover:to-brand-600 rounded text-sm font-bold" disabled>确认</button>
        </div>
    </div>
</div>

<script src="/static/js/common.js"></script>
<script src="/static/js/upload.js"></script>
<script src="/static/js/diagnosis.js"></script>
<script src="/static/js/brand_editor.js"></script>
<script src="/static/js/export.js"></script>
<script src="/static/js/ai_process.js"></script>



</div><!-- /electronMainContent -->

<!-- ═══ 商品详情侧边窗 ═══ -->
<div id="electronDetailOverlay" class="electron-detail-overlay" onclick="electronCloseDetail()"></div>
<div id="electronDetailPanel" class="electron-detail-panel">
  <div id="electronDetailContent"></div>
</div>

<script src="/static/js/electron_init.js"></script>
<script>
// ═══ (Legacy inline Electron logic replaced by electron_init.js) ═══
(function(){ return; }
  var isElectron = (window.electronAPI !== undefined) || (window.location.pathname === '/electron');
  if (!isElectron) return;

  var sidebar = document.getElementById('electronSidebar');
  var mainContent = document.getElementById('electronMainContent');
  if (sidebar) sidebar.style.display = '';
  if (mainContent) mainContent.classList.add('electron-shifted');

  // 步骤定义
  var steps = [
    {id:'upload', label:'1 上传 & 诊断'},
    {id:'brand-review', label:'2 品牌审核'},
    {id:'ai-process', label:'3 AI 处理'},
    {id:'review', label:'4 复核'},
    {id:'export', label:'5 导出'},
  ];
  var currentStep = 'upload';

  function renderSteps() {
    var el = document.getElementById('electronSessionSteps');
    if (!el) return;
    el.innerHTML = steps.map(function(s){
      var cls = 'electron-sidebar-item';
      if (s.id === currentStep) cls += ' active';
      return '<div class="'+cls+'" data-step="'+s.id+'" onclick="electronSwitchStep(this.dataset.step)">'+s.label+'</div>';
    }).join('');
  }

  window.electronSwitchStep = function(stepId) {
    currentStep = stepId;
    renderSteps();
    // 显示对应 content section
    var sections = {
      'upload': ['uploadSection'],
      'brand-review': ['diagnosisSection'],
      'ai-process': ['progressSection'],
      'review': ['diagnosisSection'],
      'export': ['diagnosisSection'],
    };
    // 隐藏所有
    ['uploadSection','diagnosisSection','progressSection'].forEach(function(id){
      var el = document.getElementById(id);
      if (el && sections[stepId] && sections[stepId].indexOf(id) !== -1) {
        el.classList.remove('hidden');
      }
    });
    // 诊断页本就会显示 upload + diagnosis
    if (stepId === 'upload') {
      var us = document.getElementById('uploadSection');
      var ds = document.getElementById('diagnosisSection');
      if (us) us.classList.remove('hidden');
      if (ds) ds.classList.add('hidden');
    }
  };

  window.electronSwitchGroup = function(gid) {
    localStorage.setItem('last_group_id', gid);
    var ug = document.getElementById('uploadGroup');
    if (ug) ug.value = gid;
    loadElectronHistory();
  };

  function loadElectronGroups() {
    fetch('/api/groups').then(function(r){return r.json()}).then(function(d){
      var sel = document.getElementById('electronGroupSelect');
      if (!sel) return;
      var cur = sel.value;
      sel.innerHTML = '<option value="">-- 选择分组 --</option>';
      Object.entries(d.groups||{}).forEach(function(e){
        sel.innerHTML += '<option value="'+e[0]+'">📁 '+escHtml(e[1].name)+'</option>';
      });
      sel.value = cur || localStorage.getItem('last_group_id') || '';
    }).catch(function(){});
  }

  function loadElectronHistory() {
    var el = document.getElementById('electronHistory');
    if (!el) return;
    fetch('/api/recent_files').then(function(r){return r.json()}).then(function(files){
      el.innerHTML = (files||[]).slice(0,5).map(function(f){
        return '<div class="electron-sidebar-item" style="font-size:10px" data-fileid="'+f.id+'" onclick="importRecentFile(this.dataset.fileid)">'+
          (f.time||'').split(' ')[0]+' · '+(f.name||'').substring(0,20)+'</div>';
      }).join('');
    }).catch(function(){});
  }

  window.electronNavTo = function(page) {
    if (page === 'brand-database') { renderBrandDatabasePage(); }
    else if (page === 'category-tree') { renderCategoryTreePage(); }
  };

  window.electronOpenSettings = function() {
    if (window.electronAPI) { window.electronAPI.openSettings(); }
  };

  // 详情面板
  window.electronOpenDetail = function(item) {
    var panel = document.getElementById('electronDetailPanel');
    var overlay = document.getElementById('electronDetailOverlay');
    if (!panel || !overlay) return;
    renderElectronDetail(item);
    panel.classList.add('open');
    overlay.classList.add('open');
  };
  window.electronCloseDetail = function() {
    var panel = document.getElementById('electronDetailPanel');
    var overlay = document.getElementById('electronDetailOverlay');
    if (panel) panel.classList.remove('open');
    if (overlay) overlay.classList.remove('open');
  };

  function renderElectronDetail(item) {
    var el = document.getElementById('electronDetailContent');
    if (!el) return;
    var html = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">'+
      '<span style="font-weight:600;">商品详情</span>'+
      '<button onclick="electronCloseDetail()" style="background:none;border:none;color:#86868b;cursor:pointer;font-size:16px;">✕</button></div>';
    if (item.org_image_url) html += '<div style="background:rgba(255,255,255,0.03);border-radius:8px;height:100px;display:flex;align-items:center;justify-content:center;margin-bottom:10px;"><img src="'+escAttr(item.org_image_url)+'" style="max-width:100%;max-height:100%;object-fit:contain;" onerror="this.style.display=\'none\'"></div>';
    html += '<div style="margin-bottom:10px;"><div style="color:#86868b;font-size:10px;font-weight:600;text-transform:uppercase;margin-bottom:4px;">基本信息</div>';
    [['商品名',item.name],['编码',item.code],['原始品牌',item.original_brand||item.brand],['原始分类',item.original_category||item.category]].forEach(function(r){
      if (!r[1]) return;
      html += '<div style="display:flex;justify-content:space-between;font-size:11px;line-height:2;"><span style="color:#6e6e73;">'+esc(r[0])+'</span><span>'+esc(String(r[1]))+'</span></div>';
    });
    html += '</div>';
    if (item.brand_ai) {
      html += '<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);border-radius:8px;padding:10px;margin-bottom:8px;">';
      html += '<div style="color:#86868b;font-size:10px;font-weight:600;text-transform:uppercase;margin-bottom:4px;">品牌</div>';
      html += '<span style="font-weight:500;">'+esc(item.brand_ai)+'</span> ';
      html += '<span style="font-size:10px;color:#98989d;">置信度 '+item.brand_confidence+' · '+esc(item.brand_type||'')+'</span>';
      html += '</div>';
    }
    if (item.category_ai) {
      html += '<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);border-radius:8px;padding:10px;margin-bottom:8px;">';
      html += '<div style="color:#86868b;font-size:10px;font-weight:600;text-transform:uppercase;margin-bottom:4px;">分类</div>';
      html += '<span>'+esc(item.category_ai)+'</span>';
      html += '</div>';
    }
    html += '<div style="display:flex;gap:8px;margin-top:12px;">';
    html += '<button class="electron-btn primary" onclick="electronCloseDetail()">关闭</button>';
    html += '</div>';
    el.innerHTML = html;
  }

  function escHtml(s) { if(!s) return ''; return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
  function escAttr(s) { if(!s) return ''; return String(s).replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/'/g,'&#39;'); }
  function esc(s) { return escHtml(s); }

  // 品牌库和分类树页面渲染（简化版本，在侧边栏面板弹出）
  function renderBrandDatabasePage() {
    var existingPanel = document.getElementById('electronBrandPanel');
    if (existingPanel) { existingPanel.remove(); return; }
    fetch('/api/brands/list').then(function(r){return r.json()}).then(function(d){
      var brands = d.brands || [];
      var html = '<div id="electronBrandPanel" style="position:fixed;top:0;left:220px;right:0;bottom:0;z-index:50;background:var(--bg-primary,#0f172a);padding:20px;overflow-y:auto;">';
      html += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">';
      html += '<h2 style="font-size:18px;font-weight:700;">品牌数据库</h2>';
      html += '<button onclick="this.closest(\'#electronBrandPanel\').remove()" style="background:none;border:none;color:#86868b;font-size:20px;cursor:pointer;">✕</button></div>';
      html += '<div style="margin-bottom:12px;"><input placeholder="搜索品牌..." oninput="var v=this.value.toLowerCase();document.querySelectorAll(\'#electronBrandPanel tbody tr\').forEach(function(r){r.style.display=r.textContent.toLowerCase().indexOf(v)>=0?\'\':\'none\'})"></div>';
      html += '<table style="width:100%;font-size:12px;border-collapse:collapse;"><thead><tr style="text-align:left;color:#86868b;text-transform:uppercase;font-size:10px;border-bottom:1px solid rgba(255,255,255,0.06);">';
      html += '<th style="padding:8px;">标准名</th><th style="padding:8px;">别名</th><th style="padding:8px;">类型</th><th style="padding:8px;">产地</th>';
      html += '</tr></thead><tbody>';
      brands.forEach(function(b){
        html += '<tr style="border-bottom:1px solid rgba(255,255,255,0.03);">';
        html += '<td style="padding:8px;font-weight:500;">'+esc(b.display_name||b.name)+'</td>';
        html += '<td style="padding:8px;color:#98989d;">'+esc((b.aliases||[]).join(', '))+'</td>';
        html += '<td style="padding:8px;">'+esc(b.type||'')+'</td>';
        html += '<td style="padding:8px;">'+esc(b.country||'')+'</td>';
        html += '</tr>';
      });
      html += '</tbody></table></div>';
      document.body.appendChild(document.createRange().createContextualFragment(html));
    });
  }

  function renderCategoryTreePage() {
    var existingPanel = document.getElementById('electronCategoryPanel');
    if (existingPanel) { existingPanel.remove(); return; }
    var html = '<div id="electronCategoryPanel" style="position:fixed;top:0;left:220px;right:0;bottom:0;z-index:50;background:#0f172a;padding:20px;overflow-y:auto;">';
    html += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">';
    html += '<h2 style="font-size:18px;font-weight:700;">分类路径树</h2>';
    html += '<button onclick="this.closest(\'#electronCategoryPanel\').remove()" style="background:none;border:none;color:#86868b;font-size:20px;cursor:pointer;">✕</button></div>';
    html += '<p style="color:#94a3b8;">上传文件诊断后，分类树将在此显示。</p>';
    html += '</div>';
    document.body.appendChild(document.createRange().createContextualFragment(html));
  }

  // Init
  renderSteps();
  loadElectronGroups();
  loadElectronHistory();
})();
</script>

</body>
</html>
'''

# 复核页面 HTML 模板
REVIEW_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>人工复核 - 商品数据清理系统</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        .status-pending { background: #f59e0b; color: #fff; padding: 2px 8px; border-radius: 4px; font-size: 12px; }
        .status-confirmed { background: #16a34a; color: #fff; padding: 2px 8px; border-radius: 4px; font-size: 12px; }
        .status-modified { background: #3b82f6; color: #fff; padding: 2px 8px; border-radius: 4px; font-size: 12px; }
        .tag-self { background: #8b5cf6; color: #fff; padding: 2px 6px; border-radius: 4px; font-size: 11px; }
        .tag-import { background: #ef4444; color: #fff; padding: 2px 6px; border-radius: 4px; font-size: 11px; }
        .tag-domestic { background: #22c55e; color: #fff; padding: 2px 6px; border-radius: 4px; font-size: 11px; }
        .tag-promo { background: #f97316; color: #fff; padding: 2px 6px; border-radius: 4px; font-size: 11px; }
        .tag-recommend { background: #eab308; color: #fff; padding: 2px 6px; border-radius: 4px; font-size: 11px; }
        .card-active { border-color: #06b6d4 !important; background: rgba(6,182,212,0.08) !important; }
        .detail-panel { position: fixed; top: 0; right: -520px; width: 520px; height: 100vh; background: #1e293b; transition: right 0.3s ease; z-index: 1000; overflow-y: auto; box-shadow: -4px 0 20px rgba(0,0,0,0.5); }
        .detail-panel.open { right: 0; }
        .detail-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 999; display: none; }
        .detail-overlay.open { display: block; }
    </style>
</head>
<body class="bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 min-h-screen text-white">
<div id="review-app" class="flex flex-col h-screen">
    <!-- 顶栏 -->
    <header class="bg-slate-800/80 border-b border-slate-700 px-6 py-3 flex items-center justify-between shrink-0">
        <div class="flex items-center gap-4">
            <h1 class="text-lg font-bold text-brand-400">人工复核</h1>
            <span id="sessionBadge" class="text-slate-400 text-xs bg-slate-700 px-2 py-1 rounded">--</span>
        </div>
        <div class="flex items-center gap-3">
            <span id="progressText" class="text-slate-400 text-sm">--</span>
            <div class="w-24 bg-slate-700 rounded-full h-2">
                <div id="progressBar" class="bg-brand-500 h-2 rounded-full" style="width:0"></div>
            </div>
            <button onclick="exportCustom()" class="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 rounded text-sm">导出当前筛选</button>
            <button onclick="exportCustom(null)" class="px-3 py-1.5 bg-gradient-to-br from-brand-500 to-brand-700 hover:from-brand-400 hover:to-brand-600 rounded text-sm font-bold">导出全部</button>
        </div>
    </header>

    <!-- 筛选栏 -->
    <div class="bg-slate-800/50 border-b border-slate-700/50 px-6 py-2 flex items-center gap-3 shrink-0">
        <div id="statusFilters" class="flex gap-1">
            <button data-status="all" class="filter-btn px-3 py-1 rounded text-xs bg-gradient-to-br from-brand-500 to-brand-700 text-white">全部</button>
            <button data-status="待复核" class="filter-btn px-3 py-1 rounded text-xs bg-slate-700 text-slate-300">待复核</button>
            <button data-status="已确认" class="filter-btn px-3 py-1 rounded text-xs bg-slate-700 text-slate-300">已确认</button>
            <button data-status="已修改" class="filter-btn px-3 py-1 rounded text-xs bg-slate-700 text-slate-300">已修改</button>
        </div>
        <div class="w-px h-5 bg-slate-600"></div>
        <select id="selfOpFilter" onchange="applyFilters()" class="bg-slate-700 text-slate-300 text-xs rounded px-2 py-1 border border-slate-600">
            <option value="">自营: 全部</option>
            <option value="自营">自营</option>
        </select>
        <select id="importFilter" onchange="applyFilters()" class="bg-slate-700 text-slate-300 text-xs rounded px-2 py-1 border border-slate-600">
            <option value="">进口/国产: 全部</option>
            <option value="进口">进口</option>
            <option value="国产">国产</option>
        </select>
        <div class="flex-1"></div>
        <input id="searchInput" type="text" placeholder="搜索商品名或编码..." oninput="applyFilters()"
            class="bg-slate-700 text-slate-200 text-sm rounded px-3 py-1 border border-slate-600 w-56 focus:outline-none focus:border-brand-500">
    </div>

    <!-- 主内容区 -->
    <div class="flex flex-1 overflow-hidden">
        <div class="flex-1 overflow-y-auto px-6 py-4">
            <div id="loadingMsg" class="text-center text-slate-400 py-16">
                <div class="animate-pulse text-lg">正在加载复核数据...</div>
                <p class="text-sm mt-2">若处理尚未完成，数据将自动刷新</p>
            </div>
            <div id="reviewList" class="space-y-2 hidden"></div>
            <div id="emptyMsg" class="text-center text-slate-500 py-16 hidden">
                <p class="text-lg">没有符合条件的数据</p>
            </div>
            <div id="pagination" class="flex items-center justify-center gap-2 mt-6 hidden"></div>
        </div>
        <div id="detailPlaceholder" class="w-[420px] shrink-0 border-l border-slate-700/50 bg-slate-800/30 p-6 overflow-y-auto hidden">
            <div class="text-center text-slate-500 mt-20">
                <p class="text-4xl mb-2">&larr;</p>
                <p>点击左侧商品查看详情</p>
            </div>
        </div>
    </div>
</div>

<div id="detailOverlay" class="detail-overlay" onclick="closeDetail()"></div>
<div id="detailPanel" class="detail-panel">
    <div class="p-6">
        <div class="flex items-center justify-between mb-4">
            <h2 class="text-lg font-bold text-brand-400">商品详情</h2>
            <button onclick="closeDetail()" class="text-slate-400 hover:text-white text-xl">&times;</button>
        </div>
        <div id="detailContent"></div>
    </div>
</div>

<script src="/static/js/common.js"></script>
<script src="/static/js/review.js"></script>



</body>
</html>
'''


# ── Electron Layout Template (single, correct version) ──

ELECTRON_LAYOUT = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>产品数据清洗工具</title>
  <link rel="stylesheet" href="/static/css/native.css">
</head>
<body>
  <aside class="island-panel sidebar" id="electronSidebar">
    <div class="sidebar-top">
      <div class="window-dots">
        <div class="dot red"></div><div class="dot yellow"></div><div class="dot green"></div>
      </div>
      <div class="group-select-row">
        <select class="group-select" id="electronGroupSelect" onchange="electronSwitchGroup(this.value)"><option value="">-- 选择分组 --</option></select>
        <button class="group-select-add" onclick="showGroupManager()" title="新建分组">+</button>
      </div>
      <div class="nav-section">
        <div class="section-title">当前会话</div>
        <div class="nav-item" data-step="upload"><svg class="status-icon pending" viewBox="0 0 24 24"><circle cx="12" cy="12" r="7"/></svg><span>上传 & 诊断</span></div>
        <div class="nav-item" data-step="brand-review"><svg class="status-icon pending" viewBox="0 0 24 24"><circle cx="12" cy="12" r="7"/></svg><span>品牌审核</span></div>
        <div class="nav-item" data-step="category-review"><svg class="status-icon pending" viewBox="0 0 24 24"><circle cx="12" cy="12" r="7"/></svg><span>分类审核</span></div>
        <div class="nav-item" data-step="ai-process"><svg class="status-icon pending" viewBox="0 0 24 24"><circle cx="12" cy="12" r="7"/></svg><span>AI 处理</span></div>
        <div class="nav-item" data-step="review"><svg class="status-icon pending" viewBox="0 0 24 24"><circle cx="12" cy="12" r="7"/></svg><span>复核</span></div>
        <div class="nav-item" data-step="export"><svg class="status-icon pending" viewBox="0 0 24 24"><circle cx="12" cy="12" r="7"/></svg><span>导出</span></div>
      </div>
      <div class="nav-section"><div class="section-title">品牌库</div>
        <div class="nav-item" data-page="brand-database" onclick="navigateToSidebar('brand-database')"><svg class="status-icon pending" viewBox="0 0 24 24"><circle cx="12" cy="12" r="7"/></svg><span>品牌数据库</span></div>
        <div class="nav-item" data-page="brand-corrections" onclick="navigateToSidebar('brand-corrections')"><svg class="status-icon pending" viewBox="0 0 24 24"><circle cx="12" cy="12" r="7"/></svg><span>品牌修正记录</span></div>
      </div>
      <div class="nav-section"><div class="section-title">分类体系</div>
        <div class="nav-item" data-page="category-tree" onclick="navigateToSidebar('category-tree')"><svg class="status-icon pending" viewBox="0 0 24 24"><circle cx="12" cy="12" r="7"/></svg><span>分类路径树</span></div>
        <div class="nav-item" data-page="category-classify" onclick="navigateToSidebar('category-classify')"><svg class="status-icon pending" viewBox="0 0 24 24"><circle cx="12" cy="12" r="7"/></svg><span>路径分类标记</span></div>
      </div>
      <div class="nav-section"><div class="section-title">历史会话</div><div id="electronHistory"></div></div>
    </div>
    <div class="sidebar-bottom"><span onclick="electronOpenSettings()" style="cursor:pointer;">设置</span></div>
  </aside>

  <main class="main-area" id="electronMainContent">
    <div class="breadcrumb"><span id="breadcrumbPrev">上传 & 诊断</span><svg viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/></svg><span class="cur" id="breadcrumbCur"></span></div>
    {body_content}
    <div id="panel-review" class="tab-panel hidden"><div id="reviewContainer" style="padding:16px;"></div></div>
    <div id="panel-export" class="tab-panel hidden"><div id="exportContainer" style="padding:16px;"></div></div>
  </main>

  <div id="_panelStorage" style="display:none;"></div>
  <div class="rc-columns-wrapper" id="rcColumnsWrapper">
    <div class="right-column" id="rightColumn"></div>
    <div class="right-column" id="rightColumn2"></div>
  </div>

  <div id="exportPreviewModal" class="export-modal"><div class="export-modal-overlay" onclick="closeExportPreview()"></div><div class="export-modal-content bg-slate-800 border border-slate-700"><h3 class="text-lg font-bold text-slate-100 mb-4 flex items-center gap-2">导出到品牌库</h3><p class="text-sm text-slate-400 mb-3">以下 <span id="exportCount" class="text-brand-400 font-bold">0</span> 个品牌将合并到品牌库：</p><div class="overflow-y-auto max-h-[40vh] mb-4 bg-slate-900 rounded-lg p-3 border border-slate-700/50" id="exportPreviewList"></div><div class="flex justify-end gap-2"><button onclick="closeExportPreview()" class="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded text-sm text-slate-200">取消</button><button onclick="confirmExportToLibrary()" class="px-4 py-2 bg-gradient-to-br from-brand-500 to-brand-700 hover:from-brand-400 hover:to-brand-600 rounded text-sm font-medium text-white shadow-sm">确认导出</button></div></div></div>
  <div id="addBrandModal" class="export-modal"><div class="export-modal-overlay" onclick="closeAddBrandModal()"></div><div class="export-modal-content" style="width:450px;"><h3 class="text-lg font-bold text-brand-400 mb-4">添加/编辑品牌</h3><div class="space-y-4"><div><label class="block text-sm text-slate-400 mb-1">品牌名称 (必填)</label><input type="text" id="modalBrandName" class="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-white focus:border-brand-500 outline-none" placeholder="例如: 乐事/Lay&apos;s"></div><div><label class="block text-sm text-slate-400 mb-1">品牌类型</label><div class="flex gap-1"><div id="modalBrandTypeContainer" class="flex-1" style="position:relative"><input type="text" id="modalBrandType" class="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-white text-sm" placeholder="加载中..." autocomplete="off"><div id="modalBrandTypeList" class="brand-dropdown-list" style="width:100%"></div></div><button onclick="manageBrandTypes()" class="px-2 py-1 bg-slate-600 hover:bg-slate-500 rounded text-sm" title="管理类型">⚙</button></div></div><div><label class="block text-sm text-slate-400 mb-1">国家/地区</label><div class="flex gap-1"><div id="modalBrandCountryContainer" class="flex-1" style="position:relative"><input type="text" id="modalBrandCountry" class="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-white text-sm" placeholder="加载中..." autocomplete="off"><div id="modalBrandCountryList" class="brand-dropdown-list" style="width:100%"></div></div><button onclick="manageCountries()" class="px-2 py-1 bg-slate-600 hover:bg-slate-500 rounded text-sm" title="管理国家">⚙</button></div></div><div id="modalParentBrandRow"><label class="block text-sm text-slate-400 mb-1">关联主品牌（可选）</label><div id="modalParentBrandContainer" style="position:relative"><input type="text" id="modalParentBrand" class="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-white text-sm" placeholder="不关联..." autocomplete="off"><div id="modalParentBrandList" class="brand-dropdown-list" style="width:100%;display:none;"></div></div><div id="modalRelationType" class="flex gap-4 mt-1.5" style="display:none;"><label class="text-sm text-slate-400 flex items-center gap-1.5 cursor-pointer" onclick="document.getElementById('relationSubBrand').checked=true"><input type="radio" name="relation" id="relationSubBrand" value="sub_brand" checked class="accent-brand-500"> 子品牌</label><label class="text-sm text-slate-400 flex items-center gap-1.5 cursor-pointer" onclick="document.getElementById('relationAlias').checked=true"><input type="radio" name="relation" id="relationAlias" value="alias" class="accent-brand-500"> 别名</label></div></div><div class="flex gap-2 pt-2"><button onclick="closeAddBrandModal()" class="flex-1 py-2 bg-slate-600 hover:bg-slate-500 rounded font-bold">取消</button><button onclick="submitNewBrandFromModal()" class="flex-1 py-2 bg-gradient-to-br from-brand-500 to-brand-700 hover:from-brand-400 hover:to-brand-600 rounded font-bold">确认添加</button></div></div></div></div>
  <div id="brandConfigModal" class="export-modal"><div class="export-modal-overlay" onclick="closeBrandConfigModal()"></div><div class="export-modal-content" style="width:500px;"><h3 id="brandConfigModalTitle" class="text-lg font-bold text-brand-400 mb-4">管理</h3><div id="brandConfigList" class="max-h-60 overflow-y-auto mb-4 space-y-1 text-sm"></div><div class="flex gap-2"><input type="text" id="brandConfigNewInput" class="flex-1 bg-slate-700 border border-slate-600 rounded px-3 py-2 text-white text-sm" placeholder="输入新类型名称..."><button onclick="submitBrandConfigNew()" class="px-4 py-2 bg-gradient-to-br from-brand-500 to-brand-700 hover:from-brand-400 hover:to-brand-600 rounded text-sm font-bold">+ 新增</button></div></div></div>
  <div id="categoryPickerModal" class="export-modal"><div class="export-modal-overlay" onclick="closePickerModal()"></div><div class="export-modal-content" style="width:500px;"><h3 class="text-lg font-bold text-brand-400 mb-4">设置分类</h3><input type="text" id="pickerSearch" placeholder="搜索分类..." class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded text-sm mb-3" oninput="filterPickerTree(this.value)" autocomplete="off"><div id="pickerTreeContainer" class="max-h-64 overflow-y-auto border border-slate-700/50 rounded p-2 mb-3"></div><div id="pickerSelectedDisplay" class="text-xs text-slate-400 mb-3 min-h-[20px]"></div><div class="flex gap-2 justify-end"><button onclick="closePickerModal()" class="px-4 py-2 bg-slate-600 hover:bg-slate-500 rounded text-sm">取消</button><button id="pickerConfirmBtn" onclick="confirmPickerSelection()" class="px-4 py-2 bg-gradient-to-br from-brand-500 to-brand-700 hover:from-brand-400 hover:to-brand-600 rounded text-sm font-bold" disabled>确认</button></div></div></div>

  <div id="detailOverlay" class="detail-overlay" onclick="closeDetail()"></div>
  <div id="detailPanel" class="detail-panel"><div id="detailContent"></div></div>

  <script>window._electronMode = true;</script>
  <script src="/static/js/common.js"></script>
  <script src="/static/js/detail-panel.js"></script>
  <script src="/static/js/upload.js"></script>
  <script src="/static/js/diagnosis.js"></script>
  <script src="/static/js/brand_editor.js"></script>
  <script src="/static/js/ai_process.js"></script>
  <script src="/static/js/export.js"></script>
  <script src="/static/js/review.js"></script>
  <script src="/static/js/brand-library.js"></script>
  <script src="/static/js/category-tree.js"></script>
  <script>
(function(){
var STEP_LABEL={'upload':'上传 & 诊断','brand-review':'品牌审核','category-review':'分类审核','ai-process':'AI 处理','review':'复核','export':'导出'};
var PAGE_SECTION={'brand-database':'品牌库','brand-corrections':'品牌库','category-tree':'分类体系','category-classify':'分类体系'};
var PAGE_LABEL={'brand-database':'品牌数据库','brand-corrections':'品牌修正记录','category-tree':'分类路径树','category-classify':'路径分类标记'};
var ICONS={
  done:'<svg class="status-icon done" viewBox="0 0 24 24"><path d="M5 13l4 4L19 7"/></svg>',
  pending:'<svg class="status-icon pending" viewBox="0 0 24 24"><circle cx="12" cy="12" r="7"/></svg>',
  active:'<svg class="status-icon active" viewBox="0 0 24 24"><circle cx="12" cy="12" r="5"/></svg>',
  processing:'<svg class="status-icon processing" viewBox="0 0 24 24"><circle cx="12" cy="12" r="7"/></svg>',
  failed:'<svg class="status-icon failed" viewBox="0 0 24 24"><circle cx="12" cy="12" r="7"/></svg>'
};
var _current=null;

function H(s){return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}

// ── Right-column panel helpers ──
var _rcResize={active:false,startX:0,startW:0,startY:0,startH:0,target:null};

function _chooseColumn(){
  var c1=document.getElementById('rightColumn'),c2=document.getElementById('rightColumn2');
  var n1=c1.querySelectorAll('.panel-card').length,n2=c2.querySelectorAll('.panel-card').length;
  if(n1<2)return c1;if(n2<2)return c2;return c2;
}
function _balanceColumns(){
  var c1=document.getElementById('rightColumn'),c2=document.getElementById('rightColumn2');
  var cards1=c1.querySelectorAll('.panel-card'),cards2=c2.querySelectorAll('.panel-card');
  if(cards1.length<2&&cards2.length>0){c1.appendChild(cards2[cards2.length-1]);}
  _refreshAll();
}
function _refreshAll(){
  var c1=document.getElementById('rightColumn'),c2=document.getElementById('rightColumn2');
  var n1=c1.querySelectorAll('.panel-card').length,n2=c2.querySelectorAll('.panel-card').length;
  var w=document.getElementById('rcColumnsWrapper');
  w.classList.toggle('open',n1+n2>0);
  if(n2>0){c2.classList.add('open');}else{c2.classList.remove('open');}
  if(n1>0){c1.classList.add('open');}else if(n2===0){c1.classList.remove('open');}
  var handle=w.querySelector('.rc-col-resize-handle');
  if(n2>0){
    if(!handle){
      handle=document.createElement('div');handle.className='rc-col-resize-handle';
      handle.addEventListener('mousedown',function(e){
        var c1w=c1.offsetWidth,c2w=c2.offsetWidth;
        _rcResize.active=true;_rcResize.target='col-resize';
        _rcResize._c1=c1;_rcResize._c2=c2;
        _rcResize._startW1=c1w;_rcResize._startW2=c2w;
        _rcResize.startX=e.clientX;handle.classList.add('active');e.preventDefault();
      });
      c1.after(handle);
    }
    handle.classList.add('visible');
  }else if(handle){handle.classList.remove('visible');}
  c1.querySelectorAll('.panel-card').forEach(function(c){c.style.flex='1 1 0';});
  c2.querySelectorAll('.panel-card').forEach(function(c){c.style.flex='1 1 0';});
  _refreshPanelHandles();_initRCSize();
}

function _movePanelToCard(panelId,cardId,title){
  var card=document.querySelector('[data-panel="'+cardId+'"]');
  if(!card){
    var col=_chooseColumn();
    card=document.createElement('div');card.className='panel-card';
    card.setAttribute('data-panel',cardId);
    card.innerHTML='<div class="panel-card-header"><span class="panel-card-title">'+title+'</span><button class="panel-card-close" onclick="window._closePanelCard(\\''+cardId+'\\',\\''+panelId+'\\')">&times;</button></div><div class="panel-card-body"></div>';
    col.appendChild(card);
  }
  var t=card.querySelector('.panel-card-title');if(t)t.textContent=title;
  var body=card.querySelector('.panel-card-body');
  var panel=document.getElementById(panelId);
  if(panel){
    panel.style.cssText='position:relative;width:100%;height:auto;right:auto;top:auto;box-shadow:none;z-index:auto;display:block;overflow-y:auto;max-height:100%;';
    body.appendChild(panel);
  }
  _refreshAll();return body;
}
window._movePanelToCard=_movePanelToCard;
window._closePanelCard=function(cardId,panelId){
  var card=document.querySelector('[data-panel="'+cardId+'"]');
  if(card){
    var panel=document.getElementById(panelId);
    if(panel){panel.style.cssText='';var s=document.getElementById('_panelStorage');if(s)s.appendChild(panel);}
    card.remove();
  }
  _balanceColumns();_refreshAll();
};

function _initRCSize(){
  var c1=document.getElementById('rightColumn');
  if(!c1||c1.querySelector('.rc-resize-handle'))return;
  var h=document.createElement('div');h.className='rc-resize-handle';
  h.addEventListener('mousedown',function(e){
    _rcResize.active=true;_rcResize.target=c1;_rcResize.startX=e.clientX;_rcResize.startW=c1.offsetWidth;
    h.classList.add('active');e.preventDefault();
  });
  c1.appendChild(h);
}
function _refreshPanelHandles(){
  [document.getElementById('rightColumn'),document.getElementById('rightColumn2')].forEach(function(rc){
    if(!rc)return;
    rc.querySelectorAll('.panel-resize-handle').forEach(function(h){h.remove();});
    var cards=rc.querySelectorAll('.panel-card');if(cards.length<2)return;
    for(var i=0;i<cards.length-1;i++){
      var handle=document.createElement('div');handle.className='panel-resize-handle';
      (function(idx,col){handle.addEventListener('mousedown',function(e){
        var a=col.querySelectorAll('.panel-card')[idx],b=col.querySelectorAll('.panel-card')[idx+1];
        _rcResize.active=true;_rcResize.target='panel';_rcResize._cardA=a;_rcResize._cardB=b;
        _rcResize._startHA=a.offsetHeight;_rcResize._startHB=b.offsetHeight;
        _rcResize.startY=e.clientY;handle.classList.add('active');e.preventDefault();
      });})(i,rc);
      cards[i].after(handle);
    }
  });
}
document.addEventListener('mousemove',function(e){
  if(!_rcResize.active)return;
  if(_rcResize.target==='col-resize'){
    var dx=e.clientX-_rcResize.startX;
    var w1=_rcResize._startW1+dx,w2=_rcResize._startW2-dx;
    if(w1<200){w1=200;w2=_rcResize._startW1+_rcResize._startW2-200;}
    if(w2<200){w2=200;w1=_rcResize._startW1+_rcResize._startW2-200;}
    _rcResize._c1.style.width=w1+'px';_rcResize._c2.style.width=w2+'px';
  }else if(_rcResize.target&&_rcResize.target!=='panel'){
    var w=_rcResize.startW-(e.clientX-_rcResize.startX);
    if(w<280)w=280;if(w>window.innerWidth*0.55)w=window.innerWidth*0.55;
    _rcResize.target.style.width=w+'px';
  }else if(_rcResize.target==='panel'){
    var dy=e.clientY-_rcResize.startY;
    var a=_rcResize._cardA,b=_rcResize._cardB;
    var ha=_rcResize._startHA+dy,hb=_rcResize._startHB-dy;
    if(ha<80){ha=80;hb=_rcResize._startHA+_rcResize._startHB-80;}
    if(hb<80){hb=80;ha=_rcResize._startHA+_rcResize._startHB-80;}
    a.style.flex='0 0 '+ha+'px';b.style.flex='0 0 '+hb+'px';
  }
});
document.addEventListener('mouseup',function(){
  if(!_rcResize.active)return;_rcResize.active=false;
  document.querySelectorAll('.rc-resize-handle.active,.panel-resize-handle.active,.rc-col-resize-handle.active').forEach(function(h){h.classList.remove('active');});
});
_initRCSize();

// ── Navigation ──
function updateBreadcrumb(){
  if(!_current)return;
  var p=document.getElementById('breadcrumbPrev'),c=document.getElementById('breadcrumbCur');
  if(_current.type==='page'){p.textContent=PAGE_SECTION[_current.id]||'';c.textContent=PAGE_LABEL[_current.id]||_current.id;}
  else{p.textContent=STEP_LABEL[_current.id]||'';c.textContent='';}
}
function highlightSidebar(){
  document.querySelectorAll('.nav-item[data-step],.nav-item[data-page]').forEach(function(el){
    var match=(_current&&_current.type==='step'&&el.getAttribute('data-step')===_current.id)||(_current&&_current.type==='page'&&el.getAttribute('data-page')===_current.id);
    el.classList.toggle('active',match);
  });
}

function showStepContent(step){
  var up=document.getElementById('uploadSection'),di=document.getElementById('diagnosisSection');
  var ss=document.getElementById('statsSection'),ps=document.getElementById('progressSection');
  document.querySelectorAll('.tab-panel').forEach(function(p){p.classList.add('hidden');});
  if(step==='upload'){if(up)up.style.display='';if(di)di.classList.add('hidden');}
  else if(step==='review'||step==='export'){if(up)up.style.display='none';if(di)di.classList.add('hidden');if(ss)ss.style.display='none';if(ps)ps.style.display='none';}
  else{if(up)up.style.display='none';if(di)di.classList.remove('hidden');if(ss)ss.style.display='none';if(ps)ps.style.display='none';filterSubsections(step);}
  document.querySelectorAll('[id^="pagePanel-"]').forEach(function(p){p.style.display='none';});
}

function filterSubsections(step){
  var bp=document.getElementById('brandPanel'),mc=document.getElementById('mainContent'),cp=document.getElementById('categoryPanel'),ac=document.getElementById('aiConfigPanel'),ap=document.getElementById('aiProgressSection');
  var all=(step==='upload');
  if(bp)bp.style.display=(step==='brand-review'||all)?'':'none';
  if(mc)mc.style.display=(step==='brand-review'||all)?'':'none';
  if(cp)cp.style.display=(step==='category-review'||all)?'':'none';
  if(ac)ac.style.display=(step==='ai-process'||all)?'':'none';
  if(ap)ap.style.display=(step==='ai-process'||all)?'':'none';
}

function showPagePanel(page){
  var up=document.getElementById('uploadSection'),di=document.getElementById('diagnosisSection');
  if(up)up.style.display='none';if(di)di.classList.add('hidden');
  document.querySelectorAll('[id^="pagePanel-"]').forEach(function(p){p.style.display='none';});
  var pid='pagePanel-'+page,panel=document.getElementById(pid);
  if(!panel){
    panel=document.createElement('div');panel.id=pid;
    panel.style.cssText='flex:1;overflow-y:auto;padding:20px';
    var main=document.getElementById('electronMainContent'),bc=main.querySelector('.breadcrumb');
    main.insertBefore(panel,bc.nextSibling);
    if(page==='brand-database'){panel.innerHTML='<div id="brandDatabaseContent" style="padding:20px;"></div>';setTimeout(function(){if(typeof renderBrandDatabase==='function')renderBrandDatabase();},50);}
    else if(page==='category-tree'){
      panel.innerHTML='<div style="padding:16px;display:flex;flex-direction:column;gap:10px;height:100%;">'+
        '<div style="display:flex;gap:8px;">'+
        '<input id="pageCateTreeSearch" placeholder="搜索分类路径..." oninput="filterCategoryTreePage(this.value)" style="flex:1;padding:6px 10px;border:1px solid var(--border);border-radius:var(--radius-sm);background:var(--panel);color:var(--text-main);font-size:12px;outline:none;">'+
        '<input id="pageProductSearch" placeholder="搜商品名/编码..." oninput="searchProductPage(this.value)" style="flex:1;padding:6px 10px;border:1px solid var(--border);border-radius:var(--radius-sm);background:var(--panel);color:var(--text-main);font-size:12px;outline:none;">'+
        '<button id="pageToggleMktBtn" onclick="toggleMarketingPage()" style="padding:6px 10px;border:1px solid var(--border);border-radius:var(--radius-sm);background:var(--panel);color:var(--text-sub);cursor:pointer;font-size:11px;white-space:nowrap;">隐藏营销</button></div>'+
        '<div id="pageProductSearchResults" style="display:none;max-height:200px;overflow-y:auto;background:var(--panel);border:1px solid var(--border);border-radius:var(--radius-sm);padding:8px;"></div>'+
        '<div id="pageCateTreeContainer" style="flex:1;overflow-y:auto;"></div></div>';
      setTimeout(function(){if(typeof renderCategoryTreePage==='function')renderCategoryTreePage();},50);
    }
    else if(page==='category-classify'){panel.innerHTML='<div id="categoryClassifyContent" style="padding:20px;"></div>';setTimeout(function(){if(typeof _renderClassifyPage==='function')_renderClassifyPage();},50);}
    else if(page==='brand-corrections'){panel.innerHTML='<div id="brandCorrectionsContent" style="padding:20px;"></div>';setTimeout(function(){if(typeof _renderBrandCorrectionsPage==='function')_renderBrandCorrectionsPage();},50);}
    else {panel.innerHTML='<div style="padding:40px;text-align:center;color:var(--text-muted)"><p style="font-size:16px;font-weight:500;margin-bottom:8px">'+(PAGE_LABEL[page]||page)+'</p><p style="font-size:12px">功能将在后续任务中激活</p></div>';}
  }
  panel.style.display='';
}

function navigateToStep(step){
  _current={type:'step',id:step};
  highlightSidebar();showStepContent(step);updateBreadcrumb();
  if(step==='review'&&typeof sessionId!=='undefined'&&sessionId){
    var panel=document.getElementById('panel-review');if(panel)panel.classList.remove('hidden');
    var rc=document.getElementById('reviewContainer');if(!rc)return;
    rc.innerHTML='<div style="text-align:center;color:var(--text-muted);padding:40px;">加载复核数据...</div>';
    fetch('/review?embed=1').then(function(r){return r.text()}).then(function(html){
      rc.innerHTML=html;
      var app=rc.querySelector('#review-app');if(app){app.classList.remove('h-screen');app.style.height='100%';}
      if(typeof window.initReview==='function')window.initReview();
    }).catch(function(e){rc.innerHTML='<p style="color:var(--red);padding:20px;">加载失败: '+e.message+'</p>';});
  }
  if(step==='export'){}
}

function navigateToSidebar(page){
  _current={type:'page',id:page};
  highlightSidebar();showPagePanel(page);updateBreadcrumb();
}

// ── Status icons ──
function setStepIconHTML(step,status){
  var el=document.querySelector('.nav-item[data-step="'+step+'"] .status-icon');
  if(el){var w=document.createElement('span');w.innerHTML=ICONS[status]||ICONS.pending;el.parentNode.replaceChild(w.firstChild,el);}
}
function setStepDone(step){setStepIconHTML(step,'done');}
function setStepActive(step){setStepIconHTML(step,'active');}
function setStepProcessing(step){setStepIconHTML(step,'processing');}
function setStepFailed(step){setStepIconHTML(step,'failed');}

// ── Groups & history ──
function loadGroups(){
  fetch('/api/groups').then(function(r){return r.json()}).then(function(d){
    var s=document.getElementById('electronGroupSelect');if(!s)return;var c=s.value;
    s.innerHTML='<option value="">-- 选择分组 --</option>';
    Object.entries(d.groups||{}).forEach(function(e){s.innerHTML+='<option value="'+e[0]+'">'+H(e[1].name)+'</option>';});
    var g=localStorage.getItem('last_group_id')||'';s.value=c||g;
    var u=document.getElementById('uploadGroup');if(u&&g)u.value=g;
  }).catch(function(){});
}

function renderHistory(){
  var e=document.getElementById('electronHistory');if(!e)return;
  fetch('/api/recent_files').then(function(r){return r.json()}).then(function(f){
    e.innerHTML=(f||[]).slice(0,5).map(function(x){
      return '<div class="nav-item" style="font-size:11px" onclick="window._loadHistoryFile(\\''+x.id+'\\')"><svg class="status-icon pending" viewBox="0 0 24 24"><circle cx="12" cy="12" r="7"/></svg>'+((x.time||'').split(' ')[0])+' | '+((x.name||'').substring(0,22))+'</div>';
    }).join('');
  }).catch(function(){});
}
window._loadHistoryFile=function(fid){if(typeof importRecentFile==='function')importRecentFile(fid);navigateToStep('upload');};

function switchGroup(g){localStorage.setItem('last_group_id',g);var u=document.getElementById('uploadGroup');if(u)u.value=g;renderHistory();}

// ── Init ──
document.querySelectorAll('.nav-item[data-step]').forEach(function(el){
  el.addEventListener('click',function(){navigateToStep(el.getAttribute('data-step'));});
  el.style.cursor='pointer';
});

loadGroups();renderHistory();

// Hide web header if injected
var oldHeader=document.querySelector('#electronMainContent > header');
if(oldHeader)oldHeader.style.display='none';

navigateToStep('upload');

window.electronSwitchGroup=switchGroup;
window.electronOpenSettings=function(){if(window.electronAPI)window.electronAPI.openSettings();else window.open('/settings','_blank');};
window.navigateToSidebar=navigateToSidebar;
window.navigateToStep=navigateToStep;
window.setStepDone=setStepDone;window.setStepActive=setStepActive;
window.setStepProcessing=setStepProcessing;window.setStepFailed=setStepFailed;
})();
</script>
</body>
</html>
"""
