// sidebar.js — Sidebar navigation and session step management

// State
const S = {
  currentSession: null,
  currentPage: 'upload',
  sessionSteps: [
    { id: 'upload', label: '1 上传 & 诊断', status: '' },
    { id: 'brand-review', label: '2 品牌审核', status: '' },
    { id: 'ai-process', label: '3 AI 处理', status: '' },
    { id: 'review', label: '4 复核', status: '' },
    { id: 'export', label: '5 导出', status: '' },
  ],
};

function initSidebar() {
  renderSessionSteps();
  loadSidebarGroups();
  loadSidebarHistory();
}

function renderSessionSteps() {
  const container = document.getElementById('sidebarSessionSteps');
  if (!container) return;
  container.innerHTML = S.sessionSteps.map(step => {
    const isActive = step.id === S.currentPage;
    const isCompleted = step.status === 'completed';
    let cls = 'sidebar-item';
    if (isActive) cls += ' active';
    else if (isCompleted) cls += ' completed';
    return '<div class="' + cls + '" onclick="switchTab(\'' + step.id + '\')">' +
      step.label +
      (isCompleted ? '<span class="badge badge-success" style="margin-left:auto">✓</span>' : '') +
      '</div>';
  }).join('');
}

function setStepStatus(stepId, status) {
  const step = S.sessionSteps.find(s => s.id === stepId);
  if (step) {
    step.status = status;
    renderSessionSteps();
  }
}

async function loadSidebarGroups() {
  try {
    const res = await fetch('/api/groups');
    const data = await res.json();
    const sel = document.getElementById('sidebarGroupSelect');
    if (!sel) return;
    const current = sel.value;
    sel.innerHTML = '<option value="">-- 选择分组 --</option>';
    for (const [id, g] of Object.entries(data.groups || {})) {
      sel.innerHTML += '<option value="' + id + '">📁 ' + escHtml(g.name) + '</option>';
    }
    sel.value = current;
  } catch (e) { console.error('loadSidebarGroups:', e); }
}

async function loadSidebarHistory() {
  const container = document.getElementById('sidebarHistory');
  if (!container) return;
  try {
    const res = await fetch('/api/recent_files');
    const files = await res.json();
    container.innerHTML = files.slice(0, 5).map(f =>
      '<div class="sidebar-item" style="font-size:10px;" onclick="importRecentFile(\'' + f.id + '\')">' +
        (f.time ? f.time.split(' ')[0] : '') + ' · ' + (f.name || '').substring(0, 20) +
      '</div>'
    ).join('');
  } catch (e) { container.innerHTML = ''; }
}

function switchGroup(groupId) {
  localStorage.setItem('last_group_id', groupId);
  const uploadGroup = document.getElementById('uploadGroup');
  if (uploadGroup) uploadGroup.value = groupId;
  loadSidebarHistory();
}

function navigateTo(page) {
  S.currentPage = page;
  renderSessionSteps();

  // Deactivate all tab items
  document.querySelectorAll('.tab-item').forEach(t => t.classList.remove('active'));

  // Show the page content
  showPageContent(page);
}

function switchTab(tabId) {
  S.currentPage = tabId;
  renderSessionSteps();

  // Update tab bar
  document.querySelectorAll('.tab-item').forEach(t => {
    t.classList.toggle('active', t.dataset.tab === tabId);
  });

  // Show the tab content
  showPageContent(tabId);
}

function showPageContent(pageId) {
  // Hide all tab panels and page content
  document.querySelectorAll('.tab-panel, .page-content').forEach(p => p.classList.add('hidden'));

  // Show the selected one
  const panel = document.getElementById('panel-' + pageId);
  if (panel) panel.classList.remove('hidden');
}

function openSettings() {
  if (window.electronAPI) {
    window.electronAPI.openSettings();
  } else {
    // Web fallback
    alert('Settings available in Electron desktop app');
  }
}

function initTabBar() {
  // No-op: tab bar is static HTML, switching handled by switchTab()
}
