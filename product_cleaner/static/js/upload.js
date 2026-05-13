// ===== 上传模块 =====
(function() {
    const uploadBtn = document.getElementById('uploadBtn');
    const fileInput = document.getElementById('fileInput');
    
    // 初始化加载最近文件
    loadRecentFiles();

    if (uploadBtn && fileInput) {
        // 物理点击绑定（双重保险）
        uploadBtn.onclick = function() {
            fileInput.click();
        };

        fileInput.onchange = async function(e) {
            const file = e.target.files[0];
            if (!file) return;
            
            console.log('开始上传文件:', file.name);
            document.getElementById('uploadMsg').textContent = '⏳ 正在上传...';
            
            const formData = new FormData();
            formData.append('file', file);
            
            // 清除 input 值，允许再次选择同一文件进行测试
            fileInput.value = '';
            
            try {
                const res = await fetch('/api/upload', { method: 'POST', body: formData });
                
                if (!res.ok) {
                    const errorData = await res.json();
                    throw new Error(errorData.error || '服务器响应错误');
                }
                
                const data = await res.json();
                console.log('上传成功，服务器响应:', data);
                
                sessionId = data.session_id;
                localStorage.setItem('last_session_id', sessionId);
                
                if (data.async) {
                    document.getElementById('uploadMsg').textContent = '⏳ ' + data.message;
                    document.getElementById('uploadSection').classList.add('hidden');
                    document.getElementById('diagnosisSection').classList.remove('hidden');
                    document.getElementById('progressSection').classList.remove('hidden');
                    document.getElementById('statsSection').classList.add('opacity-50');
                    document.getElementById('progressText').textContent = data.message;
                    pollDiagnosisStatus();
                } else {
                    diagnosisData = data.diagnosis;
                    document.getElementById('uploadSection').classList.add('hidden');
                    document.getElementById('diagnosisSection').classList.remove('hidden');
                    document.getElementById('progressSection').classList.add('hidden');
                    showDiagnosis(data);
                }
                loadRecentFiles(); // 刷新列表
            } catch (err) {
                console.error('上传过程中发生错误:', err);
                document.getElementById('uploadMsg').textContent = '❌ 上传失败: ' + err.message;
                alert('上传失败: ' + err.message);
            }
        };
    }
})();

// 加载最近文件列表
async function loadRecentFiles() {
    const container = document.getElementById('recentFiles');
    if (!container) return;

    try {
        const res = await fetch('/api/recent_files');
        const files = await res.json();
        
        if (!files || files.length === 0) {
            container.innerHTML = '<p class="text-slate-500 text-sm italic text-center py-4">暂无历史上传记录</p>';
            return;
        }

        container.innerHTML = files.map(f => `
            <div onclick="importRecentFile('${f.id}')" 
                 class="bg-slate-900/50 hover:bg-slate-700/50 border border-slate-700 p-3 rounded-lg cursor-pointer transition-all group">
                <div class="flex justify-between items-center">
                    <div class="flex flex-col truncate">
                        <span class="text-slate-200 text-sm font-medium group-hover:text-cyan-400 truncate">${f.name}</span>
                        <span class="text-[10px] text-slate-500">${f.time}</span>
                    </div>
                    <span class="text-xs text-cyan-600 font-bold group-hover:text-cyan-400">导入 →</span>
                </div>
            </div>
        `).join('');
    } catch (err) {
        console.error('加载最近文件失败:', err);
        container.innerHTML = '<p class="text-red-500/50 text-xs italic">加载历史失败</p>';
    }
}

// 导入已有文件
async function importRecentFile(fileId) {
    if (!confirm('是否导入该历史文件并重新开始诊断？')) return;
    
    document.getElementById('uploadMsg').textContent = '⏳ 正在初始化导入...';
    
    try {
        const res = await fetch('/api/import_recent', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ file_id: fileId })
        });
        
        const data = await res.json();
        if (data.error) throw new Error(data.error);

        sessionId = data.session_id;
        localStorage.setItem('last_session_id', sessionId);
        document.getElementById('uploadSection').classList.add('hidden');
        document.getElementById('diagnosisSection').classList.remove('hidden');
        document.getElementById('progressSection').classList.remove('hidden');
        document.getElementById('statsSection').classList.add('opacity-50');
        document.getElementById('progressText').textContent = data.message;
        
        pollDiagnosisStatus();
    } catch (err) {
        alert('导入失败: ' + err.message);
    }
}

// 页面加载后尝试恢复上次 session
async function tryRestoreSession() {
    const saved = localStorage.getItem('last_session_id');
    if (!saved) { console.log('tryRestoreSession: 无 last_session_id'); return; }

    try {
        const res = await fetch(`/api/diagnosis_status?sid=${saved}`);
        const d = await res.json();
        if (d.error) {
            console.warn('tryRestoreSession: status 返回错误:', d.error);
            localStorage.removeItem('last_session_id');
            return;
        }

        sessionId = saved;

        if (d.status === 'completed') {
            try {
                const resultRes = await fetch(`/api/diagnosis_result?sid=${saved}`);
                if (!resultRes.ok) {
                    const errBody = await resultRes.json().catch(() => ({}));
                    console.warn('tryRestoreSession: result 接口异常', resultRes.status, errBody);
                    localStorage.removeItem('last_session_id');
                    return;
                }
                const resultData = await resultRes.json();
                if (resultData.success && resultData.diagnosis && resultData.diagnosis.brand_clusters) {
                    diagnosisData = resultData.diagnosis;
                    document.getElementById('uploadSection').classList.add('hidden');
                    document.getElementById('diagnosisSection').classList.remove('hidden');
                    document.getElementById('progressSection').classList.add('hidden');
                    showDiagnosis(resultData);
                    return;
                }
                console.warn('tryRestoreSession: result 数据不完整', Object.keys(resultData.diagnosis || {}));
            } catch (e) {
                console.warn('tryRestoreSession: 获取 result 异常:', e);
            }
            localStorage.removeItem('last_session_id');
        } else if (d.status === 'processing') {
            document.getElementById('uploadSection').classList.add('hidden');
            document.getElementById('diagnosisSection').classList.remove('hidden');
            document.getElementById('progressSection').classList.remove('hidden');
            document.getElementById('statsSection').classList.add('opacity-50');
            pollDiagnosisStatus();
        } else {
            console.warn('tryRestoreSession: 未知状态', d.status);
            localStorage.removeItem('last_session_id');
        }
    } catch (e) {
        console.warn('tryRestoreSession: 网络异常:', e);
        localStorage.removeItem('last_session_id');
    }
}

function exitDiagnosis() {
    if (!confirm('退出诊断后将回到上传页面，当前未入库的品牌编辑记录不会丢失。确定退出？')) return;
    localStorage.removeItem('last_session_id');
    location.reload();
}

window.addEventListener('DOMContentLoaded', tryRestoreSession);

