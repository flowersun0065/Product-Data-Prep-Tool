// ===== AI 处理模块 =====
// 独立的 AI 处理逻辑：启动、轮询进度、渲染日志、完成处理

let aiPollTimer = null;
let aiLogPollTimer = null;

// 保存 AI 配置到 localStorage（跨会话持久）
function saveAIConfig() {
    const config = {
        provider: document.getElementById('aiProvider').value,
        model_id: document.getElementById('aiModel').value,
        api_key: document.getElementById('aiApiKey').value
    };
    try { localStorage.setItem('_ai_config', JSON.stringify(config)); } catch(e) {}
    if (typeof showSaveIndicator === 'function') showSaveIndicator();
}

// 从 localStorage 加载 AI 配置
function loadAIConfig() {
    try {
        const saved = localStorage.getItem('_ai_config');
        if (!saved) return;
        const config = JSON.parse(saved);
        if (config.provider) document.getElementById('aiProvider').value = config.provider;
        if (config.model_id) document.getElementById('aiModel').value = config.model_id;
        if (config.api_key) document.getElementById('aiApiKey').value = config.api_key;
    } catch(e) { /* ignore */ }
}

// 字段变化时自动保存
function setupAutoSaveAIConfig() {
    ['aiProvider', 'aiModel', 'aiApiKey'].forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener('change', saveAIConfig);
            el.addEventListener('input', saveAIConfig);
        }
    });
}

async function startAIProcessing() {
    // 1. 收集 AI 配置
    const provider = document.getElementById('aiProvider').value;
    const apiKey = document.getElementById('aiApiKey').value;
    const modelId = document.getElementById('aiModel').value;

    if (!apiKey) {
        if (!confirm('尚未填写 API Key，AI 处理将无法进行。是否继续（仅本地处理）？')) {
            return;
        }
    }

    // 2. 立即显示连接状态（在 await 之前，确保点击就有反馈）
    showAIHeaderStatus('⏳ AI链接中...', 'bg-yellow-500');

    // 3. 先保存所有当前的品牌/分类规则
    if (typeof saveAllCategoryRules === 'function') {
        await saveAllCategoryRules();
    }

    // 3. 隐藏 AI 配置面板，显示进度区域
    document.getElementById('aiConfigPanel').classList.add('hidden');
    document.getElementById('aiProgressSection').classList.remove('hidden');
    document.getElementById('aiProgressBar').style.width = '0%';
    document.getElementById('aiProgressBar').classList.remove('bg-red-500');
    document.getElementById('aiProgressPercent').textContent = '0';
    document.getElementById('aiProgressDetail').textContent = '正在启动...';
    document.getElementById('aiLogContainer').innerHTML = '<div class="text-slate-500 italic">等待处理数据...</div>';
    document.getElementById('aiCompleteActions').classList.add('hidden');
    document.getElementById('aiErrorMessage').classList.add('hidden');
    document.getElementById('aiCancelBtn').classList.remove('hidden');
    document.getElementById('aiStatusDot').classList.remove('hidden');
    document.getElementById('aiStatusTitle').textContent = 'AI 正在处理未确认的商品...';

    // 4. POST /api/process 启动处理
    try {
        const res = await fetch('/api/process', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: sessionId,
                provider: provider,
                api_key: apiKey,
                model_id: modelId,
                batch_size: 20,
                force_reanalyze: document.getElementById('aiForceReanalyze').checked
            })
        });
        const data = await res.json();
        if (!data.success) {
            throw new Error(data.error || '启动失败');
        }
    } catch (err) {
        onAIError('启动 AI 处理失败: ' + err.message);
        return;
    }

    // 6. 连接成功，改为处理中
    showAIHeaderStatus('AI处理中...', 'bg-cyan-500');

    // 处理中即可打开复核页
    document.getElementById('aiReviewBtn').classList.remove('hidden');
    document.getElementById('aiCompleteActions').classList.remove('hidden');
    document.getElementById('aiDownloadBtn').classList.add('hidden');

    // 7. 开始轮询
    aiPollTimer = setInterval(pollAIProgress, 1500);
    aiLogPollTimer = setInterval(pollAILogs, 1500);
    // 立即轮询一次
    pollAIProgress();
    pollAILogs();
}

async function pollAIProgress() {
    try {
        const res = await fetch('/api/status?sid=' + sessionId);
        const data = await res.json();

        if (data.ai_total > 0) {
            const pct = data.progress || 0;
            document.getElementById('aiProgressBar').style.width = pct + '%';
            document.getElementById('aiProgressPercent').textContent = pct;
            document.getElementById('aiProgressDetail').innerHTML =
                `已处理: ${data.processed || 0}/${data.ai_total} &nbsp;|&nbsp; ` +
                `品牌待AI: ${data.ai_total_brand || 0} 分类待AI: ${data.ai_total_category || 0}<br>` +
                `品牌已确认: ${data.ai_skipped_brand || 0} 分类已确认: ${data.ai_skipped_category || 0}`;
        }

        if (data.status === 'completed') {
            stopPolling();
            onAIComplete(data);
        } else if (data.status === 'error') {
            stopPolling();
            onAIError(data.message || '处理出错');
        } else if (data.status === 'cancelled') {
            stopPolling();
            cancelAI();
        }
    } catch (err) {
        console.error('轮询进度失败:', err);
    }
}

async function pollAILogs() {
    try {
        const res = await fetch('/api/ai_logs?sid=' + sessionId);
        const data = await res.json();
        const logs = data.logs || [];
        if (logs.length === 0) return;

        const container = document.getElementById('aiLogContainer');
        // 移除占位文本
        if (container.innerHTML.includes('等待处理数据')) {
            container.innerHTML = '';
        }

        logs.forEach(log => {
            const entry = renderLogEntry(log);
            container.appendChild(entry);
        });
        container.scrollTop = container.scrollHeight;
    } catch (err) {
        console.error('轮询日志失败:', err);
    }
}

function renderLogEntry(log) {
    const div = document.createElement('div');
    div.className = 'flex items-start gap-2 p-2 rounded text-sm border-l-2';

    // 系统消息（非商品条目）
    if (log._system_message) {
        div.className += ' bg-slate-800/50';
        div.style.borderLeftColor = '#3b82f6';
        div.innerHTML = `
            <span class="flex-shrink-0 text-xs mt-0.5">ℹ</span>
            <div class="flex-1">
                <div class="text-slate-300 italic">${escapeHtml(log._system_message)}</div>
            </div>
        `;
        return div;
    }

    const brandStatus = log.brand?.status || 'skipped';
    const catStatus = log.category?.status || 'skipped';
    const brandValue = log.brand?.value || '-';
    const catPath = log.category?.path || '-';
    const needsReview = log.needs_review;
    const brandError = log.brand?.error;
    const catError = log.category?.error;
    const catMethod = log.category?.method || '';
    const suggestion = log.brand?.suggestion || '';
    const aiAgrees = log.brand?.ai_agrees;

    const brandConfirmed = log.brand?.confirmed;
    const catConfirmed = log.category?.confirmed;

    let icon = '⏭';
    let borderColor = '#4b5563';
    let statusText = '';
    let extraInfo = '';

    if (brandConfirmed && catConfirmed) {
        statusText = `已确认  品牌: ${brandValue}  分类: ${catPath}`;
    } else if (brandConfirmed) {
        statusText = `品牌已确认: ${brandValue}  |  分类待AI`;
    } else if (catConfirmed) {
        statusText = `品牌待AI  |  分类已确认: ${catPath}`;
    } else {
        statusText = '跳过(未处理)';
    }

    if (brandStatus === 'from_library') {
        icon = '📚';
        borderColor = '#10b981';
        statusText = `品牌库: ${brandValue}`;
    } else if (brandStatus === 'error') {
        icon = '❌';
        borderColor = '#ef4444';
        statusText = `AI调用失败: ${brandError || ''}`;
    } else if (brandStatus === 'no_brand') {
        icon = '🏷️';
        borderColor = '#94a3b8';
        statusText = 'AI判断: 无品牌';
        extraInfo = suggestion ? `建议:${suggestion}` : '';
    } else if (brandStatus === 'ai_ok' && aiAgrees === true) {
        icon = '✅';
        borderColor = '#10b981';
        statusText = `AI(与建议一致): ${brandValue}`;
        extraInfo = suggestion ? `建议:${suggestion}` : '';
    } else if (brandStatus === 'ai_ok' && aiAgrees === false) {
        icon = '🔄';
        borderColor = '#f59e0b';
        statusText = `AI(修正建议): ${brandValue}`;
        extraInfo = suggestion ? `原建议:${suggestion}` : '';
    } else if (brandStatus === 'ai_ok' && needsReview) {
        icon = '⚠';
        borderColor = '#f59e0b';
        statusText = `AI(低置信): ${brandValue}`;
    } else if (brandStatus === 'ai_ok') {
        icon = '✅';
        borderColor = '#10b981';
        statusText = `AI: ${brandValue}`;
    } else if (brandStatus === 'local_fallback') {
        icon = '🔧';
        borderColor = '#6b7280';
        statusText = `本地(fallback): ${brandValue}`;
    }

    // 分类状态
    if (catStatus === 'ai_ok') {
        const catMethod = log.category?.method || '';
        if (catMethod === 'ai_out_of_range') {
            statusText += ` | 分类(超出可选范围): ${catPath}`;
        } else {
            statusText += ` | 分类: ${catPath}`;
        }
    } else if (catStatus === 'local_fallback') {
        statusText += ` | 分类(AI失败): ${catPath || '-'}`;
        if (catError) statusText += ` (${catError})`;
    }

    if (brandError && brandStatus !== 'error') {
        statusText += ` ${brandError ? '[' + brandError + ']' : ''}`;
    }

    if (needsReview) {
        div.style.background = 'rgba(239,68,68,0.08)';
    }

    // 获取 AI 理由 + factors
    const brandReason = log.brand?.reason || '';
    const catReason = log.category?.reason || '';
    const reasons = [];
    if (brandReason) reasons.push('品牌: ' + brandReason);
    if (catReason) reasons.push('分类: ' + catReason);
    const displayReason = reasons.join(' | ') || '';
    const factors = log.factors || {};
    const entity = factors.entity || '';
    const modifiers = (factors.modifiers || []).join(', ');
    const factorParts = [];
    if (entity) factorParts.push('品种:' + entity);
    if (modifiers) factorParts.push('修饰:' + modifiers);
    const factorText = factorParts.join(' | ');

    div.innerHTML = `
        <span class="flex-shrink-0 text-xs mt-0.5">${icon}</span>
        <div class="flex-1 min-w-0">
            <div class="text-slate-200 font-medium truncate">${escapeHtml(log.name || '')}</div>
            <div class="text-xs text-slate-400">${escapeHtml(statusText)}</div>
            ${extraInfo ? '<div class="text-[10px] text-slate-500 mt-0.5">' + escapeHtml(extraInfo) + '</div>' : ''}
            ${factorText ? '<div class="text-[10px] text-slate-500">' + escapeHtml(factorText) + '</div>' : ''}
            ${displayReason ? '<div class="text-[10px] text-slate-600 italic mt-0.5">' + escapeHtml(displayReason) + '</div>' : ''}
        </div>
        ${needsReview ? '<span class="flex-shrink-0 text-amber-400 text-xs">待复核</span>' : ''}
    `;
    return div;
}

function onAIComplete(data) {
    document.getElementById('aiStatusDot').classList.add('hidden');
    document.getElementById('aiStatusTitle').textContent = '✅ 处理完成';
    document.getElementById('aiProgressDetail').innerHTML =
        `处理完成！` +
        (data.ai_total_brand ? `<br>品牌: AI处理${data.ai_total_brand}条 | 已确认跳过${data.ai_skipped_brand || 0}条` : '') +
        (data.ai_total_category ? `<br>分类: AI处理${data.ai_total_category}条 | 已确认跳过${data.ai_skipped_category || 0}条` : '');
    document.getElementById('aiProgressBar').style.width = '100%';
    document.getElementById('aiProgressPercent').textContent = '100';
    document.getElementById('aiCancelBtn').classList.add('hidden');
    document.getElementById('aiCompleteActions').classList.remove('hidden');
    document.getElementById('aiDownloadBtn').classList.remove('hidden');

    // 头部状态 → 短暂显示完成，然后隐藏
    showAIHeaderStatus('✅ AI处理完成', 'bg-emerald-500');
    setTimeout(hideAIHeaderStatus, 4000);

    // 下载按钮
    const downloadBtn = document.getElementById('aiDownloadBtn');
    if (downloadBtn) {
        downloadBtn.onclick = function() {
            window.location.href = '/api/download?sid=' + sessionId + '&type=result';
        };
    }

    // 复核按钮
    const reviewBtn = document.getElementById('aiReviewBtn');
    if (reviewBtn) {
        reviewBtn.onclick = function() {
            window.open('/review?sid=' + sessionId, '_blank');
        };
        if (data.review_pending > 0) {
            reviewBtn.textContent = '📋 前往复核 (' + data.review_pending + ')';
        }
    }
}

function onAIError(msg) {
    document.getElementById('aiStatusDot').classList.add('hidden');
    document.getElementById('aiStatusTitle').textContent = '❌ 处理出错';
    document.getElementById('aiProgressBar').style.width = '100%';
    document.getElementById('aiProgressBar').classList.add('bg-red-500');
    document.getElementById('aiProgressPercent').textContent = '!';
    document.getElementById('aiCancelBtn').classList.add('hidden');
    document.getElementById('aiErrorMessage').classList.remove('hidden');
    document.getElementById('aiErrorText').textContent = msg;
    showAIHeaderStatus('❌ AI处理失败', 'bg-red-500');
}

async function cancelAI() {
    // 通知后端停止
    try {
        await fetch('/api/process/cancel', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId })
        });
    } catch(e) {
        console.warn('取消请求发送失败:', e);
    }

    stopPolling();
    hideAIHeaderStatus();
    document.getElementById('aiProgressSection').classList.add('hidden');
    document.getElementById('aiConfigPanel').classList.remove('hidden');
    document.getElementById('aiProgressBar').classList.remove('bg-red-500');
    document.getElementById('aiProgressBar').style.width = '0%';
}

function showAIHeaderStatus(text, dotColor) {
    const el = document.getElementById('aiHeaderStatus');
    const textEl = document.getElementById('aiHeaderStatusText');
    if (el && textEl) {
        textEl.textContent = text;
        const dot = el.querySelector('span');
        if (dot) dot.className = 'flex h-2 w-2 rounded-full mr-2 animate-pulse ' + (dotColor || 'bg-cyan-500');
        el.classList.remove('hidden');
    }
}

function hideAIHeaderStatus() {
    const el = document.getElementById('aiHeaderStatus');
    if (el) el.classList.add('hidden');
}

function retryAI() {
    document.getElementById('aiProgressBar').classList.remove('bg-red-500');
    document.getElementById('aiProgressBar').style.width = '0%';
    document.getElementById('aiErrorMessage').classList.add('hidden');
    document.getElementById('aiCompleteActions').classList.add('hidden');
    startAIProcessing();
}

function stopPolling() {
    if (aiPollTimer) { clearInterval(aiPollTimer); aiPollTimer = null; }
    if (aiLogPollTimer) { clearInterval(aiLogPollTimer); aiLogPollTimer = null; }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 直接进入复核（无 AI）：所有需确认项已确认完，跳过 AI 生成复核数据
async function finalizeWithoutAI() {
    // 1. 先保存当前的品牌/分类规则
    if (typeof saveAllCategoryRules === 'function') {
        await saveAllCategoryRules();
    }

    // 2. 复用 AI 处理的进度 UI
    showAIHeaderStatus('⏳ 生成复核数据...', 'bg-yellow-500');
    const configPanel = document.getElementById('aiConfigPanel');
    if (configPanel) configPanel.classList.add('hidden');
    const progressSection = document.getElementById('aiProgressSection');
    if (progressSection) progressSection.classList.remove('hidden');
    const bar = document.getElementById('aiProgressBar');
    if (bar) { bar.style.width = '0%'; bar.classList.remove('bg-red-500'); }
    const detail = document.getElementById('aiProgressDetail');
    if (detail) detail.textContent = '正在生成复核数据（无 AI）...';
    const logC = document.getElementById('aiLogContainer');
    if (logC) logC.innerHTML = '<div class="text-slate-500 italic">无需 AI，正在整理已确认数据...</div>';
    const cancelBtn = document.getElementById('aiCancelBtn');
    if (cancelBtn) cancelBtn.classList.add('hidden');
    const errMsg = document.getElementById('aiErrorMessage');
    if (errMsg) errMsg.classList.add('hidden');
    const titleEl = document.getElementById('aiStatusTitle');
    if (titleEl) titleEl.textContent = '正在生成复核数据（未经 AI）...';

    // 3. POST /api/finalize 启动（不调用 AI）
    try {
        const res = await fetch('/api/finalize', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId })
        });
        const data = await res.json();
        if (!data.success) {
            throw new Error(data.error || '启动失败');
        }
    } catch (err) {
        onAIError('生成复核数据失败: ' + err.message);
        return;
    }

    // 4. 处理中即可打开复核页
    const reviewBtn = document.getElementById('aiReviewBtn');
    if (reviewBtn) reviewBtn.classList.remove('hidden');
    const completeActions = document.getElementById('aiCompleteActions');
    if (completeActions) completeActions.classList.remove('hidden');

    // 5. 复用同一套状态轮询（/api/status）
    aiPollTimer = setInterval(pollAIProgress, 1500);
    aiLogPollTimer = setInterval(pollAILogs, 1500);
    pollAIProgress();
    pollAILogs();
}

// 暴露到全局
window.finalizeWithoutAI = finalizeWithoutAI;
window.startAIProcessing = startAIProcessing;
window.saveAIConfig = saveAIConfig;
window.retryAI = retryAI;
window.cancelAI = cancelAI;
window.showAIHeaderStatus = showAIHeaderStatus;
window.hideAIHeaderStatus = hideAIHeaderStatus;
window.loadAIConfig = loadAIConfig;
window.setupAutoSaveAIConfig = setupAutoSaveAIConfig;

// 页面加载后自动恢复配置 + 开启自动保存
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
        loadAIConfig();
        setupAutoSaveAIConfig();
    });
} else {
    loadAIConfig();
    setupAutoSaveAIConfig();
}
