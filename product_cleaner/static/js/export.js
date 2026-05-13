// ===== 导出与预览模块 =====

// 显示导出预览
async function showExportPreview() {
    try {
        const res = await fetch('/api/brands/dynamic');
        const data = await res.json();
        const dynamicBrands = data.brands || {};
        
        const brandList = Object.entries(dynamicBrands);
        document.getElementById('exportCount').textContent = brandList.length;
        
        if (brandList.length === 0) {
            document.getElementById('exportPreviewList').innerHTML = '<p class="text-center text-gray-400 py-4">暂无待导出的品牌</p>';
        } else {
            document.getElementById('exportPreviewList').innerHTML = brandList.map(([name, info]) => `
                <div class="flex justify-between items-center py-2 border-b border-slate-700 last:border-0">
                    <div>
                        <span class="font-medium text-white">${name}</span>
                        <span class="text-xs text-gray-400 ml-2">${info.type || '未知'} · ${info.country || 'CN'}</span>
                    </div>
                    <span class="text-xs text-purple-400">${(info.aliases || []).length} 个别名</span>
                </div>
            `).join('');
        }
        
        document.getElementById('exportPreviewModal').classList.add('open');
    } catch (err) {
        console.error('获取动态品牌失败:', err);
        alert('获取品牌列表失败');
    }
}

// 关闭导出预览
function closeExportPreview() {
    document.getElementById('exportPreviewModal').classList.remove('open');
}

// 确认导出到品牌库
async function confirmExportToLibrary() {
    try {
        const res = await fetch('/api/brands/export-to-library', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: typeof sessionId !== 'undefined' ? sessionId : null
            })
        });
        const data = await res.json();
        
        if (data.success) {
            alert(`✅ 成功将 ${data.count || 0} 个品牌合并到品牌库！\n\n下次诊断时将使用更新后的品牌库。`);
            closeExportPreview();
            
            // 从后端同步最新状态（含已清空的 session）
            if (typeof syncBrandRules === 'function') {
                await syncBrandRules();
            }
            
            // 无论后端是否清空，都在前端移除已确认品牌
            if (typeof clearConfirmedBrands === 'function') {
                clearConfirmedBrands();
            }
            
            await fetchBrandDatabase();

            // 导出后重新渲染面板，确保展示 latest brand_rules 而非旧 diagnosisData
            if (typeof renderBrandGroups === 'function' && typeof diagnosisData !== 'undefined' && diagnosisData) {
                renderBrandGroups(diagnosisData.brand_clusters);
            }
            if (typeof renderPanelContent === 'function' && typeof currentPanelData !== 'undefined' && currentPanelData) {
                renderPanelContent();
            }
            if (typeof updateNewBrandsDisplay === 'function') {
                updateNewBrandsDisplay();
            }
        } else {
            alert('❌ 导出失败：' + (data.error || '未知错误'));
        }
    } catch (err) {
        console.error('导出失败:', err);
        alert('❌ 导出失败: ' + err.message);
    }
}

// 应用规则并交给 AI 处理（改为调用独立的 AI 处理模块）
async function applyRulesAndPreview() {
    // 交给 AI 处理模块处理
    if (typeof startAIProcessing === 'function') {
        await startAIProcessing();
    } else {
        alert('AI 处理模块未加载');
    }
}

window.showExportPreview = showExportPreview;
window.closeExportPreview = closeExportPreview;
window.confirmExportToLibrary = confirmExportToLibrary;
window.applyRulesAndPreview = applyRulesAndPreview;
