// brand-library.js — 品牌数据库管理页
var _brandDB = [];
var _brandConfig = { types: [], countries: [] };

async function renderBrandDatabase() {
  var container = document.getElementById('brandDatabaseContent');
  if (!container) return;
  container.textContent = '';

  try {
    var res = await fetch('/api/brands/list');
    var data = await res.json();
    _brandDB = data.brands || [];
    var configRes = await fetch('/api/brands/config');
    _brandConfig = await configRes.json();

    _brandDB.sort(function(a, b) { return (a.name || '').localeCompare(b.name || ''); });

    var types = _brandConfig.brand_types || [];
    var typesSet = {};
    _brandDB.forEach(function(b) { if (b.type) typesSet[b.type] = true; });
    var allTypes = Object.keys(typesSet);

    // ── 工具栏：搜索 + 类型过滤 + 计数 + 添加按钮 ──
    var toolbar = document.createElement('div');
    toolbar.style.cssText = 'display:flex;gap:8px;align-items:center;margin-bottom:12px;flex-wrap:wrap;';

    var searchInput = document.createElement('input');
    searchInput.id = 'brandSearch';
    searchInput.placeholder = '搜索品牌名...';
    searchInput.className = 'search-input';
    searchInput.style.width = '200px';
    searchInput.addEventListener('input', function() { filterBrandTable(); });
    toolbar.appendChild(searchInput);

    var typeFilter = document.createElement('select');
    typeFilter.id = 'brandTypeFilter';
    typeFilter.className = 'search-input';
    typeFilter.style.width = 'auto';
    typeFilter.addEventListener('change', function() { filterBrandTable(); });
    var optAll = document.createElement('option');
    optAll.value = '';
    optAll.textContent = '全部类型';
    typeFilter.appendChild(optAll);
    allTypes.forEach(function(t) {
      var opt = document.createElement('option');
      opt.value = t;
      opt.textContent = t;
      typeFilter.appendChild(opt);
    });
    toolbar.appendChild(typeFilter);

    var countSpan = document.createElement('span');
    countSpan.style.cssText = 'margin-left:auto;color:var(--text-muted);font-size:11px;';
    countSpan.textContent = '共 ' + _brandDB.length + ' 个品牌';
    toolbar.appendChild(countSpan);

    var addBtn = document.createElement('button');
    addBtn.className = 'btn-agent primary';
    addBtn.textContent = '+ 添加品牌';
    addBtn.addEventListener('click', function() { addBrand(); });
    toolbar.appendChild(addBtn);

    container.appendChild(toolbar);

    // ── 表格 ──
    var tableWrap = document.createElement('div');
    tableWrap.style.overflowX = 'auto';

    var table = document.createElement('table');
    table.style.cssText = 'width:100%;border-collapse:collapse;font-size:12px;';

    var thead = document.createElement('thead');
    var headerRow = document.createElement('tr');
    headerRow.style.borderBottom = '1px solid var(--border-light)';
    var headers = ['标准名', '别名', '类型', '产地', '主/子品牌', '操作'];
    headers.forEach(function(h) {
      var th = document.createElement('th');
      th.style.cssText = 'text-align:left;padding:8px 6px;';
      th.textContent = h;
      headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);
    table.appendChild(thead);

    var tbody = document.createElement('tbody');
    tbody.id = 'brandTableBody';

    _brandDB.forEach(function(b) {
      var row = document.createElement('tr');
      row.dataset.brand = b.name;
      row.dataset.type = b.type || '';
      row.style.borderBottom = '1px solid var(--border-light)';

      // 标准名
      var tdName = document.createElement('td');
      tdName.style.cssText = 'padding:8px 6px;font-weight:500;';
      tdName.textContent = b.display_name || b.name;
      row.appendChild(tdName);

      // 别名
      var aliases = (b.aliases || []).filter(function(a) { return a !== b.name && a !== b.display_name; }).join(', ');
      var tdAlias = document.createElement('td');
      tdAlias.style.cssText = 'padding:8px 6px;color:var(--text-sub);max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;';
      tdAlias.textContent = aliases;
      row.appendChild(tdAlias);

      // 类型
      var tdType = document.createElement('td');
      tdType.style.padding = '8px 6px';
      var typeBadge = document.createElement('span');
      typeBadge.className = 'badge';
      typeBadge.style.cssText = 'background:var(--surface);padding:2px 8px;border-radius:10px;font-size:10px;';
      typeBadge.textContent = b.type || '';
      tdType.appendChild(typeBadge);
      row.appendChild(tdType);

      // 产地
      var tdCountry = document.createElement('td');
      tdCountry.style.padding = '8px 6px';
      tdCountry.textContent = b.country || '—';
      row.appendChild(tdCountry);

      // 主/子品牌
      var tdSub = document.createElement('td');
      tdSub.style.padding = '8px 6px';
      if (b.sub_brands && b.sub_brands.length > 0) {
        var subSpan = document.createElement('span');
        subSpan.style.color = 'var(--accent)';
        subSpan.textContent = b.sub_brands.length + '个子品牌';
        tdSub.appendChild(subSpan);
      } else if (b.parent_brand) {
        var parentSpan = document.createElement('span');
        parentSpan.style.color = 'var(--text-muted)';
        parentSpan.textContent = '主品牌: ' + b.parent_brand;
        tdSub.appendChild(parentSpan);
      } else {
        var dashSpan = document.createElement('span');
        dashSpan.style.color = 'var(--text-muted)';
        dashSpan.textContent = '—';
        tdSub.appendChild(dashSpan);
      }
      row.appendChild(tdSub);

      // 操作
      var tdAction = document.createElement('td');
      tdAction.style.padding = '8px 6px';

      var editBtn = document.createElement('button');
      editBtn.className = 'btn-agent primary';
      editBtn.textContent = '编辑';
      editBtn.addEventListener('click', (function(n) { return function() { editBrand(n); }; })(b.name));
      tdAction.appendChild(editBtn);

      var delBtn = document.createElement('button');
      delBtn.className = 'btn-agent secondary';
      delBtn.style.color = 'var(--red)';
      delBtn.textContent = '删除';
      delBtn.addEventListener('click', (function(n) { return function() { deleteBrand(n); }; })(b.name));
      tdAction.appendChild(delBtn);

      row.appendChild(tdAction);
      tbody.appendChild(row);
    });

    table.appendChild(tbody);
    tableWrap.appendChild(table);
    container.appendChild(tableWrap);
  } catch (e) {
    var errEl = document.createElement('p');
    errEl.style.cssText = 'color:var(--red);padding:20px;';
    errEl.textContent = '加载失败: ' + e.message;
    container.appendChild(errEl);
  }
}

function filterBrandTable() {
  var searchEl = document.getElementById('brandSearch');
  var typeEl = document.getElementById('brandTypeFilter');
  var search = (searchEl && searchEl.value || '').toLowerCase();
  var type = (typeEl && typeEl.value || '');
  var rows = document.querySelectorAll('#brandTableBody tr');
  rows.forEach(function(row) {
    var name = (row.dataset.brand || '').toLowerCase();
    var rowType = row.dataset.type || '';
    var match = (!search || name.indexOf(search) !== -1) && (!type || rowType === type);
    row.style.display = match ? '' : 'none';
  });
}

function addBrand() {
  if (typeof openAddBrandModal === 'function') {
    openAddBrandModal(null, 'sidebar', {});
    window._brandLibRefresh = true;
  } else {
    alert('添加品牌功能不可用');
  }
}

function editBrand(name) {
  var b = _brandDB.find(function(item) { return item.name === name; });
  if (!b) return;
  if (typeof openAddBrandModal === 'function') {
    openAddBrandModal(null, 'sidebar', {
      name: b.display_name || b.name,
      type: b.type || '',
      country: b.country || 'CN',
      parent_brand: b.parent_brand || '',
      relation_type: b.relation_type || ''
    });
  } else {
    alert('编辑品牌功能不可用');
  }
}

async function deleteBrand(name) {
  if (!confirm('确定删除品牌 "' + name + '"？')) return;
  try {
    await fetch('/api/brands/config', {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: name }),
    });
    renderBrandDatabase();
  } catch (e) {
    alert('删除失败: ' + e.message);
  }
}

// Hook submitNewBrandFromModal to refresh our table after add/edit
var _origSubmit = null;
if (typeof submitNewBrandFromModal !== 'undefined') {
  _origSubmit = submitNewBrandFromModal;
  submitNewBrandFromModal = async function() {
    await _origSubmit();
    if (typeof renderBrandDatabase === 'function') {
      setTimeout(function() { renderBrandDatabase(); }, 500);
    }
  };
}

// ── 品牌修正记录页 ──
async function _renderBrandCorrectionsPage() {
  var container = document.getElementById('brandCorrectionsContent');
  if (!container) return;
  container.textContent = '';

  try {
    var res = await fetch('/api/correction/brand');
    var list = await res.json();
    if (!list || list.length === 0) {
      var emptyEl = document.createElement('p');
      emptyEl.style.cssText = 'color:var(--text-muted);padding:40px;text-align:center;';
      emptyEl.textContent = '暂无品牌修正记录';
      container.appendChild(emptyEl);
      return;
    }

    var header = document.createElement('div');
    header.style.cssText = 'font-size:12px;font-weight:600;color:var(--text-main);margin-bottom:12px;';
    header.textContent = '共 ' + list.length + ' 条修正记录';
    container.appendChild(header);

    list.forEach(function(e) {
      var suggested = e[0];
      var info = e[1];

      var entry = document.createElement('div');
      entry.style.cssText = 'padding:8px 0;border-bottom:1px solid var(--border-light);';

      var row = document.createElement('div');
      row.style.cssText = 'display:flex;gap:12px;align-items:center;';

      var oldSpan = document.createElement('span');
      oldSpan.style.cssText = 'color:var(--text-muted);text-decoration:line-through;font-size:12px;';
      oldSpan.textContent = suggested;
      row.appendChild(oldSpan);

      var arrow = document.createElement('span');
      arrow.style.color = 'var(--text-muted)';
      arrow.textContent = '→';
      row.appendChild(arrow);

      var newSpan = document.createElement('span');
      newSpan.style.cssText = 'color:var(--text-main);font-weight:500;font-size:12px;';
      newSpan.textContent = info.corrected_to || '';
      row.appendChild(newSpan);

      var countSpan = document.createElement('span');
      countSpan.style.cssText = 'margin-left:auto;color:var(--text-muted);font-size:10px;';
      countSpan.textContent = (info.count || 1) + '次';
      row.appendChild(countSpan);

      entry.appendChild(row);
      container.appendChild(entry);
    });
  } catch(e) {
    var errEl = document.createElement('p');
    errEl.style.cssText = 'color:var(--red);padding:20px;';
    errEl.textContent = '加载失败: ' + e.message;
    container.appendChild(errEl);
  }
}

// Exports
window.renderBrandDatabase = renderBrandDatabase;
window.filterBrandTable = filterBrandTable;
window.addBrand = addBrand;
window.editBrand = editBrand;
window.deleteBrand = deleteBrand;
