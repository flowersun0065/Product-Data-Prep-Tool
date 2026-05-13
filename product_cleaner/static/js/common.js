let sessionId = null;
let diagnosisData = null;
let brandRules = {};  // 已保存的规则 {code: {brand, no_brand, skipped}}
let categoryRules = {}; // 分类规则 {code: {action, replacement}}
let marketingTags = {}; // 营销标记 {code: [paths]}
let categoryOptions = { level1: [], level2_by_level1: {}, level3_by_level2: {} };
let newBrands = [];   // 用户添加的新品牌
let currentPanelData = null;  // 当前弹窗的数据
let currentPanelPage = 1;
let currentPanelFilter = '';
const ITEMS_PER_PAGE = 20;

// 品牌库（从后端获取）
let brandDatabase = [];

// 分组分页状态
let groupPagination = {
    missing: { page: 1, perPage: 10 },
    mismatch: { page: 1, perPage: 10 },
    valid: { page: 1, perPage: 10 },
    unbranded: { page: 1, perPage: 10 }
};

// 图片预览
function previewImage(url) {
    const overlay = document.createElement('div');
    overlay.className = 'fixed inset-0 z-[9999] bg-black/80 flex items-center justify-center cursor-zoom-out';
    overlay.onclick = () => overlay.remove();
    const img = document.createElement('img');
    img.src = url;
    img.className = 'max-w-[90vw] max-h-[90vh] object-contain rounded-lg shadow-2xl';
    img.onclick = (e) => e.stopPropagation();
    overlay.appendChild(img);
    document.body.appendChild(overlay);
}

// 展开/收起整个区域
function toggleSection(sectionId) {
    const section = document.getElementById(sectionId);
    const groupsContainer = section.querySelector('#' + sectionId);
    const arrow = document.getElementById(sectionId + 'Arrow');
    
    if (section.classList.contains('collapsed')) {
        section.classList.remove('collapsed');
        if (arrow) arrow.style.transform = 'rotate(0deg)';
    } else {
        section.classList.add('collapsed');
        if (arrow) arrow.style.transform = 'rotate(-90deg)';
    }
}
