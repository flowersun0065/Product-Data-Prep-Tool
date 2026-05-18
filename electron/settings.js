// settings.js — Settings window logic

var settings = {};

var sections = {
  general: function() {
    return '<div class="settings-section">' +
      '<h3 style="font-size:12px;margin-bottom:12px;">通用</h3>' +

      '<div class="settings-row">' +
        '<div><div class="settings-label">语言</div><div class="settings-hint">界面显示语言</div></div>' +
        '<select id="setting-language" onchange="save()">' +
          '<option value="zh"' + (settings.language === 'zh' ? ' selected' : '') + '>中文</option>' +
          '<option value="en"' + (settings.language === 'en' ? ' selected' : '') + '>English</option>' +
        '</select>' +
      '</div>' +

      '<div class="settings-row">' +
        '<div><div class="settings-label">启动时</div><div class="settings-hint">应用启动后的默认行为</div></div>' +
        '<select id="setting-startup_action" onchange="save()">' +
          '<option value="upload"' + (settings.startup_action === 'upload' ? ' selected' : '') + '>显示上传页</option>' +
          '<option value="restore"' + (settings.startup_action === 'restore' ? ' selected' : '') + '>恢复上次会话</option>' +
        '</select>' +
      '</div>' +

      '<div class="settings-row">' +
        '<div><div class="settings-label">商品详情打开方式</div><div class="settings-hint">点击商品时如何显示详情</div></div>' +
        '<select id="setting-detail_mode" onchange="save()">' +
          '<option value="sidebar"' + (settings.detail_mode === 'sidebar' ? ' selected' : '') + '>侧边窗（同窗口）</option>' +
          '<option value="window"' + (settings.detail_mode === 'window' ? ' selected' : '') + '>独立窗口</option>' +
          '<option value="hybrid"' + (settings.detail_mode === 'hybrid' ? ' selected' : '') + '>单击侧边窗 / 双击独立窗口</option>' +
        '</select>' +
      '</div>' +
    '</div>';
  },

  ai: function() {
    return '<div class="settings-section">' +
      '<h3 style="font-size:12px;margin-bottom:12px;">AI 默认配置</h3>' +

      '<div class="settings-row">' +
        '<div><div class="settings-label">默认 AI 提供商 & 模型</div></div>' +
        '<select id="setting-ai_provider" onchange="save()">' +
          '<option value="gemini"' + (settings.ai_provider === 'gemini' ? ' selected' : '') + '>Gemini</option>' +
          '<option value="claude"' + (settings.ai_provider === 'claude' ? ' selected' : '') + '>Claude</option>' +
          '<option value="openai"' + (settings.ai_provider === 'openai' ? ' selected' : '') + '>OpenAI</option>' +
        '</select>' +
      '</div>' +

      '<div class="settings-row">' +
        '<div><div class="settings-label">API Key</div></div>' +
        '<input type="password" id="setting-api_key" value="' + (settings.api_key || '') + '" onchange="save()" style="width:200px;">' +
      '</div>' +

      '<div class="settings-row">' +
        '<div><div class="settings-label">每批处理数量</div><div class="settings-hint">AI 每次处理的商品数量</div></div>' +
        '<input type="number" id="setting-batch_size" value="' + (settings.batch_size || 20) + '" onchange="save()" min="5" max="100" style="width:80px;">' +
      '</div>' +
    '</div>';
  },

  storage: function() {
    return '<div class="settings-section">' +
      '<h3 style="font-size:12px;margin-bottom:12px;">数据 & 存储</h3>' +
      '<div class="settings-row">' +
        '<div><div class="settings-label">数据目录</div><div class="settings-hint">品牌库/缓存/修正记录存储位置</div></div>' +
        '<button class="btn btn-ghost" onclick="selectDataDir()" style="font-size:10px;">选择...</button>' +
      '</div>' +
      '<div style="color:var(--text-secondary);font-size:10px;" id="dataDirPath">' + (settings.data_dir || '默认位置') + '</div>' +
    '</div>';
  },

  appearance: function() {
    return '<div class="settings-section">' +
      '<h3 style="font-size:12px;margin-bottom:12px;">外观</h3>' +
      '<div class="settings-row">' +
        '<div><div class="settings-label">主题</div></div>' +
        '<select id="setting-theme" onchange="save()">' +
          '<option value="system"' + (settings.theme === 'system' ? ' selected' : '') + '>跟随系统</option>' +
          '<option value="dark"' + (settings.theme === 'dark' ? ' selected' : '') + '>深色</option>' +
          '<option value="light"' + (settings.theme === 'light' ? ' selected' : '') + '>浅色</option>' +
        '</select>' +
      '</div>' +
    '</div>';
  },

  shortcuts: function() {
    return '<div class="settings-section">' +
      '<h3 style="font-size:12px;margin-bottom:12px;">快捷键</h3>' +
      '<table style="width:100%;font-size:10px;">' +
        '<tr><td style="color:var(--text-secondary);padding:4px 0;">确认</td><td><kbd style="background:var(--bg-tertiary);padding:1px 5px;border-radius:3px;">⌘↵</kbd></td></tr>' +
        '<tr><td style="color:var(--text-secondary);padding:4px 0;">编辑</td><td><kbd style="background:var(--bg-tertiary);padding:1px 5px;border-radius:3px;">⌘E</kbd></td></tr>' +
        '<tr><td style="color:var(--text-secondary);padding:4px 0;">跳过</td><td><kbd style="background:var(--bg-tertiary);padding:1px 5px;border-radius:3px;">⌘S</kbd></td></tr>' +
        '<tr><td style="color:var(--text-secondary);padding:4px 0;">上一条/下一条</td><td><kbd style="background:var(--bg-tertiary);padding:1px 5px;border-radius:3px;">↑ ↓</kbd></td></tr>' +
        '<tr><td style="color:var(--text-secondary);padding:4px 0;">全局搜索</td><td><kbd style="background:var(--bg-tertiary);padding:1px 5px;border-radius:3px;">⌘K</kbd></td></tr>' +
        '<tr><td style="color:var(--text-secondary);padding:4px 0;">详情新窗口</td><td><kbd style="background:var(--bg-tertiary);padding:1px 5px;border-radius:3px;">⌘⇧D</kbd></td></tr>' +
        '<tr><td style="color:var(--text-secondary);padding:4px 0;">导入文件</td><td><kbd style="background:var(--bg-tertiary);padding:1px 5px;border-radius:3px;">⌘O</kbd></td></tr>' +
        '<tr><td style="color:var(--text-secondary);padding:4px 0;">导出结果</td><td><kbd style="background:var(--bg-tertiary);padding:1px 5px;border-radius:3px;">⌘⇧E</kbd></td></tr>' +
        '<tr><td style="color:var(--text-secondary);padding:4px 0;">打开设置</td><td><kbd style="background:var(--bg-tertiary);padding:1px 5px;border-radius:3px;">⌘,</kbd></td></tr>' +
      '</table>' +
    '</div>';
  },
};

async function loadSettings() {
  try {
    var res = await fetch('http://localhost:5001/api/settings');
    var data = await res.json();
    for (var k in data) {
      if (data.hasOwnProperty(k)) settings[k] = data[k];
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
  if (renderer) {
    document.getElementById('settingsContent').innerHTML = renderer();
  }
}

async function save() {
  var updated = {};
  var langEl = document.getElementById('setting-language');
  var startupEl = document.getElementById('setting-startup_action');
  var detailEl = document.getElementById('setting-detail_mode');
  var aiEl = document.getElementById('setting-ai_provider');
  var keyEl = document.getElementById('setting-api_key');
  var batchEl = document.getElementById('setting-batch_size');
  var themeEl = document.getElementById('setting-theme');

  if (langEl) updated.language = langEl.value;
  if (startupEl) updated.startup_action = startupEl.value;
  if (detailEl) updated.detail_mode = detailEl.value;
  if (aiEl) updated.ai_provider = aiEl.value;
  if (keyEl) updated.api_key = keyEl.value;
  if (batchEl) updated.batch_size = parseInt(batchEl.value) || 20;
  if (themeEl) updated.theme = themeEl.value;

  try {
    await fetch('http://localhost:5001/api/settings', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updated),
    });
    // Mirror to main window for immediate effect
    for (var k in updated) {
      if (updated.hasOwnProperty(k)) settings[k] = updated[k];
    }
  } catch (e) {
    console.error('Failed to save settings:', e);
  }
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
