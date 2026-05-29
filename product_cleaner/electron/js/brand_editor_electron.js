// ═══ Electron: Brand Editor (DOM API) ═══
(function(){
  if (!window._electronMode) return;

  /* Dropdown overflow fix: allow brand dropdown lists to protrude beyond cards */
  (function() {
    var style = document.createElement('style');
    style.textContent = '.brand-group-item { overflow: visible; }';
    document.head.appendChild(style);
  })();

  function initBrandTabs() {
    var tabs = document.querySelectorAll('#emBrandTabs .pane-segment-item');
    tabs.forEach(function(tab) {
      tab.addEventListener('click', function() {
        tabs.forEach(function(t) { t.classList.remove('active'); });
        tab.classList.add('active');
        var type = tab.getAttribute('data-tab');
        ['missing','mismatch','valid','unbranded'].forEach(function(tp) {
          var p = document.getElementById('emPane' + tp.charAt(0).toUpperCase() + tp.slice(1));
          if (p) p.classList.remove('active');
        });
        var pane = document.getElementById('emPane' + type.charAt(0).toUpperCase() + type.slice(1));
        if (pane) pane.classList.add('active');
      });
    });
  }
  setTimeout(initBrandTabs, 200);

  /* ── Brand dropdown factory (pure DOM API, no innerHTML) ── */
  function _BrandDropdown(opts) {
    var containerId = opts.containerId;
    var selectedBrand = opts.selectedBrand || '';
    var placeholder = opts.placeholder || '选择品牌...';

    var wrapper = document.createElement('div');
    wrapper.className = 'brand-dropdown-wrapper';
    wrapper.id = containerId;
    wrapper.dataset.selectedBrand = selectedBrand || '';

    var input = document.createElement('input');
    input.type = 'text';
    input.className = 'brand-dropdown-input';
    input.placeholder = placeholder;
    input.autocomplete = 'off';
    if (selectedBrand) {
      input.value = _getBrandDisplayText(selectedBrand);
    }

    var list = document.createElement('div');
    list.className = 'brand-dropdown-list';
    list.id = containerId + '-list';

    wrapper.appendChild(input);
    wrapper.appendChild(list);

    var _programmatic = false;

    function _getBrandDisplayText(brandName) {
      if (!brandName) return '';
      if (typeof getBrandDisplayText === 'function') return getBrandDisplayText(brandName);
      return brandName;
    }

    function _renderItems(filterText) {
      list.textContent = '';
      var db = window.brandDatabase || [];
      var lower = (filterText || '').toLowerCase();
      var filtered;

      if (lower) {
        filtered = [];
        db.forEach(function(b) {
          var nameMatch = (b.name || '').toLowerCase().indexOf(lower) >= 0;
          var displayMatch = (b.display_name || '').toLowerCase().indexOf(lower) >= 0;
          var matchedAlias = null;
          (b.aliases || []).forEach(function(a) {
            if (a.toLowerCase().indexOf(lower) >= 0) matchedAlias = a;
          });
          if (nameMatch || displayMatch || matchedAlias) {
            filtered.push({ brand: b, matchedAlias: (nameMatch || displayMatch) ? null : matchedAlias });
          }
        });
      } else {
        filtered = db.map(function(b) { return { brand: b, matchedAlias: null }; });
      }

      if (filtered.length === 0) {
        var empty = document.createElement('div');
        empty.className = 'brand-dropdown-empty';
        empty.textContent = '无匹配品牌';
        list.appendChild(empty);
        return;
      }

      var limit = 2000;
      var display = filtered.slice(0, limit);

      display.forEach(function(item) {
        var b = item.brand;
        var cur = wrapper.dataset.selectedBrand || '';
        var isSel = b.name === cur;
        var row = document.createElement('div');
        row.className = 'brand-dropdown-item' + (isSel ? ' selected' : '');

        var col = document.createElement('div');
        col.className = 'flex flex-col';

        var topRow = document.createElement('div');
        var nameEl = document.createElement('span');
        nameEl.className = 'brand-name';
        nameEl.textContent = b.display_name || b.name;
        topRow.appendChild(nameEl);

        if (item.matchedAlias) {
          var aliasHint = document.createElement('span');
          aliasHint.style.cssText = 'font-size:10px;color:#e5c07b;margin-left:4px;';
          aliasHint.textContent = '(' + item.matchedAlias + ')';
          topRow.appendChild(aliasHint);
        }

        var meta = document.createElement('span');
        meta.className = 'brand-meta';
        meta.textContent = (b.type || '未知') + ' · ' + (b.country || 'CN');

        col.appendChild(topRow);
        col.appendChild(meta);
        row.appendChild(col);

        row.addEventListener('click', function(ev) {
          ev.stopPropagation();
          wrapper.dataset.selectedBrand = b.name;
          _programmatic = true;
          input.value = _getBrandDisplayText(b.name);
          _programmatic = false;
          _close();
        });

        list.appendChild(row);
      });
    }

    function _close() {
      list.style.display = 'none';
    }

    input.onclick = function(e) {
      e.stopPropagation();
      input.removeAttribute('readonly');
      if (list.style.display === 'block') {
        _close();
      } else {
        _renderItems(input.value);
        list.style.display = 'block';
      }
    };
    input.oninput = function() {
      input.removeAttribute('readonly');
      if (_programmatic) return;
      _renderItems(this.value);
      list.style.display = 'block';
    };

    /* Initial render */
    _renderItems('');

    return wrapper;
  }

  /* Click outside closes all brand dropdowns */
  document.addEventListener('click', function(e) {
    var allLists = document.querySelectorAll('.brand-dropdown-list');
    for (var i = 0; i < allLists.length; i++) {
      if (allLists[i].style.display === 'block') {
        var parent = allLists[i].parentElement;
        if (parent && !parent.contains(e.target)) {
          allLists[i].style.display = 'none';
        }
      }
    }
  });

  /* Override shared toggle/filter for Electron DOM compatibility */
  window.toggleBrandDropdown = function(containerId) {
    var wrapper = document.getElementById(containerId);
    if (!wrapper) return;
    var list = wrapper.querySelector('.brand-dropdown-list');
    if (!list) return;
    var input = wrapper.querySelector('.brand-dropdown-input');
    var isOpen = list.classList.contains('open');
    var allLists = document.querySelectorAll('.brand-dropdown-list.open');
    for (var i = 0; i < allLists.length; i++) {
      if (allLists[i].id !== (containerId + '-list')) allLists[i].classList.remove('open');
    }
    if (!isOpen) {
      list.classList.add('open');
      if (input) { input.removeAttribute('readonly'); input.focus(); input.select(); }
    } else {
      list.classList.remove('open');
    }
  };
  window.filterBrandDropdown = function(containerId, text) {
    var list = document.getElementById(containerId + '-list');
    if (!list) return;
    /* Re-render using brandDatabase filtering */
    list.textContent = '';
    var db = window.brandDatabase || [];
    var lower = (text || '').toLowerCase();
    var sel = (document.getElementById(containerId) || {}).dataset.selectedBrand || '';
    var filtered = lower ? db.filter(function(b) {
      return (b.name || '').toLowerCase().indexOf(lower) >= 0 ||
             (b.display_name || '').toLowerCase().indexOf(lower) >= 0 ||
             (b.aliases || []).some(function(a) { return a.toLowerCase().indexOf(lower) >= 0; });
    }) : db;
    if (!filtered.length) {
      var empty = document.createElement('div');
      empty.className = 'brand-dropdown-empty';
      empty.textContent = '无匹配品牌';
      list.appendChild(empty);
    } else {
      filtered.slice(0, 2000).forEach(function(b) {
        var row = document.createElement('div');
        row.className = 'brand-dropdown-item' + (b.name === sel ? ' selected' : '');
        var col = document.createElement('div'); col.className = 'flex flex-col';
        var topRow = document.createElement('div');
        var n = document.createElement('span'); n.className = 'brand-name'; n.textContent = b.display_name || b.name;
        topRow.appendChild(n);
        var m = document.createElement('span'); m.className = 'brand-meta'; m.textContent = (b.type || '未知') + ' · ' + (b.country || 'CN');
        col.appendChild(topRow); col.appendChild(m); row.appendChild(col);
        row.addEventListener('click', function(ev) {
          ev.stopPropagation();
          var w = document.getElementById(containerId);
          if (w) w.dataset.selectedBrand = b.name;
          var inp = w ? w.querySelector('.brand-dropdown-input') : null;
          if (inp) inp.value = (typeof getBrandDisplayText === 'function' ? getBrandDisplayText(b.name) : b.name);
          list.classList.remove('open');
        });
        list.appendChild(row);
      });
    }
    if (!list.classList.contains('open')) list.classList.add('open');
  };

  /* Override renderConfigDropdown — DOM API, no innerHTML */
  window.renderConfigDropdown = function(containerId, listId, inputId, items, labelKey, valueKey, selectedValue, placeholder) {
    var container = document.getElementById(containerId);
    var list = document.getElementById(listId);
    var input = document.getElementById(inputId);
    if (!container || !list || !input) return;

    function getSel() { return container.dataset.selected || selectedValue || ''; }

    function renderList(filteredItems) {
      list.textContent = '';
      if (!filteredItems.length) {
        var empty = document.createElement('div');
        empty.className = 'brand-dropdown-empty';
        empty.textContent = '无匹配选项';
        list.appendChild(empty);
        return;
      }
      var curSel = getSel();
      filteredItems.forEach(function(item) {
        var label = typeof item === 'string' ? item : item[labelKey || 'name'];
        var val = typeof item === 'string' ? item : item[valueKey || 'code'];
        var isSel = (val === curSel || label === curSel);
        var row = document.createElement('div');
        row.className = 'brand-dropdown-item' + (isSel ? ' selected' : '');
        var sp = document.createElement('span');
        sp.className = 'brand-name';
        sp.textContent = label;
        row.appendChild(sp);
        row.addEventListener('click', function(ev) {
          ev.stopPropagation();
          var cEl = document.getElementById(containerId);
          if (cEl) cEl.dataset.selected = val;
          var inpEl = document.getElementById(inputId);
          if (inpEl) inpEl.value = label;
          var listEl = document.getElementById(listId);
          if (listEl) listEl.classList.remove('open');
        });
        list.appendChild(row);
      });
    }

    function filter(text) {
      var lower = (text || '').toLowerCase();
      var filtered = items.filter(function(item) {
        var label = typeof item === 'string' ? item : item[labelKey || 'name'];
        return label.toLowerCase().indexOf(lower) >= 0;
      });
      renderList(filtered);
      if (!list.classList.contains('open')) list.classList.add('open');
    }

    function _openAndFilter(text) {
      var allLists = document.querySelectorAll('.brand-dropdown-list.open');
      for (var i = 0; i < allLists.length; i++) {
        if (allLists[i].id !== list.id) allLists[i].classList.remove('open');
      }
      filter(text || input.value);
    }

    input.value = selectedValue && selectedValue !== '未知' ? selectedValue : '';
    input.placeholder = placeholder || '选择...';
    container.dataset.selected = selectedValue || '';

    input.oninput = function() { filter(this.value); };
    input.onfocus = function() { _openAndFilter(this.value); };
    input.onclick = function(e) { e.stopPropagation(); _openAndFilter(this.value); };

    renderList(items);
  };

  /* Override filterParentBrands — DOM API */
  window.filterParentBrands = function(text) {
    var list = document.getElementById('modalParentBrandList');
    var container = document.getElementById('modalParentBrandContainer');
    if (!list || !container) return;
    if (!window.brandDatabase) return;
    var lower = (text || '').toLowerCase();
    var filtered = window.brandDatabase.filter(function(b) {
      return b.name && b.name.toLowerCase().indexOf(lower) >= 0;
    });
    list.textContent = '';
    if (!filtered.length) {
      var empty = document.createElement('div');
      empty.className = 'brand-dropdown-empty';
      empty.textContent = '无匹配';
      list.appendChild(empty);
    } else {
      filtered.slice(0, 2000).forEach(function(b) {
        var row = document.createElement('div');
        row.className = 'brand-dropdown-item';
        var sp = document.createElement('span');
        sp.className = 'brand-name';
        sp.textContent = b.name;
        row.appendChild(sp);
        row.addEventListener('click', function(ev) {
          ev.stopPropagation();
          var inp = document.getElementById('modalParentBrand');
          if (inp) inp.value = b.name;
          container.dataset.selected = b.name;
          list.style.display = 'none';
          var relRow = document.getElementById('modalRelationType');
          if (relRow) relRow.style.display = 'flex';
          var radio = document.getElementById('relationSubBrand');
          if (radio) radio.checked = true;
        });
        list.appendChild(row);
      });
    }
    list.style.display = 'block';
  };

  /* Override renderBrandConfigList — DOM API */
  window.renderBrandConfigList = function() {
    var container = document.getElementById('brandConfigList');
    if (!container) return;
    fetch('/api/brands/config').then(function(r) { return r.json(); }).then(function(config) {
      container.textContent = '';
      if (brandConfigMode === 'types') {
        var types = config.brand_types || [];
        if (!types.length) {
          var empty = document.createElement('p');
          empty.style.cssText = 'color:var(--text-muted);font-size:12px;';
          empty.textContent = '暂无类型';
          container.appendChild(empty);
        } else {
          types.forEach(function(t) {
            var row = document.createElement('div');
            row.style.cssText = 'display:flex;align-items:center;justify-content:space-between;padding:4px 8px;background:rgba(0,0,0,0.1);border-radius:var(--radius-sm);margin-bottom:4px;';
            var sp = document.createElement('span'); sp.textContent = t; sp.style.fontSize = '13px';
            row.appendChild(sp);
            var del = document.createElement('button');
            del.style.cssText = 'color:var(--red);background:none;border:none;cursor:pointer;font-size:12px;';
            del.textContent = '✕';
            del.onclick = function() { window.deleteBrandConfigItem(t); };
            row.appendChild(del);
            container.appendChild(row);
          });
        }
      } else {
        var countries = config.countries || [];
        if (!countries.length) {
          var empty = document.createElement('p');
          empty.style.cssText = 'color:var(--text-muted);font-size:12px;';
          empty.textContent = '暂无国家';
          container.appendChild(empty);
        } else {
          countries.forEach(function(c) {
            var row = document.createElement('div');
            row.style.cssText = 'display:flex;align-items:center;justify-content:space-between;padding:4px 8px;background:rgba(0,0,0,0.1);border-radius:var(--radius-sm);margin-bottom:4px;';
            var sp = document.createElement('span'); sp.textContent = c.code + ' (' + c.name + ')'; sp.style.fontSize = '13px';
            row.appendChild(sp);
            var del = document.createElement('button');
            del.style.cssText = 'color:var(--red);background:none;border:none;cursor:pointer;font-size:12px;';
            del.textContent = '✕';
            del.onclick = function() { window.deleteBrandConfigItem(c.code); };
            row.appendChild(del);
            container.appendChild(row);
          });
        }
      }
    }).catch(function() {
      container.textContent = '';
      var err = document.createElement('p');
      err.style.cssText = 'color:var(--red);font-size:12px;';
      err.textContent = '加载失败，请重试';
      container.appendChild(err);
    });
  };

  function cp(groups) {
    var t = 0, p = 0;
    groups.forEach(function(g) {
      t += g.count || 0;
      p += (g.items || []).filter(function(i) { return (window.brandRules || {})[String(i.code).trim()]; }).length;
    });
    return { t: t, p: p };
  }

  /* ── Group cards (DOM API) ── */
  function renderGroupCards(containerId, groups, type) {
    var c = document.getElementById(containerId);
    if (!c) return;
    c.textContent = '';
    if (!groups || !groups.length) {
      var empty = document.createElement('div');
      empty.style.cssText = 'font-size:11px;color:var(--text-muted);padding:32px;text-align:center;';
      empty.textContent = '暂无数据';
      c.appendChild(empty);
      return;
    }
    groups.forEach(function(g) {
      c.appendChild(_buildGroupCard(g, type));
    });
    if (type === 'missing') {
      setTimeout(function() {
        groups.forEach(function(g) {
          var wrap = document.getElementById('brand-dd-wrap-' + g.cluster_id);
          if (!wrap) return;
          var cid = 'brand-dd-group-' + g.cluster_id;
          try { wrap.textContent = ''; wrap.appendChild(_BrandDropdown({containerId: cid, placeholder: '搜索品牌...'})); } catch(e) {}
        });
      }, 200);
    }
  }

  function _buildGroupCard(g, type) {
    var brand = g.suggested_standard || '';
    var count = g.count, items = g.items || [];
    var rules = window.brandRules || {};
    var proc = items.filter(function(i) { return rules[String(i.code).trim()]; }).length;

    var card = document.createElement('div');
    card.className = 'brand-group-item';

    var hdr = document.createElement('div');
    hdr.className = 'brand-group-header';

    // 上排：title
    var title = document.createElement('div');
    title.className = 'g-title';
    if (type === 'missing') {
      title.textContent = '建议品牌: ';
      var b = document.createElement('b'); b.style.color = 'var(--orange)'; b.textContent = brand; title.appendChild(b);
    } else if (type === 'mismatch') {
      title.textContent = '疑似错误品牌';
    } else if (type === 'valid') {
      title.textContent = '待确认品牌: ';
      var b2 = document.createElement('b'); b2.style.color = 'var(--accent)'; b2.textContent = brand; title.appendChild(b2);
    } else {
      title.textContent = '无品牌候选';
    }
    hdr.appendChild(title);

    // 中排：meta 统计 + 示例，一行截断
    var examples = items.slice(0,2).map(function(i){return (i.name||i.code);}).join(', ');
    var meta = document.createElement('div');
    meta.className = 'g-meta';
    meta.textContent = proc + '/' + count + ' 已处理 · 共 ' + count + ' 个商品 · 示例: ' + examples;
    hdr.appendChild(meta);

    // 下排：badges + actions
    var bottomRow = document.createElement('div');
    bottomRow.className = 'g-bottom-row';

    var badges = document.createElement('div');
    badges.className = 'g-badges';
    var badge = document.createElement('span');
    if (proc === count && count > 0) { badge.className = 'badge-flat grn'; badge.textContent = '✓ 已完成'; }
    else { badge.className = 'badge-flat muted'; badge.textContent = '待处理 '+(count-proc)+'/'+count; }
    badges.appendChild(badge);
    bottomRow.appendChild(badges);

    // Actions
    var actions = document.createElement('div');
    actions.className = 'g-actions';

    if (type === 'missing') {
      var ddWrap = document.createElement('div');
      ddWrap.id = 'brand-dd-wrap-' + g.cluster_id;
      ddWrap.style.cssText = 'display:flex;align-items:center;gap:4px;';
      actions.appendChild(ddWrap);

      var applyBtn = document.createElement('button');
      applyBtn.className = 'btn-agent primary';
      applyBtn.textContent = '应用';
      applyBtn.onclick = function() {
        var w = document.getElementById('brand-dd-group-' + g.cluster_id);
        var s = w ? w.dataset.selectedBrand : null;
        if (s) window.batchSetBrand(g.cluster_id, s);
      };
      actions.appendChild(applyBtn);
    }

    var quickSel = document.createElement('select');
    quickSel.style.cssText = 'padding:5px 8px;border:1px solid var(--border);border-radius:var(--radius-sm);background:var(--panel);color:var(--text-main);font-size:11px;';
    quickSel.textContent = '';
    var _qs0 = document.createElement('option'); _qs0.value = ''; _qs0.textContent = '快捷...'; quickSel.appendChild(_qs0);
    var _qs1 = document.createElement('option'); _qs1.value = '__NO_BRAND__'; _qs1.textContent = '无品牌'; quickSel.appendChild(_qs1);
    var _qs2 = document.createElement('option'); _qs2.value = '__NEW_BRAND__'; _qs2.textContent = '+ 新品牌'; quickSel.appendChild(_qs2);
    quickSel.onchange = function() {
      if (this.value === '__NEW_BRAND__') { this.value = ''; if (typeof openAddBrandModal === 'function') openAddBrandModal(g.cluster_id, 'batch'); return; }
      if (window.batchSetBrand) window.batchSetBrand(g.cluster_id, this.value);
    };
    actions.appendChild(quickSel);

    var skipBtn = document.createElement('button');
    skipBtn.className = 'btn-agent secondary';
    skipBtn.textContent = '跳过';
    skipBtn.onclick = function() { if (window.skipGroup) window.skipGroup(g.cluster_id); };
    actions.appendChild(skipBtn);

    var viewBtn = document.createElement('button');
    viewBtn.className = 'btn-agent primary';
    viewBtn.textContent = '查看(' + count + ')';
    viewBtn.onclick = function() { window._emOpenProductList(type, g.cluster_id); };
    actions.appendChild(viewBtn);

    bottomRow.appendChild(actions);
    hdr.appendChild(bottomRow);
    card.appendChild(hdr);
    return card;
  }

  /* ── Pagination ── */
  var _brandPage = { missing: 1, mismatch: 1, valid: 1, unbranded: 1 };
  var PER_PAGE = 10;

  function renderGroupsPaged(containerId, groups, type) {
    var page = _brandPage[type] || 1;
    var total = Math.ceil(groups.length / PER_PAGE);
    if (page > total) page = total;
    if (page < 1) page = 1;
    _brandPage[type] = page;
    var start = (page - 1) * PER_PAGE;
    var paged = groups.slice(start, start + PER_PAGE);
    renderGroupCards(containerId, paged, type);

    var paginationId = containerId.replace('Groups', 'Pagination');
    var pgEl = document.getElementById(paginationId);
    if (!pgEl) return;
    pgEl.textContent = '';
    if (total <= 1) return;

    var wrap = document.createElement('div');
    wrap.style.cssText = 'display:flex;align-items:center;justify-content:center;gap:4px;padding:8px 0;';

    var prev = document.createElement('button');
    prev.className = 'btn-agent secondary';
    prev.textContent = '上一页';
    if (page <= 1) prev.disabled = true;
    prev.onclick = function() { window._changeBrandPage(type, page - 1); };
    wrap.appendChild(prev);

    var info = document.createElement('span');
    info.style.cssText = 'font-size:11px;color:var(--text-muted);padding:0 8px;';
    info.textContent = page + '/' + total;
    wrap.appendChild(info);

    var next = document.createElement('button');
    next.className = 'btn-agent secondary';
    next.textContent = '下一页';
    if (page >= total) next.disabled = true;
    next.onclick = function() { window._changeBrandPage(type, page + 1); };
    wrap.appendChild(next);

    pgEl.appendChild(wrap);
  }

  window._changeBrandPage = function(type, newPage) {
    _brandPage[type] = newPage;
    var clusters = (window.diagnosisData && window.diagnosisData.brand_clusters) || [];
    var groups;
    if (type === 'missing') groups = clusters.filter(function(c) { return c.type === 'missing'; });
    else if (type === 'mismatch') groups = clusters.filter(function(c) { return c.type === 'mismatch'; });
    else if (type === 'valid') groups = clusters.filter(function(c) { return c.type === 'valid'; });
    else groups = clusters.filter(function(c) { return c.type === 'unbranded'; });
    var containerId = 'em' + type.charAt(0).toUpperCase() + type.slice(1) + 'Groups';
    renderGroupsPaged(containerId, groups, type);
  };

  function renderBrandTabs(clusters) {
    if (!clusters || !Array.isArray(clusters)) return;
    var missing = clusters.filter(function(c) { return c.type === 'missing'; });
    var mismatch = clusters.filter(function(c) { return c.type === 'mismatch'; });
    var valid = clusters.filter(function(c) { return c.type === 'valid'; });
    var unbranded = clusters.filter(function(c) { return c.type === 'unbranded'; });

    var mg = cp(missing), e;
    e = document.getElementById('emMissingCount'); if (e) e.textContent = mg.t + '个商品code';
    e = document.getElementById('emMissingTabCount'); if (e) e.textContent = mg.t;
    e = document.getElementById('emMissingProgressFill'); if (e) e.style.width = (mg.t ? Math.round(mg.p / mg.t * 100) : 0) + '%';
    renderGroupsPaged('emMissingGroups', missing, 'missing');

    var mm = cp(mismatch);
    e = document.getElementById('emMismatchCount'); if (e) e.textContent = mm.t + '个商品code';
    e = document.getElementById('emMismatchTabCount'); if (e) e.textContent = mm.t;
    e = document.getElementById('emMismatchProgressFill'); if (e) e.style.width = (mm.t ? Math.round(mm.p / mm.t * 100) : 0) + '%';
    renderGroupsPaged('emMismatchGroups', mismatch, 'mismatch');

    var mv = cp(valid);
    e = document.getElementById('emValidCount'); if (e) e.textContent = mv.t + '个商品code';
    e = document.getElementById('emValidTabCount'); if (e) e.textContent = mv.t;
    e = document.getElementById('emValidProgressFill'); if (e) e.style.width = (mv.t ? Math.round(mv.p / mv.t * 100) : 0) + '%';
    renderGroupsPaged('emValidGroups', valid, 'valid');

    if (unbranded.length > 0) {
      var mu = cp(unbranded);
      e = document.getElementById('emUnbrandedCount'); if (e) e.textContent = mu.t + '个商品code';
      e = document.getElementById('emUnbrandedTabCount'); if (e) e.textContent = mu.t;
      e = document.getElementById('emUnbrandedProgressFill'); if (e) e.style.width = (mu.t ? Math.round(mu.p / mu.t * 100) : 0) + '%';
      renderGroupsPaged('emUnbrandedGroups', unbranded, 'unbranded');
    }
  }

  /* ── New brands panel ── */
  function renderNewBrands() {
    var sidebar = document.getElementById('newBrandsSidebar');
    var list = document.getElementById('newBrandsList');
    var countEl = document.getElementById('newBrandsCount');
    var nb = window.newBrands || [];
    if (countEl) countEl.textContent = '(' + nb.length + ')';
    if (nb.length === 0) {
      if (typeof window._closePanelCard === 'function') window._closePanelCard('new-brands', 'newBrandsSidebar');
      return;
    }
    if (typeof window._movePanelToCard === 'function') {
      window._movePanelToCard('newBrandsSidebar', 'new-brands', '新品牌发现');
    }

    var st = ((document.getElementById('newBrandsSearch') || {}).value || '').trim().toLowerCase();
    var filtered = st ? nb.filter(function(b) {
      return ((b.name||'').toLowerCase().indexOf(st) >= 0 || (b.suggested_name||'').toLowerCase().indexOf(st) >= 0 ||
              (b.sample_product||'').toLowerCase().indexOf(st) >= 0 || (b.sample_category||'').toLowerCase().indexOf(st) >= 0);
    }) : nb;
    var shown = filtered.length;
    if (countEl) countEl.textContent = st ? '(' + shown + '/' + nb.length + ')' : '(' + nb.length + ')';

    list.textContent = '';
    if (shown === 0 && st) {
      var empty = document.createElement('div');
      empty.style.cssText = 'font-size:11px;color:var(--text-muted);text-align:center;padding:32px 0;';
      empty.textContent = '未找到匹配';
      list.appendChild(empty);
      return;
    }
    filtered.forEach(function(brand) {
      list.appendChild(_buildNewBrandItem(brand, nb));
    });
  }
  window.updateNewBrandsDisplay = renderNewBrands;

  function _buildNewBrandItem(brand, nb) {
    var idx = nb.indexOf(brand);
    var sn = brand.name || '';
    var ss = brand.suggested_name || '';
    var hasSug = brand.suggested_name && brand.suggested_name !== brand.name;

    var li = document.createElement('li');
    li.className = 'audit-card';

    // Top row
    var topRow = document.createElement('div');
    topRow.style.cssText = 'display:flex;align-items:flex-start;justify-content:space-between;gap:8px;';
    var nameSpan = document.createElement('span');
    nameSpan.className = 'card-subject';
    nameSpan.style.cssText = 'flex:1;min-width:0;';
    nameSpan.textContent = brand.name;
    topRow.appendChild(nameSpan);
    var tags = document.createElement('span');
    tags.style.cssText = 'display:flex;gap:4px;flex-shrink:0;';
    var cTag = document.createElement('span'); cTag.className = 'badge-flat muted'; cTag.textContent = brand.country || 'CN'; tags.appendChild(cTag);
    var tTag = document.createElement('span'); tTag.className = 'badge-flat muted'; tTag.textContent = brand.type || '未知'; tags.appendChild(tTag);
    topRow.appendChild(tags);
    li.appendChild(topRow);

    // Suggestion
    if (hasSug) {
      var sug = document.createElement('div');
      sug.style.cssText = 'padding:6px 8px;background:var(--bg-accent);border:1px solid rgba(59,130,246,0.1);border-radius:var(--radius-sm);cursor:pointer;font-size:11px;';
      sug.onclick = function() { applySlashSuggestion(sn, ss); };
      var sugLabel = document.createElement('span'); sugLabel.style.cssText = 'color:var(--accent);font-weight:600;'; sugLabel.textContent = '建议更名为: ';
      sug.appendChild(sugLabel);
      var sugVal = document.createElement('span'); sugVal.style.color = 'var(--text-main)'; sugVal.textContent = brand.suggested_name;
      sug.appendChild(sugVal);
      li.appendChild(sug);
    }

    // Actions
    var actRow = document.createElement('div');
    actRow.className = 'actions-group';
    if (!brand.confirmed) {
      var editBtn = document.createElement('button'); editBtn.className = 'btn-agent secondary'; editBtn.textContent = '编辑';
      editBtn.onclick = function() { openAddBrandModalFromSidebar(sn, idx); };
      actRow.appendChild(editBtn);
      var dimBtn = document.createElement('button'); dimBtn.className = 'btn-agent secondary'; dimBtn.textContent = '不是品牌';
      dimBtn.onclick = function() { dismissNewBrand(idx); };
      actRow.appendChild(dimBtn);
    }
    if (brand.confirmed) {
      var done = document.createElement('button'); done.className = 'btn-agent primary'; done.style.cssText = 'opacity:0.5;cursor:default;'; done.textContent = '已入库';
      actRow.appendChild(done);
    } else {
      var conf = document.createElement('button'); conf.className = 'btn-agent primary'; conf.textContent = '确认入库';
      conf.onclick = function() { confirmBrandToLibrary(idx); };
      actRow.appendChild(conf);
    }
    li.appendChild(actRow);

    // Sample
    if (brand.sample_product) {
      var sample = document.createElement('div');
      var sampleLabel = document.createElement('div'); sampleLabel.className = 'card-section-label'; sampleLabel.style.marginBottom = '6px';
      sampleLabel.textContent = '参考样本：';
      sample.appendChild(sampleLabel);
      var sampleName = document.createElement('div');
      sampleName.style.cssText = 'font-size:12px;color:var(--text-sub);font-weight:500;margin-bottom:6px;';
      sampleName.textContent = brand.sample_product;
      sample.appendChild(sampleName);
      var crumb = document.createElement('div'); crumb.className = 'crumb-path';
      (brand.sample_category || '').split('>').forEach(function(s, i, arr) {
        if (i > 0) { var arr2 = document.createElement('span'); arr2.className = 'crumb-arrow'; arr2.textContent = '›'; crumb.appendChild(arr2); }
        var ci = document.createElement('span'); ci.className = 'crumb-item'; ci.textContent = s.trim(); crumb.appendChild(ci);
      });
      sample.appendChild(crumb);
      li.appendChild(sample);
    }
    return li;
  }

  /* ── Product list panel (side panel) ── */
  function _renderBrandProductList(items, type, title, ddPrefix, batchOptions) {
    var PER_PAGE_ITEMS = 20;
    var currentPage = 1;
    var totalPages = Math.ceil(items.length / PER_PAGE_ITEMS);
    var sp = document.getElementById('sidePanel');
    var itemList = document.getElementById('panelItemsList');
    if (!sp || !itemList) return;

    var rules = window.brandRules || {};
    var sectionLabels = { missing: '品牌缺失', mismatch: '品牌错误', valid: '待确认', unbranded: '无品牌' };

    function renderPage(pg) {
      currentPage = pg;
      document.getElementById('sidePanelTitle').textContent = title + ' (' + items.length + ')';
      var subEl = document.getElementById('sidePanelSubtitle');
      if (subEl) subEl.textContent = '第 ' + ((pg-1)*PER_PAGE_ITEMS+1) + '-' + Math.min(pg*PER_PAGE_ITEMS, items.length) + ' / 共 ' + items.length + ' 条';
      itemList.className = 'scroller-list';
      itemList.textContent = '';

      var startIdx = (pg - 1) * PER_PAGE_ITEMS;
      var pageItems = items.slice(startIdx, startIdx + PER_PAGE_ITEMS);

      pageItems.forEach(function(item) {
        itemList.appendChild(_buildProductListItem(item, type, ddPrefix, rules, sectionLabels));
      });

      // Pagination
      var pgEl = document.getElementById('panelPagination');
      pgEl.textContent = '';
      if (totalPages > 1) {
        var pgWrap = document.createElement('div');
        pgWrap.style.cssText = 'display:flex;align-items:center;justify-content:center;gap:4px;padding:8px 0;';
        var prev = document.createElement('button'); prev.className = 'btn-agent secondary'; prev.style.cssText = 'font-size:10px;padding:2px 8px;';
        prev.textContent = '上一页'; if (pg <= 1) prev.disabled = true; prev.onclick = function() { window._rp(pg - 1); }; pgWrap.appendChild(prev);
        var info = document.createElement('span'); info.style.cssText = 'font-size:11px;color:var(--text-muted);padding:0 8px;';
        info.textContent = pg + '/' + totalPages; pgWrap.appendChild(info);
        var next = document.createElement('button'); next.className = 'btn-agent secondary'; next.style.cssText = 'font-size:10px;padding:2px 8px;';
        next.textContent = '下一页'; if (pg >= totalPages) next.disabled = true; next.onclick = function() { window._rp(pg + 1); }; pgWrap.appendChild(next);
        pgEl.appendChild(pgWrap);
      }

      // Batch actions
      var baEl = document.getElementById('panelBatchActions');
      baEl.textContent = '';
      if ((batchOptions||[]).length) {
        var baWrap = document.createElement('div'); baWrap.className = 'actions-group'; baWrap.style.flexWrap = 'wrap';
        (batchOptions||[]).forEach(function(opt) {
          if (typeof opt === 'function') baWrap.appendChild(opt());
        });
        baEl.appendChild(baWrap);
      }

      // Init dropdowns
      setTimeout(function() {
        pageItems.forEach(function(item) {
          var code = String(item.code).trim();
          try { var c = itemList.querySelector('[data-code="' + code + '"]'); if (c) { c.textContent = ''; c.appendChild(_BrandDropdown({containerId: ddPrefix + code, selectedBrand: item.suggested_brand, placeholder: '选择品牌...'})); } } catch(e) {}
        });
      }, 100);
    }

    window.currentPanelData = { type: type, items: items };
    window._currentPanelRender = { items: items, type: type, title: title, ddPrefix: ddPrefix, batchOptions: batchOptions };
    window._rp = renderPage;
    renderPage(1);

    if (typeof window._movePanelToCard === 'function') {
      if (typeof window._closePanelCard === 'function') window._closePanelCard('category-product-list', 'sidePanel');
      window._movePanelToCard('sidePanel', 'product-list', title);
    }
    sp.classList.remove('hidden');
  }

  function _buildProductListItem(item, type, ddPrefix, rules, sectionLabels) {
    var code = String(item.code).trim();
    var rule = rules[code] || {};
    var itemType = item._section || type || 'missing';

    var li = document.createElement('li');
    li.className = 'audit-card';

    // Main row
    var mainRow = document.createElement('div');
    mainRow.style.cssText = 'display:flex;align-items:flex-start;justify-content:space-between;gap:8px;';

    var infoCol = document.createElement('div');
    infoCol.style.cssText = 'display:flex;align-items:flex-start;gap:8px;flex:1;min-width:0;';

    if (item.org_image_url) {
      var img = document.createElement('img');
      img.src = item.org_image_url;
      img.style.cssText = 'width:40px;height:40px;object-fit:cover;border-radius:4px;flex-shrink:0;cursor:pointer;';
      img.onerror = function() { this.style.display = 'none'; };
      img.onclick = function(e) { e.stopPropagation(); window.open(item.org_image_url); };
      infoCol.appendChild(img);
    }

    var textCol = document.createElement('div');
    textCol.style.cssText = 'min-width:0;flex:1;';

    var topRow = document.createElement('div');
    topRow.style.cssText = 'display:flex;align-items:center;gap:6px;margin-bottom:4px;';
    var typeBadge = document.createElement('span');
    var badgeCls = itemType==='missing'?'org':itemType==='mismatch'?'red':itemType==='valid'?'acc':'muted';
    typeBadge.className = 'badge-flat ' + badgeCls;
    typeBadge.textContent = sectionLabels[itemType] || itemType;
    topRow.appendChild(typeBadge);
    var nameSpan = document.createElement('span'); nameSpan.className = 'card-subject'; nameSpan.style.fontSize = '13px';
    nameSpan.textContent = item.name || code || '';
    topRow.appendChild(nameSpan);
    textCol.appendChild(topRow);

    var specGrid = document.createElement('div');
    specGrid.className = 'meta-spec-grid';
    specGrid.style.cssText = 'padding:4px 8px;margin-bottom:4px;';
    var specLine = document.createElement('div'); specLine.className = 'spec-line';
    var sk1 = document.createElement('span'); sk1.className = 'spec-k'; sk1.textContent = 'Code:';
    var sv1 = document.createElement('span'); sv1.className = 'spec-v'; sv1.textContent = code || '';
    specLine.appendChild(sk1); specLine.appendChild(sv1);
    var skLbl = document.createElement('span'); skLbl.style.marginLeft = '12px'; skLbl.className = 'spec-k'; skLbl.textContent = '行号:';
    var sv2 = document.createElement('span'); sv2.className = 'spec-v'; sv2.textContent = item.row != null ? item.row : '-';
    specLine.appendChild(skLbl); specLine.appendChild(sv2);
    specGrid.appendChild(specLine);
    textCol.appendChild(specGrid);

    _appendSuggestion(textCol, itemType, item, rule);
    _appendFactors(textCol, item);
    infoCol.appendChild(textCol);
    mainRow.appendChild(infoCol);

    // Status
    var statusDiv = document.createElement('div');
    statusDiv.style.cssText = 'flex-shrink:0;text-align:right;';
    statusDiv.appendChild(_buildItemStatus(rule));
    mainRow.appendChild(statusDiv);
    li.appendChild(mainRow);

    // Action row
    var actRow = document.createElement('div');
    actRow.style.cssText = 'display:flex;gap:6px;align-items:center;';
    var ddWrap = document.createElement('div');
    ddWrap.dataset.code = code;
    ddWrap.style.cssText = 'flex:1;display:flex;gap:4px;align-items:center;';
    actRow.appendChild(ddWrap);
    var setBtn = document.createElement('button'); setBtn.className = 'btn-agent primary'; setBtn.textContent = '设置';
    setBtn.onclick = function() {
      var w = document.getElementById(ddPrefix + code);
      var s = w ? w.dataset.selectedBrand : null;
      if (s && window.setItemBrand) window.setItemBrand(code, s);
    };
    actRow.appendChild(setBtn);
    var quickSel = document.createElement('select');
    quickSel.style.cssText = 'padding:4px 6px;border:1px solid var(--border);border-radius:var(--radius-sm);background:var(--panel);color:var(--text-main);font-size:11px;';
    quickSel.textContent = '';
    var _qs0 = document.createElement('option'); _qs0.value = ''; _qs0.textContent = '快捷...'; quickSel.appendChild(_qs0);
    var _qs1 = document.createElement('option'); _qs1.value = '__NO_BRAND__'; _qs1.textContent = '无品牌'; quickSel.appendChild(_qs1);
    var _qs2 = document.createElement('option'); _qs2.value = '__NEW_BRAND__'; _qs2.textContent = '+ 新品牌'; quickSel.appendChild(_qs2);
    quickSel.onchange = function() {
      if (this.value === '__NEW_BRAND__') { this.value = ''; if (typeof openAddBrandModal === 'function') openAddBrandModal(code, 'single'); return; }
      if (window.setItemBrand) window.setItemBrand(code, this.value);
    };
    actRow.appendChild(quickSel);
    var skipBtn = document.createElement('button'); skipBtn.className = 'btn-agent secondary'; skipBtn.textContent = '跳过';
    skipBtn.onclick = function() { if (window.skipItem) window.skipItem(code); };
    actRow.appendChild(skipBtn);
    li.appendChild(actRow);

    return li;
  }

  function _buildItemStatus(rule) {
    var span = document.createElement('span');
    if (rule.no_brand) { span.className = 'badge-flat grn'; span.textContent = '✓ 已标记: 无品牌'; }
    else if (rule.skipped) { span.className = 'badge-flat muted'; span.textContent = '⏭ 已跳过'; }
    else if (rule.brand) { span.className = 'badge-flat grn'; span.textContent = '✓ 已设置: ' + rule.brand; }
    return span;
  }

  function _appendSuggestion(parent, itemType, item, rule) {
    var div = document.createElement('div');
    div.style.fontSize = '12px';
    if (itemType === 'missing') {
      if (rule && rule.brand) { div.style.color = 'var(--green)'; div.textContent = '已设置品牌: ' + rule.brand; }
      else if (rule && rule.no_brand) { div.style.color = 'var(--green)'; div.textContent = '已标记为无品牌'; }
      else if (item.suggested_brand) { div.style.color = 'var(--orange)'; div.textContent = '建议品牌: ' + item.suggested_brand; }
      else return;
    } else if (itemType === 'mismatch') {
      if (rule && rule.brand) { div.style.color = 'var(--green)'; div.textContent = '当前品牌: ' + (item.brand||'') + ' → 已修正为: ' + rule.brand; }
      else if (rule && rule.no_brand) { div.style.color = 'var(--green)'; div.textContent = '当前品牌: ' + (item.brand||'') + ' → 已标记为无品牌'; }
      else { div.style.color = 'var(--red)'; div.textContent = '当前品牌: ' + (item.brand||'') + ' → 建议: ' + (item.suggested_brand||'无'); }
    } else if (itemType === 'unbranded') {
      div.style.color = 'var(--green)'; div.textContent = '天然无品牌商品';
    } else return;
    parent.appendChild(div);
  }

  function _appendFactors(parent, item) {
    var factors = item.factors;
    if (!factors || typeof factors !== 'object') return;
    var parts = [];
    if (factors.source) parts.push('来源="' + factors.source + '"');
    if (factors.matched_text) parts.push('匹配="' + factors.matched_text + '"');
    if (factors.history_correction) parts.push('历史修正: ' + factors.history_correction);
    if (!parts.length) return;
    var div = document.createElement('div');
    div.style.cssText = 'font-size:10px;color:var(--accent);margin-top:2px;';
    div.textContent = parts.join(' | ');
    parent.appendChild(div);
  }

  /* ── Open product list ── */
  window._emOpenProductList = function(type, clusterId) {
    var clusters = (window.diagnosisData && window.diagnosisData.brand_clusters) || [];
    var group = null;
    clusters.forEach(function(c) { if (c.type === type && c.cluster_id === clusterId) group = c; });
    if (!group) return;
    var items = group.items || [];
    var title = (group.suggested_standard || type) + ' · ' + items.length + ' 个商品';
    var batch = [];
    if (type === 'missing') batch.push(function() {
      var btn = document.createElement('button');
      btn.className = 'btn-agent primary';
      btn.textContent = '全部应用建议品牌';
      btn.onclick = function() { if (window.batchApplySuggestion) window.batchApplySuggestion(); };
      return btn;
    });
    batch.push(function() {
      var btn = document.createElement('button');
      btn.className = 'btn-agent secondary';
      btn.textContent = '全部标记无品牌';
      btn.onclick = function() { if (window.batchSetBrand) window.batchSetBrand(group.cluster_id, '__NO_BRAND__'); };
      return btn;
    });
    batch.push(function() {
      var btn = document.createElement('button');
      btn.className = 'btn-agent secondary';
      btn.textContent = '全部跳过';
      btn.onclick = function() { if (window.skipGroup) window.skipGroup(group.cluster_id); };
      return btn;
    });
    _renderBrandProductList(items, type, title, 'brand-dd-item-', batch);
  };

  window._emOpenGlobalBrandPanel = function(brandName) {
    if (typeof window.buildGlobalBrandIndex !== 'function') return;
    var index = window.buildGlobalBrandIndex();
    var info = index[brandName];
    if (!info) return;
    var items = info.items || [];
    var title = brandName + ' · ' + items.length + ' 个商品';
    _renderBrandProductList(items, null, title, 'brand-dd-global-', []);
  };

  /* ── Category refresh helpers (keep existing — they reference shared sidePanel) ── */
  // _emRefreshCategoryPanel and _emOpenCategoryProductList are large and mostly
  // legacy category-review code. They use innerHTML heavily. Left as-is for now
  // since they're not brand-editor code but category-side shared helpers.
  // TODO: migrate these when category review gets its DOM API pass.

  /* ── Watch for diagnosis data ── */
  var _nbLen = 0, _brandsDone = false, _watching = false;
  function startWatch(data) {
    if (_watching) return;
    _watching = true; _nbLen = (window.newBrands || []).length; _brandsDone = false;
    var max = 40, count = 0;
    var iv = setInterval(function() {
      count++;
      var clusters = (window.diagnosisData && window.diagnosisData.brand_clusters);
      if (clusters && clusters.length && !_brandsDone) {
        _brandsDone = true;
        renderBrandTabs(clusters);
      }
      var nb = window.newBrands || [];
      if (nb.length !== _nbLen) { _nbLen = nb.length; renderNewBrands(); }
      if ((_brandsDone && (_nbLen > 0 || count > 15)) || count >= max) { clearInterval(iv); _watching = false; }
    }, 300);
  }

  if (typeof window.showDiagnosis === 'function') {
    var _origSD = window.showDiagnosis;
    window.showDiagnosis = function(data) { var r = _origSD(data); startWatch(data); return r; };
  }

  /* ── Batch save ── */
  window.batchApplySuggestion = async function() {
    var panel = window.currentPanelData; if (!panel) return;
    var rules = panel.items.filter(function(item) {
      return !(window.brandRules || {})[String(item.code).trim()];
    }).map(function(item) {
      return { code: String(item.code).trim(), type: 'set_brand', brand: item.suggested_brand || item.brand };
    });
    await _doBatchSave(rules);
  };
  window.batchSetBrand = async function(clusterId, value) {
    var panel = window.currentPanelData; if (!panel) return;
    var type = value === '__NO_BRAND__' ? 'no_brand' : 'set_brand';
    var brand = type === 'no_brand' ? null : value;
    var rules = panel.items.map(function(item) { return { code: String(item.code).trim(), type: type, brand: brand }; });
    await _doBatchSave(rules);
  };
  window.skipGroup = async function(clusterId) {
    var panel = window.currentPanelData; if (!panel) return;
    var br = window.brandRules || {};
    var rules = panel.items.filter(function(item) {
      return !br[String(item.code).trim()];  // 只跳过未处理的
    }).map(function(item) { return { code: String(item.code).trim(), type: 'skip' }; });
    if (!rules.length) { alert('所有商品已处理，无需跳过'); return; }
    await _doBatchSave(rules);
  };
  window.setItemBrand = async function(code, value) {
    if (!value) return;
    var type = value === '__NO_BRAND__' ? 'no_brand' : 'set_brand';
    var brand = type === 'no_brand' ? null : value;
    await _doBatchSave([{ code: String(code).trim(), type: type, brand: brand }]);
  };
  window.skipItem = async function(code) {
    await _doBatchSave([{ code: String(code).trim(), type: 'skip' }]);
  };
  async function _doBatchSave(rules) {
    if (!rules.length) return;
    try {
      var res = await fetch('/api/brand_rules/batch_save', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: window.sessionId || (typeof sessionId !== 'undefined' ? sessionId : ''), rules: rules })
      });
      var data = await res.json();
      if (data.success) {
        var br = window.brandRules; if (!br) { br = {}; window.brandRules = br; }
        rules.forEach(function(r) {
          if (r.type === 'set_brand') br[r.code] = { brand: r.brand, no_brand: false, skipped: false };
          else if (r.type === 'no_brand') br[r.code] = { brand: null, no_brand: true, skipped: false };
          else if (r.type === 'skip') br[r.code] = { brand: null, no_brand: false, skipped: true };
        });
      }
    } catch(e) { console.error('_doBatchSave error:', e); }
    if (typeof renderBrandTabs === 'function' && window.diagnosisData) renderBrandTabs(window.diagnosisData.brand_clusters || []);
  }

  /* ── Global brand search ── */
  window._toggleGlobalBrandList = function() {
    var panel = document.getElementById('globalBrandListPanel');
    if (!panel) return;
    var open = panel.style.display !== 'none';
    panel.style.display = open ? 'none' : 'block';
    if (!open) window._electronFilterGlobalBrands('');
  };

  window._electronFilterGlobalBrands = function(text) {
    var panel = document.getElementById('globalBrandListPanel');
    if (!panel) return;
    if (typeof window.buildGlobalBrandIndex !== 'function') return;
    var index = window.buildGlobalBrandIndex();
    var brands = Object.keys(index).sort();
    var lower = (text || '').toLowerCase();
    if (lower) brands = brands.filter(function(b) { return b.toLowerCase().indexOf(lower) >= 0; });
    panel.textContent = '';
    if (!brands.length) {
      var empty = document.createElement('div');
      empty.style.cssText = 'padding:8px;font-size:11px;color:var(--text-muted);text-align:center;';
      empty.textContent = '无匹配品牌';
      panel.appendChild(empty);
      return;
    }
    var rules = window.brandRules || {};
    brands.forEach(function(b) {
      var info = index[b];
      var total = info.count;
      var processed = info.items.filter(function(i) { return rules[String(i.code).trim()]; }).length;
      var pct = total ? Math.round(processed / total * 100) : 0;

      var row = document.createElement('div');
      row.style.cssText = 'display:flex;align-items:center;justify-content:space-between;padding:6px 8px;cursor:pointer;border-radius:var(--radius-sm);font-size:12px;';
      row.onmouseover = function() { this.style.background = 'var(--surface-hover)'; };
      row.onmouseout = function() { this.style.background = ''; };
      row.onclick = function() { window._emOpenGlobalBrandPanel(b); };

      var nameEl = document.createElement('span');
      nameEl.style.cssText = 'color:var(--text-main);font-weight:500;';
      nameEl.textContent = b;
      row.appendChild(nameEl);

      var cnt = document.createElement('span');
      cnt.style.cssText = 'font-size:11px;color:' + (pct===100?'var(--green)':pct>0?'var(--orange)':'var(--text-muted)') + ';';
      cnt.textContent = processed + '/' + total;
      row.appendChild(cnt);

      panel.appendChild(row);
    });
  };

  setTimeout(function(){
    var checks = ['_emOpenProductList','_emOpenCategoryProductList','_emRefreshCategoryPanel','_toggleGlobalBrandList','_electronFilterGlobalBrands','_emOpenGlobalBrandPanel','updateNewBrandsDisplay','batchApplySuggestion','batchSetBrand','skipGroup','setItemBrand','skipItem'];
    var missing = checks.filter(function(k){ return typeof window[k] !== 'function'; });
    if (missing.length) console.error('brand_editor_electron: MISSING exports:', missing.join(', '));
    else console.log('brand_editor_electron: all ' + checks.length + ' exports OK');
  }, 100);

  window.filterBrandGroups = function(type, text) {
    var map = { missing: 'emMissingGroups', mismatch: 'emMismatchGroups', valid: 'emValidGroups', unbranded: 'emUnbrandedGroups' };
    var container = document.getElementById(map[type]);
    if (!container) return;
    var q = (text || '').toLowerCase();
    container.querySelectorAll('.brand-group-item').forEach(function(card) {
      var title = card.querySelector('.g-title');
      var meta = card.querySelector('.g-meta');
      var txt = (title ? title.textContent : '') + ' ' + (meta ? meta.textContent : '');
      card.style.display = !q || txt.toLowerCase().indexOf(q) !== -1 ? '' : 'none';
    });
  };
})();
