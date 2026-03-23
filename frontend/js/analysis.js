const analysisState = {
    studentId: null,
    payload: null,
    charts: {}
};

document.addEventListener('DOMContentLoaded', async () => {
    try {
        configureFilters();
        bindActions();
        analysisState.studentId = await getCurrentStudentId();
        await loadAnalysisData();
    } catch (error) {
        console.error('学习分析初始化失败:', error);
        showNotification(error.message || '学习分析初始化失败', 'error');
    }
});

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

function configureFilters() {
    const subjectSelect = document.getElementById('subject-select');
    if (subjectSelect) {
        subjectSelect.innerHTML = `
            <option value="math" selected>初二数学</option>
            <option value="portrait">成长画像</option>
        `;
    }
    const dateRange = document.getElementById('date-range');
    if (dateRange) {
        dateRange.innerHTML = `
            <option value="week">最近一周</option>
            <option value="month" selected>最近一个月</option>
            <option value="semester">本学期</option>
            <option value="year">本学年</option>
            <option value="all">全部记录</option>
        `;
    }
}

function bindActions() {
    document.getElementById('generate-report-btn')?.addEventListener('click', async () => {
        await loadAnalysisData();
        showNotification('已更新最新学习分析', 'success');
    });
    document.getElementById('subject-select')?.addEventListener('change', () => loadAnalysisData());
    document.getElementById('date-range')?.addEventListener('change', () => loadAnalysisData());
    document.getElementById('generate-plan-btn')?.addEventListener('click', () => {
        const section = document.getElementById('learning-plan-section');
        if (!section) return;
        section.style.display = 'block';
        section.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
    document.getElementById('download-report-btn')?.addEventListener('click', downloadAnalysisReport);
    document.getElementById('share-report-btn')?.addEventListener('click', shareAnalysisReport);
}

async function loadAnalysisData() {
    if (!analysisState.studentId) return;
    const range = document.getElementById('date-range')?.value || 'month';
    const response = await fetch(`/api/students/${analysisState.studentId}/analysis-dashboard?range=${encodeURIComponent(range)}`);
    const payload = await response.json();
    if (!response.ok) {
        throw new Error(payload.detail || '无法加载学习分析数据');
    }
    analysisState.payload = payload;
    renderAnalysisPage(payload);
}

function renderAnalysisPage(payload) {
    updateHeader(payload);
    renderSummaryCards(payload.summary_cards || []);
    renderCharts(payload.charts || {});
    renderWeaknesses(payload.weakness_items || []);
    renderAIReport(payload.report || {}, payload.modeling_basis || {}, payload.portrait_modeling || {});
    renderLearningPlan(payload.learning_plan || {});
}

function updateHeader(payload) {
    const title = document.querySelector('.analysis-header h1');
    if (title) title.textContent = `${payload.student_name}的成长画像分析`;
    const description = document.querySelector('.analysis-description');
    if (description) {
        description.textContent = '基于真实诊断、练习、知识点掌握和认知层级证据，持续更新学生成长画像。';
    }
}

function renderSummaryCards(cards) {
    const cardEls = document.querySelectorAll('.summary-card');
    cards.forEach((card, index) => {
        const el = cardEls[index];
        if (!el) return;
        const title = el.querySelector('.summary-info h3');
        const value = el.querySelector('.summary-data');
        const trend = el.querySelector('.trend');
        const trendText = trend?.querySelector('span');
        if (title) title.textContent = card.label;
        if (value) value.innerHTML = `${card.value}<span>${card.unit || ''}</span>`;
        if (trend) {
            if (typeof card.trend === 'number') {
                const positive = card.trend >= 0;
                trend.style.visibility = 'visible';
                trend.classList.remove('up', 'down');
                trend.classList.add(positive ? 'up' : 'down');
                if (trendText) trendText.textContent = `${positive ? '+' : ''}${card.trend}`;
            } else {
                trend.style.visibility = 'hidden';
            }
        }
    });
}

function renderCharts(charts) {
    renderProgressChart(charts.progress || { labels: [], current: [], target: [] });
    renderAccuracyChart(charts.accuracy || { labels: [], values: [] });
    renderMasteryChart(charts.mastery || { labels: [], actual: [], target: [] });
    renderTimeDistributionChart(charts.time_distribution || { labels: [], values: [] });
}

function renderProgressChart(data) {
    const canvas = document.getElementById('progressChart');
    if (!canvas || typeof Chart === 'undefined') return;
    destroyChart('progress');
    analysisState.charts.progress = new Chart(canvas.getContext('2d'), {
        type: 'line',
        data: {
            labels: data.labels,
            datasets: [
                {
                    label: '当前进度',
                    data: data.current,
                    backgroundColor: 'rgba(124, 77, 255, 0.16)',
                    borderColor: 'rgba(124, 77, 255, 0.92)',
                    tension: 0.35,
                    fill: true
                },
                {
                    label: '目标进度',
                    data: data.target,
                    borderColor: 'rgba(255, 152, 0, 0.8)',
                    borderDash: [6, 4],
                    tension: 0.35,
                    fill: false
                }
            ]
        },
        options: chartOptions(100)
    });
}

function renderAccuracyChart(data) {
    const canvas = document.getElementById('accuracyChart');
    if (!canvas || typeof Chart === 'undefined') return;
    destroyChart('accuracy');
    analysisState.charts.accuracy = new Chart(canvas.getContext('2d'), {
        type: 'bar',
        data: {
            labels: data.labels,
            datasets: [
                {
                    label: '正确率',
                    data: data.values,
                    backgroundColor: 'rgba(61, 90, 254, 0.75)',
                    borderRadius: 8
                }
            ]
        },
        options: chartOptions(100)
    });
}

function renderMasteryChart(data) {
    const canvas = document.getElementById('masteryChart');
    if (!canvas || typeof Chart === 'undefined') return;
    destroyChart('mastery');
    analysisState.charts.mastery = new Chart(canvas.getContext('2d'), {
        type: 'radar',
        data: {
            labels: data.labels,
            datasets: [
                {
                    label: '当前画像',
                    data: data.actual,
                    backgroundColor: 'rgba(124, 77, 255, 0.18)',
                    borderColor: 'rgba(124, 77, 255, 0.92)',
                    pointBackgroundColor: 'rgba(124, 77, 255, 1)'
                },
                {
                    label: '目标线',
                    data: data.target,
                    backgroundColor: 'rgba(76, 175, 80, 0.08)',
                    borderColor: 'rgba(76, 175, 80, 0.8)',
                    borderDash: [6, 4],
                    pointBackgroundColor: 'rgba(76, 175, 80, 1)'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                r: {
                    min: 0,
                    max: 100,
                    ticks: { display: false },
                    grid: { color: 'rgba(200,200,200,0.2)' }
                }
            }
        }
    });
}

function renderTimeDistributionChart(data) {
    const canvas = document.getElementById('timeDistributionChart');
    if (!canvas || typeof Chart === 'undefined') return;
    destroyChart('time');
    analysisState.charts.time = new Chart(canvas.getContext('2d'), {
        type: 'pie',
        data: {
            labels: data.labels,
            datasets: [
                {
                    data: data.values,
                    backgroundColor: [
                        'rgba(124,77,255,0.85)',
                        'rgba(76,175,80,0.85)',
                        'rgba(3,169,244,0.85)',
                        'rgba(255,152,0,0.85)',
                        'rgba(233,30,99,0.85)'
                    ]
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'right' }
            }
        }
    });
}

function chartOptions(maxValue) {
    return {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: { display: false },
            tooltip: { mode: 'index', intersect: false }
        },
        scales: {
            y: {
                beginAtZero: true,
                max: maxValue,
                ticks: {
                    callback(value) {
                        return `${value}%`;
                    }
                }
            }
        }
    };
}

function destroyChart(key) {
    if (analysisState.charts[key]) {
        analysisState.charts[key].destroy();
    }
}

function renderWeaknesses(items) {
    const container = document.querySelector('.weakness-list');
    if (!container) return;
    container.innerHTML = items.map((item) => `
        <div class="weakness-item">
            <div class="weakness-header">
                <div class="weakness-name">
                    <h4>${item.knowledge_tag}</h4>
                    <span class="weakness-subject">数学</span>
                </div>
                <div class="weakness-stats">
                    <div class="accuracy-bar">
                        <div class="accuracy-fill" style="width: ${item.accuracy}%;">${item.accuracy}%</div>
                    </div>
                </div>
            </div>
            <div class="weakness-detail">
                <p>${item.description}</p>
                <div class="weakness-actions">
                    <a href="${item.review_url}" class="action-link">复习知识点</a>
                    <a href="${item.practice_url}" class="action-link">专项练习</a>
                </div>
            </div>
        </div>
    `).join('');
}

function renderAIReport(report, modelingBasis, portraitModeling) {
    const container = document.querySelector('.ai-report-content');
    if (!container) return;
    const strengthItems = (report.strengths || []).map((item) => `<li><strong>${item.title}</strong>：${item.detail}</li>`).join('');
    const improvementItems = (report.improvements || []).map((item) => `<li><strong>${item.title}</strong>：${item.detail}</li>`).join('');
    const recommendationItems = (report.recommendations || []).map((item) => `<li>${item}</li>`).join('');
    const noteItems = (modelingBasis.modeling_notes || []).map((item) => `<li>${item}</li>`).join('');
    const parameterItems = (modelingBasis.parameter_table || []).map((item) => `
        <li><strong>${item.name}</strong>：${item.value}。${item.meaning}</li>
    `).join('');
    const referenceItems = (modelingBasis.references || []).map((item) => `
        <li>
            <strong>${item.authors} (${item.year})</strong>《${item.title}》
            <br><span>${item.used_for}</span>
            <br><a href="${item.url}" target="_blank" rel="noreferrer">查看来源</a>
        </li>
    `).join('');
    const pipelineItems = (portraitModeling.algorithm_pipeline || []).map((item) => `<li><strong>${item.step}</strong>：${item.detail}</li>`).join('');
    const formulaItems = (portraitModeling.rule_formulae || []).map((item) => `<li>${item}</li>`).join('');
    const dimensionItems = (portraitModeling.ai_output_data?.dimension_insights || []).map((item) => `
        <li><strong>${item.dimension_code}</strong>：${item.diagnosis}${item.evidence?.length ? `（证据：${item.evidence.join('；')}）` : ''}</li>
    `).join('');
    const knowledgeItems = (portraitModeling.ai_output_data?.knowledge_insights || []).map((item) => `
        <li><strong>${item.knowledge_tag}</strong>：${item.diagnosis}（优先级：${item.priority}）</li>
    `).join('');
    const cognitiveItems = (portraitModeling.ai_output_data?.cognitive_insights || []).map((item) => `
        <li><strong>${item.level_code}</strong>：${item.diagnosis}</li>
    `).join('');
    const aiStatus = portraitModeling.ai_model_status || {};
    const schemaBlock = portraitModeling.ai_output_schema?.schema
        ? `<pre style="padding:14px;border-radius:14px;background:rgba(17,24,39,.92);color:#eef2ff;overflow:auto;font-size:12px;line-height:1.6;">${escapeHtml(JSON.stringify(portraitModeling.ai_output_schema.schema, null, 2))}</pre>`
        : '';
    const flowDiagram = `
        <div style="margin:18px 0 24px;padding:18px;border-radius:18px;background:rgba(124,77,255,.04);overflow:auto;">
            <svg width="880" height="170" viewBox="0 0 880 170" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="画像建模流程图">
                <defs>
                    <linearGradient id="flowBg" x1="0" x2="1">
                        <stop offset="0%" stop-color="#7c4dff"/>
                        <stop offset="100%" stop-color="#ff8a65"/>
                    </linearGradient>
                </defs>
                <rect x="20" y="34" width="150" height="74" rx="18" fill="#fff" stroke="#d7cfff"/>
                <text x="95" y="63" text-anchor="middle" font-size="16" fill="#333">诊断与问卷</text>
                <text x="95" y="88" text-anchor="middle" font-size="12" fill="#666">题目证据 + 学习特征</text>
                <rect x="210" y="34" width="170" height="74" rx="18" fill="#fff" stroke="#d7cfff"/>
                <text x="295" y="63" text-anchor="middle" font-size="16" fill="#333">规则建模层</text>
                <text x="295" y="88" text-anchor="middle" font-size="12" fill="#666">难度/认知/速度/权重</text>
                <rect x="420" y="34" width="170" height="74" rx="18" fill="#fff" stroke="#d7cfff"/>
                <text x="505" y="63" text-anchor="middle" font-size="16" fill="#333">知识与维度聚合</text>
                <text x="505" y="88" text-anchor="middle" font-size="12" fill="#666">五维画像 + 知识矩阵</text>
                <rect x="630" y="34" width="170" height="74" rx="18" fill="#fff" stroke="#d7cfff"/>
                <text x="715" y="63" text-anchor="middle" font-size="16" fill="#333">Qwen 解释层</text>
                <text x="715" y="88" text-anchor="middle" font-size="12" fill="#666">摘要/点评/训练重点</text>
                <path d="M170 71H210" stroke="url(#flowBg)" stroke-width="4" stroke-linecap="round"/>
                <path d="M380 71H420" stroke="url(#flowBg)" stroke-width="4" stroke-linecap="round"/>
                <path d="M590 71H630" stroke="url(#flowBg)" stroke-width="4" stroke-linecap="round"/>
                <rect x="235" y="120" width="350" height="32" rx="16" fill="rgba(124,77,255,.1)"/>
                <text x="410" y="141" text-anchor="middle" font-size="13" fill="#5b3db4">最终输出：版本化成长画像 / 训练建议 / 风险标记 / AI结构化诊断</text>
            </svg>
        </div>
    `;
    container.innerHTML = `
        <h3>学习情况总结</h3>
        <p>${report.summary || '当前暂无学习总结。'}</p>
        <h3>优势领域</h3>
        <ul>${strengthItems || '<li>当前暂无明确优势领域。</li>'}</ul>
        <h3>待改进领域</h3>
        <ul>${improvementItems || '<li>当前暂无待改进领域。</li>'}</ul>
        <h3>学习习惯分析</h3>
        <p>${report.habits || '当前暂无学习习惯分析。'}</p>
        <h3>个性化学习建议</h3>
        <ol>${recommendationItems || '<li>先完成当前训练批次。</li>'}</ol>
        <h3>成长画像如何建立</h3>
        ${flowDiagram}
        <ul>${pipelineItems}</ul>
        <h3>后端规则算法</h3>
        <ul>${formulaItems}</ul>
        <h3>AI 模型参与状态</h3>
        <p>模型：${aiStatus.model_name || '未配置'}；是否尝试：${aiStatus.attempted ? '是' : '否'}；是否成功：${aiStatus.success ? '是' : '否'}；是否回退：${aiStatus.fallback_used ? '是' : '否'}。</p>
        <p>${aiStatus.error_summary || '最近一次画像 AI 调用无错误。'}</p>
        <h3>规范化 AI 画像输出</h3>
        <p>当前 AI 输出已被强制规范为 portrait_ai_output_v1，不再直接把原始大模型文本塞进前端。</p>
        ${schemaBlock}
        <h4>维度诊断</h4>
        <ul>${dimensionItems || '<li>当前暂无额外维度诊断。</li>'}</ul>
        <h4>知识点诊断</h4>
        <ul>${knowledgeItems || '<li>当前暂无额外知识点诊断。</li>'}</ul>
        <h4>认知层级诊断</h4>
        <ul>${cognitiveItems || '<li>当前暂无额外认知层级诊断。</li>'}</ul>
        <h3>画像建模说明</h3>
        <p>${modelingBasis.overview || ''}</p>
        <ul>${noteItems}</ul>
        <h3>参数与指标来源</h3>
        <ul>${parameterItems}</ul>
        <h3>论文依据</h3>
        <ul>${referenceItems}</ul>
    `;
}

function renderLearningPlan(plan) {
    const container = document.querySelector('.learning-plan-container');
    if (!container) return;
    const weeksHtml = (plan.weeks || []).map((week) => `
        <div class="weekly-plan">
            <div class="plan-week">${week.week_label}</div>
            <div class="daily-plans">
                ${week.days.map((day) => `
                    <div class="daily-plan ${day.day_label === '周末' ? 'weekend' : ''}">
                        <div class="plan-day">${day.day_label}</div>
                        <div class="plan-content">
                            ${day.tasks.map((task) => `
                                <div class="plan-task">
                                    <span class="time">${task.time}</span>
                                    <span class="task">${task.task}</span>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                `).join('')}
            </div>
        </div>
    `).join('');
    container.innerHTML = `
        <div class="plan-header">
            <h3>${plan.title || '未来两周学习安排'}</h3>
            <p>${plan.subtitle || '围绕当前成长画像安排训练节奏。'}</p>
        </div>
        <div class="weekly-plans">${weeksHtml}</div>
        <div class="ai-report-actions">
            <button id="save-plan-btn" class="plan-btn">保存计划</button>
            <button id="adjust-plan-btn" class="download-btn">调整计划</button>
            <button id="calendar-sync-btn" class="share-btn">同步日历</button>
        </div>
    `;
    document.getElementById('save-plan-btn')?.addEventListener('click', () => showNotification('学习计划已保存', 'success'));
    document.getElementById('adjust-plan-btn')?.addEventListener('click', () => showNotification('后续可在训练计划页继续细化节奏', 'info'));
    document.getElementById('calendar-sync-btn')?.addEventListener('click', () => showNotification('日历同步功能预留中', 'info'));
}

function downloadAnalysisReport() {
    if (!analysisState.payload) return;
    const { report, modeling_basis: modelingBasis } = analysisState.payload;
    const lines = [
        '学习分析报告',
        '',
        `总结：${report.summary || ''}`,
        '',
        '学习建议：',
        ...(report.recommendations || []).map((item, index) => `${index + 1}. ${item}`),
        '',
        '建模说明：',
        modelingBasis.overview || '',
        '',
        '论文依据：',
        ...(modelingBasis.references || []).map((item) => `${item.authors} (${item.year}) ${item.title} ${item.url}`)
    ];
    const blob = new Blob([lines.join('\n')], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `analysis-${analysisState.payload.student_name}.txt`;
    link.click();
    URL.revokeObjectURL(url);
}

async function shareAnalysisReport() {
    if (!analysisState.payload) return;
    const text = `${analysisState.payload.student_name} 当前画像总结：${analysisState.payload.report.summary}`;
    if (navigator.share) {
        await navigator.share({ title: '学习分析报告', text });
    } else {
        await navigator.clipboard.writeText(text);
        showNotification('分析摘要已复制到剪贴板', 'success');
    }
}

function showNotification(message, type = 'success') {
    let notification = document.querySelector('.notification');
    if (!notification) {
        notification = document.createElement('div');
        notification.className = 'notification';
        document.body.appendChild(notification);
        const style = document.createElement('style');
        style.textContent = `
            .notification {
                position: fixed;
                right: 24px;
                bottom: 24px;
                padding: 12px 18px;
                border-radius: 12px;
                color: #fff;
                background: rgba(38, 50, 56, 0.9);
                opacity: 0;
                transform: translateY(12px);
                transition: all .25s ease;
                z-index: 9999;
            }
            .notification.show { opacity: 1; transform: translateY(0); }
            .notification.success { background: rgba(76, 175, 80, 0.92); }
            .notification.error { background: rgba(244, 67, 54, 0.92); }
            .notification.info { background: rgba(33, 150, 243, 0.92); }
        `;
        document.head.appendChild(style);
    }
    notification.className = `notification ${type}`;
    notification.textContent = message;
    notification.classList.add('show');
    setTimeout(() => notification.classList.remove('show'), 2600);
}

function escapeHtml(text) {
    return String(text)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
}
