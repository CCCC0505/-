document.addEventListener('DOMContentLoaded', function() {
    // 初始化页面
    initNotebook();
    
    // 绑定事件监听器
    bindEventListeners();
    
    // 加载错题数据
    loadMistakes();
});

// 初始化错题本
function initNotebook() {
    // 更新统计数据
    updateStats();
    
    // 加载知识点标签
    loadKnowledgeTags();
    
    // 初始化过滤器
    initFilters();
}

// 更新统计数据
function updateStats() {
    // 这里应该从后端API获取实际数据
    const stats = {
        total: 128,
        mastered: 45,
        review: 83
    };
    
    document.getElementById('total-mistakes').textContent = stats.total;
    document.getElementById('mastered-count').textContent = stats.mastered;
    document.getElementById('review-count').textContent = stats.review;
}

// 加载知识点标签
function loadKnowledgeTags() {
    const knowledgeTags = document.getElementById('knowledge-tags');
    // 这里应该从后端API获取实际的知识点数据
    const tags = [
        { id: 1, name: '牛顿运动定律', count: 15 },
        { id: 2, name: '圆周运动', count: 8 },
        { id: 3, name: '热学', count: 12 },
        { id: 4, name: '电磁学', count: 20 },
        { id: 5, name: '光学', count: 10 }
    ];
    
    knowledgeTags.innerHTML = tags.map(tag => `
        <div class="knowledge-tag" data-id="${tag.id}">
            ${tag.name} (${tag.count})
        </div>
    `).join('');
}

// 初始化过滤器
function initFilters() {
    const subjectFilter = document.getElementById('subject-filter');
    const knowledgeFilter = document.getElementById('knowledge-filter');
    
    // 监听学科选择变化
    subjectFilter.addEventListener('change', function() {
        // 更新知识点下拉列表
        updateKnowledgeFilter(this.value);
        // 重新加载错题列表
        loadMistakes();
    });
    
    // 监听知识点选择变化
    knowledgeFilter.addEventListener('change', function() {
        loadMistakes();
    });
}

// 更新知识点过滤器选项
function updateKnowledgeFilter(subject) {
    const knowledgeFilter = document.getElementById('knowledge-filter');
    // 这里应该根据选择的学科从后端API获取相应的知识点列表
    const knowledgePoints = {
        'physics': [
            { id: 1, name: '牛顿运动定律' },
            { id: 2, name: '圆周运动' },
            { id: 3, name: '热学' }
        ],
        'math': [
            { id: 4, name: '函数' },
            { id: 5, name: '导数' },
            { id: 6, name: '积分' }
        ]
    };
    
    const options = knowledgePoints[subject] || [];
    knowledgeFilter.innerHTML = `
        <option value="all">全部知识点</option>
        ${options.map(point => `
            <option value="${point.id}">${point.name}</option>
        `).join('')}
    `;
}

// 加载错题列表
function loadMistakes(page = 1) {
    const mistakeList = document.getElementById('mistake-list');
    // 这里应该从后端API获取实际的错题数据
    const mistakes = [
        {
            id: 1,
            subject: '物理',
            difficulty: 'medium',
            question: '一个物体在水平面上运动，受到一个大小为5N的水平推力，物体的加速度为2m/s²，则该物体的质量是多少？',
            answer: '2.5kg',
            tags: ['牛顿运动定律', '力学计算'],
            date: '2024-03-15'
        },
        // 更多错题数据...
    ];
    
    mistakeList.innerHTML = mistakes.map(mistake => createMistakeItem(mistake)).join('');
    updatePagination(page, 10); // 总页数假设为10
}

// 创建错题项
function createMistakeItem(mistake) {
    return `
        <div class="mistake-item" data-id="${mistake.id}">
            <div class="mistake-header">
                <div class="mistake-meta">
                    <span class="mistake-subject">${mistake.subject}</span>
                    <span class="mistake-difficulty difficulty-${mistake.difficulty}">
                        ${getDifficultyText(mistake.difficulty)}
                    </span>
                </div>
                <span class="mistake-date">${mistake.date}</span>
            </div>
            <div class="mistake-content">
                <div class="mistake-question">${mistake.question}</div>
                <div class="mistake-answer">正确答案：${mistake.answer}</div>
            </div>
            <div class="mistake-footer">
                <div class="mistake-tags">
                    ${mistake.tags.map(tag => `
                        <span class="mistake-tag">${tag}</span>
                    `).join('')}
                </div>
                <div class="mistake-actions">
                    <button class="action-btn review-btn" onclick="reviewMistake(${mistake.id})">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M12 4V12L16 14" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                            <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/>
                        </svg>
                        复习
                    </button>
                    <button class="action-btn delete-btn" onclick="deleteMistake(${mistake.id})">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M3 6H21" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                            <path d="M19 6V20C19 21.1046 18.1046 22 17 22H7C5.89543 22 5 21.1046 5 20V6" stroke="currentColor" stroke-width="2"/>
                            <path d="M8 6V4C8 2.89543 8.89543 2 10 2H14C15.1046 2 16 2.89543 16 4V6" stroke="currentColor" stroke-width="2"/>
                        </svg>
                        删除
                    </button>
                </div>
            </div>
        </div>
    `;
}

// 获取难度文本
function getDifficultyText(difficulty) {
    const texts = {
        'easy': '简单',
        'medium': '中等',
        'hard': '困难'
    };
    return texts[difficulty] || '未知';
}

// 更新分页
function updatePagination(currentPage, totalPages) {
    document.getElementById('current-page').textContent = currentPage;
    document.getElementById('total-pages').textContent = totalPages;
    
    const prevBtn = document.getElementById('prev-page');
    const nextBtn = document.getElementById('next-page');
    
    prevBtn.disabled = currentPage === 1;
    nextBtn.disabled = currentPage === totalPages;
}

// 绑定事件监听器
function bindEventListeners() {
    // 搜索功能
    const searchInput = document.getElementById('search-input');
    const searchBtn = document.getElementById('search-btn');
    
    searchBtn.addEventListener('click', function() {
        const searchTerm = searchInput.value.trim();
        if (searchTerm) {
            searchMistakes(searchTerm);
        }
    });
    
    searchInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            const searchTerm = this.value.trim();
            if (searchTerm) {
                searchMistakes(searchTerm);
            }
        }
    });
    
    // 分页控制
    document.getElementById('prev-page').addEventListener('click', function() {
        const currentPage = parseInt(document.getElementById('current-page').textContent);
        if (currentPage > 1) {
            loadMistakes(currentPage - 1);
        }
    });
    
    document.getElementById('next-page').addEventListener('click', function() {
        const currentPage = parseInt(document.getElementById('current-page').textContent);
        const totalPages = parseInt(document.getElementById('total-pages').textContent);
        if (currentPage < totalPages) {
            loadMistakes(currentPage + 1);
        }
    });
}

// 搜索错题
function searchMistakes(term) {
    // 这里应该调用后端API进行搜索
    console.log('搜索错题:', term);
    // 临时刷新错题列表
    loadMistakes();
}

// 复习错题
function reviewMistake(id) {
    // 这里应该跳转到练习页面或显示详细信息
    console.log('复习错题:', id);
}

// 删除错题
function deleteMistake(id) {
    if (confirm('确定要删除这道错题吗？')) {
        // 这里应该调用后端API删除错题
        console.log('删除错题:', id);
        // 临时刷新错题列表
        loadMistakes();
    }
} 