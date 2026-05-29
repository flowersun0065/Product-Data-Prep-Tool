// ═══ Electron: AI Process overrides (DOM API) ═══
(function(){
  if (!window._electronMode) return;

  // ── AI 配置：从 settings.json 读配置列表，填充下拉框 ──
  loadAIConfig = async function() {
    try {
      var res = await fetch('/api/settings');
      var data = await res.json();
      var sel = document.getElementById('aiConfigSelect');
      if (!sel) return;
      sel.textContent = '';
      var defOpt = document.createElement('option');
      defOpt.value = '';
      defOpt.textContent = '不使用 AI';
      sel.appendChild(defOpt);
      var configs = data.ai_configs || [];
      var cur = data.current || '';
      configs.forEach(function(c) {
        var opt = document.createElement('option');
        opt.value = c.name;
        if (c.name === cur) opt.selected = true;
        opt.textContent = c.name + ' (' + c.provider + '/' + c.model + ')';
        sel.appendChild(opt);
      });
    } catch(e) {}
  };
  window.loadAIConfig = loadAIConfig;

  // ── Fix cancelAI: stop polling FIRST, then notify server ──
  var _cancelPatched = false;
  function _patchCancel() {
    if (typeof cancelAI === 'undefined') { setTimeout(_patchCancel, 50); return; }
    if (_cancelPatched) return;
    _cancelPatched = true;
    var _origCancel = cancelAI;
    cancelAI = function() {
      if (typeof aiPollTimer !== 'undefined' && aiPollTimer) { clearInterval(aiPollTimer); aiPollTimer = null; }
      if (typeof aiLogPollTimer !== 'undefined' && aiLogPollTimer) { clearInterval(aiLogPollTimer); aiLogPollTimer = null; }
      if (typeof hideAIHeaderStatus === 'function') hideAIHeaderStatus();
      var ps = document.getElementById('aiProgressSection');
      var cp = document.getElementById('aiConfigPanel');
      var ab = document.getElementById('aiActionsBar');
      var bt = document.getElementById('aiBatchTimeline');
      if (ps) ps.classList.add('hidden');
      if (ab) ab.classList.add('hidden');
      if (bt) bt.classList.add('hidden');
      if (cp) cp.classList.remove('hidden');
      var mb = document.getElementById('aiMonitorBtn');
      if (mb) mb.style.display = 'none';
      if (typeof _taskPanelClose === 'function') _taskPanelClose();
      var sid = typeof sessionId !== 'undefined' ? sessionId : '';
      if (sid) {
        fetch('/api/process/cancel', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_id: sid })
        }).catch(function(e) { console.warn('Cancel request failed:', e); });
      }
    };
    window.cancelAI = cancelAI;
  }
  setTimeout(_patchCancel, 100);

  setTimeout(function() { loadAIConfig(); _recoverAIState(); }, 100);

  function _recoverAIState() {
    var sid = typeof sessionId !== 'undefined' ? sessionId : '';
    if (!sid) return;
    fetch('/api/status?sid=' + encodeURIComponent(sid))
      .then(function(r) { return r.json(); })
      .then(function(s) {
        if (s.status !== 'processing') return;
        var cp = document.getElementById('aiConfigPanel');
        var ps = document.getElementById('aiProgressSection');
        if (cp) cp.classList.add('hidden');
        if (ps) {
          ps.classList.remove('hidden');
          var ab = document.getElementById('aiActionsBar');
          if (ab) { ab.classList.remove('hidden'); ab.style.display = 'flex'; }
          var cancelBtn = document.getElementById('aiCancelBtn');
          if (cancelBtn) cancelBtn.classList.remove('hidden');
          var errEl = document.getElementById('aiErrorMessage');
          if (errEl) errEl.classList.add('hidden');
          _updateTokenDisplay(s.token_usage || {});
          _renderBatchTimeline(s.batch_logs||[], s.ai_phase, s.ai_batch_active||0, s.ai_batch_items_done||0, s.token_usage||{});
        }
        if (typeof aiPollTimer === 'undefined' || aiPollTimer === null) {
          if (typeof pollAIProgress === 'function') aiPollTimer = setInterval(pollAIProgress, 500);
        }
        if (typeof aiLogPollTimer === 'undefined' || aiLogPollTimer === null) {
          if (typeof pollAILogs === 'function') aiLogPollTimer = setInterval(pollAILogs, 500);
        }
      }).catch(function() {});
  }

  function _patch() {
    if (typeof showAIHeaderStatus === 'undefined') { setTimeout(_patch, 50); return; }

    showAIHeaderStatus = function() {};
    hideAIHeaderStatus = function() {};

    // Override renderLogEntry — DOM API
    var _origRenderLog = renderLogEntry;
    renderLogEntry = function(log) {
      var div = document.createElement('div');
      div.style.cssText = 'display:flex;align-items:flex-start;gap:6px;padding:6px 8px;border-radius:6px;font-size:12px;border-left:2px solid var(--border);margin-bottom:4px;';

      if (log._system_message) {
        div.style.background = 'var(--surface)';
        div.style.borderLeftColor = 'var(--accent)';
        var si = document.createElement('span');
        si.style.cssText = 'flex-shrink:0;font-size:12px;margin-top:1px;';
        si.textContent = 'i';
        div.appendChild(si);
        var sc = document.createElement('div');
        sc.style.cssText = 'flex:1;';
        var scd = document.createElement('div');
        scd.style.cssText = 'color:var(--text-sub);font-style:italic;';
        scd.textContent = log._system_message;
        sc.appendChild(scd);
        div.appendChild(sc);
        return div;
      }

      var brandStatus = log.brand && log.brand.status || 'skipped';
      var catStatus = log.category && log.category.status || 'skipped';
      var needsReview = log.needs_review;

      var icon = '';
      var borderColor = 'var(--border)';
      var statusText = '';
      var extraInfo = '';

      if (brandStatus === 'from_library') { icon = 'B'; borderColor = 'var(--green)'; statusText = '品牌库: ' + (log.brand && log.brand.value || ''); }
      else if (brandStatus === 'error') { icon = '!'; borderColor = 'var(--red)'; statusText = 'AI调用失败: ' + (log.brand && log.brand.error || ''); }
      else if (brandStatus === 'no_brand') { icon = 'N'; borderColor = 'var(--text-muted)'; statusText = 'AI判断: 无品牌'; extraInfo = (log.brand && log.brand.suggestion) ? '建议:' + log.brand.suggestion : ''; }
      else if (brandStatus === 'ai_ok') {
        var aiAgrees = log.brand && log.brand.ai_agrees;
        if (aiAgrees === true) { icon = 'OK'; borderColor = 'var(--green)'; statusText = 'AI(一致): ' + (log.brand && log.brand.value || ''); }
        else if (aiAgrees === false) { icon = '~'; borderColor = 'var(--orange)'; statusText = 'AI(修正): ' + (log.brand && log.brand.value || ''); extraInfo = (log.brand && log.brand.suggestion) ? '原建议:' + log.brand.suggestion : ''; }
        else if (needsReview) { icon = '?'; borderColor = 'var(--orange)'; statusText = 'AI(低置信): ' + (log.brand && log.brand.value || ''); }
        else { icon = 'OK'; borderColor = 'var(--green)'; statusText = 'AI: ' + (log.brand && log.brand.value || ''); }
      } else if (brandStatus === 'local_fallback') { icon = 'L'; borderColor = 'var(--text-muted)'; statusText = '本地: ' + (log.brand && log.brand.value || ''); }

      if (catStatus === 'ai_ok') statusText += ' | 分类: ' + (log.category && log.category.path || '');
      else if (catStatus === 'local_fallback') statusText += ' | 分类(fallback): ' + (log.category && log.category.path || '-');

      if (needsReview) div.style.background = 'rgba(239,68,68,0.08)';
      div.style.borderLeftColor = borderColor;

      var brandReason = log.brand && log.brand.reason || '';
      var catReason = log.category && log.category.reason || '';
      var reasons = [];
      if (brandReason) reasons.push('品牌: ' + brandReason);
      if (catReason) reasons.push('分类: ' + catReason);
      var displayReason = reasons.join(' | ') || '';

      var factors = log.factors || {};
      var entity = factors.entity || '';
      var modifiers = (factors.modifiers || []).join(', ');
      var factorParts = [];
      if (entity) factorParts.push('品种:' + entity);
      if (modifiers) factorParts.push('修饰:' + modifiers);
      var factorText = factorParts.join(' | ');

      // Icon span
      var iconSpan = document.createElement('span');
      iconSpan.style.cssText = 'flex-shrink:0;font-size:10px;font-weight:600;margin-top:1px;color:' + borderColor + ';min-width:18px;text-align:center;';
      iconSpan.textContent = icon;
      div.appendChild(iconSpan);

      // Content
      var content = document.createElement('div');
      content.style.cssText = 'flex:1;min-width:0;';

      var nameDiv = document.createElement('div');
      nameDiv.style.cssText = 'color:var(--text-main);font-weight:500;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;';
      nameDiv.textContent = log.name || '';
      content.appendChild(nameDiv);

      var statusDiv = document.createElement('div');
      statusDiv.style.cssText = 'font-size:11px;color:var(--text-sub);';
      statusDiv.textContent = statusText;
      content.appendChild(statusDiv);

      if (extraInfo) {
        var extraDiv = document.createElement('div');
        extraDiv.style.cssText = 'font-size:10px;color:var(--text-muted);margin-top:2px;';
        extraDiv.textContent = extraInfo;
        content.appendChild(extraDiv);
      }
      if (factorText) {
        var factorDiv = document.createElement('div');
        factorDiv.style.cssText = 'font-size:10px;color:var(--text-muted);';
        factorDiv.textContent = factorText;
        content.appendChild(factorDiv);
      }
      if (displayReason) {
        var reasonDiv = document.createElement('div');
        reasonDiv.style.cssText = 'font-size:10px;color:var(--text-muted);font-style:italic;margin-top:2px;';
        reasonDiv.textContent = displayReason;
        content.appendChild(reasonDiv);
      }
      div.appendChild(content);

      if (needsReview) {
        var reviewSpan = document.createElement('span');
        reviewSpan.style.cssText = 'flex-shrink:0;color:var(--orange);font-size:10px;';
        reviewSpan.textContent = '待复核';
        div.appendChild(reviewSpan);
      }
      return div;
    };

    // Override onAIComplete
    var _origComplete = onAIComplete;
    onAIComplete = function(data) {
      var cancelBtn = document.getElementById('aiCancelBtn');
      if (cancelBtn) cancelBtn.classList.add('hidden');
      var mb = document.getElementById('aiMonitorBtn');
      if (mb) mb.style.display = 'none';
      var actions = document.getElementById('aiCompleteActions');
      if (actions) { actions.classList.remove('hidden'); actions.style.display = 'flex'; }
      var downloadBtn = document.getElementById('aiDownloadBtn');
      if (downloadBtn) downloadBtn.classList.remove('hidden');

      if (typeof showAIHeaderStatus === 'function') showAIHeaderStatus('AI处理完成', 'bg-emerald-500');
      setTimeout(function() { if (typeof hideAIHeaderStatus === 'function') hideAIHeaderStatus(); }, 4000);

      if (downloadBtn) {
        downloadBtn.onclick = function() { window.location.href = '/api/download?sid=' + sessionId + '&type=result'; };
      }
      var reviewBtn = document.getElementById('aiReviewBtn');
      if (reviewBtn) {
        reviewBtn.onclick = function() { if (typeof navigateToStep === 'function') navigateToStep('review'); };
        if (data.review_pending > 0) reviewBtn.textContent = '进入复核 (' + data.review_pending + ')';
      }
    };

    // Override onAIError
    var _origError = onAIError;
    onAIError = function(msg) {
      var cancelBtn = document.getElementById('aiCancelBtn');
      if (cancelBtn) cancelBtn.classList.add('hidden');
      var mb = document.getElementById('aiMonitorBtn');
      if (mb) mb.style.display = 'none';
      var errEl = document.getElementById('aiErrorMessage');
      if (errEl) errEl.classList.remove('hidden');
      var errText = document.getElementById('aiErrorText');
      if (errText) errText.textContent = msg;
      if (typeof showAIHeaderStatus === 'function') showAIHeaderStatus('AI处理失败', 'bg-red-500');
    };

    // Replace pollAIProgress
    var _renderedBatches = 0;
    pollAIProgress = async function() {
      try {
        var sid = typeof sessionId !== 'undefined' ? sessionId : '';
        if (!sid) return;
        var res = await fetch('/api/status?sid=' + encodeURIComponent(sid));
        var data = await res.json();
        _updateTokenDisplay(data.token_usage || {});
        _renderStartupNode(data);
        _renderBatchTimeline(data.batch_logs||[], data.ai_phase, data.ai_batch_active||0, data.ai_batch_items_done||0, data.token_usage||{});
        if (data.ai_paused && !window._aiPauseShown) {
          window._aiPauseShown = true;
          if (typeof _taskPanelUpsert === 'function') {
            _taskPanelUpsert({ id: 'ai-paused', title: 'AI 连续调用失败，已暂停', status: 'error', meta: '', tokens: {},
              detail: 'AI 调用持续失败（API Key 或网络问题）。\n请取消处理，切换模型或 Key 后重试。' });
          }
        }
        if (data.status === 'completed' || data.ai_phase === 'completed') {
          if (typeof aiPollTimer !== 'undefined' && aiPollTimer) { clearInterval(aiPollTimer); aiPollTimer = null; }
          if (typeof aiLogPollTimer !== 'undefined' && aiLogPollTimer) { clearInterval(aiLogPollTimer); aiLogPollTimer = null; }
          if (typeof onAIComplete === 'function') onAIComplete(data);
        } else if (data.status === 'error') {
          if (typeof aiPollTimer !== 'undefined' && aiPollTimer) { clearInterval(aiPollTimer); aiPollTimer = null; }
          if (typeof onAIError === 'function') onAIError(data.message || '处理出错');
        } else if (data.status === 'cancelled') {
          if (typeof aiPollTimer !== 'undefined' && aiPollTimer) { clearInterval(aiPollTimer); aiPollTimer = null; }
          if (typeof cancelAI === 'function') cancelAI();
        }
        var ab = document.getElementById('aiActionsBar');
        if (ab) { ab.classList.remove('hidden'); ab.style.display = 'flex'; }
      } catch(e) {}
    };

    // Rewrite pollAILogs
    var _origLogPoll = pollAILogs;
    var _monitorBatchItems = {};
    pollAILogs = async function() {
      try {
        var sid = typeof sessionId !== 'undefined' ? sessionId : '';
        if (!sid) return;
        var res = await fetch('/api/ai_logs?sid=' + encodeURIComponent(sid));
        var data = await res.json();
        var logs = data.logs || [];
        for (var li = 0; li < logs.length; li++) {
          if (logs[li]._system_message) continue;
          var item = logs[li];
          var line = item.name + ' | 品牌:' + ((item.brand||{}).value||'-') + ' | 分类:' + ((item.category||{}).path||'-').substring(0,30);
          for (var bk in _batchCards) {
            var bc = _batchCards[bk];
            if (bc.card && bc.card.classList.contains('active')) {
              _tlAppendLog(bc.logEl, line);
              if (!_monitorBatchItems[bk]) _monitorBatchItems[bk] = [];
              _monitorBatchItems[bk].push(item);
              if (typeof _taskPanelUpsert === 'function') {
                var bItems = _monitorBatchItems[bk];
                var detail = '处理中... 已处理 ' + bItems.length + ' 条\n\n';
                for (var ji = 0; ji < bItems.length; ji++) {
                  var it = bItems[ji];
                  detail += (ji+1) + '. ' + (it.name||'').substring(0,36) + ' | 品牌:' + ((it.brand||{}).value||'-') + '\n';
                }
                _taskPanelUpsert({ id: bk, title: '批次 ' + bk.replace('batch-','') + ' · 处理中', status: 'active', meta: '', tokens: {}, detail: detail });
              }
              break;
            }
          }
        }
      } catch(e) {}
    };

    console.log('[ai_process_electron] Patched AI functions for native.css (DOM API)');
  }

  // startAIProcessing: electron 完全重写
  var _aiStartTime = 0;
  startAIProcessing = async function() {
    var sid = typeof sessionId !== 'undefined' ? sessionId : '';
    if (!sid) { alert('没有活动会话'); return; }

    _aiStartTime = Date.now();
    if (typeof _taskPanelReset === 'function') _taskPanelReset();
    if (typeof _taskPanelOpen === 'function') _taskPanelOpen('AI 处理监控');
    window._aiPauseShown = false;
    _renderedBatches = 0;
    _startupCard = null; _startupLogEl = null; _startupDone = false; _startupLogCount = 0;
    _batchCards = {};
    _monitorBatchItems = {};

    var container = document.getElementById('aiBatchTimeline');
    if (container) {
      container.textContent = '';
      var co = _tlCreateCard('_startupCard', '启动 AI 处理');
      container.appendChild(co.card);
      _startupCard = co.card;
      _startupLogEl = _tlEnsureLog(co);
    }

    var configName = document.getElementById('aiConfigSelect').value;

    if (typeof saveAllCategoryRules === 'function') {
      try { await saveAllCategoryRules(); } catch(e) {}
    }

    var cp = document.getElementById('aiConfigPanel');
    if (cp) cp.classList.add('hidden');
    var ps = document.getElementById('aiProgressSection');
    if (ps) ps.classList.remove('hidden');
    var ab = document.getElementById('aiActionsBar');
    if (ab) { ab.classList.remove('hidden'); ab.style.display = 'flex'; }
    var cancelBtn = document.getElementById('aiCancelBtn');
    if (cancelBtn) cancelBtn.classList.remove('hidden');
    var monitorBtn = document.getElementById('aiMonitorBtn');
    if (monitorBtn) monitorBtn.style.display = '';
    var errEl = document.getElementById('aiErrorMessage');
    if (errEl) errEl.classList.add('hidden');
    var actions = document.getElementById('aiCompleteActions');
    if (actions) actions.classList.add('hidden');

    try {
      var res = await fetch('/api/process', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sid, config_name: configName || '', batch_size: 20,
          force_reanalyze: document.getElementById('aiForceReanalyze') ? document.getElementById('aiForceReanalyze').checked : false })
      });
      var data = await res.json();
      if (!data.success) throw new Error(data.error || '启动失败');
    } catch(err) {
      if (typeof onAIError === 'function') onAIError('启动 AI 处理失败: ' + err.message);
      return;
    }

    if (typeof pollAIProgress === 'function') aiPollTimer = setInterval(pollAIProgress, 500);
    if (typeof pollAILogs === 'function') aiLogPollTimer = setInterval(pollAILogs, 500);
    pollAIProgress();
    pollAILogs();
  };

  function _elapsed(ms) {
    if (ms < 1000) return ms + 'ms';
    var s = Math.floor(ms / 1000);
    if (s < 60) return s + 's';
    return Math.floor(s/60) + 'm' + (s%60) + 's';
  }

  function _fmtTokens(t) {
    if (!t.total_tokens) return '';
    return 'in:' + (t.prompt_tokens||0) + ' out:' + (t.completion_tokens||0);
  }

  var _startupCard = null, _startupLogEl = null, _startupDone = false, _startupLogCount = 0;

  function _renderStartupNode(data) {
    var logs = data.logs || [];
    var container = document.getElementById('aiBatchTimeline');
    if (!container) return;
    container.classList.remove('hidden');

    if (!_startupDone) {
      for (var li = _startupLogCount; li < logs.length; li++) {
        if (_startupLogEl) _tlAppendLog(_startupLogEl, logs[li]);
      }
    }
    _startupLogCount = logs.length;

    _tlSetTime(_startupCard, _elapsed(Date.now() - _aiStartTime));

    if (!_startupDone && _startupCard && data.ai_phase && data.ai_phase !== 'startup') {
      _startupDone = true;
      _tlSetState(_startupCard, data.ai_phase === 'error' ? 'done' : 'done');
      var body = _startupCard.querySelector('.tl-body');
      if (body) {
        var items = [
          {k: '状态', v: data.ai_phase === 'error' ? '连接失败' : '就绪'},
          {k: '共计', v: (data.ai_total || data.total || 0) + ' 个商品'},
          {k: '品牌待AI', v: data.ai_total_brand || 0},
          {k: '分类待AI', v: data.ai_total_category || 0}
        ];
        _tlSetKv(body, items);
        body.style.maxHeight = '2000px';
        body.style.opacity = '1';
        body.style.padding = '12px 24px 12px 48px';
      }
    }

    if (typeof _taskPanelUpsert === 'function' && logs.length) {
      _taskPanelUpsert({ id: 'startup', title: '启动 AI 处理', status: _startupDone ? 'done' : 'active',
        meta: _elapsed(Date.now() - _aiStartTime), tokens: {}, detail: logs.join('\n') });
    }
  }

  function _renderBatchTimeline(batchLogs, aiPhase, activeBatch, itemsDone, tokenUsage) {
    var container = document.getElementById('aiBatchTimeline');
    if (!container) return;
    container.classList.remove('hidden');

    if (activeBatch > 0) {
      if (!_batchCards['batch-' + activeBatch]) _ensureBatchCard('batch-' + activeBatch, activeBatch, 20);
      var ac = _batchCards['batch-' + activeBatch];
      _tlSetTime(ac.card, _elapsed(Date.now() - _aiStartTime));
      var titleEl = ac.card.querySelector('.tl-title');
      if (titleEl && (itemsDone||0) > 0) titleEl.textContent = '批次 #' + activeBatch + ' · ' + (itemsDone||0) + '/20 条商品';
      var bodyEl = ac.card.querySelector('.tl-body');
      if (bodyEl && tokenUsage && tokenUsage.total_tokens) {
        var kvEl = bodyEl.querySelector('.kv');
        if (!kvEl) { kvEl = document.createElement('div'); kvEl.className = 'kv'; bodyEl.insertBefore(kvEl, bodyEl.firstChild); }
        kvEl.textContent = '';
        var item = document.createElement('div');
        item.className = 'item';
        var k = document.createElement('span'); k.className = 'k'; k.textContent = '累计 Token';
        var v = document.createElement('span'); v.className = 'v';
        v.textContent = 'in:' + (tokenUsage.prompt_tokens||0) + ' out:' + (tokenUsage.completion_tokens||0) + ' total:' + (tokenUsage.total_tokens||0);
        item.appendChild(k); item.appendChild(v);
        kvEl.appendChild(item);
      }
      if (typeof _taskPanelUpsert === 'function' && (itemsDone||0) > 0) {
        _taskPanelUpsert({ id: 'batch-' + activeBatch, title: '批次 #' + activeBatch + ' · ' + (itemsDone||0) + '/20 条',
          status: 'active', meta: _elapsed(Date.now() - _aiStartTime), tokens: {},
          detail: '处理中... ' + (itemsDone||0) + '/20 条已处理' });
      }
      if (!batchLogs.length) return;
    }

    for (var i = _renderedBatches; i < batchLogs.length; i++) {
      var b = batchLogs[i];
      var elapsed = _elapsed(Date.now() - _aiStartTime);
      var tokens = b.tokens || {};
      var cum = b.cumulative_tokens || {};
      var batchId = 'batch-' + b.batch;
      var existing = _batchCards[batchId];
      if (existing) {
        var card = existing.card;
        _tlSetState(card, 'done');
        _tlSetTime(card, elapsed);
        var body = card.querySelector('.tl-body');
        if (body) {
          var kvItems = [{k: '方式', v: b.method === 'ai' ? 'AI' : '本地'}];
          if (tokens.total_tokens) kvItems.push({k: '批次 Token', v: _fmtTokens(tokens)});
          if (cum.total_tokens) kvItems.push({k: '累计 Token', v: _fmtTokens(cum) + ' total:' + cum.total_tokens});
          _tlSetKv(body, kvItems);
          if (b.prompt) {
            var promptBtn = document.createElement('div');
            promptBtn.style.marginTop = '6px';
            var promptId = 'prompt-' + b.batch;
            var toggleBtn = document.createElement('button');
            toggleBtn.className = 'btn-agent secondary';
            toggleBtn.style.fontSize = '10px';
            toggleBtn.textContent = '查看 Prompt';
            var pre = document.createElement('pre');
            pre.id = promptId;
            pre.style.cssText = 'display:none;margin-top:4px;padding:6px 8px;background:var(--surface);border-radius:var(--radius-sm);font-size:10px;color:var(--text-muted);max-height:160px;overflow-y:auto;white-space:pre-wrap;';
            pre.textContent = b.prompt;
            toggleBtn.onclick = function() { pre.style.display = pre.style.display === 'none' ? '' : 'none'; };
            promptBtn.appendChild(toggleBtn);
            promptBtn.appendChild(pre);
            body.appendChild(promptBtn);
          }
          body.style.maxHeight = '2000px';
          body.style.opacity = '1';
          body.style.padding = '12px 24px 12px 48px';
        }
      }
      _updateBatchTaskPanel(b);
    }
    _renderedBatches = batchLogs.length;
  }

  function _ensureBatchCard(batchId, batchNum, count) {
    if (_batchCards[batchId]) return _batchCards[batchId];
    var container = document.getElementById('aiBatchTimeline');
    if (!container) return null;
    container.classList.remove('hidden');

    var conn = document.createElement('div');
    conn.className = 'tl-connector';
    conn.id = 'conn-' + batchId;
    var line = document.createElement('div');
    line.className = 'line';
    conn.appendChild(line);
    container.appendChild(conn);

    var card = document.createElement('div');
    card.className = 'tl-card active';
    card.id = 'card-' + batchId;

    var hdr = document.createElement('div');
    hdr.className = 'tl-card-hdr';
    var dot = document.createElement('div'); dot.className = 'tl-dot'; hdr.appendChild(dot);
    var title = document.createElement('span'); title.className = 'tl-title';
    title.textContent = '批次 #' + batchNum + ' · ' + count + ' 条商品'; hdr.appendChild(title);
    var time = document.createElement('span'); time.className = 'tl-time'; hdr.appendChild(time);
    card.appendChild(hdr);

    var body = document.createElement('div');
    body.className = 'tl-body';
    body.style.cssText = 'max-height:2000px;opacity:1;padding:14px 24px 14px 48px;';
    var log = document.createElement('div');
    log.className = 'tl-log';
    log.id = 'log-' + batchId;
    log.style.cssText = 'max-height:300px;overflow-y:auto;';
    body.appendChild(log);
    card.appendChild(body);

    container.appendChild(card);
    _batchCards[batchId] = { card: card, logEl: log, lineCount: 0 };
    return _batchCards[batchId];
  }

  window._batchAppendLog = function(batchId, line) {
    var bc = _batchCards[batchId];
    if (!bc) return;
    _tlAppendLog(bc.logEl, '→ ' + line);
    bc.lineCount++;
  };

  function _updateBatchTaskPanel(b) {
    if (typeof _taskPanelUpsert !== 'function') return;
    var items = b.items || [];
    var tokens = b.tokens || {};
    var cum = b.cumulative_tokens || {};
    var elapsed = _elapsed(Date.now() - _aiStartTime);
    var detail = (b.method === 'ai' ? 'AI 处理' : '本地推算') + ' · ' + elapsed;
    if (tokens.total_tokens) detail += '\n批次 Token: ' + _fmtTokens(tokens);
    if (cum.total_tokens) detail += '\n累计 Token: ' + _fmtTokens(cum) + ' total:' + cum.total_tokens;
    detail += '\n\n';
    for (var j = 0; j < items.length; j++) {
      var it = items[j];
      var tt = it.tokens || {};
      var bs = it.brand_status || '';
      var cm = it.cat_method || '';
      var method = (bs === 'from_library' ? '品牌库' : bs === 'ai_ok' ? 'AI' : bs === 'no_brand' ? '无品牌' : cm === 'local_fallback' || cm === 'local' ? '本地' : bs || cm || '-');
      detail += '── ' + (j+1) + '. ' + (it.name || '').substring(0, 36) + ' [' + method + ']';
      if (tt.total_tokens) detail += ' (in:' + (tt.prompt_tokens||0) + ' out:' + (tt.completion_tokens||0) + ')';
      detail += '\n';
      detail += '  品牌: ' + (it.brand || '-') + (it.brand_type ? ' [' + it.brand_type + ']' : '') + '\n';
      if (it.brand_reason) detail += '  理由: ' + it.brand_reason.substring(0, 120) + '\n';
      detail += '  分类: ' + (it.category || it.cat_path || '-') + (it.cat_confidence ? ' ' + Math.round(it.cat_confidence*100) + '%' : '') + '\n';
      if (it.cat_entity || it.cat_modifiers) detail += '  factors: ' + (it.cat_entity ? 'entity=' + it.cat_entity : '') + (it.cat_modifiers ? ' modifiers=' + it.cat_modifiers : '') + '\n';
      if (it.cat_reason) detail += '  理由: ' + it.cat_reason.substring(0, 100) + '\n';
    }
    _taskPanelUpsert({ id: 'batch-' + b.batch, title: '批次 #' + b.batch + ' · ' + b.count + ' 条', status: 'done',
      meta: elapsed, tokens: tokens, detail: detail });
  }

  function _updateTokenDisplay(usage) { /* no-op, compat */ }

  _patch();
})();
