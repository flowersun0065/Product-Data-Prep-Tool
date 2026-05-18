// review.js — 复核页交互逻辑
const R = {
    sid: null,
    data: [],
    filtered: [],
    selectedCode: null,
    filterStatus: 'all',
    page: 1,
    pageSize: 30,
    pollTimer: null,
};

function init() {
    const params = new URLSearchParams(window.location.search);
    R.sid = params.get('sid');
    if (!R.sid) {
        document.getElementById('loadingMsg').innerHTML = '<p class="text-red-400">缺少 session ID，请从处理页面打开</p>';
        return;
    }
    document.getElementById('sessionBadge').textContent = 'Session: ' + R.sid;
    sessionId = R.sid;  // common.js

    fetchData();
    startPolling();

    // 筛选按钮事件
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.filter-btn').forEach(b => {
                b.className = 'filter-btn px-3 py-1 rounded text-xs bg-slate-700 text-slate-300';
            });
            btn.className = 'filter-btn px-3 py-1 rounded text-xs bg-cyan-600 text-white';
            R.filterStatus = btn.dataset.status;
            R.page = 1;
            applyFilters();
        });
    });
}

async function fetchData() {
    try {
        const resp = await fetch('/api/review/data?sid=' + R.sid);
        const json = await resp.json();
        R.data = json.data || [];
        updateProgress();
        applyFilters();
        if (R.data.length === 0) {
            document.getElementById('loadingMsg').classList.remove('hidden');
            document.getElementById('loadingMsg').innerHTML =
                '<div class="animate-pulse text-lg">等待处理数据...</div><p class="text-sm text-slate-400 mt-2">数据就绪后将自动加载</p>';
            document.getElementById('reviewList').classList.add('hidden');
        } else {
            document.getElementById('loadingMsg').classList.add('hidden');
        }
    } catch (e) {
        console.error('fetchData error:', e);
    }
}

function updateProgress() {
    const total = R.data.length;
    const confirmed = R.data.filter(d => d.review_status === '已确认').length;
    const modified = R.data.filter(d => d.review_status === '已修改').length;
    const pending = total - confirmed - modified;
    document.getElementById('progressText').textContent =
        '共 ' + total + ' / 待复核 ' + pending + ' / 已确认 ' + confirmed;
    document.getElementById('progressBar').style.width =
        total > 0 ? Math.round((confirmed + modified) / total * 100) + '%' : '0%';
}

function applyFilters() {
    let items = [...R.data];

    // 状态筛选
    if (R.filterStatus !== 'all') {
        items = items.filter(d => d.review_status === R.filterStatus);
    }

    // 自营标签筛选
    const selfOpVal = document.getElementById('selfOpFilter').value;
    if (selfOpVal) {
        items = items.filter(d => d.self_operated_tag === selfOpVal);
    }

    // 进口/国产标签筛选
    const importVal = document.getElementById('importFilter').value;
    if (importVal) {
        items = items.filter(d => d.import_tag === importVal);
    }

    // 搜索
    const query = (document.getElementById('searchInput').value || '').trim().toLowerCase();
    if (query) {
        items = items.filter(d =>
            (d.name || '').toLowerCase().includes(query) ||
            (d.code || '').toLowerCase().includes(query)
        );
    }

    R.filtered = items;
    R.page = Math.min(R.page, Math.ceil(items.length / R.pageSize) || 1);
    renderList();
}

function renderList() {
    const container = document.getElementById('reviewList');
    const empty = document.getElementById('emptyMsg');
    const pagination = document.getElementById('pagination');

    if (R.filtered.length === 0) {
        container.classList.add('hidden');
        pagination.classList.add('hidden');
        empty.classList.remove('hidden');
        return;
    }

    empty.classList.add('hidden');
    container.classList.remove('hidden');

    const start = (R.page - 1) * R.pageSize;
    const pageItems = R.filtered.slice(start, start + R.pageSize);

    let html = '';
    pageItems.forEach(item => {
        const code = item.code || '';
        const name = item.name || '';
        const brandAi = item.brand_ai || '';
        const brandOrig = item.original_brand || '';
        const brandShow = brandAi || brandOrig || '(无)';
        const specAi = item.spec_from_name || '';
        const specOrig = item.spec_original || '';
        const status = item.review_status || '待复核';
        const statusClass = status === '已确认' ? 'status-confirmed' :
                            status === '已修改' ? 'status-modified' : 'status-pending';
        const isSelected = code === R.selectedCode;

        // 标签
        let tags = '';
        if (item.self_operated_tag) tags += '<span class="tag-self">' + esc(item.self_operated_tag) + '</span> ';
        if (item.import_tag === '进口') tags += '<span class="tag-import">进口</span> ';
        if (item.import_tag === '国产') tags += '<span class="tag-domestic">国产</span> ';
        if (item.promo_tag) tags += '<span class="tag-promo">' + esc(item.promo_tag) + '</span> ';
        if (item.recommend_tag) tags += '<span class="tag-recommend">推荐</span> ';

        html += '<div class="bg-slate-800/50 rounded-lg p-4 border border-slate-700/50 cursor-pointer hover:border-slate-500 transition' +
            (isSelected ? ' card-active' : '') + '" onclick="selectItem(\'' + escAttr(code) + '\')">' +
            '<div class="flex items-start justify-between mb-1">' +
            '<span class="text-sm font-medium text-slate-200 truncate flex-1 mr-3">' + esc(name) + '</span>' +
            '<span class="' + statusClass + ' shrink-0">' + esc(status) + '</span>' +
            '</div>' +
            '<div class="text-xs text-slate-400 space-y-0.5">' +
            '<div>品牌: <span class="text-cyan-400">' + esc(brandShow) + '</span>' +
            (brandOrig && brandOrig !== brandShow ? ' <span class="text-slate-500">← 原始: ' + esc(brandOrig) + '</span>' : '') +
            '</div>' +
            (specAi || specOrig ? '<div>规格: ' +
                (specAi ? '<span class="text-cyan-400">' + esc(specAi) + '</span>' : '') +
                (specAi && specOrig ? ' / ' : '') +
                (specOrig ? '<span class="text-slate-500">原始: ' + esc(specOrig) + '</span>' : '') +
            '</div>' : '') +
            (tags ? '<div>' + tags + '</div>' : '') +
            '</div>' +
            '</div>';
    });
    container.innerHTML = html;

    // 分页
    const totalPages = Math.ceil(R.filtered.length / R.pageSize);
    if (totalPages > 1) {
        pagination.classList.remove('hidden');
        let pageHtml = '';
        pageHtml += '<button onclick="changePage(' + (R.page - 1) + ')" ' +
            (R.page <= 1 ? 'disabled' : '') +
            ' class="px-3 py-1 rounded text-xs bg-slate-700 text-slate-300 disabled:opacity-30">&lt;</button>';
        pageHtml += '<span class="text-xs text-slate-400 px-2">' + R.page + ' / ' + totalPages + '</span>';
        pageHtml += '<button onclick="changePage(' + (R.page + 1) + ')" ' +
            (R.page >= totalPages ? 'disabled' : '') +
            ' class="px-3 py-1 rounded text-xs bg-slate-700 text-slate-300 disabled:opacity-30">&gt;</button>';
        pagination.innerHTML = pageHtml;
    } else {
        pagination.classList.add('hidden');
    }
}

function selectItem(code) {
    R.selectedCode = code;
    renderList();
    renderDetail(code);
    openDetail();
    document.getElementById('detailPlaceholder').classList.remove('hidden');
}

function renderDetail(code) {
    const item = R.filtered.find(d => d.code === code);
    if (!item) return;

    const rows = [
        ['商品名', item.name],
        ['商品编码', item.code],
        ['原始品牌', item.original_brand],
        ['AI 品牌', item.brand_ai, item.brand_type ? '🏷 ' + item.brand_type : ''],
        ['品牌置信度', item.brand_confidence],
        ['品牌来源', brandStatusLabel(item.brand_status)],
        ['品牌理由', item.brand_reason],
        ['原始规格 (spu_spec)', item.spec_original],
        ['商品名提取规格', item.spec_from_name],
        ['原始分类', item.original_category],
        ['AI 分类', item.category_ai],
        ['分类置信度', item.category_confidence],
        ['分类来源', categoryStatusLabel(item.category_status)],
        ['分类方式', item.category_method],
        ['分类理由', item.category_reason],
        ['品种词', item.category_entity],
        ['修饰词', item.category_modifiers],
    ];

    // 标签行
    const tagFields = [
        ['促销标签', item.promo_tag, 'tag-promo'],
        ['推荐标签', item.recommend_tag, 'tag-recommend'],
        ['自营标签', item.self_operated_tag, 'tag-self'],
        ['进口/国产', item.import_tag, item.import_tag === '进口' ? 'tag-import' : 'tag-domestic'],
        ['原始促销标签', item.org_prom_spu_tag],
        ['原始新品标签', item.org_new_spu_tag],
        ['原始榜单标签', item.org_billboard_top],
        ['原始推荐标签', item.org_recommend_tag],
        ['原始促销价', item.org_prom_price],
    ];

    let html = '';

    // 状态 + 操作按钮
    html += '<div class="flex items-center justify-between mb-4">';
    html += '<span class="text-sm text-slate-400">状态: <b class="text-' +
        (item.review_status === '已确认' ? 'green' : item.review_status === '已修改' ? 'blue' : 'yellow') +
        '-400">' + esc(item.review_status || '待复核') + '</b></span>';
    html += '<div class="flex gap-2">';
    html += '<button onclick="confirmItem(\'' + escAttr(code) + '\')" class="px-3 py-1.5 bg-green-600 hover:bg-green-500 rounded text-xs font-bold">确认</button>';
    html += '<button onclick="editItem(\'' + escAttr(code) + '\')" class="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 rounded text-xs font-bold">修改</button>';
    html += '</div>';
    html += '</div>';

    // 图片
    if (item.org_image_url) {
        html += '<div class="mb-4"><img src="' + escAttr(item.org_image_url) + '" alt="商品图" ' +
            'class="w-full max-h-48 object-contain rounded bg-slate-900 cursor-pointer" ' +
            'onclick="previewImage(\'' + escAttr(item.org_image_url) + '\')" ' +
            'onerror="this.style.display=\'none\'"></div>';
    }

    // 基本信息
    html += '<div class="space-y-2 mb-6">';
    rows.forEach(([label, value, extra]) => {
        if (!value) return;
        html += '<div class="text-xs"><span class="text-slate-500">' + esc(label) + '</span>';
        html += '<div class="text-slate-200 text-sm">' + esc(String(value));
        if (extra) html += ' <span class="text-slate-400 text-xs">' + esc(extra) + '</span>';
        html += '</div></div>';
    });
    html += '</div>';

    // 标签
    html += '<div class="border-t border-slate-700 pt-4 space-y-2">';
    html += '<h4 class="text-xs font-bold text-slate-400 uppercase mb-2">标签</h4>';
    tagFields.forEach(([label, value, cssClass]) => {
        if (!value) return;
        html += '<div class="text-xs"><span class="text-slate-500">' + esc(label) + ': </span>';
        if (cssClass) {
            html += '<span class="' + cssClass + '">' + esc(String(value)) + '</span>';
        } else {
            html += '<span class="text-slate-300">' + esc(String(value)) + '</span>';
        }
        html += '</div>';
    });
    html += '</div>';

    // 编辑表单（默认隐藏）
    html += '<div id="editForm" class="border-t border-slate-700 pt-4 mt-4 hidden">';
    html += '<h4 class="text-xs font-bold text-slate-400 uppercase mb-2">编辑</h4>';
    html += '<div class="space-y-2">';
    html += '<label class="text-xs text-slate-400">品牌</label>';
    html += '<input id="editBrand" class="w-full bg-slate-700 text-slate-200 rounded px-2 py-1 text-sm" value="' + escAttr(item.brand_ai || '') + '">';
    html += '<label class="text-xs text-slate-400">分类</label>';
    html += '<input id="editCategory" class="w-full bg-slate-700 text-slate-200 rounded px-2 py-1 text-sm" value="' + escAttr(item.category_ai || '') + '">';
    html += '</div>';
    html += '<div class="flex gap-2 mt-3">';
    html += '<button onclick="saveEdit(\'' + escAttr(code) + '\')" class="px-3 py-1.5 bg-cyan-600 hover:bg-cyan-500 rounded text-xs font-bold">保存</button>';
    html += '<button onclick="cancelEdit()" class="px-3 py-1.5 bg-slate-600 hover:bg-slate-500 rounded text-xs">取消</button>';
    html += '</div>';
    html += '</div>';

    document.getElementById('detailContent').innerHTML = html;
}

function openDetail() {
    document.getElementById('detailPanel').classList.add('open');
    document.getElementById('detailOverlay').classList.add('open');
}

function closeDetail() {
    document.getElementById('detailPanel').classList.remove('open');
    document.getElementById('detailOverlay').classList.remove('open');
    cancelEdit();
}

async function confirmItem(code) {
    try {
        await fetch('/api/review/decision', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: R.sid, code: code, action: 'confirm' }),
        });
        // 更新本地数据
        const item = R.data.find(d => d.code === code);
        if (item) item.review_status = '已确认';
        updateProgress();
        applyFilters();
        if (R.selectedCode === code) renderDetail(code);
    } catch (e) {
        alert('操作失败: ' + e.message);
    }
}

function editItem(code) {
    document.getElementById('editForm').classList.remove('hidden');
}

function cancelEdit() {
    const form = document.getElementById('editForm');
    if (form) form.classList.add('hidden');
}

async function saveEdit(code) {
    const brand = document.getElementById('editBrand').value.trim();
    const category = document.getElementById('editCategory').value.trim();
    const changes = {};
    if (brand) changes.brand_ai = brand;
    if (category) changes.category_ai = category;

    try {
        await fetch('/api/review/decision', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: R.sid, code: code, action: 'modify', changes: changes }),
        });
        // 更新本地数据
        const item = R.data.find(d => d.code === code);
        if (item) {
            item.review_status = '已修改';
            if (changes.brand_ai) item.brand_ai = changes.brand_ai;
            if (changes.category_ai) item.category_ai = changes.category_ai;
        }
        updateProgress();
        applyFilters();
        renderDetail(code);
        cancelEdit();
    } catch (e) {
        alert('保存失败: ' + e.message);
    }
}

function changePage(n) {
    const totalPages = Math.ceil(R.filtered.length / R.pageSize);
    if (n < 1 || n > totalPages) return;
    R.page = n;
    renderList();
    document.getElementById('reviewList').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

async function exportCustom(filterOverride) {
    const filter = filterOverride !== undefined ? filterOverride :
        (R.filterStatus !== 'all' ? { review_status: R.filterStatus } : {});
    // 收集所有可用列名
    const allCols = R.data.length > 0 ? Object.keys(R.data[0]) : [];

    try {
        const resp = await fetch('/api/export/custom', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sid: R.sid, columns: allCols, filter: filter }),
        });
        if (!resp.ok) {
            const err = await resp.json();
            alert('导出失败: ' + (err.error || resp.statusText));
            return;
        }
        const blob = await resp.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'export_' + R.sid + '.xlsx';
        a.click();
        URL.revokeObjectURL(url);
    } catch (e) {
        alert('导出失败: ' + e.message);
    }
}

function startPolling() {
    if (R.pollTimer) return;
    R.pollTimer = setInterval(async () => {
        try {
            const resp = await fetch('/api/status?sid=' + R.sid);
            const json = await resp.json();
            if (json.status === 'processing') {
                fetchData();
            } else if (json.status === 'completed' || json.status === 'cancelled' || json.status === 'error') {
                fetchData();
                stopPolling();
            }
        } catch (e) { /* ignore poll errors */ }
    }, 3000);
}

function stopPolling() {
    if (R.pollTimer) {
        clearInterval(R.pollTimer);
        R.pollTimer = null;
    }
}

function esc(s) {
    if (!s) return '';
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function escAttr(s) {
    if (!s) return '';
    return String(s).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

function brandStatusLabel(status) {
    const map = {
        'ai_ok': 'AI 分析',
        'from_library': '品牌库命中',
        'no_brand': '无品牌',
        'error': 'AI 出错',
        'skipped': '已跳过',
        'local': '本地提取',
    };
    return map[status] || status || '';
}

function categoryStatusLabel(status) {
    const map = {
        'ai_ok': 'AI 分析',
        'out_of_range': '超出范围',
        'local_fallback': '本地回退',
        'skipped': '已跳过',
    };
    return map[status] || status || '';
}

// 入口
document.addEventListener('DOMContentLoaded', init);
