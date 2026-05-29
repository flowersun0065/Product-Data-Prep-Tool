// ═══ Agent Timeline State Machine ═══
// Self-contained upload + diagnosis polling + timeline card driver.
// Only active in electron mode.

(function(){
  if (!window._electronMode) return;

  var _tlPollTimer = null;
  var _tlStepLogCounts = {};
  var _tlSteps = [
    { id: 'cardRead',   conn: 'connRead',   time: 'timeRead',   bodyType: 'kv',  bodyId: 'kvRead',    label: '读取源数据' },
    { id: 'cardBrand',  conn: 'connBrand',  time: 'timeBrand',  bodyType: 'log', bodyId: 'logBrand',   label: '知识库关联 & 品牌分析' },
    { id: 'cardCate',   conn: 'connCate',   time: 'timeCate',   bodyType: 'log', bodyId: 'logCate',    label: '多级分类归集与映射' },
    { id: 'cardFinish', conn: 'connFinish', time: 'timeFinish', bodyType: 'log', bodyId: 'logFinish',  label: '数据精简 & 路由输出' }
  ];
  var _tlStepMap = { reading: 0, brands: 1, categories: 2, finalizing: 3 };

  function el(id) { return document.getElementById(id); }
  function show(el) { if (el) el.style.display = ''; }

  function cardState(idx, state) {
    var s = _tlSteps[idx];
    var card = el(s.id);
    var conn = el(s.conn);
    if (card) { window._tlSetState(card, state); show(card); }
    if (conn) show(conn);
  }

  function fillTime(idx, val) {
    var card = el(_tlSteps[idx].id);
    window._tlSetTime(card, val);
  }

  function appendLog(idx, line) {
    var bodyId = _tlSteps[idx].bodyId;
    if (!bodyId) return;
    var logEl = el(bodyId);
    if (!logEl) return;
    window._tlAppendLog(logEl, '→ ' + line);
  }

  // ── Upload ──
  async function doUpload(file) {
    // Cancel any in-progress session restore
    _tlRestoring = false;
    stop();
    // Reset all cards
    for (var i = 0; i < 4; i++) { var c = el(_tlSteps[i].id); var cn = el(_tlSteps[i].conn); if (c) { c.style.display = 'none'; c.classList.remove('active', 'done', 'pending'); } if (cn) cn.style.display = 'none'; }
    document.getElementById('tlAction').style.display = 'none';
    var drop = el('tlDrop');
    if (drop) {
      drop.classList.add('file-loaded');
      drop.textContent = '';
      var _checkSvg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
      _checkSvg.setAttribute('width', '18'); _checkSvg.setAttribute('height', '18');
      _checkSvg.setAttribute('viewBox', '0 0 24 24'); _checkSvg.setAttribute('fill', 'none');
      _checkSvg.setAttribute('stroke', 'var(--green)'); _checkSvg.setAttribute('stroke-width', '2');
      _checkSvg.setAttribute('stroke-linecap', 'round'); _checkSvg.setAttribute('stroke-linejoin', 'round');
      var _cp = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      _cp.setAttribute('d', 'M20 6L9 17l-5-5'); _checkSvg.appendChild(_cp);
      var _ns = document.createElement('span');
      _ns.style.cssText = 'font-size:13px;font-weight:500;color:var(--text-main);';
      _ns.textContent = file.name || '';
      var _ss = document.createElement('span');
      _ss.style.cssText = 'font-size:12px;color:var(--text-muted);margin-left:auto;';
      _ss.textContent = '上传中...';
      drop.appendChild(_checkSvg); drop.appendChild(_ns); drop.appendChild(_ss);
    }
    try {
      var fd = new FormData();
      fd.append('file', file);
      fd.append('group_id', el('uploadGroup').value || '');
      var r = await fetch('/api/upload', { method: 'POST', body: fd });
      var d = await r.json();
      if (d.error) throw new Error(d.error);
      window.sessionId = d.session_id;
      if (window.commonSessionId !== undefined) window.commonSessionId = d.session_id;
      localStorage.setItem('last_session_id', d.session_id);
      if (drop) {
        var lastSpan = drop.querySelector('span:last-child');
        if (lastSpan) lastSpan.textContent = '已上传，诊断中...';
      }
      start();
    } catch (e) {
      if (drop) {
        var ls = drop.querySelector('span:last-child');
        if (ls) { ls.textContent = '上传失败'; ls.style.color = 'var(--red)'; }
      }
    }
  }

  // ── Polling ──
  function start() {
    if (!window.sessionId) { setTimeout(start, 300); return; }
    _tlStepLogCounts = {};
    cardState(0, 'active');
    _tlPollTimer = setInterval(poll, 1500);
    poll();
  }

  function stop() {
    if (_tlPollTimer) { clearInterval(_tlPollTimer); _tlPollTimer = null; }
  }

  async function poll() {
    if (!window.sessionId) return stop();
    try {
      var r = await fetch('/api/diagnosis_status?sid=' + window.sessionId);
      var d = await r.json();
      if (d.error) { stop(); return; }

      var cs = d.current_step;
      var activeIdx = _tlStepMap[cs] != null ? _tlStepMap[cs] : -1;

      for (var i = 0; i < 4; i++) {
        if (activeIdx >= 0 && i < activeIdx) cardState(i, 'done');
        else if (i === activeIdx) cardState(i, 'active');
        else if (activeIdx >= 0 && i > activeIdx) cardState(i, 'pending');
      }

      // Step times
      var st = d.step_times || {};
      if (st.reading_start && st.reading_end) fillTime(0, (st.reading_end - st.reading_start).toFixed(1) + 's');
      if (st.brands_start && st.brands_end) fillTime(1, (st.brands_end - st.brands_start).toFixed(1) + 's');
      if (st.categories_start && st.categories_end) fillTime(2, (st.categories_end - st.categories_start).toFixed(1) + 's');
      if (st.finalizing_start && st.finalizing_end) fillTime(3, (st.finalizing_end - st.finalizing_start).toFixed(1) + 's');
      if (activeIdx >= 0 && d.current_step_start && !st[cs + '_end']) {
        fillTime(activeIdx, ((Date.now() / 1000) - d.current_step_start).toFixed(1) + 's...');
      }
      if (d.elapsed && d.status === 'completed') fillTime(3, d.elapsed + 's');

      // Per-step logs from backend step_logs
      var stepLogs = d.step_logs || {};
      var stepKeys = ['reading', 'brands', 'categories', 'finalizing'];
      for (var si = 0; si < 4; si++) {
        var key = stepKeys[si];
        var lines = stepLogs[key] || [];
        // Count already shown lines for this step
        var shown = (_tlStepLogCounts && _tlStepLogCounts[key]) || 0;
        for (var j = shown; j < lines.length; j++) appendLog(si, lines[j]);
        if (!_tlStepLogCounts) _tlStepLogCounts = {};
        _tlStepLogCounts[key] = lines.length;
      }

      if (d.status === 'completed') {
        stop();
        // Fill all step times from final data before changing card states
        var stDone = d.step_times || {};
        if (stDone.reading_start && stDone.reading_end) fillTime(0, (stDone.reading_end - stDone.reading_start).toFixed(1) + 's');
        if (stDone.brands_start && stDone.brands_end) fillTime(1, (stDone.brands_end - stDone.brands_start).toFixed(1) + 's');
        if (stDone.categories_start && stDone.categories_end) fillTime(2, (stDone.categories_end - stDone.categories_start).toFixed(1) + 's');
        if (stDone.finalizing_start && stDone.finalizing_end) fillTime(3, (stDone.finalizing_end - stDone.finalizing_start).toFixed(1) + 's');
        else if (d.elapsed != null) fillTime(3, d.elapsed + 's');
        // Set all cards done
        for (var k = 0; k < 4; k++) cardState(k, 'done');
        show(el('tlAction'));
        await fillResults(d);
      }

      if (d.status === 'error') {
        stop();
        if (activeIdx >= 0) cardState(activeIdx, 'pending');
        appendLog(activeIdx >= 0 ? activeIdx : 3, '错误: ' + (d.message || '未知'));
      }
    } catch (e) { /* retry */ }
  }

  // ── Fill done-state content per step ──
  async function fillResults(statusData) {
    try {
      var rr = await fetch('/api/diagnosis_result?sid=' + window.sessionId);
      var rd = await rr.json();
      var s = rd.stats || {};
      var diag = rd.diagnosis || {};

      // Step 1: KV rows
      var kv1 = el('kvRead');
      if (kv1) {
        kv1.textContent = '';
        var _i1 = document.createElement('div'); _i1.className = 'item';
        var _k1 = document.createElement('span'); _k1.className = 'k'; _k1.textContent = 'File';
        var _v1 = document.createElement('span'); _v1.className = 'v'; _v1.textContent = rd.file_name || '';
        _i1.appendChild(_k1); _i1.appendChild(_v1);
        var _i2 = document.createElement('div'); _i2.className = 'item';
        var _k2 = document.createElement('span'); _k2.className = 'k'; _k2.textContent = 'Rows';
        var _v2 = document.createElement('span'); _v2.className = 'v'; _v2.textContent = String(s.total || 0);
        _i2.appendChild(_k2); _i2.appendChild(_v2);
        kv1.appendChild(_i1); kv1.appendChild(_i2);
      }

      // Step 2: mini-tags — brand results
      var lf2 = el('logBrand');
      if (lf2) {
        lf2.textContent = '';
        var _row2 = document.createElement('div'); _row2.style.marginBottom = '8px';
        var _t1 = document.createElement('span'); _t1.className = 'mini-tag grn'; _t1.textContent = '已确立 ' + (s.valid || 0);
        var _t2 = document.createElement('span'); _t2.className = 'mini-tag org'; _t2.textContent = '缺失项 ' + (s.brand_missing || 0);
        var _t3 = document.createElement('span'); _t3.className = 'mini-tag red'; _t3.textContent = '异常冲突 ' + (s.brand_mismatch || 0);
        _row2.appendChild(_t1); _row2.appendChild(_t2); _row2.appendChild(_t3);
        var _note2 = document.createElement('span');
        _note2.style.cssText = 'font-size:12px;color:var(--text-muted);';
        _note2.textContent = 'Agent 已自动聚类收敛出标准品牌簇';
        lf2.appendChild(_row2); lf2.appendChild(_note2);
      }

      // Step 3: mini-tags — category results
      var lf3 = el('logCate');
      if (lf3) {
        var cleanedPaths = diag.cleaned_paths || {};
        var pathCount = Object.keys(cleanedPaths).length;
        var conflictCount = (diag.conflict_groups || []).length;
        var marketingCount = s.marketing || 0;
        lf3.textContent = '';
        var _row3 = document.createElement('div'); _row3.style.marginBottom = '8px';
        var _c1 = document.createElement('span'); _c1.className = 'mini-tag acc'; _c1.textContent = pathCount + ' 条标准路径';
        var _c2 = document.createElement('span'); _c2.className = 'mini-tag org'; _c2.textContent = conflictCount + ' 待人工确认';
        var _c3 = document.createElement('span'); _c3.className = 'mini-tag grn'; _c3.textContent = marketingCount + ' 自动化营销标签';
        _row3.appendChild(_c1); _row3.appendChild(_c2); _row3.appendChild(_c3);
        var _note3 = document.createElement('span');
        _note3.style.cssText = 'font-size:12px;color:var(--text-muted);';
        _note3.textContent = '路径映射表已生成';
        lf3.appendChild(_row3); lf3.appendChild(_note3);
      }

      // Step 4: text summary only
      var lf4 = el('logFinish');
      if (lf4) {
        lf4.textContent = '';
        var _wrap4 = document.createElement('span');
        _wrap4.style.cssText = 'font-size:12px;color:var(--text-muted);';
        _wrap4.appendChild(document.createTextNode('Pipeline 整体耗时 '));
        var _ts4 = document.createElement('span');
        _ts4.style.cssText = 'color:var(--text-main);font-weight:600;font-family:var(--font-mono);';
        _ts4.textContent = (statusData.elapsed != null ? statusData.elapsed : '') + 's';
        _wrap4.appendChild(_ts4);
        _wrap4.appendChild(document.createTextNode('，结果集已打包完毕。'));
        lf4.appendChild(_wrap4);
      }

      // Trigger downstream panels first (brand/category data rendering)
      if (typeof window.showDiagnosis === 'function' && rd.diagnosis) {
        window.showDiagnosis(rd);
      }

      // Populate stats panel (after showDiagnosis so our values win)
      var se = el('statsFileName'); if (se) se.textContent = '数据源：' + (rd.file_name || '');
      el('statTotal').textContent = s.total || 0;
      el('statValid').textContent = s.valid || 0;
      el('statBrandMissing').textContent = s.brand_missing || 0;
      el('statBrandMismatch').textContent = s.brand_mismatch || 0;
      el('statNeedAI').textContent = s.need_ai || 0;
      el('statMarketing').textContent = s.marketing || 0;
      // Category meta-list
      var cleanedPaths = diag.cleaned_paths || {};
      var pathCount = Object.keys(cleanedPaths).length;
      var conflictCount = (diag.conflict_groups || []).length;
      var pc = el('statPathCount'); if (pc) pc.textContent = pathCount + ' 条路径';
      var cc = el('statConflictCount'); if (cc) cc.textContent = conflictCount + ' 待确认';

      // Update drop zone
      var drop = el('tlDrop');
      if (drop) {
        var lastSpan = drop.querySelector('span:last-child');
        if (lastSpan) lastSpan.textContent = (s.total || 0) + ' 行 · 已就绪';
      }
      // Update breadcrumb session switcher
      if (typeof window._updateBreadcrumbSession === 'function') {
        var gid = (rd.diagnosis && rd.diagnosis.group_id) || '';
        var cleanFn = typeof window._cleanFileName === 'function' ? window._cleanFileName(rd.file_name) : (rd.file_name || '');
        window._updateBreadcrumbSession(cleanFn);
      }
    } catch (e) {
      console.warn('Timeline fillResults:', e);
    }
  }

  // ── Session restore (called after upload or session switch) ──
  window._tlRestoreSession = async function() {
    var drop = el('tlDrop');
    if (drop) {
      drop.classList.add('file-loaded');
      drop.textContent = '';
      var _ls6 = document.createElement('span');
      _ls6.style.color = 'var(--text-sub)';
      _ls6.textContent = '正在恢复会话...';
      drop.appendChild(_ls6);
    }
    try {
      var r = await fetch('/api/diagnosis_status?sid=' + window.sessionId);
      if (r.status === 404) throw new Error('会话已过期，请重新上传文件');
      var d = await r.json();
      if (d.error) throw new Error(d.error);

      // Update drop zone
      if (drop) {
        drop.textContent = '';
        var _sv7 = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        _sv7.setAttribute('width', '18'); _sv7.setAttribute('height', '18');
        _sv7.setAttribute('viewBox', '0 0 24 24'); _sv7.setAttribute('fill', 'none');
        _sv7.setAttribute('stroke', 'var(--green)'); _sv7.setAttribute('stroke-width', '2');
        _sv7.setAttribute('stroke-linecap', 'round'); _sv7.setAttribute('stroke-linejoin', 'round');
        var _p7 = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        _p7.setAttribute('d', 'M20 6L9 17l-5-5'); _sv7.appendChild(_p7);
        var _s7a = document.createElement('span');
        _s7a.style.cssText = 'font-size:13px;font-weight:500;color:var(--text-main);';
        _s7a.textContent = '已恢复会话';
        var _s7b = document.createElement('span');
        _s7b.style.cssText = 'font-size:12px;color:var(--text-muted);margin-left:auto;';
        _s7b.textContent = '诊断中...';
        drop.appendChild(_sv7); drop.appendChild(_s7a); drop.appendChild(_s7b);
      }

      if (d.status === 'completed') {
        // Already done — show all cards completed, replay all logs
        var stepLogs2 = d.step_logs || {};
        var stepKeys2 = ['reading', 'brands', 'categories', 'finalizing'];
        for (var si = 0; si < 4; si++) {
          var lines = stepLogs2[stepKeys2[si]] || [];
          for (var j = 0; j < lines.length; j++) appendLog(si, lines[j]);
        }
        for (var k = 0; k < 4; k++) cardState(k, 'done');
        if (d.elapsed != null) fillTime(3, d.elapsed + 's');
        show(el('tlAction'));
        await fillResults(d);
      } else if (d.status === 'processing') {
        // Still running — catch up to current step
        var cs = d.current_step;
        var activeIdx = _tlStepMap[cs] != null ? _tlStepMap[cs] : -1;
        for (var i = 0; i < 4; i++) {
          if (activeIdx >= 0 && i < activeIdx) cardState(i, 'done');
          else if (i === activeIdx) cardState(i, 'active');
          else if (activeIdx >= 0 && i > activeIdx) cardState(i, 'pending');
        }
        if (activeIdx < 0) cardState(3, 'active');
        var st = d.step_times || {};
        if (st.reading_start && st.reading_end) fillTime(0, (st.reading_end - st.reading_start).toFixed(1) + 's');
        if (st.brands_start && st.brands_end) fillTime(1, (st.brands_end - st.brands_start).toFixed(1) + 's');
        if (st.categories_start && st.categories_end) fillTime(2, (st.categories_end - st.categories_start).toFixed(1) + 's');
        if (st.finalizing_start && st.finalizing_end) fillTime(3, (st.finalizing_end - st.finalizing_start).toFixed(1) + 's');
        start();
      } else {
        // Pending — hasn't started yet, show first card active
        cardState(0, 'active');
        start();
      }
    } catch (e) {
      if (drop) { drop.classList.remove('file-loaded');
        drop.textContent = '';
        var _sv8 = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        _sv8.setAttribute('width', '32'); _sv8.setAttribute('height', '32');
        _sv8.setAttribute('viewBox', '0 0 24 24'); _sv8.setAttribute('fill', 'none');
        _sv8.setAttribute('stroke', 'var(--text-sub)'); _sv8.setAttribute('stroke-width', '1.5');
        _sv8.setAttribute('stroke-linecap', 'round'); _sv8.setAttribute('stroke-linejoin', 'round');
        var _p8 = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        _p8.setAttribute('d', 'M12 5v14M5 12h14'); _sv8.appendChild(_p8);
        var _d8 = document.createElement('div');
        var _s8a = document.createElement('span');
        _s8a.style.cssText = 'font-size:14px;font-weight:500;color:var(--text-main);';
        _s8a.textContent = '投喂诊断文件';
        var _s8b = document.createElement('span');
        _s8b.style.cssText = 'display:block;font-size:12px;color:var(--text-muted);margin-top:4px;';
        _s8b.textContent = '拖拽 .xlsx / .xls 到此处，或点击浏览';
        _d8.appendChild(_s8a); _d8.appendChild(_s8b);
        drop.appendChild(_sv8); drop.appendChild(_d8); }
      localStorage.removeItem('last_session_id');
      window.sessionId = null; sessionId = null;
    }
  };

  // ── Hook: file select → upload + timeline ──
  (function() {
    var fi = el('fileInput');
    if (!fi) return;
    fi.addEventListener('change', function() {
      var f = fi.files[0];
      if (!f) return;
      var grp = el('uploadGroup');
      if (!grp || !grp.value) { alert('请先在左侧边栏选择分组'); return; }
      doUpload(f);
    });
  })();

  // ── CTA: push stats to right column ──
  (function() {
    var btn = el('tlViewResultsBtn');
    if (!btn) return;
    btn.addEventListener('click', function() {
      if (typeof window._movePanelToCard === 'function') {
        window._movePanelToCard('statsSection', 'diagnosis-stats', '诊断结果');
        var ss = el('statsSection');
        if (ss) ss.classList.remove('hidden');
      }
    });
  })();

  // ── Page load: restore session if saved ──
  var _tlRestoring = false;
  window.addEventListener('DOMContentLoaded', function() {
    var saved = localStorage.getItem('last_session_id');
    if (!saved) return;
    _tlRestoring = true;
    window.sessionId = saved;
    if (typeof sessionId !== 'undefined') sessionId = saved;
    window._tlRestoreSession().finally(function(){ _tlRestoring = false; });
  });

})();
