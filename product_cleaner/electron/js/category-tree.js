// category-tree.js — Electron Category Path Tree (native.css design system)
var _pgShowMkt = true;
var _pgLastActivePath = null;
var _pgClassified = {};

function esc(s) { return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
function escAttr(s) { return String(s||'').replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/'/g,'&#39;'); }

async function renderCategoryTreePage() {
  var container = document.getElementById('pageCateTreeContainer');
  if (!container) return;
  var diag = window.diagnosisData;
  if (!diag || !diag.category_options || !diag.category_options.level1) {
    container.textContent = '';
    var empty = document.createElement('p');
    empty.style.cssText = 'color:var(--text-muted);padding:40px;text-align:center;font-size:13px;';
    empty.textContent = '暂无分类数据，请先上传文件进行诊断';
    container.appendChild(empty);
    return;
  }
  var options = diag.category_options;
  var pathClass = diag.path_classifications || {};
  try { var cr = await fetch('/api/classified_paths'); _pgClassified = ((await cr.json()).classified_paths) || {}; } catch(e) {}

  var pathIndex = {};
  (diag.all_codes || []).forEach(function(item) {
    (item.suggested_path || []).forEach(function(p) {
      if (!p) return;
      var key = p.replace(/\s*>\s*/g, ' > ');
      if (!pathIndex[key]) pathIndex[key] = { count: 0, items: [] };
      pathIndex[key].count++;
      pathIndex[key].items.push(item);
    });
  });

  function _buildTreeNode(name, indentClass, bold) {
    var node = document.createElement('div');
    node.className = 'tree-node';

    var row = document.createElement('div');
    row.className = 'tree-node-row ' + indentClass;
    row.style.cursor = 'pointer';
    row.onclick = function() {
      var t = this, n = t.nextElementSibling;
      if (n) n.classList.toggle('hidden');
      var a = t.querySelector('.arrow-icon');
      if (a) a.classList.toggle('collapsed');
    };

    var left = document.createElement('div'); left.className = 'node-left-part';
    var arrow = document.createElement('span'); arrow.className = 'arrow-icon';
    arrow.textContent = '';
    var _as = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    _as.setAttribute('width', '10'); _as.setAttribute('height', '10');
    _as.setAttribute('viewBox', '0 0 24 24'); _as.setAttribute('fill', 'none');
    _as.setAttribute('stroke', 'currentColor'); _as.setAttribute('stroke-width', '3');
    var _ap = document.createElementNS('http://www.w3.org/2000/svg', 'polyline');
    _ap.setAttribute('points', '6 9 12 15 18 9');
    _as.appendChild(_ap); arrow.appendChild(_as);
    left.appendChild(arrow);
    var nameSpan = document.createElement('span'); nameSpan.className = 'node-name';
    if (bold) nameSpan.style.fontWeight = '600';
    nameSpan.textContent = name;
    left.appendChild(nameSpan);
    row.appendChild(left);

    var right = document.createElement('div'); right.className = 'node-right-actions';
    row.appendChild(right);
    node.appendChild(row);
    return node;
  }

  function _appendMiniBadge(parent, label, aiLabel, count, processed) {
    var span = document.createElement('span'); span.className = 'mini-badge';
    if (label === 'marketing') { span.className += ' muted'; span.textContent = '已标记营销 0条'; }
    else if (label === 'standard') { span.className += ' grn'; span.textContent = '已标记标准 ' + count + '条'; }
    else if (aiLabel === 'marketing') { span.className += ' org'; span.textContent = '算法:营销 ' + count + '条'; }
    else { span.className += ' grn'; span.textContent = '算法:标准 ' + count + '条'; }
    parent.appendChild(span);
  }

  function _appendStatusBadge(parent, count, processed) {
    var remaining = count - processed;
    if (count === 0) {
      var s = document.createElement('span'); s.className = 'mini-badge muted'; s.textContent = '无商品'; parent.appendChild(s);
    } else if (remaining > 0) {
      var s = document.createElement('span'); s.className = 'mini-badge org'; s.textContent = '待处理 ' + remaining + '/' + count; parent.appendChild(s);
    }
  }

  container.textContent = '';

  var fragment = document.createDocumentFragment();

  options.level1.forEach(function(l1) {
    var l2s = options.level2_by_level1[l1] || [];
    var l1Node = _buildTreeNode(l1, 'indent-1', true/*bold*/);
    var l1Children = document.createElement('div');
    l1Children.className = 'tree-children';
    var hasL2 = false;

    l2s.forEach(function(l2) {
      var l3s = options.level3_by_level2[l1 + ' > ' + l2] || [];
      var l2Node = _buildTreeNode(l2, 'indent-2', false/*not bold*/);
      var l2Children = document.createElement('div');
      l2Children.className = 'tree-children';
      var hasL3 = false;

      // L2 summary badge
      var l2total = 0, l2proc = 0;
      l3s.forEach(function(l3p) {
        var pi = pathIndex[l1 + ' > ' + l2 + ' > ' + l3p] || {count:0,items:[]};
        l2total += pi.count;
        l2proc += pi.items.filter(function(i){return window.categoryRules&&window.categoryRules[i.code];}).length;
      });
      if (l2total > 0) {
        var l2rem = l2total - l2proc;
        var l2badge = document.createElement('span'); l2badge.className = 'node-inline-badges';
        var mb = document.createElement('span');
        mb.className = 'mini-badge ' + (l2rem > 0 ? 'org' : 'grn');
        mb.textContent = l2rem > 0 ? '待处理 ' + l2rem + '/' + l2total : l2total + '条';
        l2badge.appendChild(mb);
        var l2Left = l2Node.querySelector('.node-left-part');
        if (l2Left) l2Left.appendChild(l2badge);
      }

      // L2 batch buttons
      var l2Right = l2Node.querySelector('.node-right-actions');
      if (l2Right) {
        l2Right.onclick = function(e) { e.stopPropagation(); };
      }

      l3s.forEach(function(l3) {
        var path = l1 + ' > ' + l2 + ' > ' + l3;
        var info = pathIndex[path];
        var count = info ? info.count : 0;
        var processed = info ? info.items.filter(function(i) { return window.categoryRules && window.categoryRules[i.code]; }).length : 0;
        var label = _pgClassified[path];
        var aiLabel = pathClass[path] && pathClass[path].label;
        var isMkt = label === 'marketing' || aiLabel === 'marketing';
        if (!_pgShowMkt && isMkt) return;

        var l3Row = document.createElement('div');
        l3Row.className = 'tree-node-row indent-3' + (_pgLastActivePath === path ? ' active' : '');
        l3Row.dataset.path = path;

        var l3Left = document.createElement('div'); l3Left.className = 'node-left-part';
        var l3Name = document.createElement('span'); l3Name.className = 'node-name child'; l3Name.textContent = l3;
        l3Left.appendChild(l3Name);

        var l3Badges = document.createElement('span'); l3Badges.className = 'node-inline-badges';
        _appendMiniBadge(l3Badges, label, aiLabel, count, processed);
        _appendStatusBadge(l3Badges, count, processed);
        l3Left.appendChild(l3Badges);
        l3Row.appendChild(l3Left);

        var l3Right = document.createElement('div'); l3Right.className = 'node-right-actions';
        if (count > 0) {
          var viewBtn = document.createElement('button'); viewBtn.className = 'btn-agent primary'; viewBtn.textContent = '查看';
          viewBtn.onclick = (function(p) { return function() { _openCategoryProductPanel(p); }; })(path);
          l3Right.appendChild(viewBtn);
        }
        var mktBtn = document.createElement('button'); mktBtn.className = 'btn-agent secondary'; mktBtn.textContent = '标记营销';
        mktBtn.onclick = (function(p) { return function() { classifyPathPage(p, 'marketing'); }; })(path);
        l3Right.appendChild(mktBtn);
        var stdBtn = document.createElement('button'); stdBtn.className = 'btn-agent secondary'; stdBtn.textContent = '标记标准';
        stdBtn.onclick = (function(p) { return function() { classifyPathPage(p, 'standard'); }; })(path);
        l3Right.appendChild(stdBtn);
        l3Row.appendChild(l3Right);

        l2Children.appendChild(l3Row);
        hasL3 = true;
      });

      if (!hasL3) return;
      // L2 batch buttons
      var mktB = document.createElement('button'); mktB.className = 'btn-agent secondary'; mktB.textContent = '批量营销';
      mktB.onclick = function() { batchClassifyPathPage(l1, l2, 'marketing'); };
      l2Right.appendChild(mktB);
      var stdB = document.createElement('button'); stdB.className = 'btn-agent secondary'; stdB.textContent = '批量标准';
      stdB.onclick = function() { batchClassifyPathPage(l1, l2, 'standard'); };
      l2Right.appendChild(stdB);

      l2Node.appendChild(l2Children);
      l1Children.appendChild(l2Node);
      hasL2 = true;
    });

    if (!hasL2) return;
    // L1 batch buttons
    var l1Right = l1Node.querySelector('.node-right-actions');
    if (l1Right) {
      l1Right.onclick = function(e) { e.stopPropagation(); };
      var m1 = document.createElement('button'); m1.className = 'btn-agent secondary'; m1.textContent = '批量营销';
      m1.onclick = function() { batchClassifyPathPage(l1, '', 'marketing'); };
      l1Right.appendChild(m1);
      var s1 = document.createElement('button'); s1.className = 'btn-agent secondary'; s1.textContent = '批量标准';
      s1.onclick = function() { batchClassifyPathPage(l1, '', 'standard'); };
      l1Right.appendChild(s1);
    }

    l1Node.appendChild(l1Children);
    fragment.appendChild(l1Node);
  });

  if (!fragment.childNodes.length) {
    var empty = document.createElement('p');
    empty.style.cssText = 'color:var(--text-muted);padding:40px;text-align:center;font-size:13px;';
    empty.textContent = '暂无分类数据';
    container.appendChild(empty);
  } else {
    container.appendChild(fragment);
  }

  // Auto-expand + scroll to last active path
  if (_pgLastActivePath && container) {
    var l3Row = container.querySelector('[data-path="' + _pgLastActivePath.replace(/"/g, '&quot;') + '"]');
    if (l3Row) {
      var l2Node = l3Row.closest('.tree-node');
      var l1Node = l2Node ? l2Node.parentElement.closest('.tree-node') : null;
      [l1Node, l2Node].forEach(function(node) {
        if (node) {
          var children = node.querySelector('.tree-children');
          if (children && children.classList.contains('hidden')) {
            children.classList.remove('hidden');
            var arrow = node.querySelector('.arrow-icon');
            if (arrow) arrow.classList.remove('collapsed');
          }
        }
      });
      l3Row.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }
}

function filterCategoryTreePage(text) {
  var container = document.getElementById('pageCateTreeContainer');
  if (!container) return;
  var lower = (text || '').toLowerCase();
  container.querySelectorAll('.tree-node-row[data-path]').forEach(function(row) {
    row.style.display = row.textContent.toLowerCase().indexOf(lower) !== -1 ? '' : 'none';
  });
  // Also filter L2 and L1 nodes
  container.querySelectorAll('.tree-node').forEach(function(node) {
    var visible = node.querySelector('.tree-node-row[data-path]:not([style*="display: none"])');
    var headerRow = node.querySelector('.tree-node-row:not([data-path])');
    if (headerRow) headerRow.style.display = visible ? '' : 'none';
  });
}

var _pgSearchMatches = null;
var _pgSearchPage = 0;
var PG_PAGE_SIZE = 50;

function searchProductPage(query) {
  var container = document.getElementById('pageProductSearchResults');
  if (!container) return;
  var raw = (query || '').trim();
  if (!raw || raw.length < 2) {
    container.style.display = 'none';
    _pgSearchMatches = null;
    return;
  }
  var lower = raw.toLowerCase();
  var keywords = lower.split(/\s+/).filter(function(k) { return k.length > 0; });
  var codes = (window.diagnosisData && window.diagnosisData.all_codes) || [];
  var seen = {};
  var matches = [];
  codes.forEach(function(item) {
    var key = item.code || item.name || '';
    if (seen[key]) return;
    seen[key] = true;
    var name = (item.name || '').toLowerCase();
    var code = (item.code || '').toLowerCase();
    if (name.indexOf(lower) !== -1 || code.indexOf(lower) !== -1) { matches.push(item); return; }
    if (keywords.length > 1 && keywords.every(function(kw) { return name.indexOf(kw) !== -1 || code.indexOf(kw) !== -1; })) {
      matches.push(item);
    }
  });
  if (matches.length === 0) {
    container.textContent = '';
    var empty = document.createElement('div');
    empty.style.cssText = 'color:var(--text-muted);font-size:11px;padding:8px;text-align:center;';
    empty.textContent = '未找到匹配商品';
    container.appendChild(empty);
    container.style.display = 'block';
    _pgSearchMatches = null;
    return;
  }
  _pgSearchMatches = matches;
  _pgSearchPage = 0;
  _renderSearchPage(container);
  container.style.display = 'block';
}

function _renderSearchPage(container) {
  var matches = _pgSearchMatches || [];
  var page = _pgSearchPage || 0;
  var total = matches.length;
  var end = Math.min((page + 1) * PG_PAGE_SIZE, total);
  var pageItems = matches.slice(0, end);
  var hasMore = end < total;

  container.textContent = '';

  // Count bar
  var bar = document.createElement('div');
  bar.style.cssText = 'display:flex;justify-content:space-between;padding:4px 0;font-size:10px;color:var(--text-muted);border-bottom:1px solid var(--border-light);';
  var s1 = document.createElement('span'); s1.textContent = '共 ' + total + ' 个匹配'; bar.appendChild(s1);
  var s2 = document.createElement('span'); s2.textContent = '已显示 ' + end + ' 个'; bar.appendChild(s2);
  container.appendChild(bar);

  // Items
  pageItems.forEach(function(item) {
    var p = item.suggested_path ? item.suggested_path[0] : '';
    var row = document.createElement('div');
    row.className = 'tree-node-row';
    row.style.cssText = 'cursor:pointer;border-bottom:1px solid var(--border-light);';
    row.onclick = (function(path) { return function() { _openCategoryProductPanel(path); }; })(p);

    var left = document.createElement('div'); left.className = 'node-left-part';
    var nameSpan = document.createElement('span'); nameSpan.className = 'node-name child'; nameSpan.style.flex = '1';
    nameSpan.textContent = item.name || '';
    left.appendChild(nameSpan);
    var codeSpan = document.createElement('span');
    codeSpan.style.cssText = 'font-size:10px;color:var(--text-muted);font-family:var(--font-mono);';
    codeSpan.textContent = String(item.code || '');
    left.appendChild(codeSpan);
    if (p) {
      var pathSpan = document.createElement('span');
      pathSpan.style.cssText = 'font-size:10px;color:var(--accent);margin-left:8px;';
      pathSpan.textContent = p;
      left.appendChild(pathSpan);
    }
    row.appendChild(left);
    container.appendChild(row);
  });

  // Load more
  if (hasMore) {
    var moreBtn = document.createElement('button');
    moreBtn.style.cssText = 'width:100%;padding:6px;border:none;background:transparent;color:var(--accent);font-size:12px;cursor:pointer;border-radius:var(--radius-sm);';
    moreBtn.textContent = '加载更多（' + (total - end) + ' 条）';
    moreBtn.onclick = function() { _loadMoreSearchResults(this); };
    container.appendChild(moreBtn);
  }
}

function _loadMoreSearchResults(btn) {
  var container = document.getElementById('pageProductSearchResults');
  if (!container) return;
  _pgSearchPage = (_pgSearchPage || 0) + 1;
  _renderSearchPage(container);
}

function toggleMarketingPage() {
  _pgShowMkt = !_pgShowMkt;
  var btn = document.getElementById('pageToggleMktBtn');
  if (btn) btn.textContent = _pgShowMkt ? '隐藏营销' : '显示营销';
  renderCategoryTreePage();
}

async function classifyPathPage(path, label) {
  try {
    await fetch('/api/classify/path', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ path, label }) });
    if (label === 'marketing' && window.diagnosisData) {
      var normalized = path.replace(/\s*>\s*/g, ' > ');
      (window.diagnosisData.all_codes || []).forEach(function(item) {
        (item.suggested_path || []).forEach(function(sp, idx) {
          if (sp.replace(/\s*>\s*/g, ' > ') === normalized) { item.suggested_path.splice(idx, 1); }
        });
        if (!item.suggested_path || item.suggested_path.length === 0) {
          item.suggested_path = [];
          item._section = 'missing';
        }
      });
    }
    _pgLastActivePath = path;
    await renderCategoryTreePage();
  } catch(e) { console.error('分类标记失败:', e); }
}

async function batchClassifyPathPage(l1, l2, label) {
  var options = (window.diagnosisData && window.diagnosisData.category_options) || window.categoryOptions;
  if (!options) return;
  var paths = [];
  if (l2) {
    var l3s = options.level3_by_level2[l1 + ' > ' + l2] || [];
    l3s.forEach(function(l3) { paths.push(l1 + ' > ' + l2 + ' > ' + l3); });
  } else {
    var l2s = options.level2_by_level1[l1] || [];
    l2s.forEach(function(l2name) {
      var l3list = options.level3_by_level2[l1 + ' > ' + l2name] || [];
      l3list.forEach(function(l3) { paths.push(l1 + ' > ' + l2name + ' > ' + l3); });
    });
  }
  if (paths.length === 0) return;
  try {
    await fetch('/api/classify/path/batch', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ paths: paths, label: label }) });
    if (label === 'marketing' && window.diagnosisData) {
      var normalizedPaths = {};
      paths.forEach(function(p) { normalizedPaths[p.replace(/\s*>\s*/g, ' > ')] = true; });
      (window.diagnosisData.all_codes || []).forEach(function(item) {
        if (!item.suggested_path) return;
        item.suggested_path = item.suggested_path.filter(function(sp) {
          return !normalizedPaths[sp.replace(/\s*>\s*/g, ' > ')];
        });
        if (item.suggested_path.length === 0) item._section = 'missing';
      });
    }
    _pgLastActivePath = l1 + (l2 ? ' > ' + l2 : '');
    await renderCategoryTreePage();
  } catch(e) { console.error('批量标记失败:', e); }
}

async function _renderClassifyPage() {
  var container = document.getElementById('categoryClassifyContent');
  if (!container) return;
  try {
    var r = await fetch('/api/classified_paths');
    var data = await r.json();
    var paths = data.classified_paths || {};
    var entries = Object.entries(paths);

    container.textContent = '';
    if (entries.length === 0) {
      var empty = document.createElement('p');
      empty.style.cssText = 'color:var(--text-muted);padding:40px;text-align:center;font-size:13px;';
      empty.textContent = '暂无已标记的分类路径';
      container.appendChild(empty);
      return;
    }

    var header = document.createElement('div');
    header.style.cssText = 'font-size:12px;font-weight:600;color:var(--text-main);margin-bottom:10px;';
    header.textContent = '共 ' + entries.length + ' 个已标记路径';
    container.appendChild(header);

    entries.forEach(function(e) {
      var path = e[0], label = e[1];
      var row = document.createElement('div');
      row.className = 'nav-item';
      row.style.cssText = 'padding:6px 8px;margin-bottom:2px;';

      var nameSpan = document.createElement('span');
      nameSpan.style.cssText = 'flex:1;font-size:12px;';
      nameSpan.textContent = path;
      row.appendChild(nameSpan);

      var badge = document.createElement('span');
      badge.className = 'mini-badge ' + (label === 'marketing' ? 'org' : 'grn');
      badge.style.marginLeft = '8px';
      badge.textContent = label === 'marketing' ? '营销' : '标准';
      row.appendChild(badge);

      var delBtn = document.createElement('button');
      delBtn.className = 'btn-agent secondary';
      delBtn.style.cssText = 'color:var(--red);margin-left:12px;font-size:11px;';
      delBtn.textContent = '删除';
      delBtn.onclick = (function(p) { return function() { _deleteClassifyPage(p); }; })(path);
      row.appendChild(delBtn);

      container.appendChild(row);
    });
  } catch(e) {
    container.textContent = '';
    var err = document.createElement('p');
    err.style.cssText = 'color:var(--red);padding:20px;';
    err.textContent = '加载失败: ' + e.message;
    container.appendChild(err);
  }
}

async function _deleteClassifyPage(path) {
  try {
    await fetch('/api/classify/path', { method: 'DELETE', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ path: path }) });
    _renderClassifyPage();
    if (typeof renderCategoryTreePage === 'function') renderCategoryTreePage();
  } catch(e) { alert('删除失败: ' + e.message); }
}

// ── Open category product list as panel card ──
function _openCategoryProductPanel(path) {
  var allCodes = (window.diagnosisData && window.diagnosisData.all_codes) || [];
  var items = [];
  allCodes.forEach(function(item) {
    (item.suggested_path || []).forEach(function(sp) {
      if (sp && sp.replace(/\s*>\s*/g, ' > ') === path) items.push(item);
    });
  });
  if (!items.length) { alert('该路径下无商品'); return; }
  window._emOpenCategoryProductList(path, { items: items, count: items.length });
}

// Exports
window.renderCategoryTreePage = renderCategoryTreePage;
window.filterCategoryTreePage = filterCategoryTreePage;
window.searchProductPage = searchProductPage;
window.toggleMarketingPage = toggleMarketingPage;
window.classifyPathPage = classifyPathPage;
window.batchClassifyPathPage = batchClassifyPathPage;
