// ═══ Electron: Task Panel (reusable task-type right-column panel) ═══
// Generic async task monitor. Each task = one work unit, expandable for detail.
// Usage: _taskPanelOpen(title) → _taskPanelUpsert(task) → _taskPanelClose()
(function(){
  if (!window._electronMode) return;

  var _tpPanelId = '_taskPanel';
  var _tpTasks = {};
  var _tpOrder = [];
  var _tpOpen = false;

  function _tpEnsure() {
    if (_tpOpen) return;
    _tpOpen = true;
    var el = document.createElement('div');
    el.id = _tpPanelId;
    el.style.cssText = 'display:flex;flex-direction:column;';

    var wrapper = document.createElement('div');
    wrapper.style.cssText = 'display:flex;flex-direction:column;height:100%;';
    var list = document.createElement('div');
    list.id = '_tpList';
    list.style.cssText = 'flex:1;overflow-y:auto;padding:8px 10px;';
    wrapper.appendChild(list);
    el.appendChild(wrapper);

    var storage = document.getElementById('_panelStorage');
    if (!storage) { storage = document.createElement('div'); storage.id = '_panelStorage'; storage.style.display = 'none'; document.body.appendChild(storage); }
    storage.appendChild(el);
  }

  var _statusIcon = {pending:'○', active:'◌', done:'✓', error:'✗'};
  var _statusColor = {pending:'var(--text-muted)', active:'var(--accent)', done:'var(--green)', error:'var(--red)'};

  // ── Public API ──

  window._taskPanelOpen = function(title) {
    _tpEnsure();
    var t = document.getElementById('_tpTitle');
    if (t) t.textContent = title || '任务监控';
    if (typeof _movePanelToCard === 'function') {
      _movePanelToCard(_tpPanelId, _tpPanelId, title || '任务监控');
    }
  };

  window._taskPanelUpsert = function(task) {
    var id = task.id || String(Date.now());
    var existing = _tpTasks[id];
    _tpTasks[id] = task;
    if (!existing) _tpOrder.push(id);

    var list = document.getElementById('_tpList');
    if (!list) return;

    var row = document.getElementById('_tpTask-' + id);
    if (!row) {
      row = document.createElement('div');
      row.id = '_tpTask-' + id;
      row.style.cssText = 'margin-bottom:6px;';
      list.appendChild(row);
    }

    var icon = _statusIcon[task.status] || '○';
    var color = _statusColor[task.status] || 'var(--text-muted)';
    var tk = task.tokens || {};
    var spin = task.status === 'active' ? 'animation:_tpSpin 1.5s ease-in-out infinite;' : '';

    // 清空旧内容再重建（upsert 语义）
    row.textContent = '';

    var card = document.createElement('div');
    card.style.cssText = 'border:1px solid var(--border);border-radius:var(--radius-md);background:var(--panel);overflow:hidden;margin-bottom:6px;';

    // Card header（可点击折叠/展开）
    var hdr = document.createElement('div');
    hdr.style.cssText = 'display:flex;align-items:center;justify-content:space-between;padding:8px 10px;cursor:pointer;';
    (function(tid, hasDetail) {
      hdr.addEventListener('click', function() {
        var b = document.getElementById('_tpBody-' + tid);
        if (!b) return;
        var s = b.style.maxHeight;
        b.style.maxHeight = (!s || s === '0px') ? (hasDetail ? '800px' : '0px') : '0px';
        var a = this.querySelector('.tp-arrow');
        if (a) a.style.transform = b.style.maxHeight === '0px' ? 'rotate(0deg)' : 'rotate(90deg)';
      });
    })(id, !!task.detail);

    // 左侧：icon + title
    var left = document.createElement('div');
    left.style.cssText = 'display:flex;align-items:center;gap:8px;';
    var iconEl = document.createElement('span');
    iconEl.style.cssText = 'color:' + color + ';font-weight:bold;font-size:14px;' + spin;
    iconEl.textContent = icon;
    left.appendChild(iconEl);
    var titleEl = document.createElement('span');
    titleEl.style.cssText = 'font-size:12px;color:var(--text-main);font-weight:500;';
    titleEl.textContent = task.title || id;
    left.appendChild(titleEl);
    hdr.appendChild(left);

    // 右侧：meta + tokens + arrow
    var right = document.createElement('div');
    right.style.cssText = 'display:flex;align-items:center;gap:8px;';
    var metaEl = document.createElement('span');
    metaEl.style.cssText = 'font-size:10px;color:var(--text-muted);';
    metaEl.textContent = task.meta || '';
    right.appendChild(metaEl);
    if (tk.total_tokens) {
      var tokEl = document.createElement('span');
      tokEl.style.cssText = 'font-size:10px;color:var(--text-sub);';
      tokEl.textContent = 'in:' + (tk.prompt_tokens || 0) + ' out:' + (tk.completion_tokens || 0);
      right.appendChild(tokEl);
    }
    if (task.detail) {
      var arrowSvg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
      arrowSvg.setAttribute('class', 'tp-arrow');
      arrowSvg.setAttribute('width', '10');
      arrowSvg.setAttribute('height', '10');
      arrowSvg.setAttribute('viewBox', '0 0 24 24');
      arrowSvg.setAttribute('fill', 'none');
      arrowSvg.setAttribute('stroke', 'var(--text-muted)');
      arrowSvg.setAttribute('stroke-width', '2');
      arrowSvg.style.cssText = 'transition:transform 0.2s;flex-shrink:0;';
      var polyline = document.createElementNS('http://www.w3.org/2000/svg', 'polyline');
      polyline.setAttribute('points', '9 18 15 12 9 6');
      arrowSvg.appendChild(polyline);
      right.appendChild(arrowSvg);
    }
    hdr.appendChild(right);
    card.appendChild(hdr);

    // Card body（可展开）
    var bodyWrap = document.createElement('div');
    bodyWrap.id = '_tpBody-' + id;
    bodyWrap.style.cssText = 'max-height:0;overflow:hidden;transition:max-height 0.3s ease;';
    var bodyContent = document.createElement('div');
    bodyContent.style.cssText = 'padding:0 10px 10px 26px;font-size:10px;color:var(--text-sub);line-height:1.5;white-space:pre-wrap;border-top:1px solid var(--border-light);max-height:400px;overflow-y:auto;';
    bodyContent.textContent = task.detail || '';
    bodyWrap.appendChild(bodyContent);
    card.appendChild(bodyWrap);

    row.appendChild(card);

    list.scrollTop = list.scrollHeight;
  };

  window._taskPanelClose = function() {
    if (typeof _closePanelCard === 'function') {
      _closePanelCard(_tpPanelId, _tpPanelId);
    }
    _tpOpen = false;
  };

  window._taskPanelReset = function() {
    _tpTasks = {};
    _tpOrder = [];
    var list = document.getElementById('_tpList');
    if (list) list.textContent = '';
  };

  // CSS animation for active spinner
  var style = document.createElement('style');
  style.textContent = '@keyframes _tpSpin{0%,100%{opacity:1}50%{opacity:0.3}}';
  document.head.appendChild(style);

  setTimeout(function(){
    var checks = ['_taskPanelOpen','_taskPanelUpsert','_taskPanelClose','_taskPanelReset'];
    var missing = checks.filter(function(k){ return typeof window[k] !== 'function'; });
    if (missing.length) console.error('task_panel: MISSING exports:', missing.join(', '));
    else console.log('task_panel: all ' + checks.length + ' exports OK');
  }, 100);
})();
