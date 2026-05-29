// ═══ Agent Mode Controller ═══
// Independent conversation system — separate from workflow and bat assistant.
// Manages: message rendering, stream responses, tool-use display, preview panel.
(function() {
  if (!window._electronMode) return;

  /* ── State ── */
  var _conversationId = null;
  var _messages = [];
  var _isStreaming = false;

  /* ── DOM refs ── */
  function getEl(id) { return document.getElementById(id); }

  var chatStream, inputDock, agentInput, sendBtn, previewPanel, previewContent, previewClose;

  function cacheDom() {
    chatStream = getEl('agentChatStream');
    inputDock = getEl('agentInputDock');
    agentInput = getEl('agentInput');
    sendBtn = getEl('agentSendBtn');
    previewPanel = getEl('agentPreviewPanel');
    previewContent = getEl('previewContent');
    previewClose = getEl('previewCloseBtn');
  }

  /* ── Message rendering (DOM API only) ── */
  function renderUserMessage(text) {
    var wrapper = document.createElement('div');
    wrapper.className = 'agent-message user';

    var bubble = document.createElement('div');
    bubble.className = 'agent-msg-bubble';
    bubble.textContent = text;

    var meta = document.createElement('div');
    meta.className = 'agent-msg-meta';
    meta.textContent = '刚刚';

    wrapper.appendChild(bubble);
    wrapper.appendChild(meta);
    return wrapper;
  }

  function renderAssistantMessage(text) {
    var wrapper = document.createElement('div');
    wrapper.className = 'agent-message assistant';

    var bubble = document.createElement('div');
    bubble.className = 'agent-msg-bubble';
    bubble.textContent = text;

    var meta = document.createElement('div');
    meta.className = 'agent-msg-meta';
    meta.textContent = 'Agent';

    wrapper.appendChild(bubble);
    wrapper.appendChild(meta);
    return wrapper;
  }

  function renderToolCard(toolName, result) {
    var card = document.createElement('div');
    card.className = 'agent-tool-card';

    var header = document.createElement('div');
    header.className = 'tool-header';
    header.textContent = 'tool: ' + toolName;

    var body = document.createElement('div');
    body.className = 'tool-body';
    body.textContent = typeof result === 'string' ? result : JSON.stringify(result, null, 2);

    card.appendChild(header);
    card.appendChild(body);
    return card;
  }

  function renderCodeBlock(language, code) {
    var block = document.createElement('div');
    block.className = 'agent-code-block';

    var header = document.createElement('div');
    header.className = 'code-header';
    header.textContent = language || 'code';

    var body = document.createElement('div');
    body.className = 'code-body';
    body.textContent = code;

    block.appendChild(header);
    block.appendChild(body);
    return block;
  }

  function appendMessage(el) {
    if (!chatStream) return;
    // Remove welcome if present
    var welcome = chatStream.querySelector('.agent-welcome');
    if (welcome) welcome.remove();
    chatStream.appendChild(el);
    chatStream.scrollTop = chatStream.scrollHeight;
  }

  /* ── Input handling ── */
  function sendMessage() {
    if (!agentInput || _isStreaming) return;
    var text = agentInput.value.trim();
    if (!text) return;
    agentInput.value = '';

    appendMessage(renderUserMessage(text));
    _messages.push({ role: 'user', content: text });

    _isStreaming = true;
    if (sendBtn) sendBtn.disabled = true;

    _ensureConversation().then(function() {
      return fetch('/api/agent/conversations/' + _conversationId + '/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          session_id: localStorage.getItem('last_session_id') || '',
          context: window._selectedContext || null
        })
      });
    }).then(function(r) { return r.json(); })
    .then(function(data) {
      if (data.reply) appendMessage(renderAssistantMessage(data.reply));
      if (data.actions && data.actions.length) {
        data.actions.forEach(function(a) {
          if (a.result) appendMessage(renderToolCard(a.tool, a.result));
        });
      }
      _isStreaming = false;
      if (sendBtn) sendBtn.disabled = false;
    }).catch(function(e) {
      appendMessage(renderAssistantMessage('抱歉，连接失败: ' + e.message));
      _isStreaming = false;
      if (sendBtn) sendBtn.disabled = false;
    });
  }

  function _ensureConversation() {
    if (_conversationId) return Promise.resolve();
    return fetch('/api/agent/conversations', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: '', session_id: localStorage.getItem('last_session_id') || '' })
    }).then(function(r) { return r.json(); })
    .then(function(d) { _conversationId = d.conversation_id; });
  }

  /* ── Preview panel ── */
  function showPreview(htmlContent) {
    if (!previewPanel || !previewContent) return;
    if (typeof htmlContent === 'string') {
      previewContent.textContent = '';
      var div = document.createElement('div');
      div.textContent = htmlContent;
      previewContent.appendChild(div);
    } else if (htmlContent instanceof Node) {
      previewContent.textContent = '';
      previewContent.appendChild(htmlContent);
    }
    previewPanel.style.display = '';
  }

  function hidePreview() {
    if (previewPanel) previewPanel.style.display = 'none';
  }

  /* ── New conversation ── */
  function newConversation() {
    _conversationId = null;
    _messages = [];
    if (chatStream) {
      chatStream.textContent = '';
      var welcome = document.createElement('div');
      welcome.className = 'agent-welcome';
      var icon = document.createElement('span');
      icon.className = 'agent-welcome-icon';
      icon.textContent = '☛';
      var p = document.createElement('p');
      p.textContent = 'Agent 模式 — 完整对话与分析';
      welcome.appendChild(icon);
      welcome.appendChild(p);
      chatStream.appendChild(welcome);
    }
    hidePreview();
  }

  /* ── Dispatch from bat console (called by bat Enter handler) ── */
  window._dispatchToAgent = function(text) {
    var agentTab = document.querySelector('#sidebarTabs .sidebar-tab-item[data-tab="agent"]');
    if (agentTab) agentTab.click();

    _ensureConversation().then(function() {
      if (agentInput) agentInput.value = text;
      sendMessage();
    });
  };

  /* ── Bat quick chat (called by bat console Enter for simple Q&A) ── */
  window._batQuickChat = function(text) {
    var ct = document.getElementById('consoleText');
    if (ct) ct.textContent = '...';

    _ensureConversation().then(function() {
      return fetch('/api/agent/conversations/' + _conversationId + '/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          session_id: localStorage.getItem('last_session_id') || '',
          context: window._selectedContext || null
        })
      });
    }).then(function(r) { return r.json(); })
    .then(function(data) {
      if (data.reply) {
        if (ct) ct.textContent = data.reply;
        var bs = document.getElementById('batSpeech');
        if (bs) { bs.textContent = ''; var sp = document.createElement('span'); sp.textContent = data.reply.substring(0, 80); bs.appendChild(sp); bs.style.opacity = '1'; }
      }
    }).catch(function(e) {
      if (ct) ct.textContent = '抱歉，连接失败: ' + e.message;
    });
  };

  /* ── Init ── */
  window.addEventListener('DOMContentLoaded', function() {
    cacheDom();

    if (sendBtn) {
      sendBtn.addEventListener('click', sendMessage);
    }
    if (agentInput) {
      agentInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') sendMessage();
      });
    }
    if (previewClose) {
      previewClose.addEventListener('click', hidePreview);
    }

    // Expose API
    window.AgentController = {
      sendMessage: sendMessage,
      newConversation: newConversation,
      showPreview: showPreview,
      hidePreview: hidePreview,
      get conversationId() { return _conversationId; }
    };

    newConversation();
  });

})();