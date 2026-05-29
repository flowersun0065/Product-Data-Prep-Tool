// variety_words.js — 词库管理页（两层分组：类别 → 分组 → 词条）
var _lexiconCategories = [];
var _lexiconSubgroups = [];
var _lexiconSelected = null;
var _lexiconSubgroup = null;
var _lexiconLastAdded = null;

function renderVarietyWords() {
  var container = document.getElementById('varietyWordsContent');
  if (!container) return;
  _injectFlashStyle();
  _buildShell(container);
  _loadCategories();
}

function _injectFlashStyle() {
  if (document.getElementById('lexicon-flash-style')) return;
  var style = document.createElement('style');
  style.id = 'lexicon-flash-style';
  style.textContent = '@keyframes lexicon-flash { 0% { background:var(--green);border-color:var(--green);color:#fff; } 100% { background:var(--surface);border-color:var(--border);color:inherit; } }';
  document.head.appendChild(style);
}

function _buildShell(container) {
  if (document.getElementById('lexiconCategoryTabs')) return;
  container.textContent = '';

  var header = document.createElement('div');
  header.id = 'lexiconHeader';
  header.style.cssText = 'display:flex;gap:4px;align-items:center;margin-bottom:10px;';
  container.appendChild(header);

  var tabs = document.createElement('div');
  tabs.id = 'lexiconCategoryTabs';
  tabs.style.cssText = 'display:flex;gap:4px;margin-bottom:12px;flex-wrap:wrap;';
  container.appendChild(tabs);

  var main = document.createElement('div');
  main.id = 'lexiconMain';
  main.style.cssText = 'display:flex;gap:8px;flex:1;min-height:0;';
  container.appendChild(main);
}

/* ── Data loading ── */

async function _loadCategories() {
  try {
    var res = await fetch('/api/lexicon_words/categories');
    var data = await res.json();
    _lexiconCategories = data.categories || [];
  } catch(e) { _lexiconCategories = []; }
  if (!_lexiconSelected && _lexiconCategories.length) {
    _lexiconSelected = _lexiconCategories[0].key;
  }
  _renderHeader();
  _renderCategoryTabs();
  _loadSubgroups();
}

async function _loadSubgroups() {
  if (!_lexiconSelected) return;
  _lexiconSubgroups = [];
  _lexiconSubgroup = null;
  try {
    var res = await fetch('/api/lexicon_words?category=' + encodeURIComponent(_lexiconSelected));
    var data = await res.json();
    _lexiconSubgroups = data.subgroups || [];
    _lexiconSubgroups._category = _lexiconSelected;
    if (_lexiconSubgroups.length) _lexiconSubgroup = _lexiconSubgroups[0].subgroup;
  } catch(e) {}
  _renderSubgroupList();
  _renderTagPanel();
}

/* ── Render: header + category tabs ── */

function _renderHeader() {
  var el = document.getElementById('lexiconHeader');
  if (!el) return;
  el.textContent = '';
  var totalAll = 0;
  _lexiconCategories.forEach(function(c) { totalAll += c.count; });

  var title = document.createElement('span');
  title.style.cssText = 'font-size:12px;font-weight:600;color:var(--text-main);';
  title.textContent = '词库管理';
  el.appendChild(title);

  var stats = document.createElement('span');
  stats.style.cssText = 'color:var(--text-muted);font-size:10px;';
  stats.textContent = '(' + _lexiconCategories.length + '个类别，' + totalAll + '个词)';
  el.appendChild(stats);
}

function _renderCategoryTabs() {
  var el = document.getElementById('lexiconCategoryTabs');
  if (!el) return;
  el.textContent = '';

  _lexiconCategories.forEach(function(c) {
    var btn = document.createElement('button');
    var isSel = c.key === _lexiconSelected;
    btn.style.cssText = 'padding:3px 8px;border-radius:10px;border:1px solid;font-size:10px;cursor:pointer;'
      + (isSel ? 'background:var(--accent);color:#fff;border-color:var(--accent);'
              : 'background:var(--surface);color:var(--text-main);border-color:var(--border);');
    btn.textContent = c.label + ' ' + c.count;
    btn.onclick = (function(k) { return function() { selectLexiconCategory(k); }; })(c.key);
    el.appendChild(btn);
  });
}

/* ── Render: subgroup list (left panel) ── */

function _renderSubgroupList() {
  var main = document.getElementById('lexiconMain');
  if (!main) return;
  var old = document.getElementById('lexiconSubgroupPanel');
  if (old) old.remove();

  var panel = document.createElement('div');
  panel.id = 'lexiconSubgroupPanel';
  panel.className = 'island-panel';
  panel.style.cssText = 'width:190px;flex-shrink:0;padding:12px 10px;gap:2px;';

  var search = document.createElement('input');
  search.id = 'lexiconGroupSearch';
  search.className = 'search-input';
  search.placeholder = '搜索分组...';
  search.style.cssText = 'width:100%;box-sizing:border-box;margin-bottom:8px;flex-shrink:0;';
  search.oninput = _filterLexiconGroups;
  panel.appendChild(search);

  var list = document.createElement('div');
  list.id = 'lexiconSubgroupList';
  list.style.cssText = 'flex:1;overflow-y:auto;';
  _fillSubgroupItems(list);
  panel.appendChild(list);

  var addBtn = document.createElement('button');
  addBtn.className = 'btn-agent secondary';
  addBtn.style.cssText = 'width:100%;font-size:11px;flex-shrink:0;';
  addBtn.textContent = '+ 新增分组';
  addBtn.onclick = addLexiconSubgroup;
  panel.appendChild(addBtn);

  main.insertBefore(panel, main.firstChild);
}

function _fillSubgroupItems(list) {
  list.textContent = '';
  _lexiconSubgroups.forEach(function(g) {
    var item = document.createElement('div');
    item.className = 'nav-item' + (_lexiconSubgroup === g.subgroup ? ' active' : '');
    item.dataset.subgroup = g.subgroup;
    item.style.cursor = 'pointer';
    item.onclick = (function(sg) { return function() { selectLexiconSubgroup(sg); }; })(g.subgroup);

    var name = document.createElement('span');
    name.style.cssText = 'flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;';
    name.textContent = g.subgroup;

    var cnt = document.createElement('span');
    cnt.style.cssText = 'font-size:10px;font-weight:600;margin-left:4px;opacity:0.5;';
    cnt.textContent = g.count;

    item.appendChild(name);
    item.appendChild(cnt);
    list.appendChild(item);
  });
}

function _filterLexiconGroups() {
  var q = (document.getElementById('lexiconGroupSearch') || {}).value || '';
  q = q.toLowerCase();
  var list = document.getElementById('lexiconSubgroupList');
  if (!list) return;
  Array.from(list.children).forEach(function(el) {
    el.style.display = !q || (el.dataset.subgroup || '').toLowerCase().indexOf(q) !== -1 ? '' : 'none';
  });
}

/* ── Render: tag cloud panel (right) ── */

function _renderTagPanel() {
  var main = document.getElementById('lexiconMain');
  if (!main) return;
  var old = document.getElementById('lexiconTagPanel');
  if (old) old.remove();

  var panel = document.createElement('div');
  panel.id = 'lexiconTagPanel';
  panel.className = 'island-panel';
  panel.style.cssText = 'flex:1;display:flex;flex-direction:column;overflow:hidden;';

  var selGroup = _lexiconSubgroups.find(function(g) { return g.subgroup === _lexiconSubgroup; });
  if (selGroup) {
    _buildTagPanelContent(panel, selGroup);
  } else {
    var empty = document.createElement('div');
    empty.style.cssText = 'flex:1;display:flex;align-items:center;justify-content:center;color:var(--text-muted);font-size:12px;';
    empty.textContent = '请选择左侧分组';
    panel.appendChild(empty);
  }
  main.appendChild(panel);
}

function _buildTagPanelContent(panel, group) {
  /* toolbar */
  var toolbar = document.createElement('div');
  toolbar.style.cssText = 'padding:10px 18px;border-bottom:1px solid var(--border-light);display:flex;gap:8px;align-items:center;';

  var tTitle = document.createElement('span');
  tTitle.style.cssText = 'font-weight:600;font-size:11px;color:var(--text-main);';
  tTitle.textContent = group.subgroup;

  var tCount = document.createElement('span');
  tCount.style.cssText = 'color:var(--text-muted);font-size:10px;';
  tCount.textContent = group.count + '词';

  var tSpacer = document.createElement('span');
  tSpacer.style.cssText = 'margin-left:auto;';

  var renameBtn = document.createElement('button');
  renameBtn.className = 'btn-agent secondary';
  renameBtn.style.fontSize = '10px';
  renameBtn.textContent = '重命名';
  renameBtn.onclick = (function(sg) { return function() { renameLexiconSubgroup(sg); }; })(group.subgroup);

  var delBtn = document.createElement('button');
  delBtn.className = 'btn-agent secondary';
  delBtn.style.cssText = 'color:var(--red);font-size:10px;';
  delBtn.textContent = '删除';
  delBtn.onclick = (function(sg) { return function() { deleteLexiconSubgroup(sg); }; })(group.subgroup);

  toolbar.appendChild(tTitle);
  toolbar.appendChild(tCount);
  toolbar.appendChild(tSpacer);
  toolbar.appendChild(renameBtn);
  toolbar.appendChild(delBtn);
  panel.appendChild(toolbar);

  /* inline add */
  var addRow = document.createElement('div');
  addRow.style.cssText = 'padding:10px 18px;border-bottom:1px solid var(--border-light);display:flex;gap:8px;';

  var input = document.createElement('input');
  input.id = 'lexiconAddInput';
  input.className = 'search-input';
  input.placeholder = '输入新词后回车...';
  input.style.cssText = 'flex:1;font-size:11px;box-sizing:border-box;';
  input.onkeydown = function(e) { if (e.key === 'Enter') addLexiconWordFromInput(); };

  var addBtn = document.createElement('button');
  addBtn.className = 'btn-agent primary';
  addBtn.style.fontSize = '11px';
  addBtn.textContent = '添加';
  addBtn.onclick = addLexiconWordFromInput;

  addRow.appendChild(input);
  addRow.appendChild(addBtn);
  panel.appendChild(addRow);

  /* tag cloud */
  var cloud = document.createElement('div');
  cloud.id = 'lexiconTagCloud';
  cloud.style.cssText = 'flex:1;overflow-y:auto;padding:8px;display:flex;flex-wrap:wrap;align-content:flex-start;gap:6px;';
  _fillTags(cloud, group.words || []);
  panel.appendChild(cloud);
}

function _fillTags(cloud, words) {
  cloud.textContent = '';
  if (!words.length) {
    var empty = document.createElement('div');
    empty.style.cssText = 'width:100%;text-align:center;color:var(--text-muted);padding:30px;font-size:11px;';
    empty.textContent = '暂无词条，在上方输入框添加';
    cloud.appendChild(empty);
    return;
  }
  words.forEach(function(w) {
    var tag = document.createElement('span');
    tag.className = 'lexicon-tag';
    tag.style.cssText = 'display:inline-flex;align-items:center;gap:4px;padding:2px 6px;'
      + 'background:var(--surface);border:1px solid var(--border);border-radius:10px;'
      + 'font-size:11px;cursor:default;line-height:1.5;user-select:none;';

    var label = document.createElement('span');
    label.style.cursor = 'pointer';
    label.title = '点击编辑';
    label.textContent = w;
    label.onclick = (function(word) { return function() { editLexiconWord(word); }; })(w);

    var x = document.createElement('span');
    x.style.cssText = 'cursor:pointer;color:var(--text-muted);font-size:12px;line-height:1;opacity:0.5;';
    x.title = '删除';
    x.textContent = '×';
    x.onclick = (function(word) { return function(e) { e.stopPropagation(); deleteLexiconWord(word); }; })(w);

    tag.appendChild(label);
    tag.appendChild(x);
    cloud.appendChild(tag);
  });
}

/* ── Navigation ── */

function selectLexiconCategory(key) {
  if (_lexiconSelected === key) return;
  _lexiconSelected = key;
  _renderCategoryTabs();
  _loadSubgroups();
}

function selectLexiconSubgroup(subgroup) {
  if (_lexiconSubgroup === subgroup) return;
  _lexiconSubgroup = subgroup;
  var list = document.getElementById('lexiconSubgroupList');
  if (list) _fillSubgroupItems(list);
  _renderTagPanel();
}

/* ── CRUD ── */

function addLexiconWordFromInput() {
  var input = document.getElementById('lexiconAddInput');
  if (!input) return;
  var word = input.value.trim();
  if (!word || !_lexiconSubgroup) return;
  input.value = '';
  _doAddWord(word);
}

async function _doAddWord(word) {
  try {
    var res = await fetch('/api/lexicon_words/add_word', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({category: _lexiconSelected, subgroup: _lexiconSubgroup, word: word})
    });
    var d = await res.json();
    if (!d.success) { alert(d.error); return; }
    _lexiconLastAdded = word;
    _syncAndRefreshTagPanel();
  } catch(e) { alert('添加失败: ' + e.message); }
}

async function deleteLexiconWord(word) {
  if (!confirm('确定删除“' + word + '”？')) return;
  try {
    var res = await fetch('/api/lexicon_words/delete_word', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({category: _lexiconSelected, subgroup: _lexiconSubgroup, word: word})
    });
    var d = await res.json();
    if (!d.success) { alert(d.error); return; }
    _syncAndRefreshTagPanel();
  } catch(e) { alert('删除失败: ' + e.message); }
}

async function editLexiconWord(oldWord) {
  var newWord = prompt('编辑词条：', oldWord);
  if (!newWord || !newWord.trim() || newWord.trim() === oldWord) return;
  newWord = newWord.trim();
  try {
    var res = await fetch('/api/lexicon_words/rename_word', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({category: _lexiconSelected, subgroup: _lexiconSubgroup, old_word: oldWord, new_word: newWord})
    });
    var d = await res.json();
    if (!d.success) { alert(d.error); return; }
    _syncAndRefreshTagPanel();
  } catch(e) { alert('编辑失败: ' + e.message); }
}

async function addLexiconSubgroup() {
  var name = prompt('在“' + _lexiconSelected + '”中新增分组名称：');
  if (!name || !name.trim()) return;
  name = name.trim();
  try {
    var res = await fetch('/api/lexicon_words/add_subgroup', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({category: _lexiconSelected, subgroup: name})
    });
    var d = await res.json();
    if (!d.success) { alert(d.error); return; }
    _lexiconSubgroup = name;
    _loadSubgroups();
  } catch(e) { alert('添加失败: ' + e.message); }
}

async function deleteLexiconSubgroup(subgroup) {
  if (!confirm('确定删除分组“' + subgroup + '”及其所有词条？')) return;
  try {
    var res = await fetch('/api/lexicon_words/delete_subgroup', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({category: _lexiconSelected, subgroup: subgroup})
    });
    var d = await res.json();
    if (!d.success) { alert(d.error); return; }
    if (_lexiconSubgroup === subgroup) _lexiconSubgroup = null;
    _loadSubgroups();
  } catch(e) { alert('删除失败: ' + e.message); }
}

async function renameLexiconSubgroup(subgroup) {
  var newName = prompt('重命名分组：', subgroup);
  if (!newName || !newName.trim() || newName.trim() === subgroup) return;
  newName = newName.trim();
  try {
    var res = await fetch('/api/lexicon_words/rename_subgroup', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({category: _lexiconSelected, old_name: subgroup, new_name: newName})
    });
    var d = await res.json();
    if (!d.success) { alert(d.error); return; }
    _lexiconSubgroup = newName;
    _loadSubgroups();
  } catch(e) { alert('重命名失败: ' + e.message); }
}

async function _syncAndRefreshTagPanel() {
  try {
    var res = await fetch('/api/lexicon_words?category=' + encodeURIComponent(_lexiconSelected));
    var data = await res.json();
    _lexiconSubgroups = data.subgroups || [];
    _lexiconSubgroups._category = _lexiconSelected;
    var cres = await fetch('/api/lexicon_words/categories');
    var cdata = await cres.json();
    _lexiconCategories = cdata.categories || [];
  } catch(e) {}
  _renderHeader();
  _renderCategoryTabs();
  var list = document.getElementById('lexiconSubgroupList');
  if (list) _fillSubgroupItems(list);
  var panel = document.getElementById('lexiconTagPanel');
  if (panel) {
    panel.textContent = '';
    var selGroup = _lexiconSubgroups.find(function(g) { return g.subgroup === _lexiconSubgroup; });
    if (selGroup) {
      _buildTagPanelContent(panel, selGroup);
      _flashNewTag();
    } else {
      var empty = document.createElement('div');
      empty.style.cssText = 'flex:1;display:flex;align-items:center;justify-content:center;color:var(--text-muted);font-size:12px;';
      empty.textContent = '请选择左侧分组';
      panel.appendChild(empty);
    }
  }
}

function _flashNewTag() {
  if (!_lexiconLastAdded) return;
  var word = _lexiconLastAdded;
  _lexiconLastAdded = null;
  var tags = document.querySelectorAll('#lexiconTagCloud .lexicon-tag');
  for (var i = 0; i < tags.length; i++) {
    var label = tags[i].querySelector('span');
    if (label && label.textContent === word) {
      tags[i].style.animation = 'lexicon-flash 1.2s ease-out';
      tags[i].scrollIntoView({ behavior: 'smooth', block: 'center' });
      tags[i].addEventListener('animationend', function() { this.style.animation = ''; }, { once: true });
      return;
    }
  }
}

/* ── Exports ── */

window.renderVarietyWords = renderVarietyWords;
window.addLexiconWordFromInput = addLexiconWordFromInput;
window.deleteLexiconWord = deleteLexiconWord;
window.editLexiconWord = editLexiconWord;
window.addLexiconSubgroup = addLexiconSubgroup;
window.deleteLexiconSubgroup = deleteLexiconSubgroup;
window.renameLexiconSubgroup = renameLexiconSubgroup;
