// detail-panel.js — Shared product detail panel (slide-in from right)
// Used by: electron review tab, brand/category panels, diagnosis.js product clicks

function openDetail(item, mode) {
  var detailMode = mode || (window._settings && window._settings.detail_mode) || 'sidebar';
  if (detailMode === 'window' && window.electronAPI) {
    window.electronAPI.openDetailWindow(item);
    return;
  }
  document.getElementById('detailOverlay').classList.add('open');
  (window._dpRenderDetail || renderDetail)(item);
  document.getElementById('detailPanel').classList.add('open');
}

function closeDetail() {
  document.getElementById('detailOverlay').classList.remove('open');
  document.getElementById('detailPanel').classList.remove('open');
  (window._dpCancelEdit || cancelEdit)();
}

// Keep references for electron mode (review.js overwrites these global functions)
window._dpOpenDetail = openDetail;
window._dpCloseDetail = closeDetail;
window._dpRenderDetail = renderDetail;
window._dpConfirmItem = confirmItem;
window._dpSaveEdit = saveEdit;
window._dpEditItem = editItem;
window._dpCancelEdit = cancelEdit;

// ── Helpers ──
function _brandStatusLabel(status) {
  var map = {
    'ai_ok': 'AI 分析', 'from_library': '品牌库命中', 'no_brand': '无品牌',
    'error': 'AI 出错', 'skipped': '已跳过', 'local': '本地提取',
  };
  return map[status] || status || '';
}

function _catStatusLabel(status) {
  var map = {
    'ai_ok': 'AI 分析', 'out_of_range': '超出范围',
    'local_fallback': '本地回退', 'skipped': '已跳过',
  };
  return map[status] || status || '';
}

function renderDetail(item) {
  var code = item.code || '';

  var rows = [
    ['商品名', item.name],
    ['商品编码', item.code],
    ['原始品牌', item.original_brand],
    ['AI 品牌', item.brand_ai, item.brand_type ? item.brand_type : ''],
    ['品牌置信度', item.brand_confidence],
    ['品牌来源', _brandStatusLabel(item.brand_status)],
    ['品牌理由', item.brand_reason],
    ['原始规格 (spu_spec)', item.spec_original],
    ['商品名提取规格', item.spec_from_name],
    ['原始分类', item.original_category],
    ['AI 分类', item.category_ai],
    ['分类置信度', item.category_confidence],
    ['分类来源', _catStatusLabel(item.category_status)],
    ['分类方式', item.category_method],
    ['分类理由', item.category_reason],
    ['品种词', item.category_entity],
    ['修饰词', item.category_modifiers],
  ];

  var tagFields = [
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

  var html = '';

  // Status + action buttons
  var status = item.review_status || '待复核';
  var statusColor = status === '已确认' ? '#16a34a' : status === '已修改' ? '#3b82f6' : '#f59e0b';
  html += '<div class="flex items-center justify-between mb-4" style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;">';
  html += '<span class="text-sm" style="color:var(--text-secondary);">状态: <b style="color:' + statusColor + '">' + esc(status) + '</b></span>';
  html += '<div class="flex gap-2" style="display:flex;gap:8px;">';
  html += '<button onclick="confirmItem(\'' + escAttr(code) + '\')" class="btn btn-success" style="font-size:11px;padding:6px 12px;">确认</button>';
  html += '<button onclick="editItem(\'' + escAttr(code) + '\')" class="btn btn-primary" style="font-size:11px;padding:6px 12px;">修改</button>';
  html += '</div>';
  html += '</div>';

  // Image
  if (item.org_image_url) {
    html += '<div style="margin-bottom:16px;">';
    html += '<img src="' + escAttr(item.org_image_url) + '" alt="商品图" style="width:100%;max-height:180px;object-fit:contain;border-radius:6px;background:var(--bg-tertiary);cursor:pointer;" onerror="this.style.display=\'none\'">';
    html += '</div>';
  }

  // Basic info rows
  html += '<div style="margin-bottom:16px;">';
  html += '<div class="sidebar-section" style="margin:0 0 8px;color:var(--text-tertiary);font-size:9px;font-weight:600;text-transform:uppercase;">基本信息</div>';
  rows.forEach(function(r) {
    var label = r[0], value = r[1], extra = r[2];
    if (!value && value !== 0) return;
    html += '<div style="font-size:10px;line-height:2;display:flex;justify-content:space-between;">';
    html += '<span style="color:var(--text-quaternary);">' + esc(label) + '</span>';
    html += '<span style="color:var(--text-primary);">' + esc(String(value));
    if (extra) html += ' <span style="color:var(--text-secondary);font-size:9px;">' + esc(extra) + '</span>';
    html += '</span></div>';
  });
  html += '</div>';

  // Tags
  var hasTags = tagFields.some(function(t) { return !!t[1]; });
  if (hasTags) {
    html += '<div style="border-top:1px solid var(--border-primary);padding-top:12px;margin-bottom:12px;">';
    html += '<div class="sidebar-section" style="margin:0 0 8px;color:var(--text-tertiary);font-size:9px;font-weight:600;text-transform:uppercase;">标签</div>';
    tagFields.forEach(function(t) {
      var label = t[0], value = t[1], cssClass = t[2];
      if (!value) return;
      html += '<div style="font-size:10px;line-height:2;">';
      html += '<span style="color:var(--text-quaternary);">' + esc(label) + ': </span>';
      if (cssClass) {
        html += '<span class="' + cssClass + '">' + esc(String(value)) + '</span>';
      } else {
        html += '<span style="color:var(--text-primary);">' + esc(String(value)) + '</span>';
      }
      html += '</div>';
    });
    html += '</div>';
  }

  // Edit form (hidden by default)
  html += '<div id="editForm" class="hidden" style="border-top:1px solid var(--border-primary);padding-top:12px;">';
  html += '<div class="sidebar-section" style="margin:0 0 8px;color:var(--text-tertiary);font-size:9px;font-weight:600;text-transform:uppercase;">编辑</div>';
  html += '<label style="font-size:10px;color:var(--text-quaternary);">品牌</label>';
  html += '<input id="editBrand" style="width:100%;margin-bottom:8px;padding:6px 8px;border:1px solid var(--border-primary);border-radius:4px;background:var(--bg-tertiary);color:var(--text-primary);font-size:12px;" value="' + escAttr(item.brand_ai || '') + '">';
  html += '<label style="font-size:10px;color:var(--text-quaternary);">分类</label>';
  html += '<input id="editCategory" style="width:100%;margin-bottom:8px;padding:6px 8px;border:1px solid var(--border-primary);border-radius:4px;background:var(--bg-tertiary);color:var(--text-primary);font-size:12px;" value="' + escAttr(item.category_ai || '') + '">';
  html += '<div class="flex gap-2" style="display:flex;gap:8px;">';
  html += '<button class="btn btn-primary" style="flex:1;font-size:11px;" onclick="saveEdit(\'' + escAttr(code) + '\')">保存</button>';
  html += '<button class="btn btn-ghost" style="font-size:11px;" onclick="cancelEdit()">取消</button>';
  html += '</div></div>';

  document.getElementById('detailContent').innerHTML = html;
}

function editItem(code) {
  var form = document.getElementById('editForm');
  if (form) form.classList.remove('hidden');
}

function cancelEdit() {
  var form = document.getElementById('editForm');
  if (form) form.classList.add('hidden');
}

// ── Actions ──
function _getReviewSid() {
  // Try review.js's R.sid, fallback to common.js sessionId
  try { if (typeof R !== 'undefined' && R.sid) return R.sid; } catch(e) {}
  try { if (typeof sessionId !== 'undefined' && sessionId) return sessionId; } catch(e) {}
  return '';
}

async function confirmItem(code) {
  var sid = _getReviewSid();
  try {
    await fetch('/api/review/decision', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sid, code: code, action: 'confirm' }),
    });
    // Update local review data if available
    try {
      if (typeof R !== 'undefined' && R.data) {
        var item = R.data.find(function(d) { return d.code === code; });
        if (item) item.review_status = '已确认';
        if (typeof updateProgress === 'function') updateProgress();
        if (typeof applyFilters === 'function') applyFilters();
      }
    } catch(e) {}
    closeDetail();
  } catch(e) {
    console.error('confirmItem failed:', e);
  }
}

async function saveEdit(code) {
  var brand = document.getElementById('editBrand').value.trim();
  var category = document.getElementById('editCategory').value.trim();
  var changes = {};
  if (brand) changes.brand_ai = brand;
  if (category) changes.category_ai = category;

  var sid = _getReviewSid();
  try {
    await fetch('/api/review/decision', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sid, code: code, action: 'modify', changes: changes }),
    });
    // Update local review data if available
    try {
      if (typeof R !== 'undefined' && R.data) {
        var item = R.data.find(function(d) { return d.code === code; });
        if (item) {
          item.review_status = '已修改';
          if (changes.brand_ai) item.brand_ai = changes.brand_ai;
          if (changes.category_ai) item.category_ai = changes.category_ai;
        }
        if (typeof updateProgress === 'function') updateProgress();
        if (typeof applyFilters === 'function') applyFilters();
      }
    } catch(e) {}
    closeDetail();
  } catch(e) {
    console.error('saveEdit failed:', e);
  }
}

// ── Escape helpers (guarded, may already exist) ──
if (typeof esc === 'undefined') {
  function esc(s) {
    if (!s) return '';
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
}
if (typeof escAttr === 'undefined') {
  function escAttr(s) {
    if (!s) return '';
    return String(s).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }
}
