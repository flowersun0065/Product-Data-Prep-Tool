// category-tree.js — Category tree management page

var categoryTreeState = {
  expanded: {},
  selectedPath: null,
  searchResults: [],
};

async function renderCategoryTree() {
  var container = document.getElementById('categoryTreeContainer');
  if (!container) return;

  try {
    var params = new URLSearchParams(window.location.search);
    var sid = params.get('sid') || (typeof sessionId !== 'undefined' ? sessionId : '');
    if (!sid) {
      // Try to get from recent session
      var saved = localStorage.getItem('last_session_id');
      if (saved) sid = saved;
    }
    var res = await fetch('/api/diagnosis_result?sid=' + sid);
    var data = await res.json();
    var options = (data.diagnosis && data.diagnosis.category_options) || {};
    var allCodes = (data.diagnosis && data.diagnosis.all_codes) || [];

    // Build path index
    var pathIndex = {};
    allCodes.forEach(function(item) {
      (item.suggested_path || []).forEach(function(p) {
        if (!p) return;
        var key = p.replace(/\s*>\s*/g, ' > ');
        if (!pathIndex[key]) pathIndex[key] = { count: 0, items: [] };
        pathIndex[key].count++;
        pathIndex[key].items.push(item);
      });
    });

    var html = '';

    // Search bar
    html += '<div style="margin-bottom:10px;">';
    html += '<input placeholder="搜索商品名 / 编码 / 关键词..." id="categorySearch" oninput="searchCategory()" style="width:100%;">';
    html += '<div id="searchResults" style="margin-top:6px;"></div>';
    html += '</div>';

    // Tree
    html += '<div style="font-size:10px;line-height:2;" id="categoryTreeNodes">';
    if (options.level1) {
      options.level1.forEach(function(l1) {
        html += renderTreeNode(l1, options, pathIndex, 0, '');
      });
    } else {
      html += '<div style="color:var(--text-tertiary);padding:8px;">暂无分类数据，请先上传文件进行诊断</div>';
    }
    html += '</div>';

    // Right panel
    html += '<div id="categoryDetail" style="border-top:1px solid var(--border-primary);padding-top:10px;margin-top:10px;color:var(--text-tertiary);font-size:10px;">';
    html += '选择左侧分类节点查看详情';
    html += '</div>';

    container.innerHTML = html;
  } catch (e) {
    container.innerHTML = '<p style="color:var(--red);">加载失败: ' + e.message + '</p>';
  }
}

function renderTreeNode(label, options, pathIndex, depth, parentPath) {
  var fullPath = parentPath ? parentPath + ' > ' + label : label;
  var isL1 = depth === 0;
  var children;

  if (isL1) {
    children = options.level2_by_level1 && options.level2_by_level1[label] ? options.level2_by_level1[label] : [];
  } else if (depth === 1) {
    children = options.level3_by_level2 && options.level3_by_level2[fullPath] ? options.level3_by_level2[fullPath] : [];
  } else {
    children = [];
  }

  var count = (pathIndex[fullPath] && pathIndex[fullPath].count) || 0;
  var isExpanded = categoryTreeState.expanded[fullPath] !== false;
  var hasChildren = children && children.length > 0;

  var html = '<div style="padding-left:' + (depth * 14) + 'px;">';

  if (hasChildren || depth < 2) {
    html += '<span style="cursor:pointer;color:' + (isExpanded ? 'var(--green)' : 'var(--yellow)') + ';" onclick="toggleTreeNode(\'' + escAttr(fullPath) + '\')">';
    html += isExpanded ? '▼ ' : '▶ ';
    html += '</span>';
  }

  var isSelected = categoryTreeState.selectedPath === fullPath;
  html += '<span style="cursor:pointer;' + (isSelected ? 'background:rgba(0,122,255,0.08);border-radius:3px;padding:1px 4px;' : '') + '" onclick="selectCategoryNode(\'' + escAttr(fullPath) + '\')">';
  html += esc(label);
  html += ' <span style="color:var(--text-tertiary);font-size:9px;">' + count + '条</span>';
  html += '</span>';
  html += '</div>';

  if (hasChildren && isExpanded) {
    children.forEach(function(child) {
      html += renderTreeNode(child, options, pathIndex, depth + 1, fullPath);
    });
  }

  return html;
}

function toggleTreeNode(path) {
  categoryTreeState.expanded[path] = !categoryTreeState.expanded[path];
  renderCategoryTree();
}

function selectCategoryNode(path) {
  categoryTreeState.selectedPath = path;
  renderCategoryTree();

  var detail = document.getElementById('categoryDetail');
  if (!detail) return;

  detail.innerHTML = '<div style="font-weight:600;margin-bottom:6px;">' + esc(path) + '</div>' +
    '<div class="flex gap-2 mb-3" style="display:flex;gap:8px;margin-bottom:10px;">' +
    '<button class="btn btn-ghost" style="font-size:9px;" onclick="classifyPath(\'' + escAttr(path) + '\',\'standard\')">标记为标准</button>' +
    '<button class="btn btn-ghost" style="font-size:9px;" onclick="classifyPath(\'' + escAttr(path) + '\',\'marketing\')">标记为营销</button>' +
    '</div>';
}

async function classifyPath(path, label) {
  try {
    await fetch('/api/classify/path', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: path, label: label }),
    });
    selectCategoryNode(path);
  } catch (e) {
    alert('标记失败: ' + e.message);
  }
}

async function searchCategory() {
  var query = document.getElementById('categorySearch');
  var container = document.getElementById('searchResults');
  if (!container || !query) return;
  var q = query.value.trim();
  if (!q || q.length < 2) { container.innerHTML = ''; return; }

  try {
    var res = await fetch('/api/suggest_category', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ product_name: q }),
    });
    var data = await res.json();
    if (data.suggested_path) {
      container.innerHTML = '<div style="font-size:9px;color:var(--text-secondary);">建议路径: ' + esc(data.suggested_path || '') + '</div>';
    } else {
      container.innerHTML = '<div style="font-size:9px;color:var(--text-tertiary);">未找到匹配</div>';
    }
  } catch (e) {
    container.innerHTML = '';
  }
}

// Wire up to navigateTo
if (typeof navigateTo === 'function') {
  var _origNavigateTo2 = navigateTo;
  navigateTo = function(page) {
    _origNavigateTo2(page);
    if (page === 'category-tree') renderCategoryTree();
  };
}
