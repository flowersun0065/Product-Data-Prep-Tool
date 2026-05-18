// brand-library.js — Brand database management page

async function renderBrandDatabase() {
  var container = document.getElementById('brandDatabaseContent');
  if (!container) return;

  try {
    var res = await fetch('/api/brands/list');
    var data = await res.json();
    var brands = data.brands || {};

    var brandList = Object.entries(brands).sort(function(a, b) {
      return a[0].localeCompare(b[0]);
    });

    var html = '<div class="flex gap-2 mb-3" style="display:flex;gap:8px;align-items:center;margin-bottom:12px;">';
    html += '<input placeholder="搜索品牌名..." oninput="filterBrandTable()" id="brandSearch" style="width:200px;">';
    html += '<select onchange="filterBrandTable()" id="brandTypeFilter">';
    html += '<option value="">全部类型</option>';
    html += '<option value="知名品牌">知名品牌</option>';
    html += '<option value="自有品牌">自有品牌</option>';
    html += '<option value="进口品牌">进口品牌</option>';
    html += '</select>';
    html += '<span style="margin-left:auto;color:var(--text-tertiary);font-size:10px;">共 ' + brandList.length + ' 个品牌</span>';
    html += '<button class="btn btn-primary" onclick="addBrand()" style="font-size:10px;">+ 添加品牌</button>';
    html += '</div>';

    html += '<div class="data-table"><table><thead><tr>';
    html += '<th>标准名</th><th>别名</th><th>类型</th><th>产地</th><th>状态</th><th>操作</th>';
    html += '</tr></thead><tbody id="brandTableBody">';

    brandList.forEach(function(entry) {
      var name = entry[0];
      var info = entry[1];
      var aliases = (info.aliases || []).join(', ');
      html += '<tr data-brand="' + escAttr(name) + '" data-type="' + escAttr(info.type || '') + '">';
      html += '<td style="font-weight:500;">' + esc(name) + '</td>';
      html += '<td style="color:var(--text-secondary);">' + esc(aliases) + '</td>';
      html += '<td><span class="badge ' + (info.type === '自有品牌' ? 'badge-warning' : 'badge-info') + '">' + esc(info.type || '') + '</span></td>';
      html += '<td>' + esc(info.country || 'CN') + '</td>';
      html += '<td>' + (info.confirmed ? '<span class="badge badge-success">已确认</span>' : '<span class="badge badge-warning">待确认</span>') + '</td>';
      html += '<td>';
      html += '<button class="btn btn-ghost" style="padding:2px 6px;font-size:9px;" onclick="editBrand(' + JSON.stringify(name) + ')">编辑</button> ';
      html += '<button class="btn btn-danger" style="padding:2px 6px;font-size:9px;" onclick="deleteBrand(' + JSON.stringify(name) + ')">删除</button>';
      html += '</td></tr>';
    });

    html += '</tbody></table></div>';
    container.innerHTML = html;
  } catch (e) {
    container.innerHTML = '<p style="color:var(--red);">加载失败: ' + e.message + '</p>';
  }
}

function filterBrandTable() {
  var search = (document.getElementById('brandSearch') && document.getElementById('brandSearch').value || '').toLowerCase();
  var type = (document.getElementById('brandTypeFilter') && document.getElementById('brandTypeFilter').value || '');
  var rows = document.querySelectorAll('#brandTableBody tr');
  rows.forEach(function(row) {
    var name = (row.dataset.brand || '').toLowerCase();
    var rowType = row.dataset.type || '';
    var match = (!search || name.indexOf(search) !== -1) && (!type || rowType === type);
    row.classList.toggle('hidden', !match);
  });
}

async function addBrand() {
  var name = prompt('输入新品牌标准名:');
  if (!name) return;
  var type = prompt('品牌类型 (知名品牌 / 自有品牌 / 进口品牌):', '知名品牌');
  var country = prompt('产地代码 (CN/JP/KR/US):', 'CN');
  try {
    await fetch('/api/brands/add', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: name, type: type, country: country }),
    });
    renderBrandDatabase();
  } catch (e) {
    alert('添加失败: ' + e.message);
  }
}

async function editBrand(name) {
  var newType = prompt('修改品牌类型 (知名品牌 / 自有品牌 / 进口品牌):', '');
  if (!newType) return;
  try {
    await fetch('/api/brands/config/type', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: name, type: newType }),
    });
    renderBrandDatabase();
  } catch (e) {
    alert('编辑失败: ' + e.message);
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

// Wire up to navigateTo from sidebar.js
var _origNavigateTo = typeof navigateTo === 'function' ? navigateTo : null;
if (typeof navigateTo === 'function') {
  var origNavigateTo = navigateTo;
  navigateTo = function(page) {
    origNavigateTo(page);
    if (page === 'brand-database') renderBrandDatabase();
  };
}
