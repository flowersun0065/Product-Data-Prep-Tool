// ═══ Electron: Detail Panel (rightColumn card instead of overlay) ═══
// Overrides openDetail/closeDetail for electron mode.
(function(){
  if (!window._electronMode) return;

  var _origOpenDetail = openDetail;
  var _origCloseDetail = closeDetail;

  openDetail = function(item, mode) {
    var detailMode = mode || (window._settings && window._settings.detail_mode) || 'sidebar';
    if (detailMode === 'window' && window.electronAPI) {
      window.electronAPI.openDetailWindow(item);
      return;
    }
    if (typeof window._movePanelToCard === 'function') {
      window._movePanelToCard('detailPanel', 'product-detail', (item.name || item.code || '商品详情'));
    }
    (window._dpRenderDetail || _origOpenDetail)(item);
    document.getElementById('detailPanel').classList.add('open');
  };

  closeDetail = function() {
    if (typeof window._closePanelCard === 'function') {
      window._closePanelCard('product-detail', 'detailPanel');
    }
    document.getElementById('detailPanel').classList.remove('open');
    (window._dpCancelEdit || cancelEdit)();
  };
})();
