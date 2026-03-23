const practiceState = {
    studentId: null,
    batchId: null,
    trainingMode: window.localStorage.getItem('practice_training_mode') || 'balanced',
    questions: [],
    currentIndex: 0,
    questionStartAt: null,
    workbench: null,
    urlContext: {
        subject: '数学',
        grade: '初二',
        knowledge: '一次函数'
    }
};

document.addEventListener('DOMContentLoaded', async () => {
    injectPracticeStyles();
    const params = new URLSearchParams(window.location.search);
    practiceState.urlContext.subject = params.get('subject') || '数学';
    practiceState.urlContext.grade = params.get('grade') || '初中二年级';
    practiceState.urlContext.knowledge = params.get('knowledge') || '一次函数';
    updatePageInfo(practiceState.urlContext.subject, practiceState.urlContext.grade, practiceState.urlContext.knowledge);
    setupEventListeners();
    await initializePracticePage();
});

async function initializePracticePage() {
    try {
        practiceState.studentId = await getCurrentStudentId();
        await loadWorkbenchSummary();
        injectPersonalizedPracticePanel();
        await loadPersonalizedBatch();
        await loadHotspotQuestions();
    } catch (error) {
        console.error('初始化练习中心失败:', error);
        injectPersonalizedPracticePanel(error.message || '请先完成首页画像冷启动');
        renderHotspotQuestions([]);
        showPageNotification(error.message || '练习中心初始化失败', 'error');
    }
}

function updatePageInfo(subject, grade, knowledge) {
    document.getElementById('practice-title').textContent = `${subject}练习中心`;
    document.getElementById('practice-description').textContent = `围绕${knowledge}或你的成长画像提供训练内容`;
    document.getElementById('current-subject').textContent = subject;
    document.getElementById('current-grade').textContent = grade;
    document.getElementById('current-knowledge').textContent = knowledge;
    const knowledgeLink = document.getElementById('knowledge-link');
    if (knowledgeLink) {
        knowledgeLink.setAttribute('href', `subject-1.html?subject=${encodeURIComponent(subject)}&grade=${encodeURIComponent(grade)}&knowledge=${encodeURIComponent(knowledge)}`);
        knowledgeLink.textContent = knowledge;
    }
}

function setupEventListeners() {
    document.getElementById('submit-answer')?.addEventListener('click', handleSubmitAnswer);
    document.getElementById('next-question')?.addEventListener('click', handleNextQuestion);
    document.querySelectorAll('.hint, [data-help="hint"]').forEach((button) => {
        button.addEventListener('click', showHint);
    });
    document.querySelector('.skip')?.addEventListener('click', handleNextQuestion);
    document.querySelectorAll('.ai-help-btn').forEach((button) => {
        button.addEventListener('click', handleAiHelp);
    });
    document.getElementById('refresh-hotspot')?.addEventListener('click', () => loadHotspotQuestions(true));
    document.addEventListener('click', (event) => {
        if (event.target && event.target.classList.contains('solve-btn')) {
            const hotspotItem = event.target.closest('.hotspot-item');
            const questionContent = hotspotItem?.querySelector('.hotspot-item-content p')?.textContent || '';
            handleHotspotSolve(questionContent);
        }
    });
    document.querySelector('.more-hotspot-btn')?.addEventListener('click', () => loadHotspotQuestions(true, 5));
}

async function getCurrentStudentId() {
    const saved = window.localStorage.getItem('current_student_id');
    if (saved) return saved;
    const response = await fetch('/api/ui/context');
    const payload = await response.json();
    if (!response.ok) {
        throw new Error(payload.detail || '无法获取当前学生上下文');
    }
    const studentId = payload.current_student.student_id;
    window.localStorage.setItem('current_student_id', studentId);
    return studentId;
}

async function loadWorkbenchSummary() {
    const response = await fetch(`/api/students/${practiceState.studentId}/workbench`);
    const payload = await response.json();
    if (!response.ok) {
        throw new Error(payload.detail || '当前学生还没有成长画像，请先完成首页画像冷启动');
    }
    practiceState.workbench = payload;
}

function injectPersonalizedPracticePanel(errorMessage = '') {
    document.querySelector('.portrait-practice-panel')?.remove();
    const header = document.querySelector('.practice-header');
    if (!header) return;
    const panel = document.createElement('div');
    panel.className = 'portrait-practice-panel';
    const latest = practiceState.workbench?.latest_snapshot;
    const recommendation = practiceState.workbench?.latest_recommendation;
    const aiRun = practiceState.workbench?.latest_ai_run;
    panel.innerHTML = `
        <div class="portrait-practice-main">
            <div class="panel-tag">个性化练习</div>
            <h3>${latest ? latest.summary_card?.headline || latest.portrait_summary : '当前还没有真实画像'}</h3>
            <p>${latest
                ? `这套题将根据你的成长画像进行推题。当前短板：${latest.summary_card?.weakness_highlight || '暂无'}；训练重点：${(latest.training_focus || []).slice(0, 3).join('、') || '暂无'}。`
                : errorMessage || '请先在首页完成画像冷启动，个性化练习才会使用你的真实画像推题。'}</p>
            <div class="personalized-mode-group">
                ${renderModeButton('balanced', '平衡训练')}
                ${renderModeButton('weakness', '刷弱项')}
                ${renderModeButton('accuracy', '稳正确率')}
                ${renderModeButton('challenge', '挑战提升')}
            </div>
            <div class="type-distribution-wrap" id="type-distribution-wrap">
                <div class="distribution-placeholder">生成题单后，这里会显示本轮题单的补弱/巩固/提升分布。</div>
            </div>
        </div>
        <div class="portrait-practice-side">
            <div class="practice-mini-card">
                <span>AI推荐状态</span>
                <strong>${recommendation?.ai_status?.success ? 'Qwen 已解释推荐' : aiRun?.success ? 'Qwen 已参与画像' : '当前可能回退到规则'}</strong>
            </div>
            <div class="practice-mini-card">
                <span>当前模式</span>
                <strong>${modeLabel(practiceState.trainingMode)}</strong>
            </div>
            <div class="practice-mini-card">
                <span>AI模型</span>
                <strong>${aiRun?.model_name || 'qwen3.5-plus'}</strong>
            </div>
        </div>
    `;
    header.insertAdjacentElement('afterend', panel);
    panel.querySelectorAll('.mode-chip').forEach((button) => {
        button.addEventListener('click', async () => {
            practiceState.trainingMode = button.dataset.mode;
            window.localStorage.setItem('practice_training_mode', practiceState.trainingMode);
            highlightModeButtons();
            await loadPersonalizedBatch();
        });
    });
    highlightModeButtons();
}

function renderModeButton(mode, label) {
    return `<button class="mode-chip ${practiceState.trainingMode === mode ? 'active' : ''}" data-mode="${mode}">${label}</button>`;
}

function highlightModeButtons() {
    document.querySelectorAll('.mode-chip').forEach((button) => {
        button.classList.toggle('active', button.dataset.mode === practiceState.trainingMode);
    });
}

async function loadPersonalizedBatch() {
    if (!practiceState.studentId) return;
    const container = document.getElementById('question-container');
    if (container) {
        container.innerHTML = `<div class="question-content"><div class="question-body"><p class="question-text">正在根据画像生成${modeLabel(practiceState.trainingMode)}题单...</p></div></div>`;
    }
    const recommendation = await fetchRecommendationBatch(practiceState.studentId, practiceState.trainingMode);
    practiceState.batchId = recommendation.batch_id;
    practiceState.questions = recommendation.items || [];
    practiceState.currentIndex = 0;
    document.getElementById('total-questions').textContent = practiceState.questions.length || 0;
    renderQuestionByIndex(practiceState.currentIndex);
    updatePersonalizedPracticePanelWithRecommendation(recommendation);
}

function updatePersonalizedPracticePanelWithRecommendation(recommendation) {
    const panel = document.querySelector('.portrait-practice-panel');
    if (!panel) return;
    const main = panel.querySelector('.portrait-practice-main p');
    if (main) {
        main.textContent = `当前模式：${recommendation.training_mode_label}。批次目标：${recommendation.batch_goal}。训练重点：${(recommendation.training_focus || []).slice(0, 3).join('、') || '暂无'}。`;
    }
    renderTypeDistribution(recommendation.type_distribution || []);
    const cards = panel.querySelectorAll('.practice-mini-card strong');
    if (cards[0]) cards[0].textContent = recommendation.ai_status?.success ? 'Qwen 已解释推荐' : recommendation.ai_status?.fallback_used ? '规则回退推荐' : '推荐已生成';
    if (cards[1]) cards[1].textContent = recommendation.training_mode_label;
    if (cards[2]) cards[2].textContent = recommendation.ai_status?.model_name || 'qwen3.5-plus';
}

function renderTypeDistribution(typeDistribution) {
    const container = document.getElementById('type-distribution-wrap');
    if (!container) return;
    const buckets = ['补弱题', '巩固题', '提升题'].map((label) => {
        const found = (typeDistribution || []).find((item) => item.label === label);
        return { label, count: found ? found.count : 0 };
    });
    const total = buckets.reduce((sum, item) => sum + item.count, 0);
    if (!total) {
        container.innerHTML = `<div class="distribution-placeholder">当前批次暂无分布数据。</div>`;
        return;
    }
    container.innerHTML = `
        <div class="distribution-header">
            <span>本轮题单结构</span>
            <strong>${total} 题</strong>
        </div>
        <div class="distribution-bar">
            ${buckets.map((item) => `
                <div class="distribution-segment ${distributionClass(item.label)}" style="width:${(item.count / total) * 100}%">
                    ${item.count ? `<span>${item.count}</span>` : ''}
                </div>
            `).join('')}
        </div>
        <div class="distribution-legend">
            ${buckets.map((item) => `
                <div class="distribution-legend-item">
                    <span class="dot ${distributionClass(item.label)}"></span>
                    <span>${item.label}</span>
                    <strong>${item.count}</strong>
                </div>
            `).join('')}
        </div>
    `;
}

function distributionClass(label) {
    if (label === '补弱题') return 'weakness';
    if (label === '提升题') return 'challenge';
    return 'solid';
}

async function fetchRecommendationBatch(studentId, trainingMode = 'balanced') {
    const response = await fetch('/api/practice/recommendations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ student_id: studentId, requested_count: 5, training_mode: trainingMode })
    });
    const payload = await response.json();
    if (!response.ok) {
        throw new Error(payload.detail || '无法获取个性化练习题目');
    }
    return payload;
}

function renderQuestionByIndex(index) {
    const question = practiceState.questions[index];
    if (!question) {
        showPageNotification('当前没有可用题目，请切换训练模式或先完成画像建立', 'info');
        return;
    }
    practiceState.questionStartAt = Date.now();
    const container = document.getElementById('question-container');
    const progressFill = document.querySelector('.progress-fill');
    document.getElementById('current-question').textContent = index + 1;
    document.getElementById('total-questions').textContent = practiceState.questions.length;
    if (progressFill) {
        progressFill.style.width = `${((index + 1) / practiceState.questions.length) * 100}%`;
    }
    container.innerHTML = `
        <div class="question-content">
            <div class="question-header">
                <div class="question-type">${question.recommendation_type} · ${modeLabel(practiceState.trainingMode)}</div>
                <div class="question-difficulty medium">难度 ${question.difficulty}</div>
            </div>
            <div class="question-body">
                <p class="question-text">${question.stem}</p>
                <div class="portrait-reason-box">
                    <strong>画像推题理由：</strong>${question.ai_reason || question.rule_reason}
                </div>
                <div class="question-options">
                    ${(question.options || []).map((option) => `
                        <div class="option">
                            <input type="radio" name="answer" id="option-${option.label.toLowerCase()}" value="${option.label}">
                            <label for="option-${option.label.toLowerCase()}">${option.label}. ${option.value}</label>
                        </div>
                    `).join('')}
                </div>
            </div>
            <div class="question-footer">
                <button class="submit-btn" id="submit-answer">提交答案</button>
            </div>
        </div>
    `;
    document.getElementById('answer-feedback').style.display = 'none';
    document.getElementById('question-container').style.display = 'block';
    document.getElementById('submit-answer')?.addEventListener('click', handleSubmitAnswer);
    loadHotspotQuestions();
}

async function handleSubmitAnswer() {
    const selectedOption = document.querySelector('input[name="answer"]:checked');
    if (!selectedOption) {
        showPageNotification('请选择一个答案', 'info');
        return;
    }
    const currentQuestion = practiceState.questions[practiceState.currentIndex];
    if (!currentQuestion || !practiceState.studentId || !practiceState.batchId) {
        showPageNotification('当前题目上下文缺失，请重新加载练习', 'error');
        return;
    }
    const durationSeconds = practiceState.questionStartAt
        ? Math.max(15, Math.round((Date.now() - practiceState.questionStartAt) / 1000))
        : currentQuestion.target_duration_seconds || 90;

    try {
        const result = await fetch('/api/practice/answers', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                student_id: practiceState.studentId,
                batch_id: practiceState.batchId,
                question_id: currentQuestion.question_id,
                answer_text: selectedOption.value,
                duration_seconds: durationSeconds
            })
        });
        const payload = await result.json();
        if (!result.ok) {
            throw new Error(payload.detail || '提交答案失败');
        }
        currentQuestion.completed = true;
        currentQuestion.last_result = payload.is_correct;
        currentQuestion.last_feedback_summary = payload.feedback_summary;
        showAnswerFeedback(payload, currentQuestion);
    } catch (error) {
        console.error('提交练习失败:', error);
        showPageNotification(error.message || '提交练习失败', 'error');
    }
}

function showAnswerFeedback(payload, currentQuestion) {
    const feedbackElement = document.getElementById('answer-feedback');
    const resultElement = feedbackElement.querySelector('.feedback-result');
    document.getElementById('question-container').style.display = 'none';
    feedbackElement.style.display = 'block';

    if (payload.is_correct) {
        resultElement.classList.add('correct');
        resultElement.classList.remove('incorrect');
        resultElement.innerHTML = `
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <circle cx="12" cy="12" r="10" fill="#4CAF50" fill-opacity="0.1" stroke="#4CAF50" stroke-width="2"/>
                <path d="M8 12L11 15L16 9" stroke="#4CAF50" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <h3>回答正确！画像已同步更新</h3>
        `;
    } else {
        resultElement.classList.add('incorrect');
        resultElement.classList.remove('correct');
        resultElement.innerHTML = `
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <circle cx="12" cy="12" r="10" fill="#f44336" fill-opacity="0.1" stroke="#f44336" stroke-width="2"/>
                <path d="M15 9L9 15" stroke="#f44336" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M9 9L15 15" stroke="#f44336" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <h3>回答错误！正确答案是: ${payload.correct_answer}</h3>
        `;
    }

    const explanation = feedbackElement.querySelector('.feedback-explanation');
    const dimensionDeltaHtml = (payload.dimension_deltas || []).slice(0, 5).map((item) => `
        <div class="delta-item ${item.delta >= 0 ? 'up' : 'down'}">
            <div class="delta-name">${item.dimension_name}</div>
            <div class="delta-score">${item.previous_score} → ${item.current_score}</div>
            <div class="delta-value">${item.delta >= 0 ? '+' : ''}${item.delta}</div>
        </div>
    `).join('');
    if (explanation) {
        explanation.innerHTML = `
            <h4>画像反馈</h4>
            <p>${payload.feedback_summary}</p>
            <p>${payload.reference_explanation || ''}</p>
            <p><strong>下一步建议：</strong>${(payload.next_steps || []).join('；')}</p>
            <p><strong>本题画像标签：</strong>${(currentQuestion.knowledge_tags || []).join('、') || '暂无'}</p>
            <div class="dimension-delta-board">
                <h5>本次作答后的画像变化</h5>
                <div class="dimension-delta-list">
                    ${dimensionDeltaHtml || '<p>当前暂无明显维度变化。</p>'}
                </div>
            </div>
        `;
    }
}

function handleNextQuestion() {
    document.getElementById('answer-feedback').style.display = 'none';
    document.getElementById('question-container').style.display = 'block';
    const nextIndex = practiceState.currentIndex + 1;
    if (nextIndex < practiceState.questions.length) {
        practiceState.currentIndex = nextIndex;
        renderQuestionByIndex(practiceState.currentIndex);
    } else {
        showPageNotification('这一轮个性化练习已经完成，可以切换训练模式继续练习。', 'success');
    }
}

function showHint() {
    const aiMessageElement = document.getElementById('ai-message');
    const currentQuestion = practiceState.questions[practiceState.currentIndex];
    aiMessageElement.style.display = 'block';
    aiMessageElement.innerHTML = `
        <p><strong>画像提示：</strong></p>
        <p>${currentQuestion?.ai_reason || currentQuestion?.rule_reason || '先回看题目中的已知条件，再判断它考查的是哪个知识点。'}</p>
    `;
}

function handleAiHelp(event) {
    const helpType = event.currentTarget.getAttribute('data-help');
    const aiMessageElement = document.getElementById('ai-message');
    const currentQuestion = practiceState.questions[practiceState.currentIndex];
    aiMessageElement.style.display = 'block';
    if (helpType === 'hint') {
        showHint();
        return;
    }
    if (helpType === 'similar') {
        aiMessageElement.innerHTML = `
            <p><strong>类似题目方向：</strong></p>
            <p>建议继续练习与“${(currentQuestion?.knowledge_tags || []).join('、') || '当前知识点'}”相关的同层级题目，再观察是否稳定答对。</p>
        `;
        return;
    }
    aiMessageElement.innerHTML = `
        <p><strong>知识点回顾：</strong></p>
        <p>${currentQuestion?.explanation || '先回顾该题对应的基础概念，再结合例题梳理解法步骤。'}</p>
    `;
}

async function loadHotspotQuestions(isRefresh = false, count = 3) {
    const hotspotSubtitle = document.querySelector('.hotspot-subtitle p');
    if (hotspotSubtitle) {
        hotspotSubtitle.textContent = isRefresh ? '正在刷新 AI 热点题目...' : '正在加载 AI 热点题目...';
    }
    const context = currentHotspotContext();
    try {
        const result = await window.aiService.generateHotspotQuestions(
            context.subject,
            context.grade,
            context.knowledge,
            count
        );
        renderHotspotQuestions(result.questions || []);
        if (hotspotSubtitle) {
            hotspotSubtitle.textContent = result.aiStatus?.message || '已生成热点题目';
        }
    } catch (error) {
        console.error('加载热点题目失败:', error);
        renderHotspotQuestions([]);
        if (hotspotSubtitle) {
            hotspotSubtitle.textContent = '热点题目加载失败';
        }
    }
}

function currentHotspotContext() {
    const currentQuestion = practiceState.questions[practiceState.currentIndex];
    if (currentQuestion) {
        return {
            subject: '数学',
            grade: '初中二年级',
            knowledge: (currentQuestion.knowledge_tags || [practiceState.urlContext.knowledge])[0] || practiceState.urlContext.knowledge
        };
    }
    return practiceState.urlContext;
}

function renderHotspotQuestions(questions) {
    const hotspotContainer = document.querySelector('.hotspot-questions');
    if (!hotspotContainer) return;
    if (!questions.length) {
        hotspotContainer.innerHTML = `
            <div class="hotspot-item">
                <div class="hotspot-item-content">
                    <p>当前暂无热点题目，稍后可点击刷新重新生成。</p>
                </div>
            </div>
        `;
        return;
    }
    hotspotContainer.innerHTML = questions.map((question) => `
        <div class="hotspot-item">
            <div class="hotspot-item-header">
                <div class="hotspot-badge">${question.badge}</div>
                <div class="hotspot-difficulty">${question.difficulty}</div>
            </div>
            <div class="hotspot-item-content">
                <p>${question.content}</p>
            </div>
            <div class="hotspot-item-footer">
                <button class="solve-btn">解答此题</button>
                <div class="hotspot-tag">${question.tag}</div>
            </div>
        </div>
    `).join('');
}

function handleHotspotSolve(questionContent) {
    const aiMessage = document.getElementById('ai-message');
    if (!aiMessage || !questionContent) return;
    aiMessage.style.display = 'block';
    aiMessage.innerHTML = `
        <div class="ai-thinking"><span></span><span></span><span></span></div>
        <p>正在分析热点题目...</p>
    `;
    const prompt = `请详细分析并解答这道题目：${questionContent}

请分成以下部分输出：
1. 题目考查什么
2. 解题思路
3. 详细步骤
4. 最终答案
5. 与当前知识点的联系`;

    window.aiService.sendMessage(prompt, (_, fullText) => {
        aiMessage.innerHTML = `<p><strong>AI热点题分析：</strong></p><p>${fullText.replace(/\n/g, '<br>')}</p>`;
    }).catch(() => {
        aiMessage.innerHTML = '<p>很抱歉，热点题分析生成失败，请稍后再试。</p>';
    });
}

function modeLabel(mode) {
    if (mode === 'weakness') return '刷弱项';
    if (mode === 'accuracy') return '稳定正确率';
    if (mode === 'challenge') return '挑战提升';
    return '平衡训练';
}

function showPageNotification(message, type = 'info') {
    if (typeof showNotification === 'function') {
        showNotification('练习中心', message, type);
    } else {
        alert(message);
    }
}

function injectPracticeStyles() {
    const style = document.createElement('style');
    style.textContent = `
        .portrait-practice-panel {
            margin: 0 0 20px;
            background: linear-gradient(135deg, rgba(124,77,255,.08), rgba(33,150,243,.06));
            border: 1px solid rgba(124,77,255,.12);
            border-radius: 18px;
            padding: 18px 20px;
            display: grid;
            grid-template-columns: 1.7fr 1fr;
            gap: 16px;
        }
        .panel-tag {
            display: inline-flex;
            padding: 4px 10px;
            border-radius: 999px;
            background: rgba(124,77,255,.12);
            color: #6a47ef;
            font-size: 12px;
            font-weight: 700;
            margin-bottom: 8px;
        }
        .portrait-practice-main h3 { margin: 0 0 8px; font-size: 22px; color: #2b2b2b; }
        .portrait-practice-main p { margin: 0; color: #666; line-height: 1.8; }
        .personalized-mode-group {
            margin-top: 14px;
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }
        .type-distribution-wrap {
            margin-top: 16px;
            padding: 14px 16px;
            border-radius: 14px;
            background: rgba(255,255,255,.72);
            border: 1px solid rgba(124,77,255,.1);
        }
        .distribution-placeholder {
            color: #8181a6;
            font-size: 13px;
            line-height: 1.7;
        }
        .distribution-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
            color: #4a4a68;
            font-size: 13px;
        }
        .distribution-header strong {
            color: #2f2f45;
            font-size: 14px;
        }
        .distribution-bar {
            display: flex;
            width: 100%;
            height: 14px;
            overflow: hidden;
            border-radius: 999px;
            background: rgba(124,77,255,.08);
        }
        .distribution-segment {
            position: relative;
            min-width: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #fff;
            font-size: 10px;
            font-weight: 700;
        }
        .distribution-segment.weakness { background: linear-gradient(90deg, #ff8a65, #ff7043); }
        .distribution-segment.solid { background: linear-gradient(90deg, #7C4DFF, #5A68FF); }
        .distribution-segment.challenge { background: linear-gradient(90deg, #26a69a, #42a5f5); }
        .distribution-legend {
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            margin-top: 12px;
        }
        .distribution-legend-item {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            color: #666;
            font-size: 12px;
        }
        .distribution-legend-item strong {
            color: #34344c;
        }
        .distribution-legend-item .dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            display: inline-block;
        }
        .distribution-legend-item .dot.weakness { background: #ff7a4f; }
        .distribution-legend-item .dot.solid { background: #6b5cff; }
        .distribution-legend-item .dot.challenge { background: #2bb7a9; }
        .mode-chip {
            border: none;
            border-radius: 999px;
            padding: 8px 12px;
            background: rgba(124,77,255,.08);
            color: #5b46d7;
            cursor: pointer;
            font-size: 13px;
        }
        .mode-chip.active {
            background: linear-gradient(90deg, #7C4DFF, #5A68FF);
            color: #fff;
            box-shadow: 0 8px 16px rgba(124,77,255,.18);
        }
        .portrait-practice-side {
            display: grid;
            gap: 10px;
        }
        .practice-mini-card {
            background: rgba(255,255,255,.82);
            border-radius: 14px;
            padding: 12px 14px;
            box-shadow: 0 8px 16px rgba(0,0,0,.04);
        }
        .practice-mini-card span {
            display: block;
            font-size: 12px;
            color: #8b8b8b;
            margin-bottom: 4px;
        }
        .practice-mini-card strong { color: #333; font-size: 14px; }
        .portrait-reason-box {
            margin: 12px 0 16px;
            padding: 12px 14px;
            background: rgba(124,77,255,.05);
            border: 1px dashed rgba(124,77,255,.18);
            border-radius: 12px;
            color: #4b4b4b;
            line-height: 1.7;
        }
        .dimension-delta-board {
            margin-top: 16px;
            padding: 14px;
            border-radius: 14px;
            background: rgba(90, 104, 255, 0.04);
            border: 1px solid rgba(90, 104, 255, 0.1);
        }
        .dimension-delta-board h5 {
            margin: 0 0 12px;
            font-size: 14px;
            color: #3949ab;
        }
        .dimension-delta-list {
            display: grid;
            gap: 8px;
        }
        .delta-item {
            display: grid;
            grid-template-columns: 1.2fr 1fr auto;
            gap: 10px;
            align-items: center;
            padding: 10px 12px;
            border-radius: 12px;
            background: rgba(255,255,255,.86);
        }
        .delta-item.up .delta-value { color: #2e7d32; font-weight: 700; }
        .delta-item.down .delta-value { color: #d84315; font-weight: 700; }
        .delta-name { color: #333; font-weight: 600; }
        .delta-score { color: #777; font-size: 13px; }
        @media (max-width: 980px) {
            .portrait-practice-panel {
                grid-template-columns: 1fr;
            }
            .delta-item {
                grid-template-columns: 1fr;
            }
        }
    `;
    document.head.appendChild(style);
}
