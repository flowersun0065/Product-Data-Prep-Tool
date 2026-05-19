// electron_init.js — Electron sidebar navigation + detail panel + brand/category pages
(function(){
  var isElectron = (window.electronAPI !== undefined) || (window.location.pathname === '/electron');
  if (!isElectron) return;

  // Show sidebar
  var sidebar = document.getElementById('electronSidebar');
  var mainContent = document.getElementById('electronMainContent');
  if (sidebar) sidebar.style.display = '';
  if (mainContent) mainContent.classList.add('electron-shifted');

  // Session steps
  var steps = [
    {id:'upload', label:'1 上传 & 诊断'},
    {id:'brand-review', label:'2 品牌审核'},
    {id:'ai-process', label:'3 AI 处理'},
    {id:'review', label:'4 复核'},
    {id:'export', label:'5 导出'},
  ];
  var currentStep = 'upload';

  function renderSteps() {
    var el = document.getElementById('electronSessionSteps');
    if (!el) return;
    el.innerHTML = steps.map(function(s){
      var cls = 'electron-sidebar-item';
      if (s.id === currentStep) cls += ' active';
      return '<div class="' + cls + '" data-sid="' + s.id + '" onclick="electronSwitchStep(this.dataset.sid)">' + s.label + '</div>';
    }).join('');
  }

  // Step switching
  window.electronSwitchStep = function(stepId) {
    currentStep = stepId;
    renderSteps();
    var us = document.getElementById('uploadSection');
    var ds = document.getElementById('diagnosisSection');
    var ps = document.getElementById('progressSection');
    if (stepId === 'upload') {
      if (us) us.classList.remove('hidden');
      if (ds) ds.classList.add('hidden');
      if (ps) ps.classList.add('hidden');
    } else if (stepId === 'brand-review' || stepId === 'ai-process') {
      if (us) us.classList.add('hidden');
      if (ds) ds.classList.remove('hidden');
      if (ps) ps.classList.remove('hidden');
    }
  };

  // Group switching
  window.electronSwitchGroup = function(gid) {
    localStorage.setItem('last_group_id', gid);
    var ug = document.getElementById('uploadGroup');
    if (ug) ug.value = gid;
    loadElectronHistory();
    // Also sync the upload section group selector
    var uploadSel = document.getElementById('uploadGroup');
    if (uploadSel) uploadSel.value = gid;
  };

  // Load groups into sidebar selector
  function loadElectronGroups() {
    fetch('/api/groups').then(function(r){return r.json()}).then(function(d){
      var sel = document.getElementById('electronGroupSelect');
      if (!sel) return;
      var cur = sel.value;
      sel.innerHTML = '<option value="">-- 选择分组 --</option>';
      Object.entries(d.groups||{}).forEach(function(e){
        sel.innerHTML += '<option value="' + e[0] + '">📁 ' + escHtml(e[1].name) + '</option>';
      });
      var lastGid = localStorage.getItem('last_group_id') || '';
      sel.value = cur || lastGid;
      if (lastGid) {
        var ug = document.getElementById('uploadGroup');
        if (ug) ug.value = lastGid;
      }
    }).catch(function(){});
  }

  // Load recent files into sidebar
  function loadElectronHistory() {
    var el = document.getElementById('electronHistory');
    if (!el) return;
    fetch('/api/recent_files').then(function(r){return r.json()}).then(function(files){
      el.innerHTML = (files||[]).slice(0,5).map(function(f){
        return '<div class="electron-sidebar-item" style="font-size:10px" data-fid="' + f.id + '" onclick="importRecentFile(this.dataset.fid)">' +
          ((f.time||'').split(' ')[0]) + ' · ' + ((f.name||'').substring(0,20)) + '</div>';
      }).join('');
    }).catch(function(){});
  }

  // Sidebar page navigation (brand library, category tree)
  window.electronNavTo = function(page) {
    if (page === 'brand-database') { renderBrandDatabasePage(); }
    else if (page === 'category-tree') { renderCategoryTreePage(); }
  };

  window.electronOpenSettings = function() {
    if (window.electronAPI) { window.electronAPI.openSettings(); }
  };

  // ═══ Shared Detail Panel ═══
  window.electronOpenDetail = function(item) {
    var panel = document.getElementById('electronDetailPanel');
    var overlay = document.getElementById('electronDetailOverlay');
    if (!panel || !overlay) return;
    renderElectronDetail(item);
    panel.classList.add('open');
    overlay.classList.add('open');
  };

  window.electronCloseDetail = function() {
    var panel = document.getElementById('electronDetailPanel');
    var overlay = document.getElementById('electronDetailOverlay');
    if (panel) panel.classList.remove('open');
    if (overlay) overlay.classList.remove('open');
  };

  function renderElectronDetail(item) {
    var el = document.getElementById('electronDetailContent');
    if (!el) return;
    var h = '';
    h += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">';
    h += '<span style="font-weight:600;font-size:13px;">商品详情</span>';
    h += '<button onclick="electronCloseDetail()" style="background:none;border:none;color:#86868b;cursor:pointer;font-size:16px;">✕</button></div>';

    if (item.org_image_url) {
      h += '<div style="background:rgba(255,255,255,0.03);border-radius:8px;height:100px;display:flex;align-items:center;justify-content:center;margin-bottom:10px;overflow:hidden;">';
      h += '<img src="' + escAttr(item.org_image_url) + '" style="max-width:100%;max-height:100%;object-fit:contain;" onerror="this.style.display=none">';
      h += '</div>';
    }

    h += '<div style="margin-bottom:10px;"><div style="color:#86868b;font-size:10px;font-weight:600;text-transform:uppercase;margin-bottom:4px;">基本信息</div>';
    [
      ['商品名', item.name],
      ['编码', item.code],
      ['原始品牌', item.original_brand || item.brand],
      ['原始分类', item.original_category || item.category],
    ].forEach(function(r){
      if (!r[1]) return;
      h += '<div style="display:flex;justify-content:space-between;font-size:11px;line-height:2;"><span style="color:#6e6e73;">' + esc(r[0]) + '</span><span>' + esc(String(r[1])) + '</span></div>';
    });
    h += '</div>';

    if (item.brand_ai) {
      h += '<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);border-radius:8px;padding:10px;margin-bottom:8px;">';
      h += '<div style="color:#86868b;font-size:10px;font-weight:600;text-transform:uppercase;margin-bottom:4px;">品牌</div>';
      h += '<span style="font-weight:500;">' + esc(item.brand_ai) + '</span> ';
      h += '<span style="font-size:10px;color:#98989d;">置信度 ' + item.brand_confidence + ' · ' + esc(item.brand_type||'') + '</span>';
      h += '</div>';
    }

    if (item.category_ai) {
      h += '<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);border-radius:8px;padding:10px;margin-bottom:8px;">';
      h += '<div style="color:#86868b;font-size:10px;font-weight:600;text-transform:uppercase;margin-bottom:4px;">分类</div>';
      h += '<span>' + esc(item.category_ai) + '</span>';
      h += '</div>';
    }

    h += '<div style="display:flex;gap:8px;margin-top:12px;"><button class="electron-btn primary" onclick="electronCloseDetail()">关闭</button></div>';
    el.innerHTML = h;
  }

  // ═══ Brand Library Overlay Page ═══
  function renderBrandDatabasePage() {
    var existing = document.getElementById('electronBrandPanel');
    if (existing) { existing.remove(); return; }
    fetch('/api/brands/list').then(function(r){return r.json()}).then(function(d){
      var brands = d.brands || [];
      if (!Array.isArray(brands)) { brands = Object.values(brands); }
      var h = '<div id="electronBrandPanel" style="position:fixed;top:0;left:220px;right:0;bottom:0;z-index:50;background:#0f172a;padding:20px;overflow-y:auto;font-family:-apple-system,SF Pro Text,system-ui,sans-serif;">';
      h += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">';
      h += '<h2 style="font-size:18px;font-weight:700;">品牌数据库 <span style="color:#86868b;font-size:13px;font-weight:400;">共 ' + brands.length + ' 个品牌</span></h2>';
      h += '<button onclick="document.getElementById(\'electronBrandPanel\').remove()" style="background:none;border:none;color:#86868b;font-size:20px;cursor:pointer;">✕</button></div>';
      h += '<div style="margin-bottom:12px;"><input placeholder="搜索品牌..." id="electronBrandSearch" oninput="var v=this.value.toLowerCase();var rows=document.querySelectorAll(\'#electronBrandPanel tbody tr\');for(var i=0;i<rows.length;i++){rows[i].style.display=rows[i].textContent.toLowerCase().indexOf(v)>=0?\'\':\'none\'}" style="padding:6px 10px;background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.1);border-radius:6px;color:#fff;width:240px;font-size:12px;"></div>';
      h += '<table style="width:100%;font-size:12px;border-collapse:collapse;">';
      h += '<thead><tr style="text-align:left;color:#86868b;text-transform:uppercase;font-size:10px;border-bottom:1px solid rgba(255,255,255,0.06);">';
      h += '<th style="padding:8px 10px;">标准名</th><th style="padding:8px 10px;">别名</th><th style="padding:8px 10px;">类型</th><th style="padding:8px 10px;">产地</th>';
      h += '</tr></thead><tbody>';
      brands.forEach(function(b){
        h += '<tr style="border-bottom:1px solid rgba(255,255,255,0.03);">';
        h += '<td style="padding:8px 10px;font-weight:500;">' + esc(b.display_name||b.name) + '</td>';
        h += '<td style="padding:8px 10px;color:#98989d;">' + esc((b.aliases||[]).join(', ')) + '</td>';
        h += '<td style="padding:8px 10px;">' + esc(b.type||'') + '</td>';
        h += '<td style="padding:8px 10px;">' + esc(b.country||'') + '</td>';
        h += '</tr>';
      });
      h += '</tbody></table></div>';
      document.body.insertAdjacentHTML('beforeend', h);
    });
  }

  // ═══ Category Tree Overlay Page ═══
  function renderCategoryTreePage() {
    var existing = document.getElementById('electronCategoryPanel');
    if (existing) { existing.remove(); return; }
    var h = '<div id="electronCategoryPanel" style="position:fixed;top:0;left:220px;right:0;bottom:0;z-index:50;background:#0f172a;padding:20px;overflow-y:auto;font-family:-apple-system,SF Pro Text,system-ui,sans-serif;">';
    h += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">';
    h += '<h2 style="font-size:18px;font-weight:700;">分类路径树</h2>';
    h += '<button onclick="document.getElementById(\'electronCategoryPanel\').remove()" style="background:none;border:none;color:#86868b;font-size:20px;cursor:pointer;">✕</button></div>';
    h += '<p style="color:#94a3b8;">上传文件完成诊断后，分类路径树将在此显示。</p>';
    h += '</div>';
    document.body.insertAdjacentHTML('beforeend', h);
  }

  // Helpers
  function esc(s) {
    if (!s) return '';
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }
  function escHtml(s) { return esc(s); }
  function escAttr(s) {
    if (!s) return '';
    return String(s).replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
  }

  // Init
  renderSteps();
  loadElectronGroups();
  loadElectronHistory();
})();
