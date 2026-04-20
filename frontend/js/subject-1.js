const DEFAULT_SUBJECT = '数学';
const DEFAULT_SUBJECT_TITLE = '数学知识点';
const DEFAULT_LEVEL = '初中';
const DEFAULT_GRADE = '初二';
const DEFAULT_KNOWLEDGE = '一次函数';
const DEFAULT_DESCRIPTION = '围绕当前样例题库提供概念说明、例题讲解与练习入口。';
const SUBJECT_ICON_CLASSES = ['math-icon', 'chinese-icon', 'english-icon', 'physics-icon', 'chemistry-icon', 'biology-icon', 'politics-icon', 'history-icon', 'geography-icon'];
const SUBJECT_ICON_MAP = {
    数学: 'math-icon',
    语文: 'chinese-icon',
    英语: 'english-icon',
    物理: 'physics-icon',
    化学: 'chemistry-icon',
    生物: 'biology-icon',
    政治: 'politics-icon',
    历史: 'history-icon',
    地理: 'geography-icon'
};

document.addEventListener('DOMContentLoaded', () => {
    const params = new URLSearchParams(window.location.search);
    const state = {
        subject: params.get('subject') || DEFAULT_SUBJECT,
        grade: params.get('grade') || DEFAULT_GRADE,
        level: params.get('level') || DEFAULT_LEVEL,
        currentKnowledge: params.get('knowledge') || DEFAULT_KNOWLEDGE
    };

    applyPageContext(state);
    bindTabSwitching();
    bindSearch();
    bindPracticeButton(state);
    loadKnowledgePoints(state);
});

function applyPageContext(state) {
    const isMath = state.subject === DEFAULT_SUBJECT;
    const titleText = isMath ? DEFAULT_SUBJECT_TITLE : `${state.subject}知识点`;
    const description = isMath
        ? DEFAULT_DESCRIPTION
        : `当前版本聚焦初二数学，${state.subject}内容后续开放。`;

    document.title = `${titleText} - 初二数学个性化课后练习平台`;
    document.getElementById('subject-name').textContent = titleText;
    document.getElementById('current-subject').textContent = titleText;
    document.getElementById('current-grade').textContent = `${state.level}${state.grade}`;
    document.getElementById('subject-description').textContent = description;
    document.getElementById('knowledge-content').innerHTML = `<p>${description}</p>`;

    const icon = document.getElementById('subject-icon-large');
    if (icon) {
        icon.classList.remove(...SUBJECT_ICON_CLASSES);
        icon.classList.add(SUBJECT_ICON_MAP[state.subject] || 'math-icon');
    }

    document.getElementById('start-practice-text').textContent = '进入该知识点练习';
}

function bindTabSwitching() {
    const buttons = document.querySelectorAll('.tab-button');
    const contents = document.querySelectorAll('.tab-content');

    buttons.forEach((button) => {
        button.addEventListener('click', () => {
            const tabId = button.dataset.tab;
            buttons.forEach((item) => item.classList.remove('active'));
            contents.forEach((item) => item.classList.remove('active'));
            button.classList.add('active');
            document.getElementById(`${tabId}-content`)?.classList.add('active');
        });
    });
}

function bindSearch() {
    const searchInput = document.getElementById('knowledge-search-input');
    const searchButton = document.getElementById('knowledge-search-btn');
    if (!searchInput || !searchButton) {
        return;
    }

    const applyFilter = () => {
        const keyword = searchInput.value.trim().toLowerCase();
        document.querySelectorAll('.knowledge-item').forEach((item) => {
            const title = item.querySelector('.knowledge-title')?.textContent.toLowerCase() || '';
            item.style.display = !keyword || title.includes(keyword) ? 'flex' : 'none';
        });
    };

    searchInput.addEventListener('input', applyFilter);
    searchButton.addEventListener('click', applyFilter);
}

function bindPracticeButton(state) {
    const startButton = document.getElementById('start-practice-btn');
    if (!startButton) {
        return;
    }

    startButton.addEventListener('click', (event) => {
        if (startButton.classList.contains('is-disabled')) {
            event.preventDefault();
        }
    });

    updatePracticeButton(state);
}

async function loadKnowledgePoints(state) {
    const list = document.getElementById('knowledge-list');
    const loading = document.getElementById('knowledge-loading');

    if (loading) {
        loading.style.display = 'flex';
    }

    try {
        const response = await fetch(`/api/ui/knowledge-points?subject=${encodeURIComponent(state.subject)}`);
        const payload = await response.json();
        const knowledgePoints = Array.isArray(payload.knowledge_points) ? payload.knowledge_points : [];

        if (loading) {
            loading.style.display = 'none';
        }

        if (!knowledgePoints.length) {
            const emptyMessage = payload.message || `${state.subject}内容后续开放`;
            if (list) {
                list.innerHTML = `<p class="no-data">${emptyMessage}</p>`;
            }
            state.currentKnowledge = state.currentKnowledge || `${state.subject}知识点`;
            document.getElementById('current-knowledge').textContent = state.currentKnowledge;
            await loadKnowledgeDetail(state, state.currentKnowledge);
            return;
        }

        renderKnowledgeList(list, knowledgePoints, state);
        const preferred = knowledgePoints.find((item) => item.title === state.currentKnowledge) || knowledgePoints[0];
        state.currentKnowledge = preferred.title;
        highlightKnowledgeItem(preferred.id);
        document.getElementById('current-knowledge').textContent = preferred.title;
        await loadKnowledgeDetail(state, preferred.title);
    } catch (error) {
        console.error('加载知识点失败:', error);
        if (loading) {
            loading.style.display = 'none';
        }
        if (list) {
            list.innerHTML = '<p class="no-data">知识点加载失败，请刷新重试。</p>';
        }
    }
}

function renderKnowledgeList(container, knowledgePoints, state) {
    if (!container) {
        return;
    }

    container.innerHTML = '';
    knowledgePoints.forEach((point) => {
        const item = document.createElement('div');
        item.className = 'knowledge-item';
        item.dataset.id = point.id;
        item.dataset.title = point.title;
        item.innerHTML = `
            <span class="knowledge-title">${point.title}</span>
            <div class="knowledge-meta">
                <span class="difficulty ${point.difficulty === '基础' ? 'easy' : point.difficulty === '中等' ? 'medium' : 'hard'}">${point.difficulty}</span>
                <span class="importance ${point.importance === '基础' ? 'basic' : 'key'}">${point.importance}</span>
            </div>
        `;
        item.addEventListener('click', async () => {
            state.currentKnowledge = point.title;
            highlightKnowledgeItem(point.id);
            document.getElementById('current-knowledge').textContent = point.title;
            await loadKnowledgeDetail(state, point.title);
        });
        container.appendChild(item);
    });
}

function highlightKnowledgeItem(knowledgeId) {
    document.querySelectorAll('.knowledge-item').forEach((item) => {
        item.classList.toggle('active', item.dataset.id === knowledgeId);
    });
}

async function loadKnowledgeDetail(state, knowledgeName) {
    const detailLoading = document.getElementById('detail-loading');
    if (detailLoading) {
        detailLoading.style.display = 'flex';
    }

    try {
        const response = await fetch(
            `/api/ui/knowledge-detail?subject=${encodeURIComponent(state.subject)}&knowledge=${encodeURIComponent(knowledgeName)}`
        );
        const detail = await response.json();

        if (detailLoading) {
            detailLoading.style.display = 'none';
        }

        document.getElementById('current-knowledge').textContent = detail.knowledge || knowledgeName;
        document.getElementById('knowledge-difficulty').textContent = detail.difficulty || '中等';
        document.getElementById('knowledge-importance').textContent = detail.importance || '重点';
        document.getElementById('knowledge-frequency').textContent = detail.frequency || '当前样例重点';
        document.getElementById('knowledge-content').innerHTML = `<p>${detail.subject_overview || DEFAULT_DESCRIPTION}</p>`;
        document.getElementById('concept-explanation').innerHTML = `<p>${detail.concept_explanation || DEFAULT_DESCRIPTION}</p>`;
        document.getElementById('formula-derivation').innerHTML = `<p>${detail.formula_derivation || '建议先掌握定义与关键条件。'}</p>`;
        document.getElementById('application-scenarios').innerHTML = `<p>${detail.application_scenarios || '完成知识点学习后可继续进入练习。'}</p>`;

        renderExamples(detail.examples || []);
        renderExercises(detail.exercises || []);
        renderSupportResources(detail.support_resources || []);
        updateAIRecommendations(detail);

        state.currentKnowledge = detail.knowledge || knowledgeName;
        updatePracticeButton(state, detail.exercises || []);
    } catch (error) {
        console.error('加载知识点详情失败:', error);
        if (detailLoading) {
            detailLoading.style.display = 'none';
        }
        document.getElementById('knowledge-content').innerHTML = '<p class="no-data">知识点详情加载失败，请刷新重试。</p>';
    }
}

function renderExamples(examples) {
    const container = document.getElementById('examples-list');
    if (!container) {
        return;
    }

    if (!examples.length) {
        container.innerHTML = '<p class="no-data">当前知识点暂未配置例题讲解。</p>';
        return;
    }

    container.innerHTML = examples.map((example, index) => `
        <div class="example-item">
            <div class="example-header">
                <h4>例题 ${index + 1}：${example.title}</h4>
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
}

function renderExercises(exercises) {
    const container = document.getElementById('exercises-list');
    if (!container) {
        return;
    }

    if (!exercises.length) {
        container.innerHTML = '<p class="no-data">当前知识点暂无练习题，稍后开放。</p>';
        return;
    }

    container.innerHTML = '';
    exercises.forEach((exercise, index) => {
        const item = document.createElement('div');
        item.className = `exercise-item ${exercise.difficulty}`;

        const options = exercise.type === 'choice'
            ? `
                <div class="exercise-options">
                    ${(exercise.options || []).map((option, optionIndex) => `
                        <div class="exercise-option">
                            <input type="radio" name="exercise-${index}" id="option-${index}-${optionIndex}">
                            <label for="option-${index}-${optionIndex}">${option}</label>
                        </div>
                    `).join('')}
                </div>
            `
            : '';

        item.innerHTML = `
            <div class="exercise-header">
                <span class="exercise-number">练习 ${index + 1}</span>
                <span class="exercise-type">${exercise.type === 'choice' ? '选择题' : exercise.type === 'fill' ? '填空题' : '计算题'}</span>
                <span class="exercise-difficulty ${exercise.difficulty}">
                    ${exercise.difficulty === 'easy' ? '基础' : exercise.difficulty === 'medium' ? '中等' : '困难'}
                </span>
            </div>
            <div class="exercise-content">
                <p class="exercise-question">${exercise.question}</p>
                ${options}
            </div>
            <div class="exercise-footer">
                <button class="check-answer-btn" type="button">查看答案</button>
                <div class="exercise-analysis" style="display: none;">
                    <h4>答案与解析</h4>
                    <p class="answer"><strong>答案：</strong>${exercise.answer}</p>
                    <p class="analysis"><strong>解析：</strong>${exercise.analysis}</p>
                </div>
            </div>
        `;

        const button = item.querySelector('.check-answer-btn');
        const analysis = item.querySelector('.exercise-analysis');
        button?.addEventListener('click', () => {
            const expanded = analysis.style.display === 'block';
            analysis.style.display = expanded ? 'none' : 'block';
            button.textContent = expanded ? '查看答案' : '隐藏答案';
        });

        container.appendChild(item);
    });
}

function renderSupportResources(resources) {
    const container = document.getElementById('support-list');
    if (!container) {
        return;
    }

    if (!resources.length) {
        container.innerHTML = '<p class="no-data">当前暂无额外学习建议。</p>';
        return;
    }

    container.innerHTML = resources.map((resource) => `
        <div class="video-item">
            <div class="video-info">
                <h4>${resource.href ? `<a class="resource-link" href="${resource.href}">${resource.title}</a>` : resource.title}</h4>
                <p>${resource.description}</p>
                <div class="video-meta">
                    <span class="video-views">${resource.tag || '学习建议'}</span>
                </div>
            </div>
        </div>
    `).join('');
}

function updatePracticeButton(state, exercises = []) {
    const button = document.getElementById('start-practice-btn');
    if (!button) {
        return;
    }

    button.href = `practice.html?subject=${encodeURIComponent(state.subject)}&grade=${encodeURIComponent(state.grade)}&level=${encodeURIComponent(state.level)}&knowledge=${encodeURIComponent(state.currentKnowledge)}`;

    const enabled = state.subject === DEFAULT_SUBJECT && exercises.length > 0;
    button.classList.toggle('is-disabled', !enabled);
    button.setAttribute('aria-disabled', String(!enabled));
}

function updateAIRecommendations(detail) {
    const message = document.getElementById('ai-recommendation');
    const cards = document.getElementById('ai-rec-cards');

    if (message) {
        message.innerHTML = detail.ai_recommendation
            ? detail.ai_recommendation
            : `建议先完成“<span class="highlight">${DEFAULT_KNOWLEDGE}</span>”的基础练习，再进入下一轮强化。`;
    }

    if (cards) {
        const recommendations = Array.isArray(detail.ai_recommend_cards) ? detail.ai_recommend_cards : [];
        cards.innerHTML = recommendations.map((card) => `
            <div class="ai-rec-card">
                <div class="ai-rec-icon exercise-icon"></div>
                <div class="ai-rec-info">
                    <h4>${card.title}</h4>
                    <p>${card.description}</p>
                </div>
            </div>
        `).join('');
    }
}
