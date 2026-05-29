// ═══ Electron: Review Tab (DOM API) ═══
(function(){
  if (!window._electronMode) return;

  var _R = {
    data: [], filtered: [],
    filterStatus: 'all', filterSelfOp: '', filterImport: '', searchText: '',
    page: 0, pageSize: 30,
    selectedCode: null, pollTimer: null
  };

  /* ── Main entry ── */
  window.renderElectronReview = function() {
    var rc = document.getElementById('reviewContainer');
    if (!rc) return;
    rc.textContent = '';
    _showLoading(rc, '正在加载复核数据...');
    _R.page = 0; _R.filterStatus = 'all'; _R.filterSelfOp = ''; _R.filterImport = ''; _R.searchText = '';
    _fetchReviewData();
    _startReviewPolling();
  };

  function _showLoading(parent, msg) {
    parent.textContent = '';
    var d = document.createElement('div');
    d.style.cssText = 'text-align:center;color:var(--text-muted);padding:40px;';
    d.textContent = msg;
    parent.appendChild(d);
  }

  function _showEmpty(parent, msg) {
    _showLoading(parent, msg);
  }

  /* ── Data ── */
  function _fetchReviewData() {
    var sid = typeof sessionId !== 'undefined' ? sessionId : '';
    if (!sid) {
      _showEmpty(document.getElementById('reviewContainer'), '请先上传文件并完成 AI 处理');
      return;
    }
    fetch('/api/review/data?sid=' + encodeURIComponent(sid))
      .then(function(r) { return r.json(); })
      .then(function(d) { _R.data = d.data || []; _applyFilters(); })
      .catch(function(e) {
        var rc = document.getElementById('reviewContainer');
        if (rc) { rc.textContent = ''; rc.appendChild(_errorMsg('加载失败: ' + e.message)); }
      });
  }

  function _errorMsg(msg) {
    var d = document.createElement('div');
    d.style.cssText = 'color:var(--red);padding:20px;';
    d.textContent = msg;
    return d;
  }

  function _startReviewPolling() {
    if (_R.pollTimer) clearInterval(_R.pollTimer);
    _R.pollTimer = setInterval(function() {
      var sid = typeof sessionId !== 'undefined' ? sessionId : '';
      if (!sid) return;
      fetch('/api/status?sid=' + encodeURIComponent(sid))
        .then(function(r) { return r.json(); })
        .then(function(s) {
          if (s.status === 'processing') _fetchReviewData();
          else if (s.status === 'completed' || s.status === 'cancelled' || s.status === 'error') {
            _fetchReviewData();
            if (_R.pollTimer) { clearInterval(_R.pollTimer); _R.pollTimer = null; }
          }
        }).catch(function() {});
    }, 3000);
  }

  /* ── Filters ── */
  function _applyFilters() {
    var data = _R.data || [];
    var filtered = data;

    if (_R.filterStatus !== 'all') {
      var statusMap = { 'pending': '待复核', 'confirmed': '已确认', 'modified': '已修改' };
      var target = statusMap[_R.filterStatus] || _R.filterStatus;
      filtered = filtered.filter(function(item) {
        var rs = item.review_status || '';
        if (!rs && target === '待复核') return true;
        return rs === target;
      });
    }
    if (_R.filterSelfOp)
      filtered = filtered.filter(function(item) { return (item.self_operated_tag || '') === _R.filterSelfOp; });
    if (_R.filterImport)
      filtered = filtered.filter(function(item) { return (item.import_tag || '') === _R.filterImport; });
    if (_R.searchText) {
      var lower = _R.searchText.toLowerCase();
      filtered = filtered.filter(function(item) {
        return (item.name || '').toLowerCase().indexOf(lower) !== -1 ||
               (item.code || '').toLowerCase().indexOf(lower) !== -1;
      });
    }
    _R.filtered = filtered;
    _R.page = 0;
    _renderReview();
  }

  /* ── Render ── */
  function _renderReview() {
    var rc = document.getElementById('reviewContainer');
    if (!rc) return;
    rc.textContent = '';

    var total = _R.data.length;
    var filtered = _R.filtered;
    var confirmed = _R.data.filter(function(i) { return i.review_status === '已确认'; }).length;
    var modified = _R.data.filter(function(i) { return i.review_status === '已修改'; }).length;
    var pending = total - confirmed - modified;
    var totalPages = Math.ceil(filtered.length / _R.pageSize);
    var start = _R.page * _R.pageSize;
    var pageItems = filtered.slice(start, start + _R.pageSize);

    // Tabs
    rc.appendChild(_buildTabs(total, pending, confirmed, modified));

    // Filter bar
    rc.appendChild(_buildFilterBar());

    // List
    rc.appendChild(_buildItemList(pageItems));

    // Pagination
    if (totalPages > 1) rc.appendChild(_buildPagination(totalPages, filtered.length));
  }

  function _buildTabs(total, pending, confirmed, modified) {
    var wrap = document.createElement('div');
    wrap.className = 'pane-tabs-header';

    var seg = document.createElement('div');
    seg.className = 'pane-segmented-control';
    seg.id = 'reviewStatusSegments';

    var statuses = [
      { value: 'all', label: '全部', count: total },
      { value: 'pending', label: '待复核', count: pending, color: 'var(--orange)' },
      { value: 'confirmed', label: '已确认', count: confirmed, color: 'var(--green)' },
      { value: 'modified', label: '已修改', count: modified, color: 'var(--accent)' }
    ];
    statuses.forEach(function(s) {
      var active = _R.filterStatus === s.value;
      var item = document.createElement('div');
      item.className = 'pane-segment-item' + (active ? ' active' : '');
      item.dataset.status = s.value;
      item.textContent = s.label;

      var cnt = document.createElement('span');
      cnt.className = 'tab-count';
      cnt.style.color = s.color || 'var(--text-muted)';
      cnt.textContent = s.count;
      item.appendChild(cnt);

      item.onclick = function() {
        _R.filterStatus = this.dataset.status;
        _applyFilters();
      };
      seg.appendChild(item);
    });

    wrap.appendChild(seg);
    return wrap;
  }

  function _buildFilterBar() {
    var bar = document.createElement('div');
    bar.className = 'stat-mini-bar';

    var selfOp = document.createElement('select');
    selfOp.id = 'reviewSelfOpFilter';
    Object.assign(selfOp.style, { padding:'5px 8px', border:'1px solid var(--border)', borderRadius:'var(--radius-sm)',
      background:'var(--surface)', color:'var(--text-main)', fontSize:'11px' });
    selfOp.textContent = '';
    var _so0 = document.createElement('option'); _so0.value = ''; _so0.textContent = '自营: 全部'; selfOp.appendChild(_so0);
    var _so1 = document.createElement('option'); _so1.value = '自营'; _so1.textContent = '自营'; selfOp.appendChild(_so1);
    selfOp.value = _R.filterSelfOp;
    selfOp.onchange = function() { _R.filterSelfOp = this.value; _applyFilters(); };
    bar.appendChild(selfOp);

    var imp = document.createElement('select');
    imp.id = 'reviewImportFilter';
    Object.assign(imp.style, { padding:'5px 8px', border:'1px solid var(--border)', borderRadius:'var(--radius-sm)',
      background:'var(--surface)', color:'var(--text-main)', fontSize:'11px' });
    imp.textContent = '';
    var _io0 = document.createElement('option'); _io0.value = ''; _io0.textContent = '进口/国产: 全部'; imp.appendChild(_io0);
    var _io1 = document.createElement('option'); _io1.value = '进口'; _io1.textContent = '进口'; imp.appendChild(_io1);
    var _io2 = document.createElement('option'); _io2.value = '国产'; _io2.textContent = '国产'; imp.appendChild(_io2);
    imp.value = _R.filterImport;
    imp.onchange = function() { _R.filterImport = this.value; _applyFilters(); };
    bar.appendChild(imp);

    var search = document.createElement('input');
    search.id = 'reviewSearchInput';
    search.className = 'filter-input';
    search.placeholder = '搜索商品名或编码...';
    search.value = _R.searchText;
    search.oninput = function() { _R.searchText = this.value; _applyFilters(); };
    bar.appendChild(search);

    var exportFilter = document.createElement('button');
    exportFilter.className = 'btn-agent secondary';
    exportFilter.style.fontSize = '11px';
    exportFilter.textContent = '导出筛选';
    exportFilter.onclick = window._reviewExportCustom;
    bar.appendChild(exportFilter);

    var exportAll = document.createElement('button');
    exportAll.className = 'btn-agent primary';
    exportAll.style.fontSize = '11px';
    exportAll.textContent = '导出全部';
    exportAll.onclick = window._reviewExportAll;
    bar.appendChild(exportAll);

    return bar;
  }

  function _buildItemList(pageItems) {
    var list = document.createElement('div');
    list.className = 'list-content';
    if (!pageItems.length) {
      var empty = document.createElement('div');
      empty.style.cssText = 'text-align:center;color:var(--text-muted);padding:40px;';
      empty.textContent = '没有符合条件的数据';
      list.appendChild(empty);
    } else {
      for (var i = 0; i < pageItems.length; i++) {
        list.appendChild(_buildItemCard(pageItems[i]));
      }
    }
    return list;
  }

  function _buildItemCard(item) {
    var code = String(item.code || '').trim();
    var name = item.name || '';
    var rs = item.review_status || '';
    var isSelected = _R.selectedCode === code;

    var card = document.createElement('div');
    card.style.cssText = 'padding:10px 14px;border:1px solid ' + (isSelected ? 'var(--accent)' : 'var(--border)') +
      ';border-radius:var(--radius-md);margin-bottom:6px;cursor:pointer;background:' + (isSelected ? 'var(--bg-accent)' : 'var(--panel)') + ';';
    card.onclick = (function(c) { return function() { window._reviewSelectItem(c); }; })(code);
    card.onmouseover = function() { if (!this._sel) this.style.borderColor = 'var(--accent)'; };
    card.onmouseout = function() { if (!this._sel) this.style.borderColor = 'var(--border)'; };

    var row = document.createElement('div');
    row.style.cssText = 'display:flex;justify-content:space-between;align-items:flex-start;';

    var left = document.createElement('div');
    left.style.cssText = 'flex:1;min-width:0;';

    // Status + name
    var topRow = document.createElement('div');
    topRow.style.cssText = 'display:flex;align-items:center;gap:8px;margin-bottom:4px;';
    topRow.appendChild(_statusBadge(rs));

    var nameEl = document.createElement('span');
    nameEl.style.cssText = 'font-size:13px;font-weight:500;color:var(--text-main);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;';
    nameEl.textContent = name;
    topRow.appendChild(nameEl);
    left.appendChild(topRow);

    // Code
    var codeEl = document.createElement('div');
    codeEl.style.cssText = 'font-size:10px;color:var(--text-muted);font-family:var(--font-mono);margin-bottom:4px;';
    codeEl.textContent = code;
    left.appendChild(codeEl);

    // Brand
    var origBrand = item.original_brand || '';
    var aiBrand = item.brand_ai || '';
    var brandConf = item.brand_confidence || 0;
    if (aiBrand || origBrand) {
      left.appendChild(_buildBrandRow(origBrand, aiBrand, brandConf));
    }

    // Category
    var origCat = item.original_category || '';
    var aiCat = item.category_ai || '';
    if (aiCat || origCat) {
      var catDiv = document.createElement('div');
      catDiv.style.cssText = 'font-size:11px;margin-bottom:2px;';
      if (aiCat) {
        var catSpan = document.createElement('span');
        catSpan.style.color = 'var(--accent)';
        catSpan.textContent = aiCat;
        catDiv.appendChild(catSpan);
      } else if (origCat) {
        var catSpan2 = document.createElement('span');
        catSpan2.style.color = 'var(--text-sub)';
        catSpan2.textContent = origCat;
        catDiv.appendChild(catSpan2);
      }
      left.appendChild(catDiv);
    }

    // Tags
    var tagsDiv = _buildTagsRow(item);
    if (tagsDiv) left.appendChild(tagsDiv);

    row.appendChild(left);

    // Buttons
    var btns = document.createElement('div');
    btns.style.cssText = 'flex-shrink:0;margin-left:12px;display:flex;flex-direction:column;align-items:flex-end;gap:4px;';

    var confirmBtn = document.createElement('button');
    confirmBtn.className = 'btn-agent primary';
    confirmBtn.textContent = '确认';
    confirmBtn.onclick = (function(c) { return function(e) { e.stopPropagation(); window._reviewConfirmItem(c); }; })(code);
    btns.appendChild(confirmBtn);

    var modBtn = document.createElement('button');
    modBtn.className = 'btn-agent secondary';
    modBtn.textContent = '修改';
    modBtn.onclick = (function(c) { return function(e) { e.stopPropagation(); window._reviewModifyItem(c); }; })(code);
    btns.appendChild(modBtn);

    row.appendChild(btns);
    card.appendChild(row);
    return card;
  }

  function _statusBadge(rs) {
    var span = document.createElement('span');
    if (rs === '已确认') { span.className = 'badge-flat grn'; span.textContent = '已确认'; }
    else if (rs === '已修改') { span.className = 'badge-flat acc'; span.textContent = '已修改'; }
    else { span.className = 'badge-flat org'; span.textContent = '待复核'; }
    return span;
  }

  function _buildBrandRow(origBrand, aiBrand, brandConf) {
    var div = document.createElement('div');
    div.style.cssText = 'font-size:11px;margin-bottom:2px;';
    if (aiBrand && aiBrand !== origBrand) {
      var oldS = document.createElement('span');
      oldS.style.cssText = 'color:var(--text-muted);text-decoration:line-through;';
      oldS.textContent = origBrand;
      div.appendChild(oldS);

      var arrow = document.createTextNode(' → ');
      div.appendChild(arrow);

      var newS = document.createElement('span');
      newS.style.cssText = 'color:var(--accent);font-weight:500;';
      newS.textContent = aiBrand;
      div.appendChild(newS);

      if (brandConf) {
        var conf = document.createElement('span');
        conf.style.cssText = 'font-size:10px;color:var(--text-muted);';
        conf.textContent = ' ' + Math.round(brandConf * 100) + '%';
        div.appendChild(conf);
      }
    } else if (aiBrand) {
      var s = document.createElement('span');
      s.style.color = 'var(--text-main)';
      s.textContent = aiBrand;
      div.appendChild(s);
    } else if (origBrand) {
      var s2 = document.createElement('span');
      s2.style.color = 'var(--text-main)';
      s2.textContent = origBrand;
      div.appendChild(s2);
    }
    return div;
  }

  function _buildTagsRow(item) {
    var tags = [
      { v: item.self_operated_tag, label: '自营', cls: 'acc' },
      { v: item.import_tag, label: item.import_tag || '', cls: item.import_tag === '进口' ? 'red' : 'grn' },
      { v: item.promo_tag, label: '促销', cls: 'org' },
      { v: item.recommend_tag, label: '推荐', cls: 'org' }
    ];
    var div = document.createElement('div');
    div.style.cssText = 'display:flex;gap:4px;flex-wrap:wrap;margin-top:4px;';
    var has = false;
    tags.forEach(function(t) {
      if (t.v) {
        var span = document.createElement('span');
        span.className = 'badge-flat ' + t.cls;
        span.textContent = t.label;
        div.appendChild(span);
        has = true;
      }
    });
    return has ? div : null;
  }

  function _buildPagination(totalPages, filteredLen) {
    var wrap = document.createElement('div');
    wrap.style.cssText = 'display:flex;align-items:center;justify-content:center;gap:8px;padding:12px 0;';

    var prev = document.createElement('button');
    prev.className = 'btn-agent secondary';
    prev.textContent = '上一页';
    if (_R.page === 0) prev.disabled = true;
    prev.onclick = function() { window._reviewChangePage(_R.page - 1); };
    wrap.appendChild(prev);

    var info = document.createElement('span');
    info.style.cssText = 'font-size:11px;color:var(--text-muted);';
    info.textContent = (_R.page + 1) + ' / ' + totalPages + ' (' + filteredLen + '条)';
    wrap.appendChild(info);

    var next = document.createElement('button');
    next.className = 'btn-agent secondary';
    next.textContent = '下一页';
    if (_R.page >= totalPages - 1) next.disabled = true;
    next.onclick = function() { window._reviewChangePage(_R.page + 1); };
    wrap.appendChild(next);

    return wrap;
  }

  /* ── Detail panel ── */
  var _rvPanelSeq = 0;
  window._rvActivePanelId = null;

  window._reviewSelectItem = function(code) {
    _R.selectedCode = code;
    _renderReview();

    var item;
    for (var i = 0; i < _R.filtered.length; i++) {
      if (String(_R.filtered[i].code).trim() === code) { item = _R.filtered[i]; break; }
    }
    if (!item) return;

    var panelId = '_rvDetail-' + (++_rvPanelSeq);
    window._rvActivePanelId = panelId;

    var panelEl = document.createElement('div');
    panelEl.id = panelId;
    panelEl.style.cssText = 'display:flex;flex-direction:column;';

    var content = document.createElement('div');
    content.style.cssText = 'padding:14px;display:flex;flex-direction:column;gap:6px;max-height:75vh;overflow-y:auto;';
    _buildDetailContent(content, item, code, panelId);
    panelEl.appendChild(content);

    var storage = document.getElementById('_panelStorage');
    if (!storage) { storage = document.createElement('div'); storage.id = '_panelStorage'; storage.style.display = 'none'; document.body.appendChild(storage); }
    storage.appendChild(panelEl);

    if (typeof _movePanelToCard === 'function')
      _movePanelToCard(panelId, panelId, item.name || code);
  };

  function _buildDetailContent(content, item, code, panelId) {
    // Header
    var header = document.createElement('div');
    header.style.cssText = 'display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:6px;';
    var hLeft = document.createElement('div');
    hLeft.style.cssText = 'flex:1;min-width:0;';
    var hName = document.createElement('div');
    hName.style.cssText = 'font-size:14px;font-weight:600;color:var(--text-main);margin-bottom:2px;';
    hName.textContent = item.name || '';
    hLeft.appendChild(hName);
    var hCode = document.createElement('div');
    hCode.style.cssText = 'font-size:10px;color:var(--text-muted);font-family:var(--font-mono);';
    hCode.textContent = code;
    hLeft.appendChild(hCode);
    header.appendChild(hLeft);
    var hBadge = document.createElement('div');
    hBadge.style.cssText = 'flex-shrink:0;margin-left:12px;';
    hBadge.appendChild(_statusBadge(item.review_status || ''));
    header.appendChild(hBadge);
    content.appendChild(header);

    // Image
    if (item.org_image_url) {
      var imgWrap = document.createElement('div');
      imgWrap.style.cssText = 'text-align:center;padding:6px 0;';
      var img = document.createElement('img');
      img.src = item.org_image_url;
      img.alt = '商品图';
      img.style.cssText = 'max-width:100%;max-height:160px;object-fit:contain;border-radius:6px;cursor:pointer;';
      img.onerror = function() { this.style.display = 'none'; };
      img.onclick = function() { window.open(item.org_image_url, '_blank'); };
      imgWrap.appendChild(img);
      content.appendChild(imgWrap);
    }

    // Basic info section
    content.appendChild(_buildInfoSection(item));

    // Tags sections
    _buildTagSections(content, item);

    // Action buttons
    var actions = document.createElement('div');
    actions.style.cssText = 'display:flex;gap:8px;padding-top:8px;border-top:1px solid var(--border-light);justify-content:flex-end;';
    var confBtn = document.createElement('button');
    confBtn.className = 'btn-agent primary';
    confBtn.textContent = '确认';
    confBtn.onclick = function() { window._reviewConfirmFromPanel(code, panelId); };
    actions.appendChild(confBtn);
    var modBtn = document.createElement('button');
    modBtn.className = 'btn-agent secondary';
    modBtn.textContent = '修改';
    modBtn.onclick = function() { window._reviewModifyFromPanel(code, panelId); };
    actions.appendChild(modBtn);
    content.appendChild(actions);
  }

  function _infoRow(label, value, color) {
    if (!value && value !== 0) return null;
    var row = document.createElement('div');
    row.style.cssText = 'display:flex;justify-content:space-between;padding:3px 0;font-size:11px;';
    var lbl = document.createElement('span');
    lbl.style.cssText = 'color:var(--text-muted);flex-shrink:0;';
    lbl.textContent = label;
    row.appendChild(lbl);
    var val = document.createElement('span');
    val.style.cssText = 'color:' + (color || 'var(--text-main)') + ';text-align:right;margin-left:12px;';
    val.textContent = String(value);
    row.appendChild(val);
    return row;
  }

  function _brandSrcLabel(s) {
    var m = {'ai_ok':'AI分析','from_library':'品牌库命中','no_brand':'无品牌','error':'AI出错','skipped':'已跳过','local':'本地提取'};
    return m[s] || s || '';
  }
  function _catSrcLabel(s) {
    var m = {'ai_ok':'AI分析','ai_out_of_range':'超出范围','local_fallback':'本地推算','local':'本地推算','skipped':'已跳过','rule_fallback':'本地推算'};
    return m[s] || s || '';
  }

  function _buildInfoSection(item) {
    var sec = document.createElement('div');
    sec.style.cssText = 'border-top:1px solid var(--border-light);padding-top:6px;margin-bottom:4px;';

    var title = document.createElement('div');
    title.style.cssText = 'font-size:10px;color:var(--text-muted);font-weight:600;text-transform:uppercase;margin-bottom:4px;';
    title.textContent = '基本信息';
    sec.appendChild(title);

    function addRow(label, value, color) { var r = _infoRow(label, value, color); if (r) sec.appendChild(r); }

    addRow('原始品牌', item.original_brand, 'var(--text-sub)');
    var brandLabel = (item.brand_status === 'error' || item.brand_status === 'local') ? '系统建议品牌' : 'AI 品牌';
    addRow(brandLabel, item.brand_ai + (item.brand_type ? ' [' + item.brand_type + ']' : ''), 'var(--accent)');
    if ((item.brand_status === 'error' || item.brand_status === 'local') && item.brand_reason)
      addRow('品牌备注', item.brand_reason);
    if (item.brand_confidence) addRow('品牌置信度', Math.round(item.brand_confidence * 100) + '%');
    if (item.brand_status && item.brand_status !== 'error' && item.brand_status !== 'local')
      addRow('品牌来源', _brandSrcLabel(item.brand_status));
    if (item.brand_reason && item.brand_status !== 'error' && item.brand_status !== 'local')
      addRow('品牌理由', item.brand_reason);
    if (item.spec_original) addRow('原始规格', item.spec_original);
    if (item.spec_weight) addRow('计量规格', item.spec_weight, 'var(--accent)');
    if (item.spec_pack) addRow('包装规格', item.spec_pack, 'var(--accent)');
    if (item.spec_from_name && item.spec_from_name !== item.spec_weight) addRow('名称提取', item.spec_from_name, 'var(--accent)');
    addRow('原始分类', item.original_category, 'var(--text-sub)');
    addRow('AI 分类', item.category_ai, 'var(--accent)');
    if (item.category_confidence) addRow('分类置信度', Math.round(item.category_confidence * 100) + '%');
    if (item.category_status) addRow('分类来源', _catSrcLabel(item.category_status));
    if (item.category_method) addRow('分类方式', _catSrcLabel(item.category_method));
    if (item.category_reason) addRow('分类理由', item.category_reason);
    if (item.category_entity) addRow('品种词', item.category_entity, 'var(--accent)');
    if (item.category_modifiers) addRow('修饰词', item.category_modifiers);

    return sec;
  }

  function _buildTagSections(content, item) {
    function tagBadge(v, label, cls) {
      if (!v) return null;
      var span = document.createElement('span');
      span.className = 'badge-flat ' + cls;
      span.style.margin = '2px';
      span.textContent = label || v;
      return span;
    }

    function buildSection(titleText, tags) {
      var sec = document.createElement('div');
      sec.style.cssText = 'border-top:1px solid var(--border-light);padding-top:6px;';
      var t = document.createElement('div');
      t.style.cssText = 'font-size:10px;color:var(--text-muted);font-weight:600;text-transform:uppercase;margin-bottom:4px;';
      t.textContent = titleText;
      sec.appendChild(t);
      var wrap = document.createElement('div');
      wrap.style.cssText = 'display:flex;flex-wrap:wrap;gap:2px;';
      tags.forEach(function(tag) { if (tag) wrap.appendChild(tag); });
      if (wrap.children.length) sec.appendChild(wrap);
      return sec;
    }

    var computed = [
      tagBadge(item.promo_tag, '促销: ' + item.promo_tag, 'org'),
      tagBadge(item.recommend_tag, '推荐: ' + item.recommend_tag, 'org'),
      tagBadge(item.self_operated_tag, '自营', 'acc'),
      tagBadge(item.import_tag, item.import_tag, item.import_tag === '进口' ? 'red' : 'grn')
    ];
    var orig = [
      tagBadge(item.org_prom_spu_tag, '促销标签: ' + item.org_prom_spu_tag, 'muted'),
      tagBadge(item.org_new_spu_tag, '新品标签: ' + item.org_new_spu_tag, 'muted'),
      tagBadge(item.org_billboard_top, '榜单标签: ' + item.org_billboard_top, 'muted'),
      tagBadge(item.org_recommend_tag, '推荐标签: ' + item.org_recommend_tag, 'muted'),
      tagBadge(item.org_prom_price, '促销价: ' + item.org_prom_price, 'muted')
    ];

    var cs = buildSection('计算标签', computed);
    if (cs && cs.children.length > 1) content.appendChild(cs);
    var os = buildSection('原始标签', orig);
    if (os && os.children.length > 1) content.appendChild(os);
  }

  /* ── Review actions ── */
  window._reviewConfirmFromPanel = function(code, panelId) {
    _sendDecision(code, 'confirm');
    if (typeof _closePanelCard === 'function') _closePanelCard(panelId, panelId);
  };
  window._reviewConfirmItem = function(code) { _sendDecision(code, 'confirm'); };

  window._reviewModifyFromPanel = function(code, panelId) {
    var item;
    for (var i = 0; i < _R.data.length; i++) {
      if (String(_R.data[i].code).trim() === code) { item = _R.data[i]; break; }
    }
    if (!item) return;
    var panel = document.getElementById(panelId);
    if (!panel) return;

    panel.textContent = '';
    var wrap = document.createElement('div');
    wrap.style.padding = '14px';

    var nameEl = document.createElement('div');
    nameEl.style.cssText = 'font-size:12px;font-weight:500;color:var(--text-main);margin-bottom:8px;';
    nameEl.textContent = item.name || '';
    wrap.appendChild(nameEl);

    // Brand input
    var brandWrap = document.createElement('div');
    brandWrap.style.marginBottom = '8px';
    var bLabel = document.createElement('label');
    bLabel.style.cssText = 'font-size:11px;color:var(--text-muted);display:block;margin-bottom:4px;';
    bLabel.textContent = '品牌';
    brandWrap.appendChild(bLabel);
    var bInput = document.createElement('input');
    bInput.id = '_reviewEditBrand';
    bInput.value = item.brand_ai || item.original_brand || '';
    Object.assign(bInput.style, { width:'100%', padding:'6px 8px', border:'1px solid var(--border)', borderRadius:'var(--radius-sm)',
      background:'var(--surface)', color:'var(--text-main)', fontSize:'12px', boxSizing:'border-box' });
    brandWrap.appendChild(bInput);
    wrap.appendChild(brandWrap);

    // Category input
    var catWrap = document.createElement('div');
    catWrap.style.marginBottom = '8px';
    var cLabel = document.createElement('label');
    cLabel.style.cssText = 'font-size:11px;color:var(--text-muted);display:block;margin-bottom:4px;';
    cLabel.textContent = '分类路径';
    catWrap.appendChild(cLabel);
    var cInput = document.createElement('input');
    cInput.id = '_reviewEditCategory';
    cInput.value = item.category_ai || item.original_category || '';
    Object.assign(cInput.style, { width:'100%', padding:'6px 8px', border:'1px solid var(--border)', borderRadius:'var(--radius-sm)',
      background:'var(--surface)', color:'var(--text-main)', fontSize:'12px', boxSizing:'border-box' });
    catWrap.appendChild(cInput);
    wrap.appendChild(catWrap);

    // Buttons
    var btnRow = document.createElement('div');
    btnRow.style.cssText = 'display:flex;gap:8px;justify-content:flex-end;';
    var cancelBtn = document.createElement('button');
    cancelBtn.className = 'btn-agent secondary';
    cancelBtn.textContent = '取消';
    cancelBtn.onclick = function() { window._reviewCancelEdit(panelId, code); };
    btnRow.appendChild(cancelBtn);
    var saveBtn = document.createElement('button');
    saveBtn.className = 'btn-agent primary';
    saveBtn.textContent = '保存修改';
    saveBtn.onclick = function() { window._reviewSaveModify(code, panelId); };
    btnRow.appendChild(saveBtn);
    wrap.appendChild(btnRow);
    panel.appendChild(wrap);
  };

  window._reviewCancelEdit = function(panelId, code) {
    if (typeof _closePanelCard === 'function') _closePanelCard(panelId, panelId);
    window._reviewSelectItem(code);
  };
  window._reviewModifyItem = function(code) {
    window._reviewSelectItem(code);
    setTimeout(function() {
      if (window._rvActivePanelId) window._reviewModifyFromPanel(code, window._rvActivePanelId);
    }, 200);
  };
  window._reviewSaveModify = function(code, panelId) {
    var bInput = document.getElementById('_reviewEditBrand');
    var cInput = document.getElementById('_reviewEditCategory');
    var changes = {};
    if (bInput) changes.brand_ai = bInput.value;
    if (cInput) changes.category_ai = cInput.value;
    _sendDecision(code, 'modify', changes);
    if (typeof _closePanelCard === 'function' && panelId) _closePanelCard(panelId, panelId);
  };

  function _sendDecision(code, action, changes) {
    var sid = typeof sessionId !== 'undefined' ? sessionId : '';
    fetch('/api/review/decision', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sid, code: code, action: action, changes: changes || {} })
    }).then(function(r) { return r.json(); })
      .then(function(d) {
        if (!d.success) return;
        for (var i = 0; i < _R.data.length; i++) {
          if (String(_R.data[i].code).trim() === code) {
            _R.data[i].review_status = action === 'confirm' ? '已确认' : '已修改';
            if (changes) { for (var k in changes) _R.data[i][k] = changes[k]; }
            break;
          }
        }
        _applyFilters();
      }).catch(function(e) { console.error('Review decision failed:', e); });
  }

  /* ── Filter/pagination controls ── */
  window._reviewApplyFilter = function() { /* kept for compat, inline handlers replaced */ };
  window._reviewChangePage = function(page) { _R.page = Math.max(0, page); _renderReview(); };

  /* ── Export ── */
  window._reviewExportAll = function() {
    var sid = typeof sessionId !== 'undefined' ? sessionId : '';
    window.location.href = '/api/review/export?sid=' + encodeURIComponent(sid);
  };
  window._reviewExportCustom = function() {
    var sid = typeof sessionId !== 'undefined' ? sessionId : '';
    var params = new URLSearchParams({ sid: sid });
    if (_R.filterStatus !== 'all') params.set('status', _R.filterStatus);
    if (_R.filterSelfOp) params.set('self_operated', _R.filterSelfOp);
    if (_R.filterImport) params.set('import', _R.filterImport);
    window.location.href = '/api/review/export?' + params.toString();
  };

  setTimeout(function(){
    var checks = ['renderElectronReview','_reviewSelectItem','_reviewConfirmItem','_reviewModifyItem','_reviewSaveModify','_reviewApplyFilter','_reviewChangePage','_reviewExportAll','_reviewExportCustom'];
    var missing = checks.filter(function(k){ return typeof window[k] !== 'function'; });
    if (missing.length) console.error('review_electron: MISSING exports:', missing.join(', '));
    else console.log('review_electron: all ' + checks.length + ' exports OK');
  }, 100);
})();
