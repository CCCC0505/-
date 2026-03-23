document.addEventListener('DOMContentLoaded', function() {
    // 当前学科和知识点ID
    let currentSubject = ''; // 将通过URL参数获取
    let currentKnowledgeId = null;
    let currentGrade = ''; // 将通过URL参数获取
    let currentSchool = ''; // 将通过URL参数获取
    
    // 页面元素
    const knowledgeList = document.getElementById('knowledge-list');
    const knowledgeLoading = document.getElementById('knowledge-loading');
    const detailLoading = document.getElementById('detail-loading');
    const currentKnowledgeElem = document.getElementById('current-knowledge');
    const currentSubjectElem = document.getElementById('current-subject');
    const currentGradeElem = document.getElementById('current-grade');
    const knowledgeContent = document.getElementById('knowledge-content');
    const searchInput = document.getElementById('knowledge-search-input');
    const searchBtn = document.getElementById('knowledge-search-btn');
    const subjectNameElem = document.getElementById('subject-name');
    
    // 学科名称映射
    const subjectNames = {
        'math': '数学',
        'chinese': '语文',
        'english': '英语',
        'physics': '物理',
        'chemistry': '化学',
        'biology': '生物',
        'politics': '政治',
        'history': '历史',
        'geography': '地理'
    };
    
    // 学科图标类映射
    const subjectIconClasses = {
        'math': 'math-icon',
        'chinese': 'chinese-icon',
        'english': 'english-icon',
        'physics': 'physics-icon',
        'chemistry': 'chemistry-icon',
        'biology': 'biology-icon',
        'politics': 'politics-icon',
        'history': 'history-icon',
        'geography': 'geography-icon'
    };
    
    // 从URL参数获取学科、年级和学校类型
    const urlParams = new URLSearchParams(window.location.search);
    
    // 直接获取中文学科名称
    currentSubject = urlParams.get('subject') || '数学';
    currentGrade = urlParams.get('grade') || '一年级';
    currentSchool = urlParams.get('level') || '小学';
    
    // 设置页面标题和面包屑导航
    if (currentSubjectElem) currentSubjectElem.textContent = currentSubject;
    if (currentGradeElem) currentGradeElem.textContent = `${currentSchool}${currentGrade}`;
    if (subjectNameElem) subjectNameElem.textContent = currentSubject;
    
    // 初始化知识点列表
    loadSampleKnowledgePoints();
    
    // 初始化标签页切换
    initTabSwitching();
    
    // 初始化搜索功能
    if (searchInput && searchBtn) {
        searchInput.addEventListener('input', searchKnowledgePoints);
        searchBtn.addEventListener('click', searchKnowledgePoints);
    }
    
    // 添加开始练习按钮的点击事件
    const startPracticeBtn = document.getElementById('start-practice-btn');
    if (startPracticeBtn) {
        startPracticeBtn.addEventListener('click', function(e) {
            e.preventDefault();
            
            // 构建练习中心页面URL，带上当前学科、年级和知识点参数
            const currentKnowledgeText = currentKnowledgeElem ? currentKnowledgeElem.textContent : '';
            const practiceUrl = `./practice.html?subject=${encodeURIComponent(currentSubject)}&grade=${encodeURIComponent(currentGrade)}&level=${encodeURIComponent(currentSchool)}&knowledge=${encodeURIComponent(currentKnowledgeText)}`;
            
            // 跳转到练习中心页面
            window.location.href = practiceUrl;
        });
    }
    
    // 示例知识点数据
    function loadSampleKnowledgePoints() {
        // 显示加载状态
        if (knowledgeLoading) knowledgeLoading.style.display = 'flex';
        if (knowledgeList) knowledgeList.innerHTML = '';
        fetch(`/api/ui/knowledge-points?subject=${encodeURIComponent(currentSubject)}`)
            .then(response => response.json())
            .then(data => {
            const knowledgePoints = data.knowledge_points || [];
            if (knowledgeLoading) knowledgeLoading.style.display = 'none';
            if (knowledgePoints.length > 0) {
                knowledgePoints.forEach(point => {
                    const item = document.createElement('div');
                    item.className = 'knowledge-item';
                    item.dataset.id = point.id;
                    item.innerHTML = `
                        <span class="knowledge-title">${point.title}</span>
                        <div class="knowledge-meta">
                            <span class="difficulty ${point.difficulty === '简单' ? 'easy' : point.difficulty === '中等' ? 'medium' : 'hard'}">${point.difficulty}</span>
                            <span class="importance ${point.importance === '基础' ? 'basic' : 'key'}">${point.importance}</span>
                        </div>
                    `;
                    
                    // 点击知识点加载详情
                    item.addEventListener('click', function() {
                        document.querySelectorAll('.knowledge-item').forEach(k => k.classList.remove('active'));
                            this.classList.add('active');
                            loadKnowledgeDetail(this.dataset.id);
                        currentKnowledgeId = this.dataset.id;
                        if (currentKnowledgeElem) {
                            currentKnowledgeElem.textContent = this.querySelector('.knowledge-title').textContent;
                        }
                    });
                    
                    if (knowledgeList) knowledgeList.appendChild(item);
                });

                if (knowledgeList.firstChild) {
                    knowledgeList.firstChild.classList.add('active');
                    currentKnowledgeId = knowledgeList.firstChild.dataset.id;
                    const firstTitle = knowledgeList.firstChild.querySelector('.knowledge-title')?.textContent || '';
                    if (currentKnowledgeElem) {
                        currentKnowledgeElem.textContent = firstTitle;
                    }
                    loadKnowledgeDetail(currentKnowledgeId, firstTitle);
                }
            } else {
                if (knowledgeList) knowledgeList.innerHTML = '<p class="no-data">暂无知识点数据</p>';
            }
        })
        .catch(error => {
            console.error('加载知识点失败:', error);
            if (knowledgeLoading) knowledgeLoading.style.display = 'none';
            if (knowledgeList) knowledgeList.innerHTML = '<p class="no-data">知识点加载失败，请刷新重试</p>';
        });
    }
    
    // 加载知识点详情
    function loadKnowledgeDetail(knowledgeId, knowledgeName = '') {
        if (detailLoading) detailLoading.style.display = 'flex';
        if (knowledgeContent) knowledgeContent.style.display = 'none';

        fetch(`/api/ui/knowledge-detail?subject=${encodeURIComponent(currentSubject)}&knowledge=${encodeURIComponent(knowledgeName || (currentKnowledgeElem ? currentKnowledgeElem.textContent : ''))}`)
        .then(response => response.json())
        .then(detail => {
            if (detailLoading) detailLoading.style.display = 'none';
            if (knowledgeContent) knowledgeContent.style.display = 'block';
            document.getElementById('knowledge-difficulty').textContent = detail.difficulty || '中等';
            document.getElementById('knowledge-importance').textContent = detail.importance || '重点';
            document.getElementById('knowledge-frequency').textContent = detail.frequency || '核心知识点';

            document.getElementById('concept-explanation').innerHTML = `<p>${detail.concept_explanation || ''}</p>`;
            document.getElementById('formula-derivation').innerHTML = `<p>${detail.formula_derivation || ''}</p>`;
            document.getElementById('application-scenarios').innerHTML = `<p>${detail.application_scenarios || ''}</p>`;

            document.getElementById('examples-content').innerHTML = (detail.examples || []).map((example, index) => `
                <div class="example-item">
                    <div class="example-header">
                        <h4>例题${index + 1}: ${example.title}</h4>
                        <span class="example-difficulty ${example.difficulty === '基础' ? 'easy' : example.difficulty === '中等' ? 'medium' : 'hard'}">${example.difficulty}</span>
                    </div>
                    <div class="example-body">
                        <p class="example-question">${example.question}</p>
                        <div class="example-analysis">
                            <h5>解析</h5>
                            <p>${example.analysis}</p>
                        </div>
                    </div>
                </div>
            `).join('');

            loadExerciseSamples(detail.exercises || []);

            document.getElementById('videos-content').innerHTML = (detail.videos || []).map((video) => `
                <div class="video-item">
                    <div class="video-thumbnail">
                        <img src="../images/生成卡通形象.png" alt="视频缩略图">
                        <div class="play-button"></div>
                    </div>
                    <div class="video-info">
                        <h4>${video.title}</h4>
                        <p>${video.description}</p>
                        <div class="video-meta">
                            <span class="video-duration">${video.duration}</span>
                            <span class="video-views">${video.views}</span>
                        </div>
                    </div>
                </div>
            `).join('');

            updateAIRecommendations(detail);
        })
        .catch(error => {
            console.error('加载知识点详情失败:', error);
            if (detailLoading) detailLoading.style.display = 'none';
            if (knowledgeContent) knowledgeContent.style.display = 'block';
            knowledgeContent.innerHTML = '<p class="no-data">知识点详情加载失败，请刷新重试。</p>';
        });
    }
    
    // 加载习题示例
    function loadExerciseSamples(exerciseSamples) {
        const exercisesList = document.getElementById('exercises-list');
        if (!exercisesList) return;
        
        exercisesList.innerHTML = '';
        
        exerciseSamples.forEach((exercise, index) => {
            const exerciseItem = document.createElement('div');
            exerciseItem.className = `exercise-item ${exercise.difficulty}`;
            
            let optionsHtml = '';
            if (exercise.type === 'choice') {
                optionsHtml = `
                    <div class="exercise-options">
                        ${exercise.options.map((option, i) => 
                            `<div class="exercise-option">
                                <input type="radio" name="exercise-${index}" id="option-${index}-${i}">
                                <label for="option-${index}-${i}">${option}</label>
                            </div>`
                        ).join('')}
                    </div>
                `;
            }
            
            exerciseItem.innerHTML = `
                <div class="exercise-header">
                    <span class="exercise-number">习题 ${index + 1}</span>
                    <span class="exercise-type">${exercise.type === 'choice' ? '选择题' : exercise.type === 'fill' ? '填空题' : '计算题'}</span>
                    <span class="exercise-difficulty ${exercise.difficulty}">
                        ${exercise.difficulty === 'easy' ? '基础' : 
                          exercise.difficulty === 'medium' ? '中等' : '困难'}
                    </span>
                </div>
                <div class="exercise-content">
                    <p class="exercise-question">${exercise.question}</p>
                    ${optionsHtml}
                    ${exercise.type === 'fill' ? 
                        `<div class="exercise-fill">
                            <input type="text" placeholder="请输入答案">
                        </div>` : ''
                    }
                    ${exercise.type === 'calculation' ? 
                        `<div class="exercise-calculation">
                            <textarea placeholder="请输入计算过程和结果"></textarea>
                        </div>` : ''
                    }
                </div>
                <div class="exercise-footer">
                    <button class="check-answer-btn">查看答案</button>
                    <div class="exercise-analysis" style="display: none;">
                        <h4>答案与解析</h4>
                        <p class="answer"><strong>答案：</strong>${exercise.answer}</p>
                        <p class="analysis"><strong>解析：</strong>${exercise.analysis}</p>
                    </div>
                </div>
            `;
            
            exercisesList.appendChild(exerciseItem);
            
            // 添加查看答案按钮事件
            const checkAnswerBtn = exerciseItem.querySelector('.check-answer-btn');
            const analysisDiv = exerciseItem.querySelector('.exercise-analysis');
            
            checkAnswerBtn.addEventListener('click', function() {
                if (analysisDiv.style.display === 'none') {
                    analysisDiv.style.display = 'block';
                    this.textContent = '隐藏答案';
                } else {
                    analysisDiv.style.display = 'none';
                    this.textContent = '查看答案';
                }
            });
        });
                    }
                    
                    // 更新AI推荐
    function updateAIRecommendations(detail) {
        const aiRecommendation = document.getElementById('ai-recommendation');
        const aiRecCards = document.getElementById('ai-rec-cards');
        
        if (aiRecommendation) {
            aiRecommendation.innerHTML = detail.ai_recommendation
                ? `根据当前学习记录，AI 推荐你重点关注"<span class="highlight">${currentKnowledgeElem ? currentKnowledgeElem.textContent : ''}</span>"：${detail.ai_recommendation}`
                : `根据当前学习数据，建议重点关注"<span class="highlight">${currentKnowledgeElem ? currentKnowledgeElem.textContent : ''}</span>"中的关键概念和应用场景。`;
        }
        
        if (aiRecCards) {
            aiRecCards.innerHTML = (detail.ai_recommend_cards || []).map(card => `
                <div class="ai-rec-card">
                    <div class="ai-rec-icon exercise-icon"></div>
                    <div class="ai-rec-info">
                        <h4>${card.title}</h4>
                        <p>${card.description}</p>
                    </div>
                </div>
            `).join('');
        }
        
        // 添加解释按钮事件
        const explainBtn = document.getElementById('ai-explain-btn');
        if (explainBtn) {
            explainBtn.addEventListener('click', function() {
                alert(`AI推荐解释：\n\n当前推荐结合了知识点内容、已有题目覆盖和学生近期学习表现，旨在帮助你更高效地掌握"${currentKnowledgeElem ? currentKnowledgeElem.textContent : ''}"。`);
            });
        }
        
        // 添加刷新按钮事件
        const refreshBtn = document.getElementById('refresh-rec-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', function() {
                loadKnowledgeDetail(currentKnowledgeId, currentKnowledgeElem ? currentKnowledgeElem.textContent : '');
            });
        }
    }
    
    // 初始化标签页切换
    function initTabSwitching() {
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabButtons.forEach(button => {
        button.addEventListener('click', function() {
            // 移除所有活动状态
            tabButtons.forEach(btn => btn.classList.remove('active'));
            tabContents.forEach(content => content.classList.remove('active'));
            
                // 添加当前活动状态
            this.classList.add('active');
                const tabId = this.getAttribute('data-tab');
                document.getElementById(`${tabId}-content`).classList.add('active');
            });
        });
    }
    
    // 搜索知识点
    function searchKnowledgePoints() {
        const searchTerm = searchInput.value.toLowerCase();
        const knowledgeItems = document.querySelectorAll('.knowledge-item');
        
        knowledgeItems.forEach(item => {
            const title = item.querySelector('.knowledge-title').textContent.toLowerCase();
            
            if (title.includes(searchTerm) || searchTerm === '') {
                item.style.display = 'flex';
            } else {
                item.style.display = 'none';
            }
        });
    }
});
