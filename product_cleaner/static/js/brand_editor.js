// ===== 品牌编辑模块 =====

var brandConfigMode;

// 获取品牌库
async function fetchBrandDatabase() {
    try {
        const res = await fetch('/api/brands/list');
        const data = await res.json();
        brandDatabase = data.brands || [];
        return brandDatabase;
    } catch (err) {
        console.error('获取品牌库失败:', err);
        brandDatabase = [];
        return brandDatabase;
    }
}

// 渲染品牌分组
function countGroupProcessed(groups) {
    let total = 0, processed = 0;
    for (const g of groups) {
        total += g.count || 0;
        processed += (g.items || []).filter(i => {
            return brandRules[String(i.code).trim()];
        }).length;
    }
    return { total, processed };
}

function renderBrandGroups(clusters) {
    if (!clusters || !Array.isArray(clusters)) return;
    const missingGroups = clusters.filter(c => c.type === 'missing');
    const mismatchGroups = clusters.filter(c => c.type === 'mismatch');
    const validGroups = clusters.filter(c => c.type === 'valid');

    const mg = countGroupProcessed(missingGroups);
    document.getElementById('missingCount').textContent =
        `共 ${mg.total} 个商品，已处理 ${mg.processed}/${mg.total}`;
    renderGroupSection('missingGroups', missingGroups, 'missing');

    const mmg = countGroupProcessed(mismatchGroups);
    document.getElementById('mismatchCount').textContent =
        `共 ${mmg.total} 个商品，已处理 ${mmg.processed}/${mmg.total}`;
    renderGroupSection('mismatchGroups', mismatchGroups, 'mismatch');

    const vg = countGroupProcessed(validGroups);
    document.getElementById('validCount').textContent =
        `共 ${vg.total} 个商品，已处理 ${vg.processed}/${vg.total}`;
    renderGroupSection('validGroups', validGroups, 'valid');

    const unbrandedGroups = clusters.filter(c => c.type === 'unbranded');
    if (unbrandedGroups.length > 0) {
        const ug = countGroupProcessed(unbrandedGroups);
        document.getElementById('unbrandedCount').textContent =
            `共 ${ug.total} 个商品，已处理 ${ug.processed}/${ug.total}`;
        renderGroupSection('unbrandedGroups', unbrandedGroups, 'unbranded');
    }
}

// 渲染分组区块（带分页）
function renderGroupSection(containerId, groups, type) {
    const container = document.getElementById(containerId);
    const pagination = groupPagination[type];
    const totalPages = Math.ceil(groups.length / pagination.perPage);
    
    // 修正页码
    if (pagination.page > totalPages) pagination.page = totalPages;
    if (pagination.page < 1) pagination.page = 1;
    
    const start = (pagination.page - 1) * pagination.perPage;
    const end = start + pagination.perPage;
    const pageGroups = groups.slice(start, end);
    
    // 渲染分组卡片
    const cardsHtml = pageGroups.map(g => renderGroupCard(g, type)).join('');
    
    // 渲染分页控制
    let paginationHtml = '';
    if (groups.length > pagination.perPage) {
        paginationHtml = `
            <div class="flex justify-center items-center gap-2 mt-3">
                <button onclick="changeGroupPage('${type}', ${pagination.page - 1})" 
                        ${pagination.page === 1 ? 'disabled' : ''}
                        class="px-3 py-1 bg-slate-600 hover:bg-slate-500 rounded text-sm disabled:opacity-50">
                    上一页
                </button>
                <span class="text-sm text-slate-400">
                    第 ${pagination.page}/${totalPages} 页 (${groups.length} 个分组)
                </span>
                <button onclick="changeGroupPage('${type}', ${pagination.page + 1})"
                        ${pagination.page === totalPages ? 'disabled' : ''}
                        class="px-3 py-1 bg-slate-600 hover:bg-slate-500 rounded text-sm disabled:opacity-50">
                    下一页
                </button>
                <button onclick="expandAllGroups('${type}')"
                        class="px-3 py-1 bg-slate-600 hover:bg-slate-500 rounded text-sm">
                    展开本页
                </button>
                <button onclick="collapseAllGroups('${type}')"
                        class="px-3 py-1 bg-slate-600 hover:bg-slate-500 rounded text-sm">
                    收起本页
                </button>
            </div>
        `;
    }
    
    container.innerHTML = cardsHtml + paginationHtml;
}

// 切换分组页码
function changeGroupPage(type, page) {
    groupPagination[type].page = page;
    if (diagnosisData) {
        renderBrandGroups(diagnosisData.brand_clusters);
    }
}

// 全部展开
function expandAllGroups(type) {
    const containerId = type === 'missing' ? 'missingGroups' : 
                        type === 'mismatch' ? 'mismatchGroups' : 'validGroups';
    const cards = document.querySelectorAll(`#${containerId} .group-card`);
    cards.forEach(card => card.classList.remove('collapsed'));
}

// 全部收起
function collapseAllGroups(type) {
    const containerId = type === 'missing' ? 'missingGroups' : 
                        type === 'mismatch' ? 'mismatchGroups' : 'validGroups';
    const cards = document.querySelectorAll(`#${containerId} .group-card`);
    cards.forEach(card => card.classList.add('collapsed'));
}

// 渲染分组卡片
function renderGroupCard(group, type) {
    const brand = group.suggested_standard || '无建议';
    const count = group.count;
    const examples = (group.examples || []).slice(0, 2).join(', ');
    const items = group.items || [];

    // 确保 code 为字符串并去除空格，与 brandRules 的 key 格式一致
    const processedCount = items.filter(item => {
        const code = String(item.code).trim();
        return brandRules[code];
    }).length;
    const remainingCount = count - processedCount;

    // 收集当前组内所有已设置品牌，用于卡片头部展示
    const correctedBrands = new Set();
    items.forEach(item => {
        const code = String(item.code).trim();
        const rule = brandRules[code];
        if (rule && rule.brand) correctedBrands.add(rule.brand);
    });
    const allCorrected = remainingCount === 0;

    let header = '';
    let actions = '';

    if (type === 'missing') {
        if (allCorrected && correctedBrands.size === 1) {
            header = `已设置品牌: <span class="text-green-400">${[...correctedBrands][0]}</span>`;
        } else if (allCorrected && correctedBrands.size > 1) {
            header = `建议品牌: <span class="text-yellow-400">${brand}</span> → 已设置 <span class="text-green-400">${correctedBrands.size}</span> 个不同品牌`;
        } else if (processedCount > 0) {
            header = `建议品牌: <span class="text-yellow-400">${brand}</span>（已处理 ${processedCount}/${count}）`;
        } else {
            header = `建议品牌: <span class="text-yellow-400">${brand}</span>`;
        }
        actions = `
            <button onclick="openSidePanel('missing', ${group.cluster_id})" class="px-3 py-1 bg-blue-600 hover:bg-blue-500 rounded text-sm">
                查看商品(${remainingCount})
            </button>
            <div class="flex items-center gap-1">
                ${renderBrandDropdown(`brand-dd-missing-${group.cluster_id}`, '', '批量设置...')}
                <button onclick="applyDropdownBrand('brand-dd-missing-${group.cluster_id}', ${group.cluster_id})" class="px-2 py-1 bg-blue-600 hover:bg-blue-500 rounded text-sm">应用</button>
            </div>
            <select onchange="batchSetBrand(${group.cluster_id}, this.value)" class="px-2 py-1 bg-slate-600 rounded text-sm">
                <option value="">快捷操作...</option>
                <option value="__NO_BRAND__">无品牌商品</option>
                <option value="__NEW_BRAND__">+ 新品牌</option>
            </select>
            <button onclick="skipGroup(${group.cluster_id})" class="px-3 py-1 bg-gray-600 hover:bg-gray-500 rounded text-sm">
                跳过
            </button>
        `;
    } else if (type === 'unbranded') {
        header = '<span class="text-green-400">🥬 系统建议: 天然无品牌商品</span>';
        actions = `
            <button onclick="confirmUnbrandedGroup(${group.cluster_id})" class="px-3 py-1 bg-green-600 hover:bg-green-500 rounded text-sm font-bold whitespace-nowrap">
                ✅ 确认无品牌
            </button>
            <button onclick="openSidePanel('unbranded', ${group.cluster_id})" class="px-3 py-1 bg-blue-600 hover:bg-blue-500 rounded text-sm">
                查看商品(${remainingCount})
            </button>
            <button onclick="skipGroup(${group.cluster_id})" class="px-3 py-1 bg-gray-600 hover:bg-gray-500 rounded text-sm">
                跳过
            </button>
        `;
    } else if (type === 'mismatch') {
        const currentBrand = group.brands[0] || '未知';
        if (allCorrected && correctedBrands.size === 1) {
            header = `当前: <span class="text-red-400">${currentBrand}</span> → 已修正为: <span class="text-green-400">${[...correctedBrands][0]}</span>`;
        } else if (allCorrected && correctedBrands.size > 1) {
            header = `当前: <span class="text-red-400">${currentBrand}</span> → 已设置 <span class="text-green-400">${correctedBrands.size}</span> 个不同品牌`;
        } else if (processedCount > 0) {
            header = `当前: <span class="text-red-400">${currentBrand}</span> → 建议: <span class="text-yellow-400">${brand}</span>（已处理 ${processedCount}/${count}）`;
        } else {
            header = `当前: <span class="text-red-400">${currentBrand}</span> → 建议: <span class="text-yellow-400">${brand}</span>`;
        }
        actions = `
            <button onclick="openSidePanel('mismatch', ${group.cluster_id})" class="px-3 py-1 bg-blue-600 hover:bg-blue-500 rounded text-sm">
                查看商品(${remainingCount})
            </button>
            <div class="flex items-center gap-1">
                ${renderBrandDropdown(`brand-dd-mismatch-${group.cluster_id}`, '', '修改为...')}
                <button onclick="applyDropdownBrand('brand-dd-mismatch-${group.cluster_id}', ${group.cluster_id})" class="px-2 py-1 bg-blue-600 hover:bg-blue-500 rounded text-sm">应用</button>
            </div>
            <select onchange="batchSetBrand(${group.cluster_id}, this.value)" class="px-2 py-1 bg-slate-600 rounded text-sm">
                <option value="">快捷操作...</option>
                <option value="__NO_BRAND__">无品牌商品</option>
            </select>
            <button onclick="skipGroup(${group.cluster_id})" class="px-3 py-1 bg-gray-600 hover:bg-gray-500 rounded text-sm">
                跳过
            </button>
        `;
    } else if (type === 'valid') {
        if (allCorrected) {
            header = `品牌: <span class="text-green-400">${brand}</span>（全部已确认）`;
        } else if (processedCount > 0) {
            header = `品牌: <span class="text-blue-400">${brand}</span>（已确认 ${processedCount}/${count}）`;
        } else {
            header = `品牌: <span class="text-blue-400">${brand}</span>`;
        }
        actions = `
            <button onclick="openSidePanel('valid', ${group.cluster_id})" class="px-3 py-1 bg-blue-600 hover:bg-blue-500 rounded text-sm">
                查看商品(${remainingCount})
            </button>
            <button onclick="confirmValidGroup(${group.cluster_id})" class="px-3 py-1 bg-green-600 hover:bg-green-500 rounded text-sm">
                确认正确
            </button>
            <button onclick="skipGroup(${group.cluster_id})" class="px-3 py-1 bg-gray-600 hover:bg-gray-500 rounded text-sm">
                跳过
            </button>
        `;
    }

    const statusBadge = remainingCount === 0 ?
        '<span class="text-xs bg-green-600 px-2 py-1 rounded">✓ 已完成</span>' :
        `<span class="text-xs bg-yellow-600 px-2 py-1 rounded">待处理 ${remainingCount}/${count}</span>`;

    return `
        <div class="group-card ${type}" data-cluster-id="${group.cluster_id}">
            <div class="flex justify-between items-start mb-2">
                <div>
                    <div class="font-semibold group-toggle" onclick="toggleGroup(this)">${header}</div>
                    <div class="text-sm text-gray-400 mt-1">${count}个商品code | ${statusBadge}</div>
                </div>
            </div>
            <div class="group-details">
                <div class="text-sm text-gray-300 mb-3">示例: ${examples}...</div>
                <div class="flex gap-2 flex-wrap">
                    ${actions}
                </div>
            </div>
        </div>
    `;
}

// 折叠/展开分组
function toggleGroup(element) {
    const card = element.closest('.group-card');
    card.classList.toggle('collapsed');
}

// 渲染可搜索品牌下拉框
function renderBrandDropdown(containerId, selectedValue, placeholder) {
    placeholder = placeholder || '选择品牌...';
    const displayText = selectedValue ? getBrandDisplayText(selectedValue) : '';
    return `
        <div class="brand-dropdown-wrapper" id="${containerId}" data-selected-brand="${selectedValue || ''}">
            <input type="text" class="brand-dropdown-input" 
                   placeholder="${placeholder}" 
                   value="${displayText}"
                   oninput="filterBrandDropdown('${containerId}', this.value)"
                   onclick="toggleBrandDropdown('${containerId}')"
                   autocomplete="off" />
            <div class="brand-dropdown-list" id="${containerId}-list">
                ${renderBrandDropdownItems(containerId, selectedValue)}
            </div>
        </div>
    `;
}

// 获取品牌显示文本
function getBrandDisplayText(brandName) {
    if (!brandName) return '';
    const brand = brandDatabase.find(b => b.name === brandName);
    if (!brand) return brandName;
    return brand.display_name || brand.name;
}

// 渲染下拉框选项列表
function renderBrandDropdownItems(containerId, selectedValue, filterText) {
    let filtered = brandDatabase;
    const lowerFilter = filterText ? filterText.toLowerCase() : '';
    
    if (lowerFilter) {
        filtered = brandDatabase.map(b => {
            // 匹配逻辑：主名、显示名、别名
            const nameMatch = b.name.toLowerCase().includes(lowerFilter);
            const displayMatch = b.display_name.toLowerCase().includes(lowerFilter);
            const matchedAlias = b.aliases.find(a => a.toLowerCase().includes(lowerFilter));
            
            if (nameMatch || displayMatch || matchedAlias) {
                return { ...b, matchedAlias: (nameMatch || displayMatch) ? null : matchedAlias };
            }
            return null;
        }).filter(b => b !== null);
    }
    
    if (filtered.length === 0) {
        return '<div class="brand-dropdown-empty">无匹配品牌</div>';
    }
    
    // 增加限制到 2000 条，确保滚动到底部能看全所有品牌
    const limit = 2000;
    const displayBrands = filtered.slice(0, limit);
    
    return displayBrands.map(b => {
        const selected = b.name === selectedValue ? 'selected' : '';
        const meta = `${b.type} · ${b.country}`;
        const displayText = b.display_name || b.name;
        
        // 如果是通过别名匹配的，显示别名提示
        const aliasHint = b.matchedAlias ? `<span class="text-[10px] text-yellow-500 ml-1">(${b.matchedAlias})</span>` : '';
        
        return `
            <div class="brand-dropdown-item ${selected}" 
                 onclick="selectBrandFromDropdown('${containerId}', '${b.name.replace(/'/g, "\\'")}')">
                <div class="flex flex-col">
                    <div>
                        <span class="brand-name">${displayText}</span>
                        ${aliasHint}
                    </div>
                    <span class="brand-meta">${meta}</span>
                </div>
            </div>
        `;
    }).join('');
}

// 切换下拉框显示/隐藏
function toggleBrandDropdown(containerId) {
    const wrapper = document.getElementById(containerId);
    const list = document.getElementById(containerId + '-list');
    const input = wrapper.querySelector('.brand-dropdown-input');
    const isOpen = list.classList.contains('open');
    
    // 关闭所有其他下拉框
    document.querySelectorAll('.brand-dropdown-list.open').forEach(el => {
        if (el.id !== containerId + '-list') el.classList.remove('open');
    });
    
    if (!isOpen) {
        // 显式确保 input 可编辑
        input.removeAttribute('readonly');
        list.classList.add('open');
        input.focus();
        input.select(); // 自动全选
        
        // 初始展开时渲染全部
        list.innerHTML = renderBrandDropdownItems(containerId, wrapper.dataset.selectedBrand);
    } else {
        list.classList.remove('open');
    }
}

// 过滤下拉框选项
function filterBrandDropdown(containerId, text) {
    const list = document.getElementById(containerId + '-list');
    const selectedBrand = document.getElementById(containerId).dataset.selectedBrand;
    list.innerHTML = renderBrandDropdownItems(containerId, selectedBrand, text);
    list.classList.add('open');
}

// 从下拉框选择品牌
function selectBrandFromDropdown(containerId, brandName) {
    const wrapper = document.getElementById(containerId);
    const input = wrapper.querySelector('.brand-dropdown-input');
    const list = document.getElementById(containerId + '-list');
    
    wrapper.dataset.selectedBrand = brandName;
    input.value = getBrandDisplayText(brandName);
    list.classList.remove('open');
}

// 应用下拉框选择的品牌（批量）
function applyDropdownBrand(containerId, clusterId) {
    const wrapper = document.getElementById(containerId);
    const brandName = wrapper.dataset.selectedBrand;
    if (!brandName) {
        alert('请先选择品牌');
        return;
    }
    batchSetBrand(clusterId, brandName);
    // 重置下拉框
    wrapper.dataset.selectedBrand = '';
    wrapper.querySelector('.brand-dropdown-input').value = '';
}

// 应用下拉框选择的品牌（单个商品）
function applyItemDropdownBrand(containerId, code) {
    const wrapper = document.getElementById(containerId);
    const brandName = wrapper.dataset.selectedBrand;
    if (!brandName) {
        alert('请先选择品牌');
        return;
    }
    setItemBrand(code, brandName);
    // 重置下拉框
    wrapper.dataset.selectedBrand = '';
    wrapper.querySelector('.brand-dropdown-input').value = '';
}

// 点击外部关闭下拉框
document.addEventListener('click', function(e) {
    if (!e.target.closest('.brand-dropdown-wrapper')) {
        document.querySelectorAll('.brand-dropdown-list.open').forEach(el => {
            el.classList.remove('open');
        });
        document.querySelectorAll('.brand-dropdown-input').forEach(input => {
            input.setAttribute('readonly', true);
        });
    }
});

// 同步 brandRules 从后端
async function syncBrandRules() {
    try {
        const res = await fetch(`/api/brand_rules/get?sid=${sessionId}`);
        const data = await res.json();
        if (data.brand_rules) {
            brandRules = data.brand_rules;
        }
        if (data.new_brands !== undefined) {
            newBrands = data.new_brands;
        }
        updateNewBrandsDisplay();
    } catch (err) {
        console.error('同步品牌规则失败:', err);
    }
}

// 关闭侧边弹窗
async function closeSidePanel() {
    document.getElementById('sidePanelOverlay').classList.remove('open');
    document.getElementById('sidePanel').classList.remove('open');
    currentPanelData = null;

    // 从后端同步 brandRules 确保状态一致
    await syncBrandRules();
    
    // 刷新品牌分组显示
    if (diagnosisData) {
        renderBrandGroups(diagnosisData.brand_clusters);
    }
}

// 打开侧边弹窗（从品牌分组卡片）
function openSidePanel(type, clusterId) {
    if (!diagnosisData) return;
    const cluster = diagnosisData.brand_clusters.find(c => c.cluster_id === clusterId);
    if (!cluster) return;

    currentPanelData = { type, items: cluster.items || [], group: cluster };
    currentPanelPage = 1;
    currentPanelFilter = '';

    const titles = { missing: '品牌缺失商品', mismatch: '品牌错误商品', valid: '待确认品牌', unbranded: '无品牌商品' };
    document.getElementById('sidePanelTitle').textContent = titles[type] || '商品详情';
    renderPanelContent();
    document.getElementById('sidePanelOverlay').classList.add('open');
    document.getElementById('sidePanel').classList.add('open');
}

// 渲染弹窗内容
function renderPanelContent() {
    if (!currentPanelData) return;

    const { type, items } = currentPanelData;
    const isUnifiedBrand = type === 'unifiedBrand';

    // 过滤
    let filteredItems = items;
    if (currentPanelFilter) {
        filteredItems = items.filter(item =>
            item.name.toLowerCase().includes(currentPanelFilter.toLowerCase()) ||
            String(item.code).toLowerCase().includes(currentPanelFilter.toLowerCase())
        );
    }

    // 分页
    const totalPages = Math.ceil(filteredItems.length / ITEMS_PER_PAGE);
    const start = (currentPanelPage - 1) * ITEMS_PER_PAGE;
    const pageItems = filteredItems.slice(start, start + ITEMS_PER_PAGE);

    // 渲染商品列表（统一面板模式下按 item._section 传递类型渲染来源标签）
    const itemsHtml = pageItems.map(item => renderPanelItem(item, isUnifiedBrand ? (item._section || 'missing') : type)).join('');
    document.getElementById('panelItemsList').innerHTML = itemsHtml || '<p class="text-gray-400 text-center">无商品</p>';

    // 渲染分页
    renderPagination(totalPages);

    // 渲染批量操作
    renderBatchActions(isUnifiedBrand ? 'missing' : type);
}

// 渲染弹窗商品项
function renderPanelItem(item, type) {
    const code = String(item.code).trim();
    const rule = brandRules[code];
    let statusHtml = '';
    let itemClass = 'item-row';

    // 来源标签（统一品牌面板模式下显示）
    const sectionLabel = item._section || '';
    const sectionStyle = sectionLabel === 'missing' ? 'bg-yellow-900/50 text-yellow-400' :
        sectionLabel === 'mismatch' ? 'bg-red-900/50 text-red-400' :
        sectionLabel === 'valid' ? 'bg-blue-900/50 text-blue-400' : '';
    const sectionText = sectionLabel === 'missing' ? '品牌缺失' :
        sectionLabel === 'mismatch' ? '品牌错误' :
        sectionLabel === 'valid' ? '待确认正确' : '';

    if (rule) {
        if (rule.no_brand) {
            statusHtml = '<span class="text-green-400">✓ 已标记: 无品牌</span>';
            itemClass += ' processed';
        } else if (rule.skipped) {
            statusHtml = '<span class="text-gray-400">⏭ 已跳过</span>';
            itemClass += ' skipped';
        } else if (rule.brand) {
            statusHtml = `<span class="text-green-400">✓ 已设置: ${rule.brand}</span>`;
            itemClass += ' processed';
        }
    }

    let suggestionHtml = '';
    if (type === 'missing') {
        if (rule && rule.brand) {
            suggestionHtml = `<div class="text-sm text-green-400">已设置品牌: ${rule.brand}</div>`;
        } else if (rule && rule.no_brand) {
            suggestionHtml = '<div class="text-sm text-green-400">已标记为无品牌</div>';
        } else if (item.suggested_brand) {
            suggestionHtml = `<div class="text-sm text-yellow-400">建议品牌: ${item.suggested_brand}</div>`;
        } else {
            suggestionHtml = '';
        }
    } else if (type === 'mismatch') {
        if (rule && rule.brand) {
            suggestionHtml = `<div class="text-sm text-green-400">当前品牌: ${item.brand} → 已修正为: ${rule.brand}</div>`;
        } else if (rule && rule.no_brand) {
            suggestionHtml = `<div class="text-sm text-green-400">当前品牌: ${item.brand} → 已标记为无品牌</div>`;
        } else {
            suggestionHtml = `<div class="text-sm text-red-400">当前品牌: ${item.brand} → 建议: ${item.suggested_brand || '无'}</div>`;
        }
    } else if (type === 'unbranded') {
        suggestionHtml = '<div class="text-sm text-green-400">🥬 系统建议: 天然无品牌商品</div>';
    }

    // 关键因素展示
    let factorsHtml = '';
    if (item.factors && typeof item.factors === 'object' && Object.keys(item.factors).length > 0) {
        const parts = [];
        if (item.factors.source) parts.push(`来源="${item.factors.source}"`);
        if (item.factors.matched_text) parts.push(`匹配="${item.factors.matched_text}"`);
        if (item.factors.history_correction) parts.push(`📌 历史修正: ${item.factors.history_correction}`);
        if (parts.length) {
            factorsHtml = `<div class="text-[10px] text-cyan-300 mt-0.5">🔍 ${parts.join(' | ')}</div>`;
        }
    }

    return `
        <div class="${itemClass}" data-code="${item.code}">
            ${sectionText ? `<div class="text-[9px] px-1.5 py-0.5 rounded inline-block mb-1 ${sectionStyle}">${sectionText}</div>` : ''}
            <div class="flex justify-between items-start mb-2">
                <div class="flex items-start gap-2">
                    ${item.org_image_url ? `<img src="${item.org_image_url}" class="w-10 h-10 object-cover rounded flex-shrink-0 cursor-zoom-in" onerror="this.style.display='none'" onclick="previewImage('${item.org_image_url}')" alt="">` : ''}
                    <div class="min-w-0">
                         <div class="font-medium truncate">${item.name}</div>
                        <div class="text-sm text-gray-400">Code: ${item.code} | 行号: ${item.row}</div>
                        ${suggestionHtml}
                        ${factorsHtml}
                    </div>
                </div>
                <div class="text-right">
                    ${statusHtml}
                </div>
            </div>
            <div class="flex gap-2 mt-3">
                <div class="flex-1 flex items-center gap-1">
                    ${renderBrandDropdown(`brand-dd-item-${item.code}`, item.suggested_brand, '选择品牌...')}
                    <button onclick="applyItemDropdownBrand('brand-dd-item-${item.code}', '${item.code}')" class="px-2 py-1 bg-blue-600 hover:bg-blue-500 rounded text-sm whitespace-nowrap">设置</button>
                </div>
                <select onchange="setItemBrand('${item.code}', this.value)" class="px-2 py-1 bg-slate-600 rounded text-sm">
                    <option value="">快捷...</option>
                    <option value="__NO_BRAND__">无品牌</option>
                    <option value="__NEW_BRAND__">+ 新品牌</option>
                </select>
                <button onclick="skipItem('${item.code}')" class="px-3 py-1 bg-gray-600 hover:bg-gray-500 rounded text-sm">
                    跳过
                </button>
            </div>
        </div>
    `;
}

// 渲染分页
function renderPagination(totalPages) {
    if (totalPages <= 1) {
        document.getElementById('panelPagination').innerHTML = '';
        return;
    }

    let html = `
        <button onclick="changePage(${currentPanelPage - 1})" ${currentPanelPage === 1 ? 'disabled' : ''}>上一页</button>
    `;

    for (let i = 1; i <= totalPages; i++) {
        const active = i === currentPanelPage ? 'active' : '';
        html += `<button onclick="changePage(${i})" class="${active}">${i}</button>`;
    }

    html += `
        <button onclick="changePage(${currentPanelPage + 1})" ${currentPanelPage === totalPages ? 'disabled' : ''}>下一页</button>
    `;

    document.getElementById('panelPagination').innerHTML = html;
}

// 渲染批量操作
function renderBatchActions(type) {
    let html = '';

    if (type === 'missing') {
        html = `
            <button onclick="batchApplySuggestion()" class="px-3 py-1 bg-yellow-600 hover:bg-yellow-500 rounded text-sm">
                全部应用建议品牌
            </button>
            <button onclick="batchMarkNoBrand()" class="px-3 py-1 bg-gray-600 hover:bg-gray-500 rounded text-sm">
                全部标记为无品牌
            </button>
        `;
    } else if (type === 'mismatch') {
        html = `
            <button onclick="batchApplySuggestion()" class="px-3 py-1 bg-yellow-600 hover:bg-yellow-500 rounded text-sm">
                全部修改为建议品牌
            </button>
        `;
    } else if (type === 'valid') {
        html = `
            <button onclick="batchConfirmValid()" class="px-3 py-1 bg-green-600 hover:bg-green-500 rounded text-sm">
                全部确认正确
            </button>
        `;
    }

    html += `
        <button onclick="batchSkipRemaining()" class="px-3 py-1 bg-gray-600 hover:bg-gray-500 rounded text-sm">
            跳过剩余未处理
        </button>
    `;

    document.getElementById('panelBatchActions').innerHTML = html;
}

// 筛选弹窗商品
function filterPanelItems() {
    currentPanelFilter = document.getElementById('panelSearch').value;
    currentPanelPage = 1;
    renderPanelContent();
}

// 切换页面
function changePage(page) {
    // 检测分类面板模式
    if (window.currentPanelData && window.currentPanelData.type === 'category') {
        if (page < 1 || page > Math.ceil(window.currentPanelData.items.length / ITEMS_PER_PAGE)) return;
        window.currentPanelPage = page;
        renderCategoryPanelContent();
        return;
    }
    // 品牌面板
    if (!currentPanelData) return;
    const { items } = currentPanelData;
    const filteredItems = currentPanelFilter ?
        items.filter(item =>
            item.name.toLowerCase().includes(currentPanelFilter.toLowerCase()) ||
            item.code.toLowerCase().includes(currentPanelFilter.toLowerCase())
        ) : items;
    const totalPages = Math.ceil(filteredItems.length / ITEMS_PER_PAGE);

    if (page < 1 || page > totalPages) return;
    currentPanelPage = page;
    renderPanelContent();
}

// 设置商品品牌
async function setItemBrand(code, value) {
    if (!value) return;

    if (value === '__NO_BRAND__') {
        await saveBrandRule(code, 'no_brand');
    } else if (value === '__NEW_BRAND__') {
        openAddBrandModal(code, 'single');
    } else {
        await saveBrandRule(code, 'set_brand', value);
    }

    // 刷新显示
    renderPanelContent();
}

// 跳过商品
async function skipItem(code) {
    await saveBrandRule(code, 'skip');
    renderPanelContent();
}

// 保存品牌规则
async function saveBrandRule(code, type, brand = null) {
    // 确保 code 为字符串并去除空格
    const normalizedCode = String(code).trim();
    // 保存旧值，用于回滚
    const prevRule = brandRules[normalizedCode];

    // 乐观更新本地
    const newRule = type === 'set_brand'      ? { brand, no_brand: false, skipped: false }
                  : type === 'no_brand'       ? { brand: null, no_brand: true, skipped: false }
                  : type === 'skip'           ? { brand: null, no_brand: false, skipped: true }
                  : type === 'confirm_valid'  ? { brand, confirmed: true, skipped: false }
                  : null;
    if (newRule) brandRules[normalizedCode] = newRule;

    try {
        const res = await fetch('/api/brand_rules/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: sessionId,
                code: normalizedCode,
                type: type,
                brand: brand
            })
        });
        const data = await res.json();
        if (!data.success) throw new Error(data.error);
    } catch (err) {
        // 失败：回滚本地状态
        if (prevRule !== undefined) brandRules[normalizedCode] = prevRule;
        else delete brandRules[normalizedCode];
        console.error('保存规则失败:', err);
    }
}

// === 添加品牌 Modal 逻辑 ===
let currentModalContext = null; // {type: 'single'|'batch', target: code|clusterId}

function openAddBrandModal(target, type, sidebarData) {
    currentModalContext = { target, type, index: currentModalContext?.index };
    
    let prefilled = { name: '', type: '未知', country: 'CN' };
    
    if (type === 'single') {
        const item = findItemByCode(target);
        if (item) prefilled.name = item.brand;
    } else if (type === 'sidebar' && sidebarData) {
        prefilled = {
            name: sidebarData.name || '',
            type: sidebarData.type || '未知',
            country: sidebarData.country || 'CN',
            parent_brand: sidebarData.parent_brand || '',
            relation_type: sidebarData.relation_type || ''
        };
    }
    
    document.getElementById('modalBrandName').value = prefilled.name;
    
    fetch('/api/brands/config').then(r => r.json()).then(config => {
        const types = config.brand_types || [];
        renderConfigDropdown('modalBrandTypeContainer', 'modalBrandTypeList', 'modalBrandType',
            types, null, null, prefilled.type, '选择类型...');
        
        const countries = (config.countries || []).map(c => c.code + ' (' + c.name + ')');
        const selCountry = countries.find(s => s.startsWith(prefilled.country)) || prefilled.country + ' (未知)';
        renderConfigDropdown('modalBrandCountryContainer', 'modalBrandCountryList', 'modalBrandCountry',
            countries, null, null, selCountry, '选择国家...');
    }).catch(() => {
        renderConfigDropdown('modalBrandTypeContainer', 'modalBrandTypeList', 'modalBrandType',
            ['食品','饮料','零食','乳品','生鲜'], null, null, prefilled.type, '选择类型...');
        const fallbackCountries = ['CN (中国)','US (美国)','JP (日本)','KR (韩国)','ID (印尼)',
            'TH (泰国)','VN (越南)','MY (马来西亚)','SG (新加坡)','IE (爱尔兰)',
            'GB (英国)','AU (澳大利亚)','FR (法国)','DE (德国)','CA (加拿大)'];
        const selFallback = prefilled.country ? fallbackCountries.find(s => s.startsWith(prefilled.country)) : 'CN (中国)';
        renderConfigDropdown('modalBrandCountryContainer', 'modalBrandCountryList', 'modalBrandCountry',
            fallbackCountries, null, null, selFallback, '选择国家...');
    });
    
    // 初始化关联主品牌下拉
    const parentInput = document.getElementById('modalParentBrand');
    const parentList = document.getElementById('modalParentBrandList');
    const parentContainer = document.getElementById('modalParentBrandContainer');
    const relationRow = document.getElementById('modalRelationType');
    if (parentInput && parentList) {
        parentContainer.dataset.selected = '';
        relationRow.style.display = 'none';
        parentInput.value = '';
        parentInput.placeholder = '不关联...';
        parentInput.oninput = function() { filterParentBrands(this.value); };
        parentInput.onfocus = function() { filterParentBrands(this.value); };
        parentInput.onclick = function(e) { e.stopPropagation(); filterParentBrands(this.value); };
        filterParentBrands('');
        document.addEventListener('click', function hideParentList(e) {
            if (!parentContainer.contains(e.target)) {
                parentList.style.display = 'none';
            }
        });
        // 预填关联主品牌
        if (prefilled.parent_brand) {
            setTimeout(() => {
                selectParentBrand(prefilled.parent_brand);
                const radioId = prefilled.relation_type === 'sub_brand' ? 'relationSubBrand' : 'relationAlias';
                const radioEl = document.getElementById(radioId);
                if (radioEl) radioEl.checked = true;
            }, 100);
        }
    }

    document.getElementById('addBrandModal').classList.add('open');
    document.getElementById('modalBrandName').focus();
}

function filterParentBrands(text) {
    const list = document.getElementById('modalParentBrandList');
    const container = document.getElementById('modalParentBrandContainer');
    if (!list || !brandDatabase) return;
    const lower = (text || '').toLowerCase();
    const filtered = brandDatabase.filter(b => b.name && b.name.toLowerCase().includes(lower));
    list.innerHTML = filtered.map(b =>
        `<div class="brand-dropdown-item" data-value="${b.name.replace(/'/g, "\\'")}"
            onclick="selectParentBrand('${b.name.replace(/'/g, "\\'")}')">
            <span class="text-xs">${b.name}</span>
        </div>`
    ).join('');
    if (!filtered.length) {
        list.innerHTML = '<div class="brand-dropdown-empty text-xs">无匹配</div>';
    }
    list.style.display = 'block';
}

function selectParentBrand(name) {
    const input = document.getElementById('modalParentBrand');
    const list = document.getElementById('modalParentBrandList');
    const container = document.getElementById('modalParentBrandContainer');
    const relationRow = document.getElementById('modalRelationType');
    input.value = name;
    container.dataset.selected = name;
    list.style.display = 'none';
    relationRow.style.display = 'flex';
    document.getElementById('relationSubBrand').checked = true;
}

// 渲染可搜索下拉框（与品牌下拉组件相同模式）
function renderConfigDropdown(containerId, listId, inputId, items, labelKey, valueKey, selectedValue, placeholder) {
    const container = document.getElementById(containerId);
    const list = document.getElementById(listId);
    const input = document.getElementById(inputId);
    
    if (!container || !list || !input) return;
    
    function filter(text) {
        const lower = (text || '').toLowerCase();
        const filtered = items.filter(item => {
            const label = typeof item === 'string' ? item : item[labelKey || 'name'];
            return label.toLowerCase().includes(lower);
        });
        renderList(filtered);
        list.classList.add('open');
    }
    
    function renderList(filteredItems) {
        list.innerHTML = filteredItems.map(item => {
            const label = typeof item === 'string' ? item : item[labelKey || 'name'];
            const val = typeof item === 'string' ? item : item[valueKey || 'code'];
            const active = (val === selectedValue || label === selectedValue) ? 'selected' : '';
            return `<div class="brand-dropdown-item ${active}" data-value="${val}" 
                onclick="selectConfigItem('${containerId}','${listId}','${inputId}','${val.replace(/'/g, "\\'")}','${label.replace(/'/g, "\\'")}')">
                <span class="text-xs">${label}</span>
            </div>`;
        }).join('');
        if (!filteredItems.length) {
            list.innerHTML = '<div class="brand-dropdown-empty text-xs">无匹配选项</div>';
        }
    }
    
    input.value = selectedValue && selectedValue !== '未知' ? selectedValue : '';
    input.placeholder = placeholder || '选择...';
    
    input.oninput = function() { filter(this.value); };
    input.onfocus = function() { filter(this.value); };
    input.onclick = function(e) { e.stopPropagation(); filter(this.value); };
    
    renderList(items);
    container.dataset.selected = selectedValue || '';
}

function selectConfigItem(containerId, listId, inputId, value, label) {
    const container = document.getElementById(containerId);
    const list = document.getElementById(listId);
    const input = document.getElementById(inputId);
    if (container) container.dataset.selected = value;
    if (input) input.value = label;
    if (list) list.classList.remove('open');
}

// 点击外部关闭配置下拉
document.addEventListener('click', function(e) {
    ['modalBrandTypeContainer', 'modalBrandCountryContainer'].forEach(id => {
        const el = document.getElementById(id);
        if (el && !el.contains(e.target)) {
            const list = el.querySelector('.brand-dropdown-list');
            if (list) list.classList.remove('open');
        }
    });
});

function manageBrandTypes() {
    brandConfigMode = 'types';
    document.getElementById('brandConfigModalTitle').textContent = '⚙️ 管理品牌类型';
    renderBrandConfigList();
    document.getElementById('brandConfigNewInput').value = '';
    document.getElementById('brandConfigNewInput').placeholder = '输入新类型名称...';
    document.getElementById('brandConfigModal').classList.add('open');
}

function manageCountries() {
    brandConfigMode = 'countries';
    document.getElementById('brandConfigModalTitle').textContent = '⚙️ 管理国家/地区';
    renderBrandConfigList();
    document.getElementById('brandConfigNewInput').value = '';
    document.getElementById('brandConfigNewInput').placeholder = '输入: 国家代码 国家名称 (如: KR 韩国)';
    document.getElementById('brandConfigModal').classList.add('open');
}

function closeBrandConfigModal() {
    document.getElementById('brandConfigModal').classList.remove('open');
}

function renderBrandConfigList() {
    const container = document.getElementById('brandConfigList');
    fetch('/api/brands/config').then(r => r.json()).then(config => {
        if (brandConfigMode === 'types') {
            const types = config.brand_types || [];
            container.innerHTML = types.map(t =>
                `<div class="flex items-center justify-between py-1 px-2 bg-slate-800/50 rounded">
                    <span>${t}</span>
                    <button onclick="deleteBrandConfigItem('${t.replace(/'/g, "\\'")}')" class="text-red-400 hover:text-red-300 text-xs px-1">✕</button>
                </div>`
            ).join('') || '<p class="text-slate-500 text-xs">暂无类型</p>';
        } else {
            const countries = config.countries || [];
            container.innerHTML = countries.map(c =>
                `<div class="flex items-center justify-between py-1 px-2 bg-slate-800/50 rounded">
                    <span>${c.code} (${c.name})</span>
                    <button onclick="deleteBrandConfigItem('${c.code}')" class="text-red-400 hover:text-red-300 text-xs px-1">✕</button>
                </div>`
            ).join('') || '<p class="text-slate-500 text-xs">暂无国家</p>';
        }
    }).catch(err => {
        console.error('加载配置失败:', err);
        container.innerHTML = '<p class="text-red-400 text-xs">加载失败，请重试</p>';
    });
}

function deleteBrandConfigItem(value) {
    if (!confirm(`确定删除"${value}"？`)) return;
    const url = brandConfigMode === 'types' ? '/api/brands/config/type' : '/api/brands/config/country';
    const body = brandConfigMode === 'types' ? JSON.stringify({type: value}) : JSON.stringify({code: value});
    fetch(url, {method: 'DELETE', headers: {'Content-Type': 'application/json'}, body}).then(() => {
        renderBrandConfigList();
        refreshBrandModalDropdowns();
    });
}

function submitBrandConfigNew() {
    const input = document.getElementById('brandConfigNewInput');
    const value = input.value.trim();
    if (!value) return;
    
    if (brandConfigMode === 'types') {
        fetch('/api/brands/config/type', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({type: value})
        }).then(() => {
            input.value = '';
            renderBrandConfigList();
            refreshBrandModalDropdowns();
        });
    } else {
        const parts = value.split(/\s+/);
        const code = parts[0].toUpperCase();
        const name = parts.slice(1).join(' ') || code;
        if (!code) return alert('格式: 国家代码 国家名称 (如: KR 韩国)');
        fetch('/api/brands/config/country', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({code, name})
        }).then(() => {
            input.value = '';
            renderBrandConfigList();
            refreshBrandModalDropdowns();
        });
    }
}

function refreshBrandModalDropdowns() {
    const typeContainer = document.getElementById('modalBrandTypeContainer');
    const countryContainer = document.getElementById('modalBrandCountryContainer');
    if (!typeContainer && !countryContainer) return;

    const typeInput = document.getElementById('modalBrandType');
    const countryInput = document.getElementById('modalBrandCountry');
    const curType = typeInput ? typeInput.value || document.getElementById('modalBrandTypeContainer')?.dataset?.selected || '未知' : '未知';
    const curCountry = countryInput ? countryInput.value || document.getElementById('modalBrandCountryContainer')?.dataset?.selected || 'CN' : 'CN';

    fetch('/api/brands/config').then(r => r.json()).then(config => {
        if (typeContainer) {
            const types = config.brand_types || [];
            renderConfigDropdown('modalBrandTypeContainer', 'modalBrandTypeList', 'modalBrandType',
                types, null, null, curType, '选择类型...');
        }
        if (countryContainer) {
            const countries = (config.countries || []).map(c => c.code + ' (' + c.name + ')');
            renderConfigDropdown('modalBrandCountryContainer', 'modalBrandCountryList', 'modalBrandCountry',
                countries, null, null, curCountry, '选择国家...');
        }
    });
}

// 专门为侧边栏建议准备的弹出逻辑
function openAddBrandModalFromSidebar(brandName, index) {
    const brand = newBrands[index];
    if (!brand) return;
    
    currentModalContext = { type: 'sidebar', target: brandName, index: index };
    
    openAddBrandModal(brandName, 'sidebar', {
        name: brand.suggested_name || brand.name,
        type: brand.type || '未知',
        country: brand.country || 'CN',
        parent_brand: brand.parent_brand || '',
        relation_type: brand.relation_type || ''
    });
}

function findItemByCode(code) {
    if (!diagnosisData) return null;
    for (const cluster of diagnosisData.brand_clusters) {
        const item = cluster.items.find(i => String(i.code).trim() === String(code).trim());
        if (item) return item;
    }
    return null;
}

function closeAddBrandModal() {
    document.getElementById('addBrandModal').classList.remove('open');
}

function getParentBrandFromModal() {
    const container = document.getElementById('modalParentBrandContainer');
    const parentBrand = container ? container.dataset.selected || '' : '';
    const relationEl = document.querySelector('input[name="relation"]:checked');
    const relationType = relationEl && parentBrand ? relationEl.value : '';
    return { parent_brand: parentBrand, relation_type: relationType };
}

async function submitNewBrandFromModal() {
    const name = document.getElementById('modalBrandName').value.trim();
    const type = (document.getElementById('modalBrandTypeContainer').dataset.selected || '未知');
    const countryRaw = (document.getElementById('modalBrandCountryContainer').dataset.selected || 'CN');
    const country = countryRaw.split(' (')[0];
    const { parent_brand, relation_type } = getParentBrandFromModal();

    if (!name) {
        alert('请输入品牌名称');
        return;
    }

    // 应用到当前上下文
    if (currentModalContext) {
        if (currentModalContext.type === 'single') {
            await addNewBrand(name, type, country, parent_brand, relation_type, true);
            await saveBrandRule(currentModalContext.target, 'set_brand', name);
            const item = findItemByCode(currentModalContext.target);
            if (item && item.brand && item.brand !== name) {
                fetch('/api/correction/brand', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        suggested: item.brand, corrected_to: name,
                        sample: { name: item.name || '', code: String(item.code).trim() }
                    })
                }).catch(e => console.warn('brand修正保存失败:', e));
            }
            renderPanelContent();
        } else if (currentModalContext.type === 'batch') {
            await addNewBrand(name, type, country, parent_brand, relation_type, true);
            await batchSetBrandAction(currentModalContext.target, name);
            renderBrandGroups(diagnosisData.brand_clusters);
            } else if (currentModalContext.type === 'sidebar') {
            const oldName = currentModalContext.target;
            const index = currentModalContext.index;
            
            if (index !== undefined && index >= 0 && newBrands[index]) {
                const oldBrand = newBrands[index];
                const updatedBrand = {
                    ...oldBrand,
                    name: name,
                    aliases: [name],
                    type: type,
                    country: country,
                    parent_brand: parent_brand,
                    relation_type: relation_type,
                    suggested_name: (name === oldBrand.suggested_name) ? null : oldBrand.suggested_name,
                    original_name: oldBrand.name !== name ? oldBrand.name : undefined
                };
                
                try {
                    const res = await fetch('/api/brands/add', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            session_id: sessionId,
                            brand_name: name,
                            old_name: oldName,
                            aliases: [name],
                            brand_type: type,
                            country: country,
                            confirm_to_library: false,
                            parent_brand: parent_brand,
                            relation_type: relation_type
                        })
                    });
                    const data = await res.json();
                    if (!data.success) throw new Error(data.error);
                } catch (err) {
                    alert('品牌信息保存失败：' + (err.message || '网络错误') + '，请重试');
                    return;
                }

                newBrands[index] = updatedBrand;
            }
        }
    }

    closeAddBrandModal();
    updateNewBrandsDisplay();
}

// 添加新品牌
async function addNewBrand(brandName, brandType = '未知', country = 'CN', parentBrand = '', relationType = '', confirmToLibrary = false) {
    if (!brandName) return;

    // 先调后端确认成功
    try {
        const res = await fetch('/api/brands/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: sessionId,
                brand_name: brandName,
                aliases: [brandName],
                brand_type: brandType,
                country: country,
                confirm_to_library: confirmToLibrary,
                parent_brand: parentBrand,
                relation_type: relationType
            })
        });
        const data = await res.json();
        if (!data.success) throw new Error(data.error || '添加失败');
    } catch (err) {
        alert('添加品牌失败：' + err.message);
        return;
    }

    // 后端成功后才更新前端
    if (!confirmToLibrary) {
        let existing = newBrands.find(b => b.name === brandName);
        if (!existing) {
            newBrands.push({
                name: brandName, aliases: [brandName],
                type: brandType, country: country, confirmed: false
            });
        } else {
            existing.type = brandType;
            existing.country = country;
        }
    }

    const dbExisting = brandDatabase.find(b => b.name === brandName);
    if (!dbExisting) {
        brandDatabase.push({
            name: brandName, display_name: brandName,
            type: brandType, country: country, aliases: [brandName]
        });
        brandDatabase.sort((a, b) => a.display_name.localeCompare(b.display_name));
    }

    updateNewBrandsDisplay();
}

// 批量操作
async function batchSetBrand(clusterId, value) {
    if (!value) return;
    if (!diagnosisData) return;

    if (value === '__NEW_BRAND__') {
        openAddBrandModal(clusterId, 'batch');
    } else {
        await batchSetBrandAction(clusterId, value);
        renderBrandGroups(diagnosisData.brand_clusters);
    }
}

async function batchSetBrandAction(clusterId, value) {
    const group = diagnosisData.brand_clusters.find(c => c.cluster_id === clusterId);
    if (!group || !group.items) return;

    const codes = group.items.map(item => String(item.code).trim());

    if (value === '__NO_BRAND__') {
        await batchSaveRules(codes.map(code => ({ code, type: 'no_brand' })));
    } else {
        await batchSaveRules(codes.map(code => ({ code, type: 'set_brand', brand: value })));
    }
}

async function batchSaveRules(rules) {
    try {
        // 标准化所有 code 为字符串并去除空格
        const normalizedRules = rules.map(rule => ({
            ...rule,
            code: String(rule.code).trim()
        }));
        
        const res = await fetch('/api/brand_rules/batch_save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: sessionId,
                rules: normalizedRules
            })
        });
        const data = await res.json();
        if (data.success) {
            // 更新本地规则缓存
            for (const rule of normalizedRules) {
                if (rule.type === 'set_brand') {
                    brandRules[rule.code] = { brand: rule.brand, no_brand: false, skipped: false };
                } else if (rule.type === 'no_brand') {
                    brandRules[rule.code] = { brand: null, no_brand: true, skipped: false };
                } else if (rule.type === 'skip') {
                    brandRules[rule.code] = { brand: null, no_brand: false, skipped: true };
                } else if (rule.type === 'confirm_valid') {
                    brandRules[rule.code] = { brand: rule.brand, confirmed: true, skipped: false };
                }
            }
            // 从后端同步 brandRules 确保状态一致
            await syncBrandRules();
        }
    } catch (err) {
        console.error('批量保存规则失败:', err);
    }
}

// 跳过整组
async function skipGroup(clusterId) {
    if (!diagnosisData) return;
    const group = diagnosisData.brand_clusters.find(c => c.cluster_id === clusterId);
    if (!group || !group.items) return;

    const codes = group.items.map(item => String(item.code).trim());
    await batchSaveRules(codes.map(code => ({ code, type: 'skip' })));
    renderBrandGroups(diagnosisData.brand_clusters);
}

// 确认整组正确
async function confirmValidGroup(clusterId) {
    if (!diagnosisData) return;
    const group = diagnosisData.brand_clusters.find(c => c.cluster_id === clusterId);
    if (!group || !group.items) return;

    const codes = group.items.map(item => ({
        code: String(item.code).trim(),
        type: 'confirm_valid',
        brand: item.brand
    }));
    await batchSaveRules(codes);
    renderBrandGroups(diagnosisData.brand_clusters);
}

// 批量操作（弹窗内）
async function batchApplySuggestion() {
    if (!currentPanelData) return;
    const { items } = currentPanelData;

    const rules = items
        .filter(item => !brandRules[String(item.code).trim()])
        .map(item => ({
            code: String(item.code).trim(),
            type: 'set_brand',
            brand: item.suggested_brand || item.brand
        }));

    await batchSaveRules(rules);
    renderPanelContent();
}

async function batchMarkNoBrand() {
    if (!currentPanelData) return;
    const { items } = currentPanelData;

    const rules = items
        .filter(item => !brandRules[String(item.code).trim()])
        .map(item => ({
            code: String(item.code).trim(),
            type: 'no_brand'
        }));

    await batchSaveRules(rules);
    renderPanelContent();
}

async function batchConfirmValid() {
    if (!currentPanelData) return;
    const { items } = currentPanelData;

    const rules = items
        .filter(item => !brandRules[String(item.code).trim()])
        .map(item => ({
            code: String(item.code).trim(),
            type: 'confirm_valid',
            brand: item.brand
        }));

    await batchSaveRules(rules);
    renderPanelContent();
}

async function batchSkipRemaining() {
    if (!currentPanelData) return;
    const { items } = currentPanelData;

    const rules = items
        .filter(item => !brandRules[String(item.code).trim()])
        .map(item => ({
            code: String(item.code).trim(),
            type: 'skip'
        }));

    await batchSaveRules(rules);
    renderPanelContent();
}

// 全部跳过
async function skipAllMissing() {
    if (!diagnosisData) return;
    const clusters = diagnosisData.brand_clusters.filter(c => c.type === 'missing');
    const allItems = clusters.flatMap(c => c.items || []);
    const rules = allItems.map(item => ({ code: String(item.code).trim(), type: 'skip' }));
    await batchSaveRules(rules);
    renderBrandGroups(diagnosisData.brand_clusters);
}

async function skipAllMismatch() {
    if (!diagnosisData) return;
    const clusters = diagnosisData.brand_clusters.filter(c => c.type === 'mismatch');
    const allItems = clusters.flatMap(c => c.items || []);
    const rules = allItems.map(item => ({ code: String(item.code).trim(), type: 'skip' }));
    await batchSaveRules(rules);
    renderBrandGroups(diagnosisData.brand_clusters);
}

async function skipAllValid() {
    if (!diagnosisData) return;
    const clusters = diagnosisData.brand_clusters.filter(c => c.type === 'valid');
    const allItems = clusters.flatMap(c => c.items || []);
    const rules = allItems.map(item => ({ code: String(item.code).trim(), type: 'skip' }));
    await batchSaveRules(rules);
    renderBrandGroups(diagnosisData.brand_clusters);
}

async function confirmAllValid() {
    if (!diagnosisData) return;
    const clusters = diagnosisData.brand_clusters.filter(c => c.type === 'valid');
    const allItems = clusters.flatMap(c => c.items || []);
    const rules = allItems.map(item => ({
        code: String(item.code).trim(),
        type: 'confirm_valid',
        brand: item.brand
    }));
    await batchSaveRules(rules);
    renderBrandGroups(diagnosisData.brand_clusters);
}

// 更新新品牌显示
function updateNewBrandsDisplay() {
    const sidebar = document.getElementById('newBrandsSidebar');
    const list = document.getElementById('newBrandsList');
    const app = document.getElementById('app');
    const countEl = document.getElementById('newBrandsCount');
    if (countEl) countEl.textContent = `(${(newBrands || []).length})`;

    if (!newBrands || newBrands.length === 0) {
        if (sidebar) sidebar.classList.add('hidden');
        if (app) app.style.paddingRight = '';
        return;
    }

    if (sidebar) sidebar.classList.remove('hidden');
    if (app) app.style.paddingRight = '380px';

    // 搜索过滤
    const searchInput = document.getElementById('newBrandsSearch');
    const searchTerm = (searchInput ? searchInput.value : '').trim().toLowerCase();
    const filteredBrands = searchTerm
        ? newBrands.filter(b =>
            (b.name || '').toLowerCase().includes(searchTerm) ||
            (b.suggested_name || '').toLowerCase().includes(searchTerm) ||
            (b.sample_product || '').toLowerCase().includes(searchTerm) ||
            (b.sample_category || '').toLowerCase().includes(searchTerm)
          )
        : newBrands;

    // 更新计数: 搜索时显示"X/Y"
    const total = newBrands.length;
    const shown = filteredBrands.length;
    if (countEl) {
        countEl.textContent = searchTerm ? `(${shown}/${total})` : `(${total})`;
    }

    if (filteredBrands.length === 0 && searchTerm) {
        list.innerHTML = `<div class="text-[11px] text-slate-500 text-center py-8">未找到匹配 "${searchTerm}" 的品牌</div>`;
        return;
    }

    list.innerHTML = filteredBrands.map((brand, rawIndex) => {
        // 原始索引，供回调使用
        const index = newBrands.indexOf(brand);
        // 安全处理字符串
        const safeName = (brand.name || '').replace(/'/g, "\\'");
        const safeSuggestedName = (brand.suggested_name || '').replace(/'/g, "\\'");
        
        // 样式处理
        const hasSuggestion = brand.suggested_name && brand.suggested_name !== brand.name;
        const suggestionHtml = hasSuggestion ? `
            <div class="mt-1 p-1 bg-cyan-900/30 border border-cyan-800/50 rounded cursor-pointer hover:bg-cyan-800/50 transition"
                 onclick="applySlashSuggestion('${safeName}', '${safeSuggestedName}')">
                <span class="text-[9px] text-cyan-400 font-bold">✨ 建议更名为:</span>
                <div class="text-[10px] text-white">${brand.suggested_name}</div>
            </div>
        ` : '';

        const contextHtml = brand.sample_product ? `
            <div class="mt-2 pt-2 border-t border-slate-700/50">
                <div class="text-[9px] text-slate-500 mb-0.5">参考样本:</div>
                <div class="text-[10px] text-slate-300 leading-tight mb-1" title="${brand.sample_product}">${brand.sample_product.substring(0, 40)}${brand.sample_product.length > 40 ? '...' : ''}</div>
                <div class="text-[9px] text-orange-400/80 italic">${brand.sample_category || ''}</div>
            </div>
        ` : '';

        // 已确认入库的显示状态
        const cardClass = brand.confirmed ? 
            'bg-green-900/20 border-green-700/50' : 
            'bg-slate-800/80 border-slate-700';
        const confirmBtnHtml = brand.confirmed ?
            `<button class="px-2 py-0.5 bg-green-600 rounded text-[9px] text-white font-bold cursor-default">
                ✅ 已就绪
            </button>` :
            `<button onclick="confirmBrandToLibrary(${index})"
                    class="px-2 py-0.5 bg-orange-600 hover:bg-orange-500 rounded text-[9px] text-white font-bold">
                确认入库
            </button>`;

        return `
            <div class="${cardClass} border p-2.5 rounded-lg shadow-sm transition-colors duration-300">
                <div class="flex justify-between items-start mb-1">
                    <span class="font-bold text-white truncate mr-1" title="${brand.name}">${brand.name}</span>
                    <span class="text-[9px] bg-slate-700 px-1.5 py-0.5 rounded text-slate-400 whitespace-nowrap">${brand.type || '未知'}</span>
                </div>
                ${suggestionHtml}
                <div class="flex justify-between items-center mt-2">
                    <span class="text-[9px] text-slate-500">${brand.country || 'CN'}</span>
                    <div class="flex gap-1">
                        ${!brand.confirmed ? `
                        <button onclick="openAddBrandModalFromSidebar('${safeName}', ${index})"
                                class="px-2 py-0.5 bg-slate-700 hover:bg-slate-600 rounded text-[9px] text-slate-300">
                            编辑
                        </button>
                        <button onclick="dismissNewBrand(${index})"
                                class="px-2 py-0.5 bg-red-900/50 hover:bg-red-800/70 rounded text-[9px] text-slate-400">
                            不是品牌
                        </button>` : ''}
                        ${confirmBtnHtml}
                    </div>
                </div>
                ${contextHtml}
            </div>
        `;
    }).join('');
}
window.updateNewBrandsDisplay = updateNewBrandsDisplay;

// 标记新品牌为「不是品牌」
async function dismissNewBrand(index) {
    const brand = newBrands[index];
    if (!brand) return;
    const brandName = brand.name;
    if (!confirm(`确定"${brandName}"不是品牌？将从待确认列表中移除。`)) return;

    newBrands.splice(index, 1);
    updateNewBrandsDisplay();

    // 保存该品牌下所有商品的 brand_rules（no_brand）
    if (diagnosisData) {
        for (const cluster of diagnosisData.brand_clusters) {
            if (cluster.suggested_standard === brandName) {
                for (const item of cluster.items || []) {
                    const code = String(item.code).trim();
                    brandRules[code] = { brand: null, no_brand: true, skipped: false };
                    await saveBrandRule(code, 'no_brand');
                }
                break;
            }
        }
        renderBrandGroups(diagnosisData.brand_clusters);
    }

    try {
        await fetch('/api/new_brands/dismiss', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ session_id: sessionId, brand_name: brandName })
        });
    } catch (err) {
        console.error('忽略品牌失败:', err);
    }
}

// 清除已导出的品牌
function clearConfirmedBrands() {
    newBrands = newBrands.filter(b => !b.confirmed);
    updateNewBrandsDisplay();
}

// 应用斜杠名建议
async function applySlashSuggestion(oldName, newName) {
    const index = newBrands.findIndex(b => b.name === oldName);
    if (index === -1) return;
    
    const oldBrand = newBrands[index];
    
    // 更新本地状态并保留参考信息
    const updatedBrand = {
        ...oldBrand,
        name: newName,
        aliases: [newName],
        suggested_name: null
    };
    
    newBrands[index] = updatedBrand;
    
    updateNewBrandsDisplay();
    
    // 同步到后端
    try {
        await fetch('/api/brands/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: sessionId,
                brand_name: newName,
                old_name: oldName, // 保持 identity，保留元数据
                aliases: [newName],
                brand_type: oldBrand.type,
                country: oldBrand.country,
                confirm_to_library: false
            })
        });
    } catch (err) {
        console.error('同步斜杠建议失败:', err);
    }
}

// 确认品牌入库
async function confirmBrandToLibrary(index) {
    const brand = newBrands[index];
    if (!brand) return;
    const brandName = brand.name;

    // 查重
    try {
        const checkResp = await fetch('/api/brands/check', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ brand_name: brandName })
        });
        const checkData = await checkResp.json();
        if (checkData.exists) {
            const existingAliases = checkData.existing_aliases || [];
            const newAliases = (brand.aliases || []).filter(a => a !== brandName && !existingAliases.includes(a));
            let msg = `"${brandName}" 已在品牌库中（标准名：${checkData.standard_name}）`;
            if (newAliases.length > 0) msg += `，将合并新别名：${newAliases.join('、')}`;
            msg += '。是否继续？';
            if (!confirm(msg)) return;
        }
    } catch (err) {
        console.warn('品牌查重失败:', err);
    }

    brand.confirmed = true;

    try {
        const resp = await fetch('/api/brands/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: sessionId,
                brand_name: brandName,
                aliases: brand.aliases,
                brand_type: brand.type,
                country: brand.country,
                parent_brand: brand.parent_brand || '',
                relation_type: brand.relation_type || '',
                confirm_to_library: true
            })
        });
        const addData = await resp.json();
        if (!resp.ok || !addData.success) throw new Error(addData.error || '后端确认失败');
        // 保存修正记录
        const origName = brand.original_name;
        if (origName && origName !== brandName && diagnosisData) {
            const sample = { name: brand.sample_product, category: brand.sample_category, code: '' };
            fetch('/api/correction/brand', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ suggested: origName, corrected_to: brandName, sample: sample })
            }).catch(e => console.warn('brand修正保存失败:', e));
            // 逐个 affected 商品存到 corrected_products.json
            for (const cluster of diagnosisData.brand_clusters || []) {
                for (const item of cluster.items || []) {
                    if (String(item.brand) === origName) {
                        const icode = String(item.code || '').trim();
                        if (icode) {
                            fetch('/api/correction/product', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ code: icode, brand: brandName, name: item.name || '' })
                            }).catch(e => console.warn('product修正保存失败:', e));
                        }
                    }
                }
            }
        }
        // 刷新品牌规则和统计
        await syncBrandRules();
        renderGlobalBrandList();
        if (diagnosisData) renderBrandGroups(diagnosisData.brand_clusters);
        updateNewBrandsDisplay();
    } catch (err) {
        console.error('确认入库失败:', err);
    }
}

// ===== 全局品牌索引构建 =====
function buildGlobalBrandIndex() {
    const diag = diagnosisData;
    if (!diag || !diag.brand_clusters) return {};
    const index = {};
    diag.brand_clusters.forEach(c => {
        const brandName = c.suggested_standard || '未知';
        if (!index[brandName]) index[brandName] = { count: 0, items: [], missingCount: 0, mismatchCount: 0, validCount: 0 };
        index[brandName].count += c.count;
        (c.items || []).forEach(item => {
            index[brandName].items.push(Object.assign({}, item, { _section: c.type }));
        });
        index[brandName][c.type + 'Count'] += c.count;
    });
    return index;
}

// ===== 全局品牌列表渲染 =====
function renderGlobalBrandList() {
    const index = buildGlobalBrandIndex();
    const container = document.getElementById('globalBrandListContainer');
    if (!container) return;
    const brands = Object.keys(index).sort();
    if (brands.length === 0) {
        container.innerHTML = '<p class="text-slate-500 text-xs italic py-2">暂无品牌数据</p>';
        return;
    }
    const html = brands.map(b => {
        const info = index[b];
        const processed = info.items.filter(i => brandRules[String(i.code).trim()]).length;
        const total = info.count;
        const pct = total ? Math.round(processed / total * 100) : 0;
        const color = pct === 100 ? '#4ade80' : pct > 0 ? '#facc15' : '#64748b';
        let detail = '';
        if (info.missingCount) detail += `<span class="text-yellow-400">⚠️缺失${info.missingCount}</span> `;
        if (info.mismatchCount) detail += `<span class="text-red-400">❌错误${info.mismatchCount}</span> `;
        if (info.validCount) detail += `<span class="text-blue-400">✅待确认${info.validCount}</span> `;
        const safeName = b.replace(/'/g, "\\'");
        return `<div class="py-1 px-2 cursor-pointer hover:bg-slate-700/50 rounded" onclick="openUnifiedBrandPanel('${safeName}')">
            <div class="flex items-center justify-between">
                <span class="text-xs font-medium text-slate-200">${b}</span>
                <span style="color:${color}" class="text-[10px]">${processed}/${total}已处理</span>
            </div>
            <div class="text-[9px] text-slate-500">${detail}</div>
        </div>`;
    }).join('');
    container.innerHTML = html;
}

function filterGlobalBrandList(text) {
    const index = buildGlobalBrandIndex();
    const container = document.getElementById('globalBrandListContainer');
    if (!container) return;
    const lower = (text || '').toLowerCase();
    const brands = Object.keys(index).sort().filter(b => b.toLowerCase().includes(lower));
    if (brands.length === 0) {
        container.innerHTML = '<p class="text-slate-500 text-xs italic py-2">无匹配品牌</p>';
        return;
    }
    const html = brands.map(b => {
        const info = index[b];
        const processed = info.items.filter(i => brandRules[String(i.code).trim()]).length;
        const total = info.count;
        const pct = total ? Math.round(processed / total * 100) : 0;
        const color = pct === 100 ? '#4ade80' : pct > 0 ? '#facc15' : '#64748b';
        let detail = '';
        if (info.missingCount) detail += `<span class="text-yellow-400">⚠️缺失${info.missingCount}</span> `;
        if (info.mismatchCount) detail += `<span class="text-red-400">❌错误${info.mismatchCount}</span> `;
        if (info.validCount) detail += `<span class="text-blue-400">✅待确认${info.validCount}</span> `;
        const safeName = b.replace(/'/g, "\\'");
        return `<div class="py-1 px-2 cursor-pointer hover:bg-slate-700/50 rounded" onclick="openUnifiedBrandPanel('${safeName}')">
            <div class="flex items-center justify-between">
                <span class="text-xs font-medium text-slate-200">${b}</span>
                <span style="color:${color}" class="text-[10px]">${processed}/${total}已处理</span>
            </div>
            <div class="text-[9px] text-slate-500">${detail}</div>
        </div>`;
    }).join('');
    container.innerHTML = html;
}

// ===== 统一品牌面板（跨板块） =====
function openUnifiedBrandPanel(brandName) {
    const index = buildGlobalBrandIndex();
    const info = index[brandName];
    if (!info || info.items.length === 0) { alert('该品牌下无商品'); return; }
    currentPanelData = {
        type: 'unifiedBrand',
        group: { suggested_standard: brandName },
        items: info.items
    };
    currentPanelPage = 1;
    currentPanelFilter = '';
    document.getElementById('sidePanelTitle').textContent = `品牌商品: ${brandName} (共${info.count}条)`;
    renderPanelContent();
    document.getElementById('sidePanelOverlay').classList.add('open');
    document.getElementById('sidePanel').classList.add('open');
}

// ===== 无品牌候选操作 =====
function confirmUnbrandedGroup(clusterId) {
    if (!diagnosisData) return;
    const group = diagnosisData.brand_clusters.find(c => c.cluster_id === clusterId);
    if (!group || !group.items) return;
    group.items.forEach(item => {
        const code = String(item.code).trim();
        brandRules[code] = { brand: null, no_brand: true, skipped: false };
    });
    batchSaveRules(group.items.map(item => ({
        code: String(item.code).trim(),
        type: 'no_brand'
    })));
    renderBrandGroups(diagnosisData.brand_clusters);
}

function confirmAllUnbranded() {
    if (!diagnosisData) return;
    const unbrandedClusters = diagnosisData.brand_clusters.filter(c => c.type === 'unbranded');
    if (unbrandedClusters.length === 0) return;
    const allItems = unbrandedClusters.flatMap(c => c.items || []);
    allItems.forEach(item => {
        const code = String(item.code).trim();
        brandRules[code] = { brand: null, no_brand: true, skipped: false };
    });
    batchSaveRules(allItems.map(item => ({
        code: String(item.code).trim(),
        type: 'no_brand'
    })));
    renderBrandGroups(diagnosisData.brand_clusters);
}

function batchSetBrandUnbranded() {
    if (!diagnosisData) return;
    const unbrandedClusters = diagnosisData.brand_clusters.filter(c => c.type === 'unbranded');
    if (unbrandedClusters.length === 0) return;
    if (unbrandedClusters.length > 1) {
        alert('请先点开查看商品进入具体分组');
        return;
    }
    openSidePanel('unbranded', unbrandedClusters[0].cluster_id);
}

// 挂载全局品牌函数
window.buildGlobalBrandIndex = buildGlobalBrandIndex;
window.renderGlobalBrandList = renderGlobalBrandList;
window.filterGlobalBrandList = filterGlobalBrandList;
window.openUnifiedBrandPanel = openUnifiedBrandPanel;
window.confirmAllUnbranded = confirmAllUnbranded;
window.confirmUnbrandedGroup = confirmUnbrandedGroup;
window.batchSetBrandUnbranded = batchSetBrandUnbranded;
window.batchApplySuggestion = batchApplySuggestion;
window.batchSetBrand = batchSetBrand;
window.skipGroup = skipGroup;
window.setItemBrand = setItemBrand;
window.skipItem = skipItem;
window.manageBrandTypes = manageBrandTypes;
window.manageCountries = manageCountries;
window.closeBrandConfigModal = closeBrandConfigModal;
window.renderBrandConfigList = renderBrandConfigList;
window.deleteBrandConfigItem = deleteBrandConfigItem;
window.submitBrandConfigNew = submitBrandConfigNew;
window.selectConfigItem = selectConfigItem;
window.dismissNewBrand = dismissNewBrand;
window.renderBrandGroups = renderBrandGroups;
