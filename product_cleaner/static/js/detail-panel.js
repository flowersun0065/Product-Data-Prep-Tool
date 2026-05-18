// detail-panel.js — Shared product detail panel (slide-in from right)

function openDetail(item, mode) {
  const detailMode = mode || (window._settings && window._settings.detail_mode) || 'sidebar';

  if (detailMode === 'window' && window.electronAPI) {
    window.electronAPI.openDetailWindow(item);
    return;
  }

  renderDetail(item);
  document.getElementById('detailPanel').classList.add('open');
  document.getElementById('detailOverlay').classList.add('open');
}

function closeDetail() {
  document.getElementById('detailPanel').classList.remove('open');
  document.getElementById('detailOverlay').classList.remove('open');
  cancelEdit();
}

function renderDetail(item) {
  var brandSourceLabel = {
    'ai_ok': 'AI 分析', 'from_library': '品牌库命中', 'no_brand': '无品牌',
    'error': 'AI 出错', 'skipped': '已跳过', 'local': '本地提取',
  };

  var catSourceLabel = {
    'ai_ok': 'AI 分析', 'out_of_range': '超出范围',
    'local_fallback': '本地回退', 'skipped': '已跳过',
  };

  var brandStatusText = brandSourceLabel[item.brand_status] || item.brand_status || '';
  var catStatusText = catSourceLabel[item.category_status] || item.category_status || '';

  var html = '';
  html += '<div class="flex items-center justify-between mb-3" style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;">';
  html += '<span style="font-size:12px;font-weight:600;">商品详情</span>';
  html += '<button onclick="closeDetail()" style="background:none;border:none;color:var(--text-tertiary);cursor:pointer;font-size:16px;">✕</button>';
  html += '</div>';

  // Image
  if (item.org_image_url) {
    html += '<div style="background:var(--bg-tertiary);border-radius:6px;height:100px;display:flex;align-items:center;justify-content:center;margin-bottom:10px;overflow:hidden;">';
    html += '<img src="' + escAttr(item.org_image_url) + '" style="max-width:100%;max-height:100%;object-fit:contain;" onerror="this.style.display=\'none\'">';
    html += '</div>';
  }

  // Basic info
  html += '<div class="mb-3" style="margin-bottom:10px;">';
  html += '<div class="sidebar-section" style="margin:0 0 4px;color:var(--text-tertiary);font-size:9px;font-weight:600;text-transform:uppercase;">基本信息</div>';

  var rows = [
    ['商品名', item.name],
    ['商品编码', item.code],
    ['原始品牌', item.original_brand || item.brand],
    ['原始分类', item.original_category || item.category],
  ];

  rows.forEach(function(row) {
    if (!row[1]) return;
    html += '<div style="display:flex;justify-content:space-between;font-size:10px;line-height:2;">';
    html += '<span style="color:var(--text-quaternary);">' + esc(row[0]) + '</span>';
    html += '<span style="color:var(--text-primary);">' + esc(String(row[1])) + '</span>';
    html += '</div>';
  });
  html += '</div>';

  // Brand status
  if (item.brand_ai) {
    html += '<div class="mb-3" style="margin-bottom:10px;background:var(--bg-tertiary);border:1px solid var(--border-primary);border-radius:6px;padding:10px;">';
    html += '<div class="sidebar-section" style="margin:0 0 4px;color:var(--text-tertiary);font-size:9px;font-weight:600;text-transform:uppercase;">品牌</div>';
    html += '<div style="display:flex;justify-content:space-between;">';
    html += '<span style="color:var(--text-primary);font-weight:500;">' + esc(item.brand_ai) + '</span>';
    html += '<span class="badge ' + (item.review_status === '已确认' ? 'badge-success' : 'badge-warning') + '">' + esc(brandStatusText) + '</span>';
    html += '</div>';
    if (item.brand_confidence) {
      html += '<div style="color:var(--text-secondary);font-size:9px;margin-top:2px;">置信度 ' + item.brand_confidence + ' · ' + esc(item.brand_type || '') + '</div>';
    }
    if (item.brand_reason) {
      html += '<div style="color:var(--text-secondary);font-size:9px;">' + esc(item.brand_reason) + '</div>';
    }
    html += '</div>';
  }

  // Category status
  if (item.category_ai) {
    html += '<div class="mb-3" style="margin-bottom:10px;background:var(--bg-tertiary);border:1px solid var(--border-primary);border-radius:6px;padding:10px;">';
    html += '<div class="sidebar-section" style="margin:0 0 4px;color:var(--text-tertiary);font-size:9px;font-weight:600;text-transform:uppercase;">分类</div>';
    html += '<div style="display:flex;justify-content:space-between;">';
    html += '<span style="color:var(--text-primary);">' + esc(item.category_ai) + '</span>';
    html += '<span class="badge badge-info">' + esc(catStatusText) + '</span>';
    html += '</div>';
    if (item.category_entity) {
      html += '<div style="color:var(--text-secondary);font-size:9px;margin-top:2px;">品种词: ' + esc(item.category_entity) + ' · 方式: ' + esc(item.category_method || '') + '</div>';
    }
    html += '</div>';
  }

  // Tags
  var tags = [
    { key: 'promo_tag', label: '促销标签', css: 'badge-danger' },
    { key: 'recommend_tag', label: '推荐标签', css: 'badge-info' },
    { key: 'self_operated_tag', label: '自营标签', css: '' },
    { key: 'import_tag', label: '进口/国产', css: item.import_tag === '进口' ? 'badge-info' : '' },
  ];
  html += '<div class="mb-3" style="margin-bottom:10px;">';
  html += '<div class="sidebar-section" style="margin:0 0 4px;color:var(--text-tertiary);font-size:9px;font-weight:600;text-transform:uppercase;">标签</div>';
  html += '<div class="flex gap-2" style="display:flex;gap:8px;flex-wrap:wrap;">';
  tags.forEach(function(t) {
    if (!item[t.key]) return;
    html += '<span class="badge ' + t.css + '">' + esc(item[t.key]) + '</span>';
  });
  html += '</div></div>';

  // Action buttons
  html += '<div class="flex gap-2" style="display:flex;gap:8px;">';
  if (item.review_status !== '已确认') {
    html += '<button class="btn btn-success" style="flex:1;" onclick="confirmItem(\'' + escAttr(item.code) + '\')">✓ 确认品牌</button>';
  }
  html += '<button class="btn btn-primary" style="flex:1;" onclick="editItem(\'' + escAttr(item.code) + '\')">✎ 修改分类</button>';
  html += '<button class="btn btn-ghost" onclick="skipItem(\'' + escAttr(item.code) + '\')">跳过</button>';
  html += '</div>';

  // Edit form (hidden by default)
  html += '<div id="editForm" class="hidden" style="border-top:1px solid var(--border-primary);padding-top:10px;margin-top:10px;">';
  html += '<div class="sidebar-section" style="margin:0 0 6px;color:var(--text-tertiary);font-size:9px;font-weight:600;text-transform:uppercase;">编辑</div>';
  html += '<label style="font-size:9px;color:var(--text-tertiary);">品牌</label>';
  html += '<input id="editBrand" style="width:100%;margin-bottom:6px;" value="' + escAttr(item.brand_ai || '') + '">';
  html += '<label style="font-size:9px;color:var(--text-tertiary);">分类</label>';
  html += '<input id="editCategory" style="width:100%;margin-bottom:6px;" value="' + escAttr(item.category_ai || '') + '">';
  html += '<div class="flex gap-2" style="display:flex;gap:8px;">';
  html += '<button class="btn btn-primary" style="flex:1;" onclick="saveDetailEdit(\'' + escAttr(item.code) + '\')">保存</button>';
  html += '<button class="btn btn-ghost" onclick="cancelEdit()">取消</button>';
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

async function saveDetailEdit(code) {
  var brand = document.getElementById('editBrand').value;
  var category = document.getElementById('editCategory').value;
  try {
    await fetch('/api/review/decision', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: typeof sessionId !== 'undefined' ? sessionId : '',
        code: code,
        action: 'modify',
        changes: { brand_ai: brand, category_ai: category },
      }),
    });
    closeDetail();
    if (typeof fetchData === 'function') fetchData();
  } catch (e) {
    alert('保存失败: ' + e.message);
  }
}

// Shared escape functions (also used by other modules)
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
