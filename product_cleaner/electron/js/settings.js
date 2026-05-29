// settings.js — Settings window logic

var settings = {};
// HTML 转义函数（settings 页面为独立页面，需自备）
function escHtml(s) { return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
function escAttr(s) { return String(s||'').replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/'/g,'&#39;'); }

var sections = {
  general: function() {
    var sec = document.createElement('div');
    sec.className = 'settings-section';
    var h3 = document.createElement('h3');
    h3.style.cssText = 'font-size:12px;margin-bottom:12px;';
    h3.textContent = '通用';
    sec.appendChild(h3);

    // 语言
    var row1 = document.createElement('div');
    row1.className = 'settings-row';
    var r1Left = document.createElement('div');
    var r1Label = document.createElement('div');
    r1Label.className = 'settings-label'; r1Label.textContent = '语言';
    r1Left.appendChild(r1Label);
    var r1Hint = document.createElement('div');
    r1Hint.className = 'settings-hint'; r1Hint.textContent = '界面显示语言';
    r1Left.appendChild(r1Hint);
    row1.appendChild(r1Left);
    var sel1 = document.createElement('select');
    sel1.id = 'setting-language';
    sel1.addEventListener('change', function() { save(); });
    var optZh = document.createElement('option'); optZh.value = 'zh'; optZh.textContent = '中文';
    if (settings.language === 'zh') optZh.selected = true;
    sel1.appendChild(optZh);
    var optEn = document.createElement('option'); optEn.value = 'en'; optEn.textContent = 'English';
    if (settings.language === 'en') optEn.selected = true;
    sel1.appendChild(optEn);
    row1.appendChild(sel1);
    sec.appendChild(row1);

    // 启动时
    var row2 = document.createElement('div');
    row2.className = 'settings-row';
    var r2Left = document.createElement('div');
    var r2Label = document.createElement('div');
    r2Label.className = 'settings-label'; r2Label.textContent = '启动时';
    r2Left.appendChild(r2Label);
    var r2Hint = document.createElement('div');
    r2Hint.className = 'settings-hint'; r2Hint.textContent = '应用启动后的默认行为';
    r2Left.appendChild(r2Hint);
    row2.appendChild(r2Left);
    var sel2 = document.createElement('select');
    sel2.id = 'setting-startup_action';
    sel2.addEventListener('change', function() { save(); });
    ['upload', 'restore'].forEach(function(v) {
      var o = document.createElement('option'); o.value = v;
      o.textContent = v === 'upload' ? '显示上传页' : '恢复上次会话';
      if (settings.startup_action === v) o.selected = true;
      sel2.appendChild(o);
    });
    row2.appendChild(sel2);
    sec.appendChild(row2);

    // 商品详情打开方式
    var row3 = document.createElement('div');
    row3.className = 'settings-row';
    var r3Left = document.createElement('div');
    var r3Label = document.createElement('div');
    r3Label.className = 'settings-label'; r3Label.textContent = '商品详情打开方式';
    r3Left.appendChild(r3Label);
    var r3Hint = document.createElement('div');
    r3Hint.className = 'settings-hint'; r3Hint.textContent = '点击商品时如何显示详情';
    r3Left.appendChild(r3Hint);
    row3.appendChild(r3Left);
    var sel3 = document.createElement('select');
    sel3.id = 'setting-detail_mode';
    sel3.addEventListener('change', function() { save(); });
    [{v:'sidebar',t:'侧边窗（同窗口）'},{v:'window',t:'独立窗口'},{v:'hybrid',t:'单击侧边窗 / 双击独立窗口'}].forEach(function(o) {
      var opt = document.createElement('option'); opt.value = o.v; opt.textContent = o.t;
      if (settings.detail_mode === o.v) opt.selected = true;
      sel3.appendChild(opt);
    });
    row3.appendChild(sel3);
    sec.appendChild(row3);

    return sec;
  },

  ai: function() {
    var configs = settings.ai_configs || [];
    var current = settings.current || '';

    var sec = document.createElement('div');
    sec.className = 'settings-section';
    var h3 = document.createElement('h3');
    h3.style.cssText = 'font-size:12px;margin-bottom:4px;';
    h3.textContent = 'AI 模型配置';
    sec.appendChild(h3);
    var desc = document.createElement('p');
    desc.style.cssText = 'font-size:10px;color:var(--text-muted);margin-bottom:12px;';
    desc.textContent = '管理多个 AI 配置，处理时选择一个使用';
    sec.appendChild(desc);

    var btnRow = document.createElement('div');
    btnRow.style.cssText = 'margin-bottom:8px;text-align:right;';
    var addBtn = document.createElement('button');
    addBtn.className = 'btn-agent primary';
    addBtn.style.fontSize = '11px';
    addBtn.textContent = '+ 新增配置';
    addBtn.addEventListener('click', function() { openConfigEditor(); });
    btnRow.appendChild(addBtn);
    sec.appendChild(btnRow);

    if (!configs.length) {
      var empty = document.createElement('div');
      empty.style.cssText = 'color:var(--text-muted);font-size:11px;padding:20px;text-align:center;';
      empty.textContent = '暂无配置，点击上方新增';
      sec.appendChild(empty);
    } else {
      configs.forEach(function(c) {
        var isCurrent = c.name === current;
        var card = document.createElement('div');
        card.style.cssText = 'border:1px solid ' + (isCurrent ? 'var(--accent)' : 'var(--border)') + ';border-radius:var(--radius-md);padding:8px 10px;margin-bottom:6px;background:var(--panel);';

        var topRow = document.createElement('div');
        topRow.style.cssText = 'display:flex;align-items:center;justify-content:space-between;';

        var nameDiv = document.createElement('div');
        var nameSpan = document.createElement('span');
        nameSpan.style.cssText = 'font-size:12px;font-weight:600;color:var(--text-main);';
        nameSpan.textContent = c.name;
        nameDiv.appendChild(nameSpan);
        if (isCurrent) {
          var badge = document.createElement('span');
          badge.className = 'badge-flat acc';
          badge.style.fontSize = '9px';
          badge.textContent = '默认';
          nameDiv.appendChild(badge);
        }
        topRow.appendChild(nameDiv);

        var actions = document.createElement('div');
        actions.style.cssText = 'display:flex;gap:4px;';
        if (!isCurrent) {
          var setBtn = document.createElement('button');
          setBtn.className = 'btn-agent secondary';
          setBtn.style.fontSize = '10px';
          setBtn.textContent = '设默认';
          setBtn.addEventListener('click', (function(n) { return function() { setDefaultConfig(n); }; })(c.name));
          actions.appendChild(setBtn);
        }
        var editBtn = document.createElement('button');
        editBtn.className = 'btn-agent secondary';
        editBtn.style.fontSize = '10px';
        editBtn.textContent = '编辑';
        editBtn.addEventListener('click', (function(n) { return function() { openConfigEditor(n); }; })(c.name));
        actions.appendChild(editBtn);
        var delBtn = document.createElement('button');
        delBtn.className = 'btn-agent secondary';
        delBtn.style.cssText = 'font-size:10px;color:var(--red);';
        delBtn.textContent = '删除';
        delBtn.addEventListener('click', (function(n) { return function() { deleteConfig(n); }; })(c.name));
        actions.appendChild(delBtn);
        topRow.appendChild(actions);
        card.appendChild(topRow);

        var meta = document.createElement('div');
        meta.style.cssText = 'font-size:10px;color:var(--text-sub);margin-top:4px;';
        meta.textContent = c.provider + ' / ' + c.model + ' · ' + (c.base_url || '默认');
        card.appendChild(meta);

        sec.appendChild(card);
      });
    }
    return sec;
  },

  storage: function() {
    var sec = document.createElement('div');
    sec.className = 'settings-section';
    var h3 = document.createElement('h3');
    h3.style.cssText = 'font-size:12px;margin-bottom:12px;';
    h3.textContent = '数据 & 存储';
    sec.appendChild(h3);

    var row = document.createElement('div');
    row.className = 'settings-row';
    var left = document.createElement('div');
    var label = document.createElement('div');
    label.className = 'settings-label'; label.textContent = '数据目录';
    left.appendChild(label);
    var hint = document.createElement('div');
    hint.className = 'settings-hint'; hint.textContent = '品牌库/缓存/修正记录存储位置';
    left.appendChild(hint);
    row.appendChild(left);
    var btn = document.createElement('button');
    btn.className = 'btn btn-ghost';
    btn.style.fontSize = '10px';
    btn.textContent = '选择...';
    btn.addEventListener('click', function() { selectDataDir(); });
    row.appendChild(btn);
    sec.appendChild(row);

    var pathDiv = document.createElement('div');
    pathDiv.style.cssText = 'color:var(--text-secondary);font-size:10px;';
    pathDiv.id = 'dataDirPath';
    pathDiv.textContent = settings.data_dir || '默认位置';
    sec.appendChild(pathDiv);

    return sec;
  },

  appearance: function() {
    var sec = document.createElement('div');
    sec.className = 'settings-section';
    var h3 = document.createElement('h3');
    h3.style.cssText = 'font-size:12px;margin-bottom:12px;';
    h3.textContent = '外观';
    sec.appendChild(h3);

    var row = document.createElement('div');
    row.className = 'settings-row';
    var left = document.createElement('div');
    var label = document.createElement('div');
    label.className = 'settings-label'; label.textContent = '主题';
    left.appendChild(label);
    row.appendChild(left);

    var sel = document.createElement('select');
    sel.id = 'setting-theme';
    sel.addEventListener('change', function() { save(); });
    [{v:'system',t:'跟随系统'},{v:'dark',t:'深色'},{v:'light',t:'浅色'}].forEach(function(o) {
      var opt = document.createElement('option'); opt.value = o.v; opt.textContent = o.t;
      if (settings.theme === o.v) opt.selected = true;
      sel.appendChild(opt);
    });
    row.appendChild(sel);
    sec.appendChild(row);

    return sec;
  },

  shortcuts: function() {
    var sec = document.createElement('div');
    sec.className = 'settings-section';
    var h3 = document.createElement('h3');
    h3.style.cssText = 'font-size:12px;margin-bottom:12px;';
    h3.textContent = '快捷键';
    sec.appendChild(h3);

    var table = document.createElement('table');
    table.style.cssText = 'width:100%;font-size:10px;';
    var shortcuts = [
      ['确认', '⌘↵'], ['编辑', '⌘E'], ['跳过', '⌘S'],
      ['上一条/下一条', '↑ ↓'], ['全局搜索', '⌘K'],
      ['详情新窗口', '⌘⇧D'], ['导入文件', '⌘O'],
      ['导出结果', '⌘⇧E'], ['打开设置', '⌘,']
    ];
    shortcuts.forEach(function(pair) {
      var tr = document.createElement('tr');
      var tdKey = document.createElement('td');
      tdKey.style.cssText = 'color:var(--text-secondary);padding:4px 0;';
      tdKey.textContent = pair[0];
      tr.appendChild(tdKey);
      var tdVal = document.createElement('td');
      var kbd = document.createElement('kbd');
      kbd.style.cssText = 'background:var(--bg-tertiary);padding:1px 5px;border-radius:3px;';
      kbd.textContent = pair[1];
      tdVal.appendChild(kbd);
      tr.appendChild(tdVal);
      table.appendChild(tr);
    });
    sec.appendChild(table);

    return sec;
  },
};

async function loadSettings() {
  try {
    var res = await fetch('/api/settings');
    var data = await res.json();
    for (var k in data) { if (data.hasOwnProperty(k)) settings[k] = data[k]; }
    // 初始化默认值
    if (!settings.ai_configs) settings.ai_configs = [];
    if (!settings.current) settings.current = '';
    // 迁移旧格式：如果有旧的 ai_provider，自动创建首个配置
    if (data.ai_provider && (!settings.ai_configs || !settings.ai_configs.length)) {
      settings.ai_configs = [{ name: 'Default', provider: data.ai_provider, model: data.model_id || '', api_key: data.api_key || '', base_url: '' }];
      settings.current = 'Default';
    }
    if (window.electronAPI) {
      try {
        settings.data_dir = await window.electronAPI.getDataDir();
      } catch(e) {}
    }
  } catch (e) {
    console.error('Failed to load settings:', e);
  }
  showSection('general');
}

function showSection(name) {
  var items = document.querySelectorAll('.settings-nav-item');
  for (var i = 0; i < items.length; i++) {
    items[i].classList.toggle('active', items[i].dataset.section === name);
  }
  var renderer = sections[name];
  var container = document.getElementById('settingsContent');
  if (renderer && container) {
    container.textContent = '';
    container.appendChild(renderer());
  }
}

// ── 配置管理函数 ──

// 打开配置编辑器（新增或编辑）
window.openConfigEditor = function(name) {
  var configs = settings.ai_configs || [];
  var cfg = name ? configs.find(function(c) { return c.name === name; }) : null;
  var isEdit = !!cfg;

  var inputStyle = 'width:100%;padding:6px 8px;border:1px solid var(--border);border-radius:var(--radius-sm);background:var(--surface);color:var(--text-main);font-size:12px;box-sizing:border-box;';
  var labelStyle = 'font-size:10px;color:var(--text-muted);display:block;';
  var fieldStyle = 'margin-bottom:8px;';

  var wrapper = document.createElement('div');
  wrapper.style.padding = '12px';

  // 名称
  var fName = document.createElement('div');
  fName.style.cssText = fieldStyle;
  var lName = document.createElement('label');
  lName.style.cssText = labelStyle; lName.textContent = '名称';
  fName.appendChild(lName);
  var iName = document.createElement('input');
  iName.id = '_cfgName'; iName.style.cssText = inputStyle;
  iName.value = cfg ? cfg.name : '';
  fName.appendChild(iName);
  wrapper.appendChild(fName);

  // Provider
  var fProv = document.createElement('div');
  fProv.style.cssText = fieldStyle;
  var lProv = document.createElement('label');
  lProv.style.cssText = labelStyle; lProv.textContent = 'Provider';
  fProv.appendChild(lProv);
  var iProv = document.createElement('input');
  iProv.id = '_cfgProvider'; iProv.style.cssText = inputStyle;
  iProv.value = cfg ? cfg.provider : 'deepseek';
  var dl = document.createElement('datalist');
  dl.id = '_cfgProviderList';
  ['deepseek','alibaba','openai','claude','gemini'].forEach(function(v) {
    var o = document.createElement('option'); o.value = v; dl.appendChild(o);
  });
  fProv.appendChild(dl);
  iProv.setAttribute('list', '_cfgProviderList');
  fProv.appendChild(iProv);
  wrapper.appendChild(fProv);

  // 模型
  var fModel = document.createElement('div');
  fModel.style.cssText = fieldStyle;
  var lModel = document.createElement('label');
  lModel.style.cssText = labelStyle; lModel.textContent = '模型';
  fModel.appendChild(lModel);
  var iModel = document.createElement('input');
  iModel.id = '_cfgModel'; iModel.style.cssText = inputStyle;
  iModel.value = cfg ? cfg.model : 'deepseek-chat';
  fModel.appendChild(iModel);
  wrapper.appendChild(fModel);

  // API Key
  var fKey = document.createElement('div');
  fKey.style.cssText = fieldStyle;
  var lKey = document.createElement('label');
  lKey.style.cssText = labelStyle; lKey.textContent = 'API Key';
  fKey.appendChild(lKey);
  var iKey = document.createElement('input');
  iKey.id = '_cfgKey'; iKey.type = 'password'; iKey.style.cssText = inputStyle;
  iKey.value = cfg ? (cfg.api_key || '') : '';
  fKey.appendChild(iKey);
  wrapper.appendChild(fKey);

  // Base URL
  var fUrl = document.createElement('div');
  fUrl.style.cssText = fieldStyle;
  var lUrl = document.createElement('label');
  lUrl.style.cssText = labelStyle; lUrl.textContent = 'Base URL (可选)';
  fUrl.appendChild(lUrl);
  var iUrl = document.createElement('input');
  iUrl.id = '_cfgUrl'; iUrl.style.cssText = inputStyle;
  iUrl.placeholder = '留空则用默认地址';
  iUrl.value = cfg ? (cfg.base_url || '') : '';
  fUrl.appendChild(iUrl);
  wrapper.appendChild(fUrl);

  // 按钮行
  var btnRow = document.createElement('div');
  btnRow.style.cssText = 'display:flex;gap:8px;justify-content:flex-end;margin-top:12px;';
  var cancelBtn = document.createElement('button');
  cancelBtn.className = 'btn-agent secondary';
  cancelBtn.textContent = '取消';
  cancelBtn.addEventListener('click', function() { showSection('ai'); });
  btnRow.appendChild(cancelBtn);
  var saveBtn = document.createElement('button');
  saveBtn.className = 'btn-agent primary';
  saveBtn.textContent = isEdit ? '保存' : '新增';
  saveBtn.addEventListener('click', function() { saveConfig(name || ''); });
  btnRow.appendChild(saveBtn);
  wrapper.appendChild(btnRow);

  // 直接替换内容区（settings 页面无 panel card 系统）
  var container = document.getElementById('settingsContent');
  if (container) {
    container.textContent = '';
    container.appendChild(wrapper);
  }
};

// 保存配置
window.saveConfig = async function(oldName) {
  var name = document.getElementById('_cfgName').value.trim();
  var provider = document.getElementById('_cfgProvider').value.trim();
  var model = document.getElementById('_cfgModel').value.trim();
  var key = document.getElementById('_cfgKey').value.trim();
  var url = document.getElementById('_cfgUrl').value.trim();

  if (!name || !provider || !model) { alert('名称、Provider、模型不能为空'); return; }

  var configs = settings.ai_configs || [];  // 已有配置
  var idx = configs.findIndex(function(c) { return c.name === oldName; });  // 查找旧名称
  var cfg = { name: name, provider: provider, model: model, api_key: key, base_url: url };

  if (idx >= 0) configs[idx] = cfg;  // 编辑模式替换
  else configs.push(cfg);  // 新增模式追加

  // 如果还没有默认配置，自动设为默认
  if (!settings.current) settings.current = name;

  await _writeSettings({ ai_configs: configs, current: settings.current });
  settings.ai_configs = configs;
  if (oldName && settings.current === oldName) settings.current = name;
  showSection('ai');  // 刷新列表回到配置列表
};

// 设为默认
window.setDefaultConfig = async function(name) {
  settings.current = name;
  await _writeSettings({ current: name });
  showSection('ai');  // 刷新
};

// 删除配置
window.deleteConfig = async function(name) {
  if (!confirm('确定删除配置 "' + name + '"？')) return;
  var configs = (settings.ai_configs || []).filter(function(c) { return c.name !== name; });  // 过滤掉删除项
  var cur = settings.current === name ? (configs.length ? configs[0].name : '') : settings.current;  // 删除当前则切换
  await _writeSettings({ ai_configs: configs, current: cur });
  settings.ai_configs = configs;
  settings.current = cur;
  showSection('ai');  // 刷新
};

// 通用写入方法：GET → merge → PUT
async function _writeSettings(updates) {
  try {
    var res = await fetch('/api/settings');
    var current = await res.json();
    for (var k in updates) { if (updates.hasOwnProperty(k)) current[k] = updates[k]; }
    await fetch('/api/settings', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(current) });
    for (var k in current) { if (current.hasOwnProperty(k)) settings[k] = current[k]; }
  } catch(e) { console.error('writeSettings failed:', e); }
}

// 保留原 save 用于通用设置（非 AI 配置）
async function save() {
  var langEl = document.getElementById('setting-language');
  var startupEl = document.getElementById('setting-startup_action');
  var detailEl = document.getElementById('setting-detail_mode');
  var batchEl = document.getElementById('setting-batch_size');
  var themeEl = document.getElementById('setting-theme');

  var updates = {};
  if (langEl) updates.language = langEl.value;
  if (startupEl) updates.startup_action = startupEl.value;
  if (detailEl) updates.detail_mode = detailEl.value;
  if (batchEl) updates.batch_size = parseInt(batchEl.value) || 20;
  if (themeEl) updates.theme = themeEl.value;

  await _writeSettings(updates);
}

async function selectDataDir() {
  if (window.electronAPI) {
    try {
      var dir = await window.electronAPI.getDataDir();
      var el = document.getElementById('dataDirPath');
      if (el) el.textContent = dir;
    } catch(e) {}
  }
}

document.addEventListener('DOMContentLoaded', loadSettings);
