// ═══ Electron: Category Review Tab (native.css) ═══
// Renders the missing-category product list grouped by section.
(function(){
  if (!window._electronMode) return;

  var _catReviewTab = 'standard';
  var _catReviewPage = 0;
  var _catReviewGroups = {};
  var _catReviewPageSize = 10;

  // ── Tab switching ──
  function initCategoryTabs() {
    var tabs = document.querySelectorAll('#emCategoryTabs .pane-segment-item');
    tabs.forEach(function(tab) {
      tab.addEventListener('click', function() {
        tabs.forEach(function(t) { t.classList.remove('active'); });
        tab.classList.add('active');
        _catReviewTab = tab.getAttribute('data-tab');
        _catReviewPage = 0;
        renderCategoryReview();
      });
    });
  }

  function updateCatTabCounts(counts) {
    ['standard','conflict','marketing','missing'].forEach(function(t) {
      var el = document.getElementById('emCat' + t.charAt(0).toUpperCase() + t.slice(1) + 'Count');
      if (el) el.textContent = counts[t] || 0;
    });
  }

  // ── Main render ──
  window.renderCategoryReview = function() {
    var container = document.getElementById('emCategoryGroups');
    if (!container) return;
    var allCodes = (window.diagnosisData && window.diagnosisData.all_codes) || [];
    if (!allCodes.length) {
      container.textContent = '';
      var emptyMsg = document.createElement('div');
      emptyMsg.style.cssText = 'font-size:11px;color:var(--text-muted);padding:32px;text-align:center;';
      emptyMsg.textContent = '暂无分类数据，请先上传文件进行诊断';
      container.appendChild(emptyMsg);
      updateCatTabCounts({});
      return;
    }

    // Section counts
    var counts = {standard: 0, conflict: 0, marketing: 0, missing: 0};
    allCodes.forEach(function(item) { if (counts[item._section] !== undefined) counts[item._section]++; });
    updateCatTabCounts(counts);

    // Filter by active tab
    var sectionItems = allCodes.filter(function(item) { return item._section === _catReviewTab; });

    // Group by path
    var groups = {};
    sectionItems.forEach(function(item) {
      var key;
      if (_catReviewTab === 'marketing') {
        key = (item.marketing_paths && item.marketing_paths[0]) || '(无路径)';
      } else if (_catReviewTab === 'missing') {
        key = '__missing__';
      } else {
        key = (item.suggested_path && item.suggested_path[0]) || '(无路径)';
      }
      if (!groups[key]) groups[key] = { path: key, items: [], count: 0 };
      groups[key].items.push(item);
      groups[key].count++;
    });

    _catReviewGroups = groups;
    var groupList = Object.values(groups).sort(function(a, b) { return b.count - a.count; });

    // Pagination
    var totalPages = Math.ceil(groupList.length / _catReviewPageSize);
    var start = _catReviewPage * _catReviewPageSize;
    var pageGroups = groupList.slice(start, start + _catReviewPageSize);

    // Update stat bar
    var labelMap = {standard: '标准路径', conflict: '冲突待归集', marketing: '纯营销', missing: '分类缺失'};
    var labelEl = document.getElementById('emCatFilterLabel');
    if (labelEl) labelEl.textContent = labelMap[_catReviewTab] || _catReviewTab;

    var totalEl = document.getElementById('emCatTotalCount');
    if (totalEl) totalEl.textContent = sectionItems.length + '个商品code';

    var rules = window.categoryRules || {};
    var processed = sectionItems.filter(function(i) { return rules[String(i.code).trim()]; }).length;
    var progressEl = document.getElementById('emCatProgressFill');
    if (progressEl) progressEl.style.width = sectionItems.length ? (processed / sectionItems.length * 100) + '%' : '0%';

    if (!pageGroups.length) {
      container.textContent = '';
      var emptyData = document.createElement('div');
      emptyData.style.cssText = 'font-size:11px;color:var(--text-muted);padding:32px;text-align:center;';
      emptyData.textContent = '暂无数据';
      container.appendChild(emptyData);
      var pagEl = document.getElementById('emCategoryPagination');
      if (pagEl) pagEl.textContent = '';
      return;
    }

    // Color per section
    var sectionColor = {standard: 'var(--green)', conflict: 'var(--orange)', marketing: 'var(--red)', missing: 'var(--orange)'};
    var sc = sectionColor[_catReviewTab] || 'var(--text-muted)';
    var isMissing = _catReviewTab === 'missing';

    // ── 分组卡片：DOM API ──
    container.textContent = '';
    pageGroups.forEach(function(g) {
      var path = g.path, count = g.count, items = g.items || [];
      var proc = items.filter(function(i) { return rules[String(i.code).trim()]; }).length;
      var examples = items.slice(0, 3).map(function(i) { return esc(i.name || i.code); }).join(', ');
      var cardKey = _catReviewTab + '|' + g.path;

      var card = document.createElement('div');
      card.className = 'cat-group-card';
      card.dataset.catKey = cardKey;
      card.style.cssText = 'border:1px solid var(--border);border-radius:var(--radius-md);padding:10px 14px;margin-bottom:8px;cursor:pointer;background:var(--panel);';
      card.addEventListener('mouseover', function() { this.style.borderColor = 'var(--accent)'; });
      card.addEventListener('mouseout', function() { this.style.borderColor = 'var(--border)'; });

      var flexRow = document.createElement('div');
      flexRow.style.cssText = 'display:flex;justify-content:space-between;align-items:center;';

      // 左侧：路径 + 信息 + 示例
      var leftCol = document.createElement('div');
      leftCol.style.cssText = 'flex:1;min-width:0;';

      var titleDiv = document.createElement('div');
      titleDiv.style.cssText = 'font-size:13px;font-weight:500;color:var(--text-main);';
      titleDiv.textContent = isMissing ? '分类缺失商品' : path;
      leftCol.appendChild(titleDiv);

      var infoDiv = document.createElement('div');
      infoDiv.style.cssText = 'font-size:11px;color:var(--text-sub);margin-top:2px;';
      if (isMissing) {
        infoDiv.textContent = '无分类路径，需手动设置';
      } else {
        var infoBold = document.createElement('b');
        infoBold.style.color = sc;
        infoBold.textContent = path;
        infoDiv.textContent = '建议路径: ';
        infoDiv.appendChild(infoBold);
      }
      leftCol.appendChild(infoDiv);

      var exampleDiv = document.createElement('div');
      exampleDiv.style.cssText = 'font-size:10px;color:var(--text-muted);margin-top:2px;';
      exampleDiv.textContent = '示例: ' + examples;
      leftCol.appendChild(exampleDiv);

      flexRow.appendChild(leftCol);

      // 右侧：计数 + 已处理
      var rightCol = document.createElement('div');
      rightCol.style.cssText = 'text-align:right;flex-shrink:0;margin-left:12px;';

      var countDiv = document.createElement('div');
      countDiv.style.cssText = 'font-size:12px;font-weight:600;color:var(--text-main);';
      countDiv.textContent = count;
      rightCol.appendChild(countDiv);

      var procDiv = document.createElement('div');
      procDiv.style.cssText = 'font-size:10px;color:' + (proc === count && count > 0 ? 'var(--green)' : 'var(--text-muted)') + ';';
      procDiv.textContent = proc + ' 已处理';
      rightCol.appendChild(procDiv);

      flexRow.appendChild(rightCol);
      card.appendChild(flexRow);
      container.appendChild(card);
    });

    // Click handlers — 复用商品列表面板
    setTimeout(function() {
      var cards = container.querySelectorAll('.cat-group-card');
      for (var c = 0; c < cards.length; c++) {
        cards[c].addEventListener('click', function() {
          var key = this.dataset.catKey;
          var group = _catReviewGroups[key.split('|').slice(1).join('|')];
          if (group) {
            window._emOpenCategoryProductList(group.path, { items: group.items, count: group.count });
          }
        });
      }
    }, 50);

    // ── 分页：DOM API ──
    var pagContainer = document.getElementById('emCategoryPagination');
    if (pagContainer) {
      pagContainer.textContent = '';
      if (totalPages > 1) {
        var pagRow = document.createElement('div');
        pagRow.style.cssText = 'display:flex;align-items:center;justify-content:center;gap:8px;padding:12px 0;';

        var prevBtn = document.createElement('button');
        prevBtn.className = 'btn-agent secondary';
        prevBtn.textContent = '上一页';
        if (_catReviewPage === 0) prevBtn.disabled = true;
        else prevBtn.addEventListener('click', function() { _changeCatReviewPage(_catReviewPage - 1); });
        pagRow.appendChild(prevBtn);

        var pageInfo = document.createElement('span');
        pageInfo.style.cssText = 'font-size:11px;color:var(--text-muted);';
        pageInfo.textContent = (_catReviewPage + 1) + ' / ' + totalPages;
        pagRow.appendChild(pageInfo);

        var nextBtn = document.createElement('button');
        nextBtn.className = 'btn-agent secondary';
        nextBtn.textContent = '下一页';
        if (_catReviewPage >= totalPages - 1) nextBtn.disabled = true;
        else nextBtn.addEventListener('click', function() { _changeCatReviewPage(_catReviewPage + 1); });
        pagRow.appendChild(nextBtn);

        pagContainer.appendChild(pagRow);
      }
    }
  };

  window._changeCatReviewPage = function(page) {
    _catReviewPage = Math.max(0, page);
    renderCategoryReview();
  };

  window.filterCategoryReview = function(text) {
    var lower = (text || '').toLowerCase().trim();
    if (!lower) { renderCategoryReview(); return; }

    // 从全量分组数据中搜索，不受分页限制
    var matched = [];
    Object.keys(_catReviewGroups).forEach(function(key) {
      var group = _catReviewGroups[key];
      // 匹配分组路径或商品名称
      if (group.path.toLowerCase().indexOf(lower) !== -1) {
        matched.push(group);
        return;
      }
      for (var i = 0; i < group.items.length; i++) {
        var item = group.items[i];
        if ((item.name || '').toLowerCase().indexOf(lower) !== -1 ||
            (item.code || '').toLowerCase().indexOf(lower) !== -1) {
          matched.push(group);
          return;
        }
        // 也搜 all_paths
        var paths = item.all_paths || [];
        for (var j = 0; j < paths.length; j++) {
          if (paths[j].toLowerCase().indexOf(lower) !== -1) {
            matched.push(group);
            return;
          }
        }
      }
    });

    // 重新渲染匹配结果（不分页）
    var container = document.getElementById('emCategoryGroups');
    if (!container) return;
    container.textContent = '';

    if (!matched.length) {
      var emptyMsg = document.createElement('div');
      emptyMsg.style.cssText = 'font-size:11px;color:var(--text-muted);padding:32px;text-align:center;';
      emptyMsg.textContent = '无匹配分组';
      container.appendChild(emptyMsg);
      return;
    }

    var sc = _catReviewTab === 'marketing' ? 'var(--red)' : 'var(--green)';
    matched.sort(function(a, b) { return b.count - a.count; });
    matched.forEach(function(g) {
      var path = g.path, count = g.count, items = g.items || [];
      var proc = items.filter(function(i) { return (window.categoryRules || {})[String(i.code).trim()]; }).length;
      var examples = items.slice(0, 3).map(function(i) { return esc(i.name || i.code); }).join(', ');

      var card = document.createElement('div');
      card.className = 'cat-group-card';
      card.style.cssText = 'border:1px solid var(--border);border-radius:var(--radius-md);padding:10px 14px;margin-bottom:8px;cursor:pointer;background:var(--panel);';
      card.addEventListener('mouseover', function() { this.style.borderColor = 'var(--accent)'; });
      card.addEventListener('mouseout', function() { this.style.borderColor = 'var(--border)'; });

      var flexRow = document.createElement('div');
      flexRow.style.cssText = 'display:flex;justify-content:space-between;align-items:center;';

      var leftCol = document.createElement('div');
      leftCol.style.cssText = 'flex:1;min-width:0;';
      var titleDiv = document.createElement('div');
      titleDiv.style.cssText = 'font-size:13px;font-weight:500;color:var(--text-main);';
      titleDiv.textContent = _catReviewTab === 'missing' ? '分类缺失商品' : path;
      leftCol.appendChild(titleDiv);

      var infoDiv = document.createElement('div');
      infoDiv.style.cssText = 'font-size:11px;color:var(--text-sub);margin-top:2px;';
      if (_catReviewTab === 'missing') {
        infoDiv.textContent = '无分类路径，需手动设置';
      } else if (_catReviewTab === 'marketing') {
        infoDiv.textContent = '纯营销路径，建议待 AI 分析';
      } else {
        var infoBold = document.createElement('b');
        infoBold.style.color = sc;
        infoBold.textContent = path;
        infoDiv.textContent = '建议路径: ';
        infoDiv.appendChild(infoBold);
      }
      leftCol.appendChild(infoDiv);

      var exampleDiv = document.createElement('div');
      exampleDiv.style.cssText = 'font-size:10px;color:var(--text-muted);margin-top:2px;';
      exampleDiv.textContent = '示例: ' + examples;
      leftCol.appendChild(exampleDiv);
      flexRow.appendChild(leftCol);

      var rightCol = document.createElement('div');
      rightCol.style.cssText = 'text-align:right;flex-shrink:0;margin-left:12px;';
      var countDiv = document.createElement('div');
      countDiv.style.cssText = 'font-size:12px;font-weight:600;color:var(--text-main);';
      countDiv.textContent = count;
      rightCol.appendChild(countDiv);
      var procDiv = document.createElement('div');
      procDiv.style.cssText = 'font-size:10px;color:' + (proc === count && count > 0 ? 'var(--green)' : 'var(--text-muted)') + ';';
      procDiv.textContent = proc + ' 已处理';
      rightCol.appendChild(procDiv);
      flexRow.appendChild(rightCol);
      card.appendChild(flexRow);
      container.appendChild(card);

      // Click to open product list
      var key = _catReviewTab + '|' + g.path;
      card.addEventListener('click', function() {
        var group = _catReviewGroups[key.split('|').slice(1).join('|')];
        if (group && window._emOpenCategoryProductList) window._emOpenCategoryProductList(g.path, {items: group.items});
      });
    });
  };

  // ── Shared category product list panel (used by category tree & category review) ──
  window._emOpenCategoryProductList = function(path, info) {
    var items = (info && info.items) || [];
    if (!items.length) { alert('该路径下无商品'); return; }

    var panelId = 'cate-prod-' + Date.now();
    var rules = window.categoryRules || {};
    var PER_PAGE = 20;
    var currentPage = 0;

    function esc(s) { return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }

    var secLabels = {conflict:'冲突待归集', marketing:'纯营销', standard:'标准审计', missing:'分类缺失'};

    function renderPage(page) {
      currentPage = page;
      var listEl = document.getElementById('panelItemsList');
      var pgEl = document.getElementById('panelPagination');
      if (!listEl) return;
      listEl.textContent = '';

      var start = page * PER_PAGE;
      var end = Math.min(start + PER_PAGE, items.length);
      var pageItems = items.slice(start, end);
      var total = Math.ceil(items.length / PER_PAGE);

      pageItems.forEach(function(item) {
        var code = String(item.code || '').trim();
        var rule = rules[code];
        var done = !!rule;
        var section = item._section || '';

        var li = document.createElement('li');
        li.className = 'audit-card';

        // Section label
        if (section && secLabels[section]) {
          var sl = document.createElement('div');
          sl.className = 'card-section-label';
          sl.style.marginBottom = '4px';
          sl.textContent = secLabels[section];
          li.appendChild(sl);
        }

        // Product name
        var nameEl = document.createElement('span');
        nameEl.className = 'card-subject';
        nameEl.textContent = item.name || code || '';
        li.appendChild(nameEl);

        // 商品缩略图
        if (item.org_image_url) {
          var thumb = document.createElement('img');
          thumb.src = item.org_image_url;
          thumb.alt = item.name || '';
          thumb.style.cssText = 'width:60px;height:60px;object-fit:cover;border-radius:4px;border:1px solid var(--border);margin-top:6px;cursor:pointer;display:block;';
          thumb.addEventListener('error', function() { this.style.display = 'none'; });
          thumb.addEventListener('click', function(e) { e.stopPropagation(); _showImagePreview(item.org_image_url, item.name || ''); });
          li.appendChild(thumb);
        }

        // Spec grid: code + row
        var sg = document.createElement('div');
        sg.className = 'meta-spec-grid';
        var sl1 = document.createElement('div'); sl1.className = 'spec-line';
        var k1 = document.createElement('span'); k1.className = 'spec-k'; k1.textContent = 'Code:';
        var v1 = document.createElement('span'); v1.className = 'spec-v'; v1.textContent = code;
        sl1.appendChild(k1); sl1.appendChild(v1);
        if (item.row != null) {
          var k1b = document.createElement('span'); k1b.className = 'spec-k'; k1b.style.marginLeft = '12px'; k1b.textContent = 'Line:';
          var v1b = document.createElement('span'); v1b.className = 'spec-v'; v1b.textContent = '#' + item.row;
          sl1.appendChild(k1b); sl1.appendChild(v1b);
        }
        sg.appendChild(sl1);
        li.appendChild(sg);

        // Suggested path
        var sugPath = item.suggested_path && item.suggested_path[0];
        if (sugPath) {
          var inAll = (item.all_paths || []).indexOf(sugPath) !== -1;
          var sugGrid = document.createElement('div');
          sugGrid.className = 'meta-spec-grid';
          sugGrid.style.cssText = 'border-left:2px solid var(--green);background:rgba(16,185,129,0.02);';

          var sugLabel = document.createElement('div');
          sugLabel.style.cssText = 'margin-bottom:6px;display:flex;align-items:center;gap:6px;';
          var sugBadge = document.createElement('span');
          sugBadge.className = 'badge-flat grn';
          sugBadge.textContent = inAll ? '建议路径(与原始一致)' : '建议分类(新分类参考)';
          sugLabel.appendChild(sugBadge);
          sugGrid.appendChild(sugLabel);

          var crumbs = document.createElement('div');
          crumbs.className = 'crumb-path';
          crumbs.style.marginBottom = '8px';
          var parts = sugPath.split(' > ');
          parts.forEach(function(part, idx) {
            var ci = document.createElement('span');
            ci.className = 'crumb-item';
            if (idx === parts.length - 1) ci.style.color = 'var(--text-main)';
            ci.textContent = part;
            crumbs.appendChild(ci);
            if (idx < parts.length - 1) {
              var ca = document.createElement('span');
              ca.className = 'crumb-arrow';
              ca.textContent = '›';
              crumbs.appendChild(ca);
            }
          });
          sugGrid.appendChild(crumbs);

          // Factors inside suggestion grid
          var factors = item.factors || {};
          if (factors.entity) {
            var fl = document.createElement('div'); fl.className = 'spec-line';
            var fk = document.createElement('span'); fk.className = 'spec-k'; fk.textContent = '🔍 entity=';
            var fv = document.createElement('span'); fv.className = 'spec-v'; fv.textContent = '"' + factors.entity + '"';
            if (factors.entity_type) {
              fv.textContent += ' [' + factors.entity_type;
              if (factors.entity_subtype) fv.textContent += '-' + factors.entity_subtype;
              fv.textContent += ']';
            }
            fl.appendChild(fk); fl.appendChild(fv);
            sugGrid.appendChild(fl);
          }
          if (factors.brand_type) {
            var tl = document.createElement('div'); tl.className = 'spec-line';
            var tk = document.createElement('span'); tk.className = 'spec-k'; tk.textContent = '🔍 type=';
            var tv = document.createElement('span'); tv.className = 'spec-v'; tv.textContent = '"' + factors.brand_type + '"';
            tl.appendChild(tk); tl.appendChild(tv);
            sugGrid.appendChild(tl);
          }
          var mods = factors.modifier_detail || [];
          if (!mods.length && factors.modifiers && factors.modifiers.length) {
            mods = factors.modifiers.map(function(m){ return {value:m, type:'未知'}; });
          }
          if (mods.length) {
            var ml = document.createElement('div'); ml.className = 'spec-line';
            var mk = document.createElement('span'); mk.className = 'spec-k'; mk.textContent = '🔍 修饰词=';
            var mv = document.createElement('span'); mv.className = 'spec-v';
            mv.textContent = mods.map(function(m){ return m.value + '[' + (m.type||'未知') + ']'; }).join(', ');
            ml.appendChild(mk); ml.appendChild(mv);
            sugGrid.appendChild(ml);
          }
          var specParts = [];
          if (factors.spec_weight) specParts.push(factors.spec_weight);
          if (factors.spec_pack) specParts.push(factors.spec_pack);
          if (specParts.length) {
            var ssl = document.createElement('div'); ssl.className = 'spec-line';
            var ssk = document.createElement('span'); ssk.className = 'spec-k'; ssk.textContent = '🔍 规格=';
            var ssv = document.createElement('span'); ssv.className = 'spec-v'; ssv.textContent = specParts.join(' | ');
            ssl.appendChild(ssk); ssl.appendChild(ssv);
            sugGrid.appendChild(ssl);
          }

          li.appendChild(sugGrid);
        }

        // Other paths
        var otherPaths = item.all_paths ? item.all_paths.filter(function(p){ return p !== sugPath && p !== path; }) : [];
        if (otherPaths.length) {
          var opLabel = document.createElement('div');
          opLabel.className = 'card-section-label';
          opLabel.style.marginBottom = '6px';
          opLabel.textContent = '其它原始路径：';
          li.appendChild(opLabel);

          otherPaths.forEach(function(op) {
            var oc = document.createElement('div');
            oc.className = 'crumb-path';
            oc.style.cssText = 'opacity:0.6;margin-bottom:4px;';
            var opp = op.split(' > ');
            opp.forEach(function(part, idx) {
              var oi = document.createElement('span');
              oi.textContent = part;
              oc.appendChild(oi);
              if (idx < opp.length - 1) {
                var oa = document.createElement('span');
                oa.textContent = ' › ';
                oc.appendChild(oa);
              }
            });
            li.appendChild(oc);
          });
        }

        // Status or actions
        if (done) {
          var stDiv = document.createElement('div');
          stDiv.className = 'actions-group';
          var st = document.createElement('span');
          st.className = 'badge-flat grn';
          st.textContent = rule.action === 'skip' ? '已跳过' : '已确认: ' + (rule.replacement || '');
          stDiv.appendChild(st);
          li.appendChild(stDiv);
        } else {
          var actRow = document.createElement('div');
          actRow.className = 'actions-group';
          actRow.style.marginTop = '4px';

          var setBtn = document.createElement('button');
          setBtn.className = 'btn-agent primary';
          setBtn.textContent = '设置分类';
          setBtn.onclick = (function(c){ return function(e){ e.stopPropagation(); if(window._emSetCategoryForItem) window._emSetCategoryForItem(c); }; })(code);
          actRow.appendChild(setBtn);

          // 设为当前路径（当前分组路径）
          if (path && (!item.suggested_path || item.suggested_path[0] !== path)) {
            var curBtn = document.createElement('button');
            curBtn.className = 'btn-agent primary';
            curBtn.textContent = '设为当前路径';
            curBtn.onclick = (function(c, p) {
              return function(e) {
                e.stopPropagation();
                window.categoryRules[c] = { action: 'confirm', replacement: p };
                if (window.saveAllCategoryRules) window.saveAllCategoryRules();
                setTimeout(function() { renderPage(currentPage); }, 200);
              };
            })(code, path);
            actRow.appendChild(curBtn);
          }

          // 按建议归集
          var sugPath = item.suggested_path && item.suggested_path[0];
          if (sugPath) {
            var sugBtn = document.createElement('button');
            sugBtn.className = 'btn-agent secondary';
            sugBtn.textContent = '按建议归集';
            sugBtn.onclick = (function(c, sp) {
              return function(e) {
                e.stopPropagation();
                window.categoryRules[c] = { action: 'confirm', replacement: sp };
                if (window.saveAllCategoryRules) window.saveAllCategoryRules();
                setTimeout(function() { renderPage(currentPage); }, 200);
              };
            })(code, sugPath);
            actRow.appendChild(sugBtn);
          }

          var skipBtn = document.createElement('button');
          skipBtn.className = 'btn-agent secondary';
          skipBtn.textContent = '跳过';
          skipBtn.onclick = (function(c){ return function(e){ e.stopPropagation(); if(window.skipSingleItemCategory) window.skipSingleItemCategory(c); }; })(code);
          actRow.appendChild(skipBtn);

          li.appendChild(actRow);
        }

        listEl.appendChild(li);
      });

      // Pagination
      if (pgEl) {
        pgEl.textContent = '';
        if (total > 1) {
          var wrap = document.createElement('div');
          wrap.className = 'pagination-row';
          var prev = document.createElement('button');
          prev.className = 'btn-agent secondary';
          prev.textContent = '上一页';
          if (page <= 0) prev.disabled = true; else prev.onclick = function(){ renderPage(page-1); };
          wrap.appendChild(prev);
          var pi = document.createElement('span');
          pi.className = 'page-info';
          pi.textContent = (page+1) + '/' + total;
          wrap.appendChild(pi);
          var next = document.createElement('button');
          next.className = 'btn-agent secondary';
          next.textContent = '下一页';
          if (page >= total-1) next.disabled = true; else next.onclick = function(){ renderPage(page+1); };
          wrap.appendChild(next);
          pgEl.appendChild(wrap);
        }
      }
    }

    // ── Render into shared #sidePanel, then move to panel card ──
    var sp = document.getElementById('sidePanel');
    var listEl = document.getElementById('panelItemsList');
    var pgWrap = document.getElementById('panelPagination');
    var batchEl = document.getElementById('panelBatchActions');
    if (!sp || !listEl) return;
    listEl.className = 'scroller-list';

    document.getElementById('sidePanelTitle').textContent = (path || '分类商品') + ' · ' + items.length + ' 条';

    // Batch buttons
    batchEl.textContent = '';
    var batchBtns = [
      {text:'全部指定', cls:'primary'},
      {text:'全部设为当前路径', cls:'primary'},
      {text:'全部按建议归集', cls:'secondary'},
      {text:'全部跳过给AI', cls:'secondary'}
    ];
    var batchBar = document.createElement('div');
    batchBar.className = 'batch-row';
    batchBtns.forEach(function(b) {
      var btn = document.createElement('button');
      btn.className = 'btn-agent ' + b.cls;
      btn.textContent = b.text;
      btn.onclick = function(){
        if (b.text === '全部指定' && window.openCategoryPickerForBatch) window.openCategoryPickerForBatch();
        else if (b.text === '全部设为当前路径' && window.batchConfirmAllToCurrentPath) window.batchConfirmAllToCurrentPath();
        else if (b.text === '全部按建议归集' && window.batchConfirmAllCategoryItems) window.batchConfirmAllCategoryItems();
        else if (b.text === '全部跳过给AI' && window.batchSkipAllCategoryItems) window.batchSkipAllCategoryItems();
        setTimeout(function(){ renderPage(currentPage); }, 300);
      };
      batchBar.appendChild(btn);
    });
    batchEl.appendChild(batchBar);

    renderPage(0);
    if (typeof _movePanelToCard === 'function') {
      if (typeof _closePanelCard === 'function') _closePanelCard('product-list', 'sidePanel');
      
      _movePanelToCard('sidePanel', 'category-product-list', (path || '分类商品') + ' · ' + items.length + ' 条');
    }
    sp.classList.remove('hidden');
  };

  // ── Category picker for single item ──
  // 复用 #categoryPickerModal（index.html），不再另建内联 picker
  window._emSetCategoryForItem = function(code) {
    if (typeof openCategoryPicker !== 'function') return;
    // 通过 diagnosis.js 的 openCategoryPicker 打开已有 modal
    openCategoryPicker(code, '');
    // 确认后刷新 Electron 分类审核列表
    setTimeout(function() {
      var confirmBtn = document.getElementById('pickerConfirmBtn');
      if (!confirmBtn) return;
      confirmBtn.setAttribute('onclick', 'confirmPickerSelection().then(function(){ if(typeof renderCategoryReview==="function") renderCategoryReview(); })');
    }, 50);
  };
  // 废弃：_emCatPickL1Changed, _emCatPickL2Changed, _emConfirmCategoryPick
  // 内联 L1/L2/L3 select picker 已删除，统一使用 #categoryPickerModal 的树形选择器

  // ── 图片预览 ──
  window._showImagePreview = function(url, name) {
    var overlay = document.createElement('div');
    overlay.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.8);z-index:10000;display:flex;align-items:center;justify-content:center;cursor:pointer;';
    overlay.addEventListener('click', function() { overlay.remove(); });

    var img = document.createElement('img');
    img.src = url;
    img.alt = name || '';
    img.style.cssText = 'max-width:90vw;max-height:85vh;object-fit:contain;border-radius:8px;box-shadow:0 8px 32px rgba(0,0,0,0.5);';
    img.addEventListener('click', function(e) { e.stopPropagation(); });  // 不关
    overlay.appendChild(img);

    document.body.appendChild(overlay);
  };

  // Init
  setTimeout(initCategoryTabs, 200);

  // Diagnostic
  setTimeout(function(){
    var checks = ['renderCategoryReview','_changeCatReviewPage','filterCategoryReview','_emSetCategoryForItem'];
    var missing = checks.filter(function(k){ return typeof window[k] !== 'function'; });
    if (missing.length) console.error('category_review_electron: MISSING exports:', missing.join(', '));
    else console.log('category_review_electron: all ' + checks.length + ' exports OK');
  }, 100);
})();
