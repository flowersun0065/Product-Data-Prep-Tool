// ===== 诊断模块 (方案 1 最终加固版) =====

// --- 全局状态变量安全初始化 (防止重复声明报错) ---
if (typeof window.diagnosisData === 'undefined') window.diagnosisData = null;
if (typeof window.categoryOptions === 'undefined') window.categoryOptions = [];
if (typeof window.categoryRules === 'undefined') window.categoryRules = {};
if (typeof window.marketingTags === 'undefined') window.marketingTags = {};
if (typeof window.itemCategoryDecisions === 'undefined') window.itemCategoryDecisions = {};
if (typeof window.currentPanelData === 'undefined') window.currentPanelData = null;
if (typeof window.currentPanelPage === 'undefined') window.currentPanelPage = 1;
if (typeof window.showMarketingInTree === 'undefined') window.showMarketingInTree = true;
if (typeof window.globalCateTreeOpen === 'undefined') window.globalCateTreeOpen = false;
if (typeof window.globalBrandListOpen === 'undefined') window.globalBrandListOpen = false;

// 轮询诊断状态
let _pollRetries = 0;
const MAX_POLL_RETRIES = 5;

async function pollDiagnosisStatus() {
    if (!sessionId) return;
    
    // 显示进度区域
    document.getElementById('progressSection').classList.remove('hidden');
    document.getElementById('statsSection').classList.add('opacity-50');
    
    try {
        const res = await fetch(`/api/diagnosis_status?sid=${sessionId}`);
        const data = await res.json();
        
        _pollRetries = 0;  // 成功一次就重置计数
        
        if (data.error) {
            document.getElementById('progressText').textContent = '❌ ' + data.error;
            document.getElementById('progressBar').style.width = '100%';
            document.getElementById('progressBar').classList.remove('bg-cyan-500');
            document.getElementById('progressBar').classList.add('bg-red-500');
            return;
        }
        
        // 更新进度条
        const progress = data.progress || 0;
        const message = data.message || '处理中...';
        
        document.getElementById('progressBar').style.width = progress + '%';
        document.getElementById('progressPercent').textContent = progress + '%';
        document.getElementById('progressText').textContent = message;

        // 步骤耗时
        const st = data.step_times || {};
        if (st.reading_start && st.reading_end) {
            document.getElementById('stepReading').textContent = `读取文件: ${(st.reading_end - st.reading_start).toFixed(1)}s`;
        }
        if (st.brands_start && st.brands_end) {
            document.getElementById('stepBrands').textContent = `分析品牌: ${(st.brands_end - st.brands_start).toFixed(1)}s`;
        }
        if (st.categories_start && st.categories_end) {
            document.getElementById('stepCategories').textContent = `分析分类: ${(st.categories_end - st.categories_start).toFixed(1)}s`;
        }
        if (data.current_step && data.current_step_start) {
            const now = Date.now() / 1000;
            const realtime = (now - data.current_step_start).toFixed(1);
            const el = document.getElementById('step' + data.current_step.charAt(0).toUpperCase() + data.current_step.slice(1));
            if (el && !st[data.current_step + '_end']) {
                el.textContent = `${data.current_step === 'reading' ? '读取文件' : data.current_step === 'brands' ? '分析品牌' : '分析分类'}: ${realtime}s`;
            }
        }
        if (data.elapsed) {
            document.getElementById('totalTime').textContent = `总计: ${data.elapsed}s`;
        }
        document.getElementById('progressSteps').classList.remove('hidden');
        
        // 显示日志
        if (data.logs && data.logs.length > 0) {
            const logsHtml = data.logs.slice(-5).map(log => `<div>${log}</div>`).join('');
            document.getElementById('progressLogs').innerHTML = logsHtml;
        }
        
        if (data.status === 'completed') {
            // 诊断完成
            document.getElementById('progressText').textContent = '✅ 诊断完成!';
            document.getElementById('progressBar').classList.remove('bg-cyan-500');
            document.getElementById('progressBar').classList.add('bg-green-500');
            
            // 隐藏进度区域，显示结果
            setTimeout(() => {
                document.getElementById('progressSection').classList.add('hidden');
                document.getElementById('statsSection').classList.remove('opacity-50');
                fetchDiagnosisResult();
            }, 500);
        } else if (data.status === 'error') {
            document.getElementById('progressText').textContent = '❌ 诊断失败: ' + (data.message || '未知错误');
            document.getElementById('progressBar').style.width = '100%';
            document.getElementById('progressBar').classList.remove('bg-cyan-500');
            document.getElementById('progressBar').classList.add('bg-red-500');
        } else {
            // 继续轮询 - 间隔 3s
            setTimeout(pollDiagnosisStatus, 3000);
        }
    } catch (err) {
        _pollRetries++;
        if (_pollRetries >= MAX_POLL_RETRIES) {
            document.getElementById('progressText').textContent =
                '❌ 服务器连接失败（已重试 ' + MAX_POLL_RETRIES + ' 次），请刷新页面重试';
            document.getElementById('progressBar').classList.remove('bg-cyan-500');
            document.getElementById('progressBar').classList.add('bg-red-500');
            document.getElementById('progressBar').style.width = '100%';
            return;
        }
        document.getElementById('progressText').textContent = '❌ 获取状态失败 (' + _pollRetries + '/' + MAX_POLL_RETRIES + '): ' + err.message;
        // 指数退避：10s, 20s, 40s, 60s, 60s
        const delay = Math.min(10000 * Math.pow(2, _pollRetries - 1), 60000);
        setTimeout(pollDiagnosisStatus, delay);
    }
}

// 获取诊断结果
async function fetchDiagnosisResult() {
    if (!sessionId) return;
    
    try {
        const res = await fetch(`/api/diagnosis_result?sid=${sessionId}`);
        const data = await res.json();
        
        if (data.error) {
            document.getElementById('uploadMsg').textContent = '❌ ' + data.error;
            return;
        }
        
        // 更新诊断数据（本地 + window 确保跨文件访问）
        diagnosisData = data.diagnosis;
        window.diagnosisData = data.diagnosis;
        
        // 显示诊断结果
        showDiagnosis(data);
        
    } catch (err) {
        document.getElementById('uploadMsg').textContent = '❌ 获取结果失败: ' + err.message;
    }
}

// 显示诊断结果
async function showDiagnosis(data) {
    // 防御性检查：诊断数据不完整时不渲染
    if (!data || !data.diagnosis || !data.diagnosis.brand_clusters || !data.stats) {
        console.error('诊断数据不完整，跳过面板展示:', data);
        return;
    }

    // 确保全局诊断数据可用（兼容 tryRestoreSession 等路径）
    diagnosisData = data.diagnosis;
    window.diagnosisData = data.diagnosis;

    // 隐藏进度区域，显示结果区域
    document.getElementById('progressSection').classList.add('hidden');
    document.getElementById('statsSection').classList.remove('hidden');
    document.getElementById('diagnosisSection').classList.remove('hidden');
    
    const stats = data.stats;
    document.getElementById('statTotal').textContent = stats.total || 0;
    document.getElementById('statValid').textContent = stats.valid || 0;
    document.getElementById('statBrandMissing').textContent = stats.brand_missing || 0;
    document.getElementById('statBrandMismatch').textContent = stats.brand_mismatch || 0;
    document.getElementById('statMarketing').textContent = stats.marketing || 0;
    document.getElementById('statNeedAI').textContent = stats.need_ai || 0;
    
    // 更新全局分类选项
    if (data.category_options) {
        window.categoryOptions = data.category_options;
    }

    // 加载已保存的分类规则
    try {
        const resp = await fetch(`/api/rules/get?sid=${sessionId}`);
        const saved = await resp.json();
        if (saved.categories) {
            Object.assign(window.categoryRules, saved.categories);
        }
        if (saved.marketing_tags) {
            Object.assign(window.marketingTags, saved.marketing_tags);
        }
    } catch (e) {
        console.warn('加载已保存的分类规则失败:', e);
    }

    // 渲染分类统一树
    renderCategoryGroups(data.diagnosis);
    renderGlobalCategoryTree();
    // 加载缺失建议（数据已含path）
    loadSuggestionsForMissing();
    
    // 先获取品牌库和规则，再显示品牌分组
    fetchBrandDatabase().then(async () => {
        await syncBrandRules();
        renderBrandGroups(data.diagnosis.brand_clusters);
        renderGlobalBrandList();
    });
}

// 渲染分类各个区域
let missingPage = 1;
let lastActiveCategoryPath = null;
const MISSING_PER_PAGE = 20;

function renderCategoryGroups(diagnosis) {
    const cateCountSpan = document.getElementById('cateCount');
    const allCodes = diagnosis.all_codes || [];
    const total = allCodes.length;
    const confirmed = allCodes.filter(c => window.categoryRules[c.code]).length;
    cateCountSpan.textContent = `共 ${total} 个商品，已处理 ${confirmed}/${total}`;

    renderCategoryTree(diagnosis);
    renderMissingItems(diagnosis.missing_items || []);
}

async function renderCategoryTree(diagnosis) {
    const container = document.getElementById('cateTreeContainer');
    if (!container) return;

    const options = diagnosis.category_options || window.categoryOptions;
    if (!options || !options.level1) {
        container.innerHTML = '<p class="text-slate-500 text-xs italic py-2">暂无分类数据</p>';
        return;
    }

    // 获取已确认的分类标记
    let classified = {};
    try {
        const res = await fetch('/api/classified_paths');
        classified = (await res.json()).classified_paths || {};
    } catch (e) {}

    const pathClass = diagnosis.path_classifications || {};

    // Build index from all_codes (用清洗后路径做索引，与树展示的路径一致)
    const pathIndex = {};
    (diagnosis.all_codes || []).forEach(item => {
        (item.suggested_path || []).forEach(p => {
            if (!p) return;
            const key = p.replace(/\s*>\s*/g, ' > ');
            if (!pathIndex[key]) pathIndex[key] = { count: 0, items: [] };
            pathIndex[key].count++;
            pathIndex[key].items.push(item);
        });
    });

    let html = '';
    options.level1.forEach(l1 => {
        const l2s = options.level2_by_level1[l1] || [];
        let l2Html = '';
        l2s.forEach(l2 => {
            const l3s = options.level3_by_level2[`${l1} > ${l2}`] || [];
            let l3Html = '';
            l3s.forEach(l3 => {
                const path = `${l1} > ${l2} > ${l3}`;
                const info = pathIndex[path];
                const count = info ? info.count : 0;
                // 即使 count=0（全营销无清洗路径），仍展示路径供用户操作

                // 分类标识（手动标记 > 算法逐级判断 > fallback）
                const label = classified[path];
                const aiLabel = pathClass[path] && pathClass[path].label;
                const isMarketing = label === 'marketing' || aiLabel === 'marketing';

                // 隐藏营销分类模式下跳过
                if (!window.showMarketingInTree && isMarketing) return;

                const processed = info ? info.items.filter(i => window.categoryRules[i.code]).length : 0;
                const remaining = count - processed;
                const statusText = count === 0 ? '无商品' : (remaining === 0 ? '已完成' : `待处理 ${remaining}/${count}`);
                const statusColor = count === 0 ? 'text-slate-500' : (remaining === 0 ? 'text-green-400' : 'text-yellow-400');
                const safePath = path.replace(/'/g, "\\'");

                let badge = '';
                if (label === 'marketing') {
                    badge = '<span class="text-[9px] text-red-400">🔴已标记营销</span>';
                } else if (label === 'standard') {
                    badge = '<span class="text-[9px] text-green-400">🟢已标记标准</span>';
                } else {
                    const ai = pathClass[path];
                    if (ai && ai.label === 'marketing') {
                        badge = '<span class="text-[9px] text-orange-400">⚠️算法:营销</span>';
                    } else {
                        badge = '<span class="text-[9px] text-blue-400">✅算法:标准</span>';
                    }
                }

                const isActive = lastActiveCategoryPath === path;
                l3Html += `<div data-path="${safePath}" class="flex items-center gap-1 py-1 pl-6 hover:bg-slate-700/30 rounded group ${isActive ? 'bg-cyan-700/20 ring-1 ring-cyan-500/50' : ''}">
                    <span class="text-xs text-slate-300">${l3}</span>
                    <span class="ml-1">${badge}</span>
                    <span class="text-[10px] text-slate-500 ml-1">${count}条</span>
                    <span class="text-[9px] ${statusColor} ml-1">${statusText}</span>
                    <span class="ml-auto opacity-0 group-hover:opacity-100 transition-opacity flex gap-1">
                        ${count > 0 ? `<button onclick="openUnifiedCategoryPanel('${safePath}')" class="text-[10px] px-2 py-0.5 bg-blue-600/70 hover:bg-blue-600 rounded">查看</button>` : ''}
                        <button onclick="classifyPath('${safePath}','marketing')" class="text-[10px] px-2 py-0.5 bg-red-600/70 hover:bg-red-600 rounded">标记营销</button>
                        <button onclick="classifyPath('${safePath}','standard')" class="text-[10px] px-2 py-0.5 bg-green-600/70 hover:bg-green-600 rounded">标记标准</button>
                    </span>
                </div>`;
            });
            if (!l3Html) return;
            const safeL1 = l1.replace(/'/g, "\\'");
            const safeL2 = l2.replace(/'/g, "\\'");
            l2Html += `<div class="tree-node ml-2">
                <div class="flex items-center gap-1 py-0.5 hover:bg-slate-700/30 rounded group"
                     style="cursor:pointer"
                     onclick="const t=this;const n=t.nextElementSibling;n.classList.toggle('hidden');const a=t.querySelector('.arrow');a.textContent=a.textContent==='▶'?'▼':'▶'">
                    <span class="arrow text-[8px] text-slate-500">▶</span>
                    <span class="text-xs text-slate-300">${l2}</span>
                    <span class="ml-auto opacity-0 group-hover:opacity-100 transition-opacity flex gap-1" onclick="event.stopPropagation()">
                        <button onclick="batchClassifyPath('${safeL1}','${safeL2}','marketing')" class="text-[9px] px-1.5 py-0.5 bg-red-600/70 hover:bg-red-600 rounded whitespace-nowrap">批量营销</button>
                        <button onclick="batchClassifyPath('${safeL1}','${safeL2}','standard')" class="text-[9px] px-1.5 py-0.5 bg-green-600/70 hover:bg-green-600 rounded whitespace-nowrap">批量标准</button>
                    </span>
                </div>
                <div class="tree-children hidden">${l3Html}</div>
            </div>`;
        });
        if (!l2Html) return;
        const safeL1Top = l1.replace(/'/g, "\\'");
        html += `<div class="tree-node">
            <div class="flex items-center gap-1 py-0.5 hover:bg-slate-700/30 rounded group font-medium"
                 style="cursor:pointer"
                 onclick="const t=this;const n=t.nextElementSibling;n.classList.toggle('hidden');const a=t.querySelector('.arrow');a.textContent=a.textContent==='▶'?'▼':'▶'">
                <span class="arrow text-[8px] text-slate-400">▶</span>
                <span class="text-xs text-slate-200">${l1}</span>
                <span class="ml-auto opacity-0 group-hover:opacity-100 transition-opacity flex gap-1" onclick="event.stopPropagation()">
                    <button onclick="batchClassifyPath('${safeL1Top}','','marketing')" class="text-[9px] px-1.5 py-0.5 bg-red-600/70 hover:bg-red-600 rounded whitespace-nowrap">批量营销</button>
                    <button onclick="batchClassifyPath('${safeL1Top}','','standard')" class="text-[9px] px-1.5 py-0.5 bg-green-600/70 hover:bg-green-600 rounded whitespace-nowrap">批量标准</button>
                </span>
            </div>
            <div class="tree-children hidden">${l2Html}</div>
        </div>`;
    });
    container.innerHTML = html || '<p class="text-slate-500 text-xs italic py-2">暂无分类数据</p>';

    // 自动展开 + 滚动到上次操作的路径
    if (lastActiveCategoryPath && container) {
        const l3Row = container.querySelector(`[data-path="${lastActiveCategoryPath}"]`);
        if (l3Row) {
            const l2Node = l3Row.closest('.tree-node');
            const l1Node = l2Node?.parentElement?.closest('.tree-node');
            [l1Node, l2Node].forEach(node => {
                if (node) {
                    const children = node.querySelector('.tree-children');
                    if (children?.classList.contains('hidden')) {
                        children.classList.remove('hidden');
                        const arrow = node.querySelector('.arrow');
                        if (arrow) arrow.textContent = '▼';
                    }
                }
            });
            l3Row.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }
}

function filterCategoryTree(text) {
    const container = document.getElementById('cateTreeContainer');
    if (!container) return;
    const lower = (text || '').toLowerCase();
    container.querySelectorAll('.tree-node').forEach(node => {
        const match = node.textContent.toLowerCase().includes(lower);
        node.style.display = match ? '' : 'none';
    });
}

// 按商品名/编码搜索清洗路径（支持连续子串 + 关键词AND两种模式同时匹配，分页展示全部结果）
function searchProduct(query) {
    const container = document.getElementById('productSearchResults');
    if (!container) return;
    const raw = (query || '').trim();
    if (!raw || raw.length < 2) {
        container.classList.add('hidden');
        container._searchMatches = null;
        return;
    }
    const lower = raw.toLowerCase();
    const keywords = lower.split(/\s+/).filter(k => k.length > 0);
    const codes = window.diagnosisData?.all_codes || [];
    const seen = new Set();
    const matches = [];
    function addMatch(item) {
        const key = item.code || item.name || '';
        if (seen.has(key)) return;
        seen.add(key);
        matches.push(item);
    }
    for (const item of codes) {
        const name = (item.name || '').toLowerCase();
        const code = (item.code || '').toLowerCase();
        // 模式一：全串模糊匹配（原有行为）
        if (name.includes(lower) || code.includes(lower)) {
            addMatch(item);
            continue;
        }
        // 模式二：关键词 AND 匹配（空格分词，需包含所有关键词）
        if (keywords.length > 1) {
            const allMatch = keywords.every(kw => name.includes(kw) || code.includes(kw));
            if (allMatch) addMatch(item);
        }
    }
    if (matches.length === 0) {
        container.innerHTML = '<div class="text-slate-500 text-xs px-2 py-1">未找到匹配商品</div>';
        container.classList.remove('hidden');
        container._searchMatches = null;
        return;
    }
    // 保存全部匹配结果，初始化分页
    container._searchMatches = matches;
    container._searchPage = 0;
    renderSearchPage(container);
    container.classList.remove('hidden');
}

const SEARCH_PAGE_SIZE = 50;

function renderSearchPage(container) {
    const matches = container._searchMatches || [];
    const page = container._searchPage || 0;
    const total = matches.length;
    const start = 0;
    const end = Math.min((page + 1) * SEARCH_PAGE_SIZE, total);
    const pageItems = matches.slice(start, end);
    const hasMore = end < total;

    const itemsHtml = pageItems.map(item => {
        const p = item.suggested_path?.[0] || '';
        const safePath = p.replace(/'/g, "\\'");
        return `<div class="flex items-center gap-2 px-2 py-1.5 hover:bg-cyan-700/30 rounded cursor-pointer border-b border-slate-700/50 last:border-0"
                     onclick="openUnifiedCategoryPanel('${safePath}')">
                    <span class="text-xs text-slate-300 truncate flex-1">${item.name}</span>
                    <span class="text-[10px] text-slate-500 font-mono">${item.code}</span>
                    ${p ? `<span class="text-[10px] text-cyan-400 truncate max-w-[200px]">→ ${p}</span>` : '<span class="text-[10px] text-slate-500">→ 暂无路径</span>'}
                </div>`;
    }).join('');

    const countBar = `<div class="flex items-center justify-between px-2 py-1 text-[10px] text-slate-500 border-b border-slate-700/50">
        <span>共 ${total} 个匹配</span>
        <span>已显示 ${end} 个</span>
    </div>`;

    const moreBtn = hasMore
        ? `<button class="w-full text-xs text-cyan-400 py-1.5 hover:bg-cyan-700/20 rounded"
                   onclick="loadMoreSearchResults(this)">加载更多（${total - end} 条）</button>`
        : '';

    container.innerHTML = countBar + itemsHtml + moreBtn;
}

function loadMoreSearchResults(btn) {
    const container = document.getElementById('productSearchResults');
    if (!container) return;
    container._searchPage = (container._searchPage || 0) + 1;
    renderSearchPage(container);
}

function toggleMarketingInTree() {
    window.showMarketingInTree = !window.showMarketingInTree;
    const btn = document.querySelector('[onclick*="toggleMarketingInTree"]');
    if (btn) btn.textContent = window.showMarketingInTree ? '隐藏营销分类' : '显示营销分类';
    renderCategoryTree(window.diagnosisData);
}

async function classifyPath(path, label) {
    try {
        await fetch('/api/classify/path', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ path, label })
        });
        // 标记营销后，清除该路径下所有商品的 suggested_path
        if (label === 'marketing' && window.diagnosisData) {
            const normalized = path.replace(/\s*>\s*/g, ' > ');
            (window.diagnosisData.all_codes || []).forEach(item => {
                (item.suggested_path || []).forEach((sp, idx) => {
                    if (sp.replace(/\s*>\s*/g, ' > ') === normalized) {
                        item.suggested_path.splice(idx, 1);
                    }
                });
                if (!item.suggested_path || item.suggested_path.length === 0) {
                    item.suggested_path = [];
                    item._section = 'missing';
                }
            });
        }
        await renderCategoryTree(window.diagnosisData);
    } catch (e) {
        console.error('分类标记失败:', e);
    }
}

async function batchClassifyPath(l1, l2, label) {
    const options = (window.diagnosisData && window.diagnosisData.category_options) || window.categoryOptions;
    if (!options) return;

    const paths = [];
    if (l2) {
        // L2 级：收集该 L2 下所有 L3 路径
        const l3s = options.level3_by_level2[`${l1} > ${l2}`] || [];
        l3s.forEach(l3 => {
            const path = `${l1} > ${l2} > ${l3}`;
            paths.push(path);
        });
    } else {
        // L1 级：收集该 L1 下所有 L2 的所有 L3 路径
        const l2s = options.level2_by_level1[l1] || [];
        l2s.forEach(l2name => {
            const l3s = options.level3_by_level2[`${l1} > ${l2name}`] || [];
            l3s.forEach(l3 => {
                paths.push(`${l1} > ${l2name} > ${l3}`);
            });
        });
    }

    if (paths.length === 0) return;
    const labelText = label === 'marketing' ? '营销' : '标准';
    if (!confirm(`确定将以下 ${paths.length} 个路径标记为「${labelText}」分类吗？\n\n${paths.slice(0, 5).join('\n')}${paths.length > 5 ? `\n...等 ${paths.length} 个` : ''}`)) return;

    try {
        await fetch('/api/classify/path/batch', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ paths, label })
        });
        // 批量标记营销后，清除这些路径下所有商品的 suggested_path
        if (label === 'marketing' && window.diagnosisData) {
            const normalizedPaths = new Set(paths.map(p => p.replace(/\s*>\s*/g, ' > ')));
            (window.diagnosisData.all_codes || []).forEach(item => {
                if (!item.suggested_path) return;
                item.suggested_path = item.suggested_path.filter(sp => {
                    const nsp = sp.replace(/\s*>\s*/g, ' > ');
                    return !normalizedPaths.has(nsp);
                });
                if (item.suggested_path.length === 0) {
                    item._section = 'missing';
                }
            });
        }
        await renderCategoryTree(window.diagnosisData);
    } catch (e) {
        console.error('批量分类标记失败:', e);
    }
}

function renderMissingItems(items) {
    const container = document.getElementById('categoryMissingGroups');
    const pagination = document.getElementById('missingPagination');
    if (!container) return;

    if (!items || items.length === 0) {
        container.innerHTML = '<p class="text-slate-600 text-sm italic py-2">暂无缺失商品</p>';
        if (pagination) pagination.classList.add('hidden');
        return;
    }

    const totalPages = Math.ceil(items.length / MISSING_PER_PAGE);
    if (missingPage > totalPages) missingPage = totalPages;
    if (missingPage < 1) missingPage = 1;

    const start = (missingPage - 1) * MISSING_PER_PAGE;
    const pageItems = items.slice(start, start + MISSING_PER_PAGE);

    container.innerHTML = pageItems.map(item => {
        const idx = items.indexOf(item);
        const code = String(item.code).trim();
        const catRule = window.categoryRules?.[code];
        const isConfirmed = catRule && catRule.action === 'confirm';
        const suggested = item._suggested_category || '';
        const confidence = item.suggested_confidence !== undefined ? item.suggested_confidence : (suggested ? 0.1 : 0);
        const confColor = confidence >= 0.8 ? 'text-green-400' : confidence >= 0.5 ? 'text-yellow-400' : 'text-red-400';
        const confLabel = confidence >= 0.8 ? '高' : confidence >= 0.5 ? '中' : '低';
        const suggestHtml = isConfirmed ?
            `<div class="text-[10px] text-green-400 mt-0.5">✅ 已确认: ${catRule.replacement}</div>` :
            (suggested ?
                `<div class="text-[10px] text-cyan-400 mt-0.5">建议分类: ${suggested} <span class="${confColor} font-bold">[${confLabel}]</span> <button onclick="applyMissingCategory(${idx},'${suggested.replace(/'/g, "\\'")}')" class="text-[10px] px-1.5 py-0.5 bg-cyan-700 hover:bg-cyan-600 rounded ml-1">确认</button></div>` :
                `<div class="text-[10px] text-slate-500 mt-0.5 italic">暂无适合分类建议，请手动选择</div>`);
        const factors = item.factors || {};
        let factorsHtml = '';
        if (factors.entity || factors.brand_type || (factors.modifier_detail && factors.modifier_detail.length) || factors.spec_weight || factors.spec_pack) {
            const parts = [];
            let entityLabel = `entity="${factors.entity}"`;
            if (factors.entity_type) {
                entityLabel += ` [${factors.entity_type}`;
                if (factors.entity_subtype) entityLabel += `-${factors.entity_subtype}`;
                entityLabel += ']';
            }
            if (factors.brand_type) parts.push(`type="${factors.brand_type}"`);
            if (factors.modifier_detail && factors.modifier_detail.length) {
                const modStr = factors.modifier_detail.map(m => `${m.value}[${m.type || '未知'}]`).join(',');
                parts.push(`修饰词=${modStr}`);
            } else if (factors.modifiers?.length) {
                parts.push(`修饰词=${factors.modifiers.join(',')}`);
            }
            const specParts = [];
            if (factors.spec_weight) specParts.push(factors.spec_weight);
            if (factors.spec_pack) specParts.push(factors.spec_pack);
            if (specParts.length) parts.push(`规格: ${specParts.join(' | ')}`);
            if (item.corrected_from_history) parts.push('📌 历史修正');
            if (parts.length) factorsHtml = `<div class="text-[9px] text-cyan-300 mt-0.5">🔍 ${entityLabel}${parts.length ? ' | ' + parts.join(' | ') : ''}</div>`;
        }
        return `<div class="flex items-start justify-between py-2 px-3 ${isConfirmed ? 'bg-green-900/20 border border-green-700/30' : 'bg-slate-700/30'} rounded mb-1">
            <div class="text-sm mr-2 flex-1 min-w-0 flex items-start gap-2">
                ${item.org_image_url ? `<img src="${item.org_image_url}" class="w-8 h-8 object-cover rounded flex-shrink-0 mt-0.5 cursor-zoom-in" onerror="this.style.display='none'" onclick="previewImage('${item.org_image_url}')" alt="">` : ''}
                <div class="min-w-0">
                    <div class="truncate">${item.name} <span class="text-[10px] text-slate-500">(${item.code})</span></div>
                    ${suggestHtml}
                    ${factorsHtml}
                </div>
            </div>
            <div class="flex gap-1 flex-shrink-0">
                ${isConfirmed ? '' :
                    `<button onclick="openCategoryPicker('${item.code}','${(item.suggested_path?.[0]||'').replace(/'/g, "\\'")}')" class="px-2 py-1 bg-yellow-600 hover:bg-yellow-500 text-white rounded text-xs">设置分类</button>
                <button onclick="skipMissingItem(${idx})" class="px-2 py-1 bg-slate-600 hover:bg-slate-500 rounded text-xs">跳过</button>`}
            </div>
        </div>`;
    }).join('');

    if (pagination) {
        if (totalPages > 1) {
            pagination.classList.remove('hidden');
            document.getElementById('missingPageInfo').textContent = `第 ${missingPage}/${totalPages} 页 (${items.length} 条)`;
            document.getElementById('missingPrevPage').disabled = missingPage <= 1;
            document.getElementById('missingNextPage').disabled = missingPage >= totalPages;
        } else {
            pagination.classList.add('hidden');
        }
    }
}

function changeMissingPage(delta) {
    missingPage += delta;
    const items = (window.diagnosisData && window.diagnosisData.missing_items) || [];
    renderMissingItems(items);
}

async function saveCategoryCorrections(code, path, factors, item, suggestedPath) {
    const f = factors || {};
    const origSuggested = suggestedPath || path;
    if (f.entity) {
        await fetch('/api/correction/category', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                entity: f.entity, brand_type: f.brand_type || '',
                modifiers: f.modifiers || [],
                suggested_path: origSuggested,
                corrected_path: path,
                samples: [{ name: item?.name || '', code: code }]
            })
        }).catch(e => console.warn('修正保存失败(category):', e));
    }
    await fetch('/api/correction/product', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: code, category: path, name: item?.name || '' })
    }).catch(e => console.warn('修正保存失败(product):', e));
}

async function applyMissingCategory(idx, path) {
    const items = (window.diagnosisData && window.diagnosisData.missing_items) || [];
    const item = items[idx];
    if (!item) return;
    const code = String(item.code).trim();
    window.categoryRules[code] = { action: 'confirm', replacement: path };
    await saveAllCategoryRules();
    await saveCategoryCorrections(code, path, item.factors, item);
    renderMissingItems(items);
    renderCategoryGroups(window.diagnosisData);
    renderGlobalCategoryTree();
}

async function skipMissingItem(idx) {
    const items = (window.diagnosisData && window.diagnosisData.missing_items) || [];
    const item = items[idx];
    if (!item) return;
    const code = String(item.code).trim();
    window.categoryRules[code] = { action: 'skip' };
    await saveAllCategoryRules();
    renderMissingItems(items);
    renderCategoryGroups(window.diagnosisData);
    renderGlobalCategoryTree();
}

// 缺失建议（直接从 suggested_path 读取，无需 API）
function loadSuggestionsForMissing() {
    const items = window.diagnosisData && window.diagnosisData.missing_items;
    if (!items || items.length === 0) return;
    items.forEach(item => {
        const rule = window.categoryRules?.[String(item.code).trim()];
        if (rule && rule.action === 'confirm' && rule.replacement) {
            item._suggested_category = rule.replacement;
            item._confirmed = true;
        } else if (item.suggested_path && item.suggested_path[0]) {
            item._suggested_category = item.suggested_path[0];
        }
    });
    renderMissingItems(items);
}

// 剔除营销分类并重分类
async function reclassifyExcludeMarketing() {
    if (!sessionId) return;
    if (!confirm('确定要剔除所有已标记营销的分类路径并重新建议分类吗？\n\n此操作将根据剩余非营销路径为缺失商品重新推荐分类。')) return;

    const btn = document.getElementById('reclassifyBtn');
    btn.disabled = true;
    btn.textContent = '处理中...';

    try {
        const res = await fetch('/api/classify/reclassify', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({session_id: sessionId})
        });
        const data = await res.json();

        if (data.success) {
            window.diagnosisData.missing_items = data.missing_items;
            window.diagnosisData.all_codes = data.all_codes;
            renderCategoryTree(window.diagnosisData);
            loadSuggestionsForMissing();
            alert(`✅ 已为 ${data.updated_count} 个商品重新建议分类`);
        } else {
            alert('❌ 重分类失败: ' + (data.error || '未知错误'));
        }
    } catch (err) {
        alert('❌ 重分类失败: ' + err.message);
    } finally {
        btn.disabled = false;
        btn.textContent = '🗑 剔除营销并重分类';
    }
}

// 展开/收起分类区本页所有卡片
function expandAllCategoryCards(containerId) {
    const container = document.getElementById(containerId);
    container.querySelectorAll('.group-card').forEach(card => card.classList.remove('collapsed'));
}
function collapseAllCategoryCards(containerId) {
    const container = document.getElementById(containerId);
    container.querySelectorAll('.group-card').forEach(card => card.classList.add('collapsed'));
}

// 切换分类分区页面
function changeCategorySectionPage(containerId, page) {
    if (page < 1) return;
    const pagination = categorySectionPagination[containerId];
    if (!pagination) return;
    pagination.page = page;
    // 重新渲染缺失分类（其他分区无前端 UI）
    if (containerId === 'categoryMissingGroups') {
        renderMissingItems(window.diagnosisData?.missing_items || []);
    }
}

// 自动保存指示灯控制
function showSaveIndicator() {
    const el = document.getElementById('saveIndicator');
    if (el) {
        el.classList.remove('opacity-0');
        setTimeout(() => { if (el) el.classList.add('opacity-0'); }, 2000);
    }
}

// 分类组操作：确认
async function confirmCategoryGroup(containerId, idx) {
    const card = document.getElementById(`cat-card-${containerId}-${idx}`);
    const group = findCategoryGroupData(containerId, idx);
    if (!group) return;

    group.items.forEach(item => {
        const targetPath = (item.suggested_path && item.suggested_path[0]) || group.path;
        window.categoryRules[item.code] = { action: 'confirm', replacement: targetPath };
        if (item.marketing_paths && item.marketing_paths.length > 0) {
            saveMarketingTag(item.code, item.marketing_paths);
        }
    });

    await saveAllCategoryRules();

    for (const gitem of group.items || []) {
        const targetPath = (gitem.suggested_path && gitem.suggested_path[0]) || group.path;
        await saveCategoryCorrections(String(gitem.code).trim(), targetPath, gitem.factors, gitem);
    }

    fadeOutAndRemove(card);
    renderCategoryGroups(window.diagnosisData);
    renderGlobalCategoryTree();
}

// 分类组操作：批量剔除
async function removeCategoryGroup(containerId, idx) {
    const card = document.getElementById(`cat-card-${containerId}-${idx}`);
    const path = card.dataset.path;
    const group = findCategoryGroupData(containerId, idx);
    if (!group) return;

    group.items.forEach(item => {
        saveMarketingTag(item.code, [path]);
    });

    await saveAllCategoryRules();
    fadeOutAndRemove(card);
    renderCategoryGroups(window.diagnosisData);
    renderGlobalCategoryTree();
}

function fadeOutAndRemove(el) {
    el.style.transition = 'all 0.5s ease';
    el.style.opacity = '0';
    el.style.transform = 'translateX(20px)';
    setTimeout(() => {
        el.remove();
        updateDynamicStats();
    }, 500);
}

function findCategoryGroupData(containerId, idx) {
    if (!window.diagnosisData) return null;
    let pool = [];
    if (containerId === 'categoryConflictGroups') pool = window.diagnosisData.conflict_groups;
    else if (containerId === 'categoryMarketingGroups') pool = window.diagnosisData.marketing_groups;
    else if (containerId === 'categoryStandardGroups') pool = window.diagnosisData.standard_groups;
    else if (containerId === 'categoryMissingGroups') pool = [{path: '待补全/缺失', items: window.diagnosisData.missing_items}];
    return pool[idx];
}

// 分类侧边弹窗
function openCategorySidePanel(type, idx, containerId) {
    const group = findCategoryGroupData(containerId, idx);
    if (!group) return;

    window.currentPanelData = {
        type: 'category',
        categoryType: type,
        group: group,
        items: group.items || []
    };
    window.currentPanelPage = 1;

    document.getElementById('sidePanelTitle').textContent = `分类商品详情: ${group.path}`;
    renderCategoryPanelContent();
    
    document.getElementById('sidePanelOverlay').classList.add('open');
    document.getElementById('sidePanel').classList.add('open');
}

function renderCategoryPanelContent() {
    if (!window.currentPanelData || window.currentPanelData.type !== 'category') return;
    const items = window.currentPanelData.items;
    const listContainer = document.getElementById('panelItemsList');
    const totalPages = Math.ceil(items.length / ITEMS_PER_PAGE);
    const start = (window.currentPanelPage - 1) * ITEMS_PER_PAGE;
    const pageItems = items.slice(start, start + ITEMS_PER_PAGE);

    listContainer.innerHTML = pageItems.map(item => {
        const rule = window.categoryRules[item.code];
        let statusHtml = '';
        let itemClass = 'item-row bg-slate-800/50 p-4 rounded-lg border border-slate-700 mb-2';

        if (rule) {
            if (rule.action === 'skip') {
                statusHtml = '<span class="text-gray-400">⏭ 已跳过</span>';
                itemClass += ' skipped opacity-60';
            } else {
                statusHtml = `<span class="text-green-400">✓ 已确认: ${rule.replacement || ''}</span>`;
                itemClass += ' processed';
            }
        }

        // 来源标签
        const sectionLabel = item._section || window.currentPanelData.categoryType || '';
        const sectionStyle = sectionLabel === 'conflict' ? 'bg-emerald-900/50 text-emerald-400' :
            sectionLabel === 'marketing' ? 'bg-red-900/50 text-red-400' :
            sectionLabel === 'standard' ? 'bg-blue-900/50 text-blue-400' :
            sectionLabel === 'missing' ? 'bg-yellow-900/50 text-yellow-400' : 'bg-slate-700 text-slate-400';
        const sectionText = sectionLabel === 'conflict' ? '冲突待归集' :
            sectionLabel === 'marketing' ? '纯营销' :
            sectionLabel === 'standard' ? '标准审计' :
            sectionLabel === 'missing' ? '分类缺失' : '';

        const otherPaths = item.all_paths ? item.all_paths.filter(p => p !== window.currentPanelData.group.path) : [];
        const otherPathsHtml = otherPaths.length > 0 ? `
            <div class="mt-2 text-[10px] text-slate-500">
                <span class="text-slate-600">其它原始路径:</span>
                ${otherPaths.map(p => `<div class="ml-2">• ${p}</div>`).join('')}
            </div>
        ` : '';

        const suggestedPath = item.suggested_path && item.suggested_path[0];
        const inAllPaths = suggestedPath && (item.all_paths || []).includes(suggestedPath);
        const suggestedHtml = suggestedPath ? `
            <div class="mt-2 text-[11px] ${inAllPaths ? 'text-green-400' : 'text-amber-400'} font-bold">
                ${inAllPaths ? '✅' : '⭐'} 建议分类${inAllPaths ? '(与现有路径一致)' : '(新分类参考)'}: ${suggestedPath}
            </div>
        ` : '';

        const factors = item.factors || {};
        let factorsHtml = '';
        if (factors.entity || factors.brand_type || (factors.modifier_detail && factors.modifier_detail.length) || factors.spec_weight || factors.spec_pack) {
            const parts = [];
            let entityLabel = `entity="${factors.entity}"`;
            if (factors.entity_type) {
                entityLabel += ` [${factors.entity_type}`;
                if (factors.entity_subtype) entityLabel += `-${factors.entity_subtype}`;
                entityLabel += ']';
            }
            if (factors.brand_type) parts.push(`type="${factors.brand_type}"`);
            if (factors.modifier_detail && factors.modifier_detail.length) {
                const modStr = factors.modifier_detail.map(m => `${m.value}[${m.type || '未知'}]`).join(',');
                parts.push(`修饰词=${modStr}`);
            } else if (factors.modifiers?.length) {
                parts.push(`修饰词=${factors.modifiers.join(',')}`);
            }
            const specParts = [];
            if (factors.spec_weight) specParts.push(factors.spec_weight);
            if (factors.spec_pack) specParts.push(factors.spec_pack);
            if (specParts.length) parts.push(`规格: ${specParts.join(' | ')}`);
            if (item.corrected_from_history) parts.push('📌 历史修正');
            if (parts.length) factorsHtml = `<div class="text-[9px] text-cyan-300 mt-0.5">🔍 ${entityLabel}${parts.length ? ' | ' + parts.join(' | ') : ''}</div>`;
        }

        const allOpts = (item.all_paths || []).concat(suggestedPath ? [suggestedPath] : []);
        const dedupOpts = [...new Set(allOpts)];
        const pathOpts = dedupOpts.map(p => `<option value="${p}" ${p === suggestedPath ? 'selected' : ''}>${p}</option>`).join('');

        const actionsHtml = rule ? `
            <div class="flex items-center gap-2">
                ${statusHtml}
            </div>` : `
            <div class="flex gap-2 items-center flex-wrap">
                <button onclick="openCategoryPicker('${item.code}','${(suggestedPath||'').replace(/'/g, "\\'")}')" class="px-3 py-1 bg-cyan-600 hover:bg-cyan-500 rounded text-sm font-bold">📂 设置分类</button>
                <button onclick="skipSingleItemCategory('${item.code}')" class="px-3 py-1 bg-gray-600 hover:bg-gray-500 rounded text-sm">跳过</button>
            </div>`;

        return `
        <div class="${itemClass}" data-code="${item.code}">
            ${sectionText ? `<div class="text-[9px] px-1.5 py-0.5 rounded inline-block mb-1 ${sectionStyle}">${sectionText}</div>` : ''}
            <div class="flex items-start gap-2">
                ${item.org_image_url ? `<img src="${item.org_image_url}" class="w-10 h-10 object-cover rounded flex-shrink-0 cursor-zoom-in" onerror="this.style.display='none'" onclick="previewImage('${item.org_image_url}')" alt="">` : ''}
                <div class="min-w-0 flex-1">
                    <div class="font-bold text-white text-sm truncate">${item.name}</div>
                    <div class="text-[10px] text-slate-500 mt-1">Code: ${item.code} | 行号: ${item.row}</div>
                </div>
            </div>
            ${suggestedHtml}
            ${factorsHtml}
            ${otherPathsHtml}
            ${actionsHtml}
        </div>`;
    }).join('');

    // 分页
    if (totalPages <= 1) {
        document.getElementById('panelPagination').innerHTML = '';
    } else {
        let pgHtml = `
            <button onclick="changeCategoryPage(${window.currentPanelPage - 1})" ${window.currentPanelPage === 1 ? 'disabled' : ''}
                    class="px-3 py-1 bg-slate-600 hover:bg-slate-500 rounded text-sm disabled:opacity-50">上一页</button>`;
        for (let i = 1; i <= totalPages; i++) {
            const active = i === window.currentPanelPage ? 'bg-slate-500 text-white' : 'bg-slate-700 text-slate-300';
            pgHtml += `<button onclick="changeCategoryPage(${i})" class="px-3 py-1 ${active} rounded text-sm">${i}</button>`;
        }
        pgHtml += `
            <button onclick="changeCategoryPage(${window.currentPanelPage + 1})" ${window.currentPanelPage === totalPages ? 'disabled' : ''}
                    class="px-3 py-1 bg-slate-600 hover:bg-slate-500 rounded text-sm disabled:opacity-50">下一页</button>`;
        document.getElementById('panelPagination').innerHTML = pgHtml;
    }

    // 批量操作
    const type = window.currentPanelData.categoryType;
    const btns = [];
    btns.push(`<button onclick="openCategoryPickerForBatch()" class="px-3 py-1 bg-cyan-600 hover:bg-cyan-500 rounded text-sm font-bold">📂 全部指定</button>`);
    btns.push(`<button onclick="batchConfirmAllToCurrentPath()" class="px-3 py-1 bg-indigo-600 hover:bg-indigo-500 rounded text-sm font-bold">全部设置为当前路径</button>`);
    if (type === 'conflict') {
        btns.push(`<button onclick="batchConfirmAllCategoryItems()" class="px-3 py-1 bg-emerald-600 hover:bg-emerald-500 rounded text-sm font-bold">全部按建议归集</button>`);
    }
    if (type === 'marketing') {
        btns.push(`<button onclick="batchMarkAllAsMarketing()" class="px-3 py-1 bg-red-600 hover:bg-red-500 rounded text-sm font-bold">全部标记为营销剔除</button>`);
    }
    if (type === 'standard') {
        btns.push(`<button onclick="batchConfirmAllCategoryItems()" class="px-3 py-1 bg-blue-600 hover:bg-blue-500 rounded text-sm font-bold">全部确认通过</button>`);
    }
    btns.push(`<button onclick="batchConfirmAllCategoryItems()" class="px-3 py-1 bg-blue-600 hover:bg-blue-500 rounded text-sm">确认建议</button>`);
    btns.push(`<button onclick="batchSkipAllCategoryItems()" class="px-3 py-1 bg-gray-600 hover:bg-gray-500 rounded text-sm">全部跳过给AI</button>`);
    document.getElementById('panelBatchActions').innerHTML = btns.join('');
}

// 分类面板翻页
function changeCategoryPage(page) {
    if (!window.currentPanelData) return;
    const items = window.currentPanelData.items;
    if (page < 1 || page > Math.ceil(items.length / ITEMS_PER_PAGE)) return;
    window.currentPanelPage = page;
    renderCategoryPanelContent();
}

// 分类面板批量操作
async function batchConfirmAllCategoryItems() {
    if (!window.currentPanelData) return;
    if (window.currentPanelData.group?.path) lastActiveCategoryPath = window.currentPanelData.group.path;
    const items = window.currentPanelData.items;
    for (const item of items) {
        const targetPath = item.suggested_path?.[0] ?? item.all_paths?.[0] ?? '';
        if (targetPath) {
            window.categoryRules[item.code] = { action: 'confirm', replacement: targetPath };
        }
        await saveCategoryCorrections(String(item.code || '').trim(), targetPath || '', item.factors, item);
    }
    await saveAllCategoryRules();
    renderCategoryPanelContent();
    renderCategoryGroups(window.diagnosisData);
    renderGlobalCategoryTree();
}

async function batchSkipAllCategoryItems() {
    if (!window.currentPanelData) return;
    if (window.currentPanelData.group?.path) lastActiveCategoryPath = window.currentPanelData.group.path;
    const items = window.currentPanelData.items;
    items.forEach(item => {
        window.categoryRules[item.code] = { action: 'skip' };
    });
    await saveAllCategoryRules();
    renderCategoryPanelContent();
    renderCategoryGroups(window.diagnosisData);
    renderGlobalCategoryTree();
}

async function batchConfirmAllToCurrentPath() {
    if (!window.currentPanelData) return;
    if (window.currentPanelData.group?.path) lastActiveCategoryPath = window.currentPanelData.group.path;
    const path = window.currentPanelData.group.path;
    if (!path) return;
    const items = window.currentPanelData.items;
    for (const item of items) {
        if (!window.categoryRules[item.code]) {
            window.categoryRules[item.code] = { action: 'confirm', replacement: path };
        }
        await saveCategoryCorrections(String(item.code || '').trim(), path, item.factors, item, item.suggested_path?.[0]);
    }
    await saveAllCategoryRules();
    renderCategoryPanelContent();
    renderCategoryGroups(window.diagnosisData);
    renderGlobalCategoryTree();
}

async function saveAllCategoryRules() {
    showSaveIndicator();
    try {
        await fetch('/api/rules/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: sessionId,
                rules: { categories: window.categoryRules, marketing_tags: window.marketingTags }
            })
        });
        await saveSessionSnapshots(); 
    } catch (err) { console.error('保存分类规则失败:', err); }
}

function saveMarketingTag(code, paths) {
    if (!window.marketingTags[code]) window.marketingTags[code] = [];
    paths.forEach(p => { if (!window.marketingTags[code].includes(p)) window.marketingTags[code].push(p); });
}

function updateItemCategory(code, value) {
    window.itemCategoryDecisions[code] = value;
}

async function confirmSingleItemCategory(code) {
    const path = window.itemCategoryDecisions[code];
    if (!path) return alert('请先从下拉框选择分类');
    window.categoryRules[code] = { action: 'confirm', replacement: path };
    await saveAllCategoryRules();

    const allCodes = (window.diagnosisData && window.diagnosisData.all_codes) || [];
    const item = allCodes.find(ac => String(ac.code).trim() === String(code).trim());
    const origSuggested = item?.suggested_path?.[0] || '';
    await saveCategoryCorrections(code, path, item?.factors, item, origSuggested);

    const rows = document.querySelectorAll(`[data-code="${code}"]`);
    rows.forEach(r => r.classList.add('opacity-40'));
    renderCategoryGroups(window.diagnosisData);
    renderGlobalCategoryTree();
}

async function skipSingleItemCategory(code) {
    window.categoryRules[code] = { action: 'skip' };
    await saveAllCategoryRules();
    const rows = document.querySelectorAll(`[data-code="${code}"]`);
    rows.forEach(r => r.classList.add('opacity-40'));
    renderCategoryGroups(window.diagnosisData);
    renderGlobalCategoryTree();
}

async function saveSessionSnapshots() {
    // 💡 显式补全 async 和内部 fetch 的 await
    await fetch('/api/session/snapshot?sid=' + sessionId);
}

function updateDynamicStats() {
    // 由于此函数在 UI 动画回调中调用，不加 async 以保持同步流，但内部触发异步保存
    saveSessionSnapshots();
}

// ===== 分类路径索引构建 =====
function buildCategoryPathIndex() {
    const diag = window.diagnosisData;
    if (!diag) return {};
    const index = {};
    (diag.all_codes || []).forEach(item => {
        const section = item._section || 'unknown';
        (item.suggested_path || []).forEach(p => {
            if (!p) return;
            const key = p.replace(/\s*>\s*/g, ' > ');
            if (!index[key]) index[key] = { count: 0, items: [], conflictCount: 0, marketingCount: 0, standardCount: 0 };
            index[key].count++;
            index[key][section + 'Count']++;
            index[key].items.push(Object.assign({}, item, { _section: section }));
        });
    });
    return index;
}

// ===== 全局分类树 =====
function renderGlobalCategoryTree() {
    const options = window.categoryOptions;
    const index = buildCategoryPathIndex();
    const container = document.getElementById('globalCateTreeContainer');
    if (!container) return;
    if (!options || !options.level1 || options.level1.length === 0) {
        container.innerHTML = '<p class="text-slate-500 text-xs italic py-2">暂无分类数据</p>';
        return;
    }
    let html = '';
    options.level1.forEach(l1 => {
        const l2s = options.level2_by_level1[l1] || [];
        let l2Html = '';
        l2s.forEach(l2 => {
            const l3s = options.level3_by_level2[`${l1} > ${l2}`] || [];
            let l3Html = '';
            l3s.forEach(l3 => {
                const path = `${l1} > ${l2} > ${l3}`;
                const info = index[path];
                const total = info ? info.count : 0;
                const processed = info ? info.items.filter(i => window.categoryRules[i.code]).length : 0;
                const pct = total ? Math.round(processed / total * 100) : 0;
                let detail = '';
                if (info) {
                    const parts = [];
                    if (info.conflictCount) parts.push(`<span class="text-emerald-400">⚠️${info.conflictCount}</span>`);
                    if (info.marketingCount) parts.push(`<span class="text-red-400">🔴${info.marketingCount}</span>`);
                    if (info.standardCount) parts.push(`<span class="text-blue-400">✅${info.standardCount}</span>`);
                    detail = parts.join(' ');
                }
                const safePath = path.replace(/'/g, "\\'");
                l3Html += `<div class="pl-6 py-0.5 cursor-pointer hover:bg-slate-700/50 rounded flex items-center gap-1" onclick="openUnifiedCategoryPanel('${safePath}')">
                    <span class="text-xs text-slate-300">${l3}</span>
                    ${total ? `<span class="text-[10px] text-slate-500 ml-1">${total}条</span>` : ''}
                    ${detail ? `<span class="text-[10px] ml-1">${detail}</span>` : ''}
                    <span class="text-[9px] ml-auto" style="color:${pct === 100 ? '#4ade80' : pct > 0 ? '#facc15' : '#64748b'}">${processed}/${total}已处理</span>
                </div>`;
            });
            if (!l3Html) return;
            l2Html += `<div class="tree-node ml-2">
                <div class="flex items-center gap-1 py-0.5 cursor-pointer hover:bg-slate-700/30 rounded tree-toggle" onclick="this.nextElementSibling.classList.toggle('hidden');const a=this.querySelector('.arrow');a.textContent=a.textContent==='▶'?'▼':'▶'">
                    <span class="arrow text-[8px] text-slate-500">▼</span>
                    <span class="text-xs text-slate-300">${l2}</span>
                </div>
                <div class="tree-children">${l3Html}</div>
            </div>`;
        });
        if (!l2Html) return;
        html += `<div class="tree-node">
            <div class="flex items-center gap-1 py-0.5 cursor-pointer hover:bg-slate-700/30 rounded tree-toggle font-medium" onclick="this.nextElementSibling.classList.toggle('hidden');const a=this.querySelector('.arrow');a.textContent=a.textContent==='▶'?'▼':'▶'">
                <span class="arrow text-[8px] text-slate-400">▼</span>
                <span class="text-xs text-slate-200">${l1}</span>
            </div>
            <div class="tree-children">${l2Html}</div>
        </div>`;
    });
    container.innerHTML = html || '<p class="text-slate-500 text-xs italic py-2">暂无分类数据</p>';
}

function filterGlobalCategoryTree(text) {
    const container = document.getElementById('globalCateTreeContainer');
    if (!container) return;
    if (!text) { renderGlobalCategoryTree(); return; }
    const index = buildCategoryPathIndex();
    const options = window.categoryOptions;
    const lower = text.toLowerCase();
    let html = '';
    options.level1.forEach(l1 => {
        const l2s = options.level2_by_level1[l1] || [];
        let l2Html = '';
        l2s.forEach(l2 => {
            const l3s = options.level3_by_level2[`${l1} > ${l2}`] || [];
            let l3Html = '';
            l3s.forEach(l3 => {
                const path = `${l1} > ${l2} > ${l3}`;
                if (!path.toLowerCase().includes(lower)) return;
                const info = index[path];
                const total = info ? info.count : 0;
                const processed = info ? info.items.filter(i => window.categoryRules[i.code]).length : 0;
                const safePath = path.replace(/'/g, "\\'");
                l3Html += `<div class="pl-6 py-0.5 cursor-pointer hover:bg-slate-700/50 rounded" onclick="openUnifiedCategoryPanel('${safePath}')">
                    <span class="text-xs text-cyan-300">${path}</span>
                    <span class="text-[10px] text-slate-500 ml-1">${total}条 | ${processed}已处理</span>
                </div>`;
            });
            if (!l3Html) return;
            l2Html += `<div class="ml-2">${l3Html}</div>`;
        });
        if (!l2Html) return;
        html += `<div class="ml-1">${l2Html}</div>`;
    });
    container.innerHTML = html || '<p class="text-slate-500 text-xs italic py-2">无匹配分类</p>';
}

// ===== 统一分类选择弹窗 =====
let pickerCode = null;
let pickerBatchMode = false;
let pickerPath = '';

function openCategoryPicker(code, suggestedPath) {
    pickerCode = code;
    pickerPath = '';
    document.getElementById('pickerSelectedDisplay').textContent = suggestedPath ? '⭐建议: ' + suggestedPath : '';
    document.getElementById('pickerConfirmBtn').disabled = true;
    document.getElementById('categoryPickerModal').classList.add('open');
    renderPickerTree();
}

function renderPickerTree(filter) {
    const options = window.categoryOptions;
    const container = document.getElementById('pickerTreeContainer');
    if (!container) return;
    if (!options || !options.level1) {
        container.innerHTML = '<p class="text-slate-500 text-xs italic py-2">暂无分类数据</p>';
        return;
    }
    let html = '';
    (filter ? options.level1.filter(l1 => l1.toLowerCase().includes(filter)) : options.level1).forEach(l1 => {
        const l2s = options.level2_by_level1[l1] || [];
        let l2Html = '';
        l2s.forEach(l2 => {
            const l3s = options.level3_by_level2[`${l1} > ${l2}`] || [];
            let l3Html = '';
            l3s.forEach(l3 => {
                const path = `${l1} > ${l2} > ${l3}`;
                if (filter && !path.toLowerCase().includes(filter)) return;
                const sel = pickerPath === path ? 'bg-cyan-700/50 text-cyan-200' : 'text-slate-300';
                const safePath = path.replace(/'/g, "\\'");
                l3Html += `<div class="pl-4 py-0.5 cursor-pointer hover:bg-slate-700/50 rounded ${sel}" onclick="selectPickerPath('${safePath}')">
                    <span class="text-[11px]">${l3}</span>
                </div>`;
            });
            if (!l3Html) return;
            l2Html += `<div class="tree-node ml-1">
                <div class="flex items-center gap-1 py-0.5 cursor-pointer hover:bg-slate-700/30 rounded tree-toggle" onclick="this.nextElementSibling.classList.toggle('hidden');const a=this.querySelector('.arrow');a.textContent=a.textContent==='▶'?'▼':'▶'">
                    <span class="arrow text-[7px] text-slate-500">▶</span>
                    <span class="text-[10px] text-slate-400">${l2}</span>
                </div>
                <div class="tree-children hidden">${l3Html}</div>
            </div>`;
        });
        if (!l2Html) return;
        html += `<div class="tree-node">
            <div class="flex items-center gap-1 py-0.5 cursor-pointer hover:bg-slate-700/30 rounded tree-toggle" onclick="this.nextElementSibling.classList.toggle('hidden');const a=this.querySelector('.arrow');a.textContent=a.textContent==='▶'?'▼':'▶'">
                <span class="arrow text-[7px] text-slate-400">▶</span>
                <span class="text-[10px] text-slate-300 font-medium">${l1}</span>
            </div>
            <div class="tree-children hidden">${l2Html}</div>
        </div>`;
    });
    container.innerHTML = html || '<p class="text-xs text-slate-500 italic py-2">无匹配</p>';
}

function openCategoryPickerForBatch() {
    pickerCode = null;
    pickerBatchMode = true;
    pickerPath = '';
    document.getElementById('pickerSelectedDisplay').textContent = '';
    document.getElementById('pickerConfirmBtn').disabled = true;
    document.getElementById('categoryPickerModal').classList.add('open');
    renderPickerTree();
}

function selectPickerPath(path) {
    pickerPath = path;
    document.getElementById('pickerSelectedDisplay').textContent = '已选: ' + path;
    document.getElementById('pickerConfirmBtn').disabled = false;
    renderPickerTree();
}

async function confirmPickerSelection() {
    if (!pickerPath) return;
    if (pickerBatchMode) {
        const items = window.currentPanelData?.items || [];
        for (const item of items) {
            if (!window.categoryRules[item.code]) {
                window.categoryRules[item.code] = { action: 'confirm', replacement: pickerPath };
            }
            const origSug = item.suggested_path?.[0] || '';
            await saveCategoryCorrections(String(item.code || '').trim(), pickerPath, item.factors, item, origSug);
        }
    } else {
        if (!pickerCode) return;
        const code = String(pickerCode).trim();
        window.categoryRules[code] = { action: 'confirm', replacement: pickerPath };
        const acItem = (window.diagnosisData?.all_codes || []).find(ac => String(ac.code).trim() === code);
        const origSug = acItem?.suggested_path?.[0] || '';
        await saveCategoryCorrections(code, pickerPath, acItem?.factors, acItem, origSug);
    }
    await saveAllCategoryRules();
    pickerBatchMode = false;
    closePickerModal();
    if (window.currentPanelData?.group?.path) lastActiveCategoryPath = window.currentPanelData.group.path;
    renderCategoryPanelContent();
    renderCategoryGroups(window.diagnosisData);
    renderGlobalCategoryTree();
}

function closePickerModal() {
    document.getElementById('categoryPickerModal').classList.remove('open');
    pickerCode = null;
    pickerBatchMode = false;
    pickerPath = '';
}

function filterPickerTree(text) {
    renderPickerTree(text ? text.toLowerCase() : '');
}

// ===== 统一分类面板（按路径打开，跨板块） =====
function openUnifiedCategoryPanel(path) {
    lastActiveCategoryPath = path;
    const index = buildCategoryPathIndex();
    const info = index[path];
    if (!info || info.items.length === 0) { alert('该路径下无商品'); return; }
    window.currentPanelData = {
        type: 'category',
        categoryType: 'unified',
        group: { path: path },
        items: info.items,
        isUnified: true
    };
    window.currentPanelPage = 1;
    document.getElementById('sidePanelTitle').textContent = `分类商品: ${path} (共${info.count}条)`;
    renderCategoryPanelContent();
    document.getElementById('sidePanelOverlay').classList.add('open');
    document.getElementById('sidePanel').classList.add('open');
}

async function batchMarkAllAsMarketing() {
    if (!window.currentPanelData) return;
    if (window.currentPanelData.group?.path) lastActiveCategoryPath = window.currentPanelData.group.path;
    const items = window.currentPanelData.items;
    items.forEach(item => {
        (item.marketing_paths || item.all_paths || []).forEach(p => saveMarketingTag(item.code, [p]));
        window.categoryRules[item.code] = { action: 'skip' };
    });
    await saveAllCategoryRules();
    renderCategoryPanelContent();
    renderCategoryGroups(window.diagnosisData);
    renderGlobalCategoryTree();
}

// ===== 显式挂载到 window（确保跨文件调用绝对稳定） =====
window.pollDiagnosisStatus = pollDiagnosisStatus;
window.fetchDiagnosisResult = fetchDiagnosisResult;
window.showDiagnosis = showDiagnosis;
window.renderCategoryGroups = renderCategoryGroups;
window.showSaveIndicator = showSaveIndicator;
window.confirmCategoryGroup = confirmCategoryGroup;
window.removeCategoryGroup = removeCategoryGroup;
window.fadeOutAndRemove = fadeOutAndRemove;
window.findCategoryGroupData = findCategoryGroupData;
window.openCategorySidePanel = openCategorySidePanel;
window.renderCategoryPanelContent = renderCategoryPanelContent;
window.saveAllCategoryRules = saveAllCategoryRules;
window.confirmSingleItemCategory = confirmSingleItemCategory;
window.skipSingleItemCategory = skipSingleItemCategory;
window.saveSessionSnapshots = saveSessionSnapshots;
window.updateDynamicStats = updateDynamicStats;
window.saveMarketingTag = saveMarketingTag;
window.updateItemCategory = updateItemCategory;
window.changeCategorySectionPage = changeCategorySectionPage;
window.expandAllCategoryCards = expandAllCategoryCards;
window.collapseAllCategoryCards = collapseAllCategoryCards;
window.changeCategoryPage = changeCategoryPage;
window.batchConfirmAllCategoryItems = batchConfirmAllCategoryItems;
window.batchConfirmAllToCurrentPath = batchConfirmAllToCurrentPath;
window.batchSkipAllCategoryItems = batchSkipAllCategoryItems;
window.buildCategoryPathIndex = buildCategoryPathIndex;
window.renderGlobalCategoryTree = renderGlobalCategoryTree;
window.filterGlobalCategoryTree = filterGlobalCategoryTree;
window.openUnifiedCategoryPanel = openUnifiedCategoryPanel;
window.openCategoryPickerForBatch = openCategoryPickerForBatch;
window.batchMarkAllAsMarketing = batchMarkAllAsMarketing;
window.toggleMarketingInTree = toggleMarketingInTree;
window.batchClassifyPath = batchClassifyPath;
window.reclassifyExcludeMarketing = reclassifyExcludeMarketing;

// Wire up detail panel on cluster item clicks
function initDiagnosisDetailPanel() {
    // Delegate click events on cluster items and missing items
    document.addEventListener('click', function(e) {
        var target = e.target.closest('[data-code]');
        if (!target) return;
        var code = target.dataset.code;
        if (!code) return;
        var item = findItemByCode(code);
        if (item) {
            e.preventDefault();
            openDetail(item);
        }
    });
}

function findItemByCode(code) {
    // Search in all_codes, missing_items, and cluster items
    var diag = window.diagnosisData;
    if (!diag) return null;

    // Check all_codes
    var allCodes = diag.all_codes || [];
    for (var i = 0; i < allCodes.length; i++) {
        if (String(allCodes[i].code) === String(code)) return allCodes[i];
    }

    // Check missing_items
    var missing = diag.missing_items || [];
    for (var i = 0; i < missing.length; i++) {
        if (String(missing[i].code) === String(code)) return missing[i];
    }

    return null;
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(initDiagnosisDetailPanel, 500);
});