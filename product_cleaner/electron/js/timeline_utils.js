// ═══ Shared Timeline Utilities ═══
// DOM helpers for tl-card nodes. Used by timeline.js (diagnosis) and ai_process_electron.js (AI batches).
// CSS classes from native.css: .tl-card / .active / .done / .tl-body / .tl-log / .log-line / .cursor / .kv
(function(){
  if (!window._electronMode) return;

  // Append a log line to a tl-log container. Keeps blinking cursor on the latest line.
  window._tlAppendLog = function(logEl, line) {
    if (!logEl || !line) return;
    var div = document.createElement('div');
    div.className = 'log-line';
    div.textContent = line;
    logEl.appendChild(div);
    logEl.querySelectorAll('.cursor').forEach(function(c) { c.classList.remove('cursor'); });
    div.classList.add('cursor');
  };

  // Replace body content with kv stats. items: [{k, v}, ...]
  window._tlSetKv = function(bodyEl, items) {
    if (!bodyEl) return;
    bodyEl.textContent = '';
    var kv = document.createElement('div');
    kv.className = 'kv';
    (items || []).forEach(function(it) {
      if (it.v || it.v === 0) {
        var item = document.createElement('div');
        item.className = 'item';
        var k = document.createElement('span');
        k.className = 'k';
        k.textContent = it.k;
        item.appendChild(k);
        var v = document.createElement('span');
        v.className = 'v';
        v.textContent = String(it.v);
        item.appendChild(v);
        kv.appendChild(item);
      }
    });
    bodyEl.appendChild(kv);
  };

  // Update the .tl-time span inside a tl-card
  window._tlSetTime = function(cardEl, text) {
    if (!cardEl) return;
    var t = cardEl.querySelector('.tl-time');
    if (t) t.textContent = text;
  };

  // Set card state: 'pending' | 'active' | 'done'. Removes cursor on done.
  window._tlSetState = function(cardEl, state) {
    if (!cardEl) return;
    cardEl.classList.remove('active', 'done', 'pending');
    cardEl.classList.add(state);
    if (state === 'done') {
      cardEl.querySelectorAll('.cursor').forEach(function(c) { c.classList.remove('cursor'); });
    }
  };

  // Create a new tl-card DOM structure. Returns {card, connector, body, titleEl}.
  window._tlCreateCard = function(id, title) {
    var card = document.createElement('div');
    card.className = 'tl-card active';
    if (id) card.id = id;
    // header
    var hdr = document.createElement('div');
    hdr.className = 'tl-card-hdr';
    var dot = document.createElement('div');
    dot.className = 'tl-dot';
    hdr.appendChild(dot);
    var titleEl = document.createElement('span');
    titleEl.className = 'tl-title';
    titleEl.textContent = title;
    hdr.appendChild(titleEl);
    var timeEl = document.createElement('span');
    timeEl.className = 'tl-time';
    hdr.appendChild(timeEl);
    card.appendChild(hdr);
    // body
    var body = document.createElement('div');
    body.className = 'tl-body';
    body.style.cssText = 'max-height:2000px;opacity:1;padding:14px 24px 14px 48px;';
    card.appendChild(body);
    // connector
    var connector = document.createElement('div');
    connector.className = 'tl-connector';
    var line = document.createElement('div');
    line.className = 'line';
    connector.appendChild(line);
    return { card: card, connector: connector, body: body, titleEl: titleEl };
  };

  // Get or create a tl-log div inside a card body
  window._tlEnsureLog = function(cardObj) {
    if (!cardObj.log) {
      cardObj.log = cardObj.body.querySelector('.tl-log');
      if (!cardObj.log) {
        cardObj.log = document.createElement('div');
        cardObj.log.className = 'tl-log';
        cardObj.body.appendChild(cardObj.log);
      }
    }
    return cardObj.log;
  };

  // Append card + connector to a timeline container
  window._tlAppendCard = function(container, cardObj) {
    if (!container || !cardObj) return;
    container.appendChild(cardObj.connector);
    container.appendChild(cardObj.card);
  };

  console.log('timeline_utils: 7 exports OK');
})();
