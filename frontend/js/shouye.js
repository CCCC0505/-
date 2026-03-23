const homeState = {
    studentId: null,
    studentName: '',
    workbench: null,
    coldStartSession: null,
    coldStartDraft: {
        questionnaire: {},
        diagnostic: {},
        diagnosticPage: 0
    }
};

document.addEventListener('DOMContentLoaded', async () => {
    document.body.classList.add('loaded');
    injectHomeStyles();
    bindHomeNavigation();
    bindAvatarInteractions();
    if (document.querySelector('.welcome-section')) {
        bindHomeCards();
        bindSubjectButtons();
        animateHomeEntrance();
        await initializeHomeData();
    }
});

async function initializeHomeData() {
    try {
        const context = await fetchContext();
        homeState.studentId = context.current_student.student_id;
        homeState.studentName = context.current_student.name;
        try {
            homeState.workbench = await fetchWorkbench(homeState.studentId);
        } catch (_) {
            homeState.workbench = null;
        }
        injectPortraitLaunchPanel();
        updateHomeStats();
        updateHomeCards();
    } catch (error) {
        console.error('首页初始化失败:', error);
        injectPortraitLaunchPanel(error.message || '初始化失败');
    }
}

async function fetchContext() {
    const response = await fetch('/api/ui/context');
    const payload = await response.json();
    if (!response.ok) {
        throw new Error(payload.detail || '无法获取当前学生信息');
    }
    if (payload.current_student?.student_id) {
        window.localStorage.setItem('current_student_id', payload.current_student.student_id);
    }
    return payload;
}

async function fetchWorkbench(studentId) {
    const response = await fetch(`/api/students/${studentId}/workbench`);
    const payload = await response.json();
    if (!response.ok) {
        throw new Error(payload.detail || '当前学生尚未建立画像');
    }
    return payload;
}

function bindHomeNavigation() {
    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach((item) => {
        item.addEventListener('click', function (event) {
            const href = this.getAttribute('href');
            if (!href || href === '#') {
                event.preventDefault();
                return;
            }
            event.preventDefault();
            navItems.forEach((node) => node.classList.remove('active'));
            this.classList.add('active');
            setTimeout(() => {
                window.location.href = href;
            }, 160);
        });
    });
}

function bindHomeCards() {
    const cards = document.querySelectorAll('.card');
    cards.forEach((card, index) => {
        card.addEventListener('mouseenter', () => {
            card.style.transform = 'translateY(-8px)';
        });
        card.addEventListener('mouseleave', () => {
            card.style.transform = '';
        });
        card.addEventListener('click', () => {
            if (index === 0) {
                openColdStartModal();
            } else if (index === 1) {
                window.location.href = 'pages/practice.html?mode=personalized';
            } else if (index === 2) {
                window.location.href = 'pages/subject.html';
            } else if (index === 3) {
                window.location.href = 'pages/analysis.html';
            }
        });
    });

    const cardButtons = document.querySelectorAll('.card-btn');
    cardButtons.forEach((button, index) => {
        button.addEventListener('click', async (event) => {
            event.stopPropagation();
            if (index === 0) {
                openColdStartModal();
                return;
            }
            if (index === 1) {
                window.location.href = 'pages/practice.html?mode=personalized';
                return;
            }
            if (index === 2) {
                window.location.href = 'pages/subject.html';
                return;
            }
            window.location.href = 'pages/analysis.html';
        });
    });
}

function bindSubjectButtons() {
    const subjectButtons = document.querySelectorAll('.subject-btn');
    subjectButtons.forEach((button) => {
        button.addEventListener('click', () => {
            const subject = button.querySelector('span:last-child')?.textContent?.trim() || '数学';
            window.location.href = `pages/subject.html?subject=${encodeURIComponent(subject)}`;
        });
    });
}

function bindAvatarInteractions() {
    const avatar = document.querySelector('.avatar');
    const bubble = document.querySelector('.chat-bubble');
    if (!avatar) return;
    avatar.addEventListener('mouseenter', () => bubble?.classList.add('chat-bubble-active'));
    avatar.addEventListener('mouseleave', () => bubble?.classList.remove('chat-bubble-active'));
    avatar.addEventListener('click', () => {
        showNotification('AI助手已就绪', '你可以直接在左侧面板和我对话，也可以先做一次画像冷启动。', 'assistant');
    });
}

function animateHomeEntrance() {
    const targets = document.querySelectorAll('.welcome-section, .card, .subject-btn, .stats-card');
    targets.forEach((el, index) => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(18px)';
        setTimeout(() => {
            el.style.transition = 'opacity .45s ease, transform .45s ease';
            el.style.opacity = '1';
            el.style.transform = 'translateY(0)';
        }, 50 + index * 30);
    });
}

function injectPortraitLaunchPanel(errorMessage = '') {
    const oldPanel = document.querySelector('.portrait-home-panel');
    oldPanel?.remove();
    const welcomeSection = document.querySelector('.welcome-section');
    if (!welcomeSection || !welcomeSection.parentNode) return;

    const isDemo = (homeState.studentName || '').includes('演示学生') || (homeState.studentName || '').includes('默认');
    const portrait = homeState.workbench?.latest_snapshot;
    const aiRun = homeState.workbench?.latest_ai_run;
    const panel = document.createElement('div');
    panel.className = 'portrait-home-panel';
    panel.innerHTML = `
        <div class="portrait-home-main">
            <div class="portrait-home-meta">画像冷启动</div>
            <h3>${portrait ? `当前画像：${portrait.summary_card?.headline || portrait.portrait_summary}` : '当前还没有你自己的成长画像'}</h3>
            <p>${portrait
                ? `当前学生：${homeState.workbench.student_name}，版本 V${portrait.version_number}。训练重点：${(portrait.training_focus || []).slice(0, 3).join('、') || '暂无'}`
                : errorMessage || '先完成一次真实的冷启动建模，后续的学习分析、个人中心、个性化练习才会真正使用你的画像数据。'}</p>
            <div class="portrait-home-actions">
                <button class="portrait-primary-btn" id="open-cold-start-btn">${portrait && !isDemo ? '重新画像冷启动' : '启动画像冷启动'}</button>
                <button class="portrait-secondary-btn" id="goto-analysis-btn">${portrait ? '查看学习分析' : '查看示例分析'}</button>
            </div>
        </div>
        <div class="portrait-home-side">
            <div class="portrait-status-card">
                <span class="label">当前学生</span>
                <strong>${homeState.studentName || '未建立'}</strong>
            </div>
            <div class="portrait-status-card">
                <span class="label">AI状态</span>
                <strong>${aiRun ? `${aiRun.model_name} · ${aiRun.success ? '已参与' : aiRun.fallback_used ? '回退' : '待验证'}` : '尚未调用'}</strong>
            </div>
            <div class="portrait-status-card">
                <span class="label">画像状态</span>
                <strong>${portrait ? `已建立 V${portrait.version_number}` : '未建立'}</strong>
            </div>
        </div>
    `;
    welcomeSection.insertAdjacentElement('afterend', panel);

    document.getElementById('open-cold-start-btn')?.addEventListener('click', openColdStartModal);
    document.getElementById('goto-analysis-btn')?.addEventListener('click', () => {
        window.location.href = 'pages/analysis.html';
    });
}

function updateHomeStats() {
    const statsCards = document.querySelectorAll('.stats-card');
    if (!statsCards.length) return;
    if (!homeState.workbench) {
        statsCards[0].querySelector('.stats-number').textContent = '0';
        statsCards[1].querySelector('.stats-number').textContent = '0';
        statsCards[2].querySelector('.stats-number').innerHTML = `0<span class="stats-unit">小时</span>`;
        return;
    }
    const workbench = homeState.workbench;
    const snapshot = workbench.latest_snapshot;
    statsCards[0].querySelector('.stats-number').textContent = `${(snapshot.knowledge_matrix || []).filter((item) => item.mastery_score >= 70).length}`;
    statsCards[1].querySelector('.stats-number').textContent = `${workbench.streak_days || 0}`;
    statsCards[2].querySelector('.stats-number').innerHTML = `${workbench.lifetime_stats?.total_study_hours || 0}<span class="stats-unit">小时</span>`;
}

function updateHomeCards() {
    const cards = document.querySelectorAll('.card');
    if (cards[0]) {
        cards[0].querySelector('h3').textContent = '画像冷启动';
        cards[0].querySelector('p').textContent = '先通过问卷和诊断题建立你的成长画像，后续的个性化练习、学习分析和个人中心都会基于这份画像运转。';
        cards[0].querySelector('.card-btn').textContent = '开始建模';
    }
    if (cards[1]) {
        cards[1].querySelector('h3').textContent = '个性化练习';
        cards[1].querySelector('p').textContent = '根据画像自动推题，先补弱项，再做巩固，最后挑战提升题，让练习真正围绕你的当前状态。';
        cards[1].querySelector('.card-btn').textContent = '开始练习';
    }
    if (cards[3] && homeState.workbench?.latest_ai_run) {
        const aiRun = homeState.workbench.latest_ai_run;
        cards[3].querySelector('h3').textContent = 'AI参与状态';
        cards[3].querySelector('p').textContent = `当前模型：${aiRun.model_name}；最近一次${aiRun.success ? '成功参与画像/训练解释' : '触发回退'}。你可以在学习分析页查看结构化 AI 输出。`;
        cards[3].querySelector('.card-btn').textContent = '查看分析';
    }
}

function openColdStartModal() {
    closeColdStartModal();
    const overlay = document.createElement('div');
    overlay.className = 'cold-start-modal-overlay';
    overlay.innerHTML = `
        <div class="cold-start-modal">
            <div class="cold-start-header">
                <div>
                    <h3>画像冷启动</h3>
                    <p>完成问卷和诊断题后，会立刻建立一份真实成长画像。</p>
                </div>
                <button class="cold-start-close" id="close-cold-start">×</button>
            </div>
            <div class="cold-start-body" id="cold-start-body">
                <div class="cold-start-intro">
                    <label>学生姓名</label>
                    <input id="cold-start-name" type="text" placeholder="请输入学生姓名" value="">
                    <p>当前版本默认建立“初二数学”画像，完成后会自动更新学习分析、个人中心和个性化练习。</p>
                    <button class="portrait-primary-btn" id="start-cold-start-flow">开始填写问卷与诊断</button>
                </div>
            </div>
        </div>
    `;
    document.body.appendChild(overlay);
    document.getElementById('close-cold-start')?.addEventListener('click', closeColdStartModal);
    overlay.addEventListener('click', (event) => {
        if (event.target === overlay) closeColdStartModal();
    });
    document.getElementById('start-cold-start-flow')?.addEventListener('click', startColdStartFlow);
}

function closeColdStartModal() {
    document.querySelector('.cold-start-modal-overlay')?.remove();
}

async function startColdStartFlow() {
    const nameInput = document.getElementById('cold-start-name');
    const studentName = nameInput?.value?.trim();
    if (!studentName) {
        showNotification('提示', '请先输入学生姓名。', 'info');
        return;
    }
    const body = document.getElementById('cold-start-body');
    if (!body) return;
    body.innerHTML = `<div class="cold-start-loading">正在加载问卷与诊断题...</div>`;
    try {
        const response = await fetch('/api/cold-start/sessions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: studentName, grade: 'grade_8' })
        });
        const payload = await response.json();
        if (!response.ok) {
            throw new Error(payload.detail || '无法创建画像冷启动会话');
        }
        homeState.coldStartSession = payload;
        homeState.coldStartDraft = {
            questionnaire: {},
            diagnostic: {},
            diagnosticPage: 0
        };
        renderColdStartWizard();
    } catch (error) {
        body.innerHTML = `<div class="cold-start-loading">${error.message || '加载失败'}</div>`;
    }
}

function renderColdStartWizard() {
    const session = homeState.coldStartSession;
    const body = document.getElementById('cold-start-body');
    if (!body || !session) return;
    const page = homeState.coldStartDraft.diagnosticPage || 0;
    const perPage = 3;
    const start = page * perPage;
    const currentQuestions = (session.diagnostic_questions || []).slice(start, start + perPage);
    const totalPages = Math.ceil((session.diagnostic_questions || []).length / perPage);
    const answeredCount = Object.keys(homeState.coldStartDraft.diagnostic || {}).length;
    const questionnaireHtml = (session.questionnaire_questions || []).map((question) => `
        <div class="cold-question-block">
            <h4>${question.title}</h4>
            <p>${question.prompt}</p>
            <select data-question-code="${question.code}" class="cold-questionnaire-select">
                <option value="">请选择</option>
                ${question.options.map((option) => `
                    <option value="${option.value}" ${homeState.coldStartDraft.questionnaire[question.code] === option.value ? 'selected' : ''}>${option.label}</option>
                `).join('')}
            </select>
        </div>
    `).join('');
    const diagnosticHtml = currentQuestions.map((question, index) => `
        <div class="cold-question-block">
            <h4>${start + index + 1}. ${question.title}</h4>
            <p>${question.stem}</p>
            <div class="cold-options">
                ${(question.options || []).map((option) => `
                    <label class="cold-option">
                        <input type="radio" name="diag-${question.question_id}" value="${option.label}" ${homeState.coldStartDraft.diagnostic[question.question_id] === option.label ? 'checked' : ''}>
                        <span>${option.label}. ${option.value}</span>
                    </label>
                `).join('')}
            </div>
        </div>
    `).join('');
    body.innerHTML = `
        <div class="cold-start-form">
            <div class="cold-stepper">
                <div class="cold-step active">1. 学生信息</div>
                <div class="cold-step active">2. 学习问卷</div>
                <div class="cold-step active">3. 诊断题第 ${page + 1}/${totalPages} 组</div>
                <div class="cold-step">4. 生成画像</div>
            </div>
            <div class="cold-start-section">
                <h3>第一步：学习习惯问卷</h3>
                ${questionnaireHtml}
            </div>
            <div class="cold-start-section">
                <h3>第二步：诊断题（每次 3 题）</h3>
                <p class="cold-step-desc">当前是第 ${page + 1} / ${totalPages} 组，已完成 ${answeredCount} / ${(session.diagnostic_questions || []).length} 题。</p>
                ${diagnosticHtml}
            </div>
            <div class="cold-start-submit">
                <div class="cold-step-actions">
                    <button class="portrait-secondary-btn" id="cold-prev-page" ${page === 0 ? 'disabled' : ''}>上一组</button>
                    ${page < totalPages - 1
                        ? '<button class="portrait-primary-btn" id="cold-next-page">下一组</button>'
                        : '<button class="portrait-primary-btn" id="submit-cold-start">提交并生成画像</button>'}
                </div>
            </div>
        </div>
    `;
    document.getElementById('cold-prev-page')?.addEventListener('click', () => {
        persistColdStartDraft(currentQuestions);
        homeState.coldStartDraft.diagnosticPage = Math.max(0, homeState.coldStartDraft.diagnosticPage - 1);
        renderColdStartWizard();
    });
    document.getElementById('cold-next-page')?.addEventListener('click', () => {
        persistColdStartDraft(currentQuestions);
        if (!isQuestionnaireComplete() || !isDiagnosticPageComplete(currentQuestions)) {
            showNotification('提示', '请先完成当前页问卷和诊断题。', 'info');
            return;
        }
        homeState.coldStartDraft.diagnosticPage += 1;
        renderColdStartWizard();
    });
    document.getElementById('submit-cold-start')?.addEventListener('click', () => finalizeColdStartFromHome(currentQuestions));
}

function persistColdStartDraft(currentQuestions) {
    document.querySelectorAll('.cold-questionnaire-select').forEach((node) => {
        homeState.coldStartDraft.questionnaire[node.dataset.questionCode] = node.value;
    });
    (currentQuestions || []).forEach((question) => {
        const checked = document.querySelector(`input[name="diag-${question.question_id}"]:checked`);
        if (checked) {
            homeState.coldStartDraft.diagnostic[question.question_id] = checked.value;
        }
    });
}

function isQuestionnaireComplete() {
    const required = homeState.coldStartSession?.questionnaire_questions || [];
    return required.every((question) => homeState.coldStartDraft.questionnaire[question.code]);
}

function isDiagnosticPageComplete(currentQuestions) {
    return (currentQuestions || []).every((question) => homeState.coldStartDraft.diagnostic[question.question_id]);
}

async function finalizeColdStartFromHome(currentQuestions) {
    const session = homeState.coldStartSession;
    if (!session) return;
    persistColdStartDraft(currentQuestions);
    const questionnaireAnswers = (session.questionnaire_questions || []).map((question) => ({
        question_code: question.code,
        answer_value: homeState.coldStartDraft.questionnaire[question.code] || ''
    }));
    if (questionnaireAnswers.some((item) => !item.answer_value)) {
        showNotification('提示', '请完整填写 6 个问卷题。', 'info');
        return;
    }
    const diagnosticAnswers = (session.diagnostic_questions || []).map((question) => {
        return {
            question_id: question.question_id,
            answer_text: homeState.coldStartDraft.diagnostic[question.question_id] || '',
            duration_seconds: question.target_duration_seconds
        };
    });
    if (diagnosticAnswers.some((item) => !item.answer_text)) {
        showNotification('提示', '请完整作答 24 道诊断题。', 'info');
        return;
    }

    const submitBtn = document.getElementById('submit-cold-start');
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = '画像生成中...';
    }

    try {
        const response = await fetch('/api/ui/cold-start/complete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: session.student_name,
                grade: 'grade_8',
                session_id: session.session_id,
                questionnaire_answers: questionnaireAnswers,
                diagnostic_answers: diagnosticAnswers
            })
        });
        const payload = await response.json();
        if (!response.ok) {
            throw new Error(payload.detail || '画像生成失败');
        }
        window.localStorage.setItem('current_student_id', payload.student_id);
        homeState.studentId = payload.student_id;
        homeState.studentName = payload.student_name;
        homeState.workbench = await fetchWorkbench(payload.student_id);
        closeColdStartModal();
        injectPortraitLaunchPanel();
        updateHomeStats();
        updateHomeCards();
        showNotification(
            '画像建立完成',
            `当前学生：${payload.student_name}。AI状态：${payload.ai_status.success ? 'Qwen 已参与' : payload.ai_status.fallback_used ? '当前使用规则回退' : '已完成生成'}`,
            'success'
        );
    } catch (error) {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = '提交并生成画像';
        }
        showNotification('画像建立失败', error.message || '请稍后重试', 'error');
    }
}

function showNotification(title, message, type = 'info') {
    const old = document.querySelector('.notification');
    old?.remove();
    const notification = document.createElement('div');
    notification.className = 'notification show';
    const iconClass = type === 'assistant' ? 'assistant-icon' : 'info-icon';
    notification.innerHTML = `
        <div class="notification-icon ${iconClass}"></div>
        <div class="notification-content">
            <h4>${title}</h4>
            <p>${message}</p>
        </div>
        <button class="notification-close">×</button>
    `;
    document.body.appendChild(notification);
    notification.querySelector('.notification-close')?.addEventListener('click', () => notification.remove());
    setTimeout(() => notification.remove(), 4600);
}

function injectHomeStyles() {
    const style = document.createElement('style');
    style.textContent = `
        body { opacity: 0; transition: opacity .4s ease; }
        body.loaded { opacity: 1; }
        .portrait-home-panel {
            margin: 18px 0 26px;
            background: linear-gradient(135deg, rgba(124,77,255,.12), rgba(33,150,243,.08));
            border: 1px solid rgba(124,77,255,.18);
            border-radius: 22px;
            padding: 22px 24px;
            display: grid;
            grid-template-columns: 1.8fr 1fr;
            gap: 18px;
        }
        .portrait-home-meta {
            font-size: 12px;
            letter-spacing: .08em;
            text-transform: uppercase;
            color: #7C4DFF;
            margin-bottom: 8px;
            font-weight: 700;
        }
        .portrait-home-main h3 { margin: 0 0 8px; font-size: 24px; color: #2b2b2b; }
        .portrait-home-main p { margin: 0; color: #666; line-height: 1.8; }
        .portrait-home-actions { margin-top: 16px; display: flex; gap: 12px; flex-wrap: wrap; }
        .portrait-primary-btn, .portrait-secondary-btn {
            border: none;
            border-radius: 999px;
            padding: 10px 18px;
            font-size: 14px;
            cursor: pointer;
            transition: transform .2s ease, box-shadow .2s ease;
        }
        .portrait-primary-btn {
            background: linear-gradient(90deg, #7C4DFF, #5A68FF);
            color: #fff;
            box-shadow: 0 10px 20px rgba(124,77,255,.18);
        }
        .portrait-secondary-btn {
            background: rgba(124,77,255,.08);
            color: #5C47D8;
        }
        .portrait-primary-btn:hover, .portrait-secondary-btn:hover { transform: translateY(-2px); }
        .portrait-home-side {
            display: grid;
            grid-template-columns: 1fr;
            gap: 12px;
        }
        .portrait-status-card {
            background: rgba(255,255,255,.78);
            border-radius: 16px;
            padding: 14px 16px;
            box-shadow: 0 8px 18px rgba(0,0,0,.04);
        }
        .portrait-status-card .label {
            display: block;
            font-size: 12px;
            color: #8b8b8b;
            margin-bottom: 6px;
        }
        .portrait-status-card strong { color: #2e2e2e; font-size: 15px; }
        .cold-start-modal-overlay {
            position: fixed;
            inset: 0;
            background: rgba(15, 18, 33, 0.54);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 9999;
            padding: 24px;
        }
        .cold-start-modal {
            width: min(1100px, 96vw);
            max-height: 90vh;
            overflow: hidden;
            background: #fff;
            border-radius: 24px;
            box-shadow: 0 20px 48px rgba(19, 18, 66, 0.22);
            display: flex;
            flex-direction: column;
        }
        .cold-start-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 16px;
            padding: 24px 24px 18px;
            border-bottom: 1px solid rgba(0,0,0,.06);
        }
        .cold-start-header h3 { margin: 0 0 6px; font-size: 24px; }
        .cold-start-header p { margin: 0; color: #666; }
        .cold-start-close {
            background: transparent;
            border: none;
            font-size: 28px;
            cursor: pointer;
            color: #888;
        }
        .cold-start-body { padding: 20px 24px 24px; overflow: auto; }
        .cold-start-intro input {
            width: 100%;
            border: 1px solid rgba(0,0,0,.12);
            border-radius: 12px;
            padding: 12px 14px;
            font-size: 14px;
            margin: 8px 0 14px;
        }
        .cold-start-loading {
            min-height: 240px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #666;
            font-size: 16px;
        }
        .cold-start-section { margin-bottom: 26px; }
        .cold-start-section h3 { margin: 0 0 16px; font-size: 18px; }
        .cold-step-desc {
            margin: -4px 0 12px;
            color: #7b7b92;
            font-size: 13px;
        }
        .cold-question-block {
            background: #fafafe;
            border: 1px solid rgba(124,77,255,.08);
            border-radius: 16px;
            padding: 14px 16px;
            margin-bottom: 12px;
        }
        .cold-question-block h4 { margin: 0 0 8px; font-size: 15px; color: #2b2b2b; }
        .cold-question-block p { margin: 0 0 10px; color: #666; line-height: 1.7; }
        .cold-questionnaire-select {
            width: 100%;
            border: 1px solid rgba(0,0,0,.12);
            border-radius: 10px;
            padding: 10px 12px;
            background: #fff;
        }
        .cold-options { display: grid; gap: 8px; }
        .cold-option {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 10px 12px;
            border-radius: 10px;
            background: #fff;
            border: 1px solid rgba(0,0,0,.08);
            cursor: pointer;
        }
        .cold-start-submit {
            position: sticky;
            bottom: 0;
            padding-top: 12px;
            background: linear-gradient(180deg, rgba(255,255,255,0), rgba(255,255,255,1) 40%);
        }
        .cold-stepper {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-bottom: 18px;
        }
        .cold-step {
            padding: 8px 12px;
            border-radius: 999px;
            background: rgba(124,77,255,.08);
            color: #7C4DFF;
            font-size: 12px;
            font-weight: 700;
        }
        .cold-step-actions {
            display: flex;
            justify-content: space-between;
            gap: 12px;
        }
        .portrait-secondary-btn[disabled] {
            opacity: .5;
            cursor: not-allowed;
        }
        .notification {
            position: fixed;
            right: 24px;
            top: 24px;
            background: rgba(255,255,255,.96);
            border-radius: 16px;
            padding: 14px 16px;
            display: flex;
            align-items: center;
            gap: 12px;
            min-width: 300px;
            max-width: 420px;
            box-shadow: 0 18px 36px rgba(19,18,66,.16);
            border-left: 4px solid #7C4DFF;
            z-index: 10000;
        }
        .notification-icon {
            width: 36px;
            height: 36px;
            border-radius: 50%;
            background: rgba(124,77,255,.08);
            flex-shrink: 0;
        }
        .notification-content h4 {
            margin: 0 0 4px;
            font-size: 15px;
            color: #333;
        }
        .notification-content p {
            margin: 0;
            font-size: 13px;
            line-height: 1.7;
            color: #666;
        }
        .notification-close {
            border: none;
            background: transparent;
            font-size: 20px;
            cursor: pointer;
            color: #999;
        }
        @media (max-width: 980px) {
            .portrait-home-panel { grid-template-columns: 1fr; }
        }
    `;
    document.head.appendChild(style);
}
