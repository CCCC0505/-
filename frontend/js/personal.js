const personalState = {
    studentId: null,
    payload: null,
    charts: {}
};

document.addEventListener('DOMContentLoaded', async () => {
    try {
        bindPersonalActions();
        personalState.studentId = await getCurrentStudentId();
        await ensureChartJs();
        await loadPersonalDashboard();
    } catch (error) {
        console.error('个人中心初始化失败:', error);
        showNotification('数据加载失败', error.message || '请稍后重试', 'error');
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

function bindPersonalActions() {
    document.querySelector('.edit-profile')?.addEventListener('click', () => {
        showNotification('提示', '当前版本暂不开放资料编辑，数据以学习画像为主。', 'info');
    });
    document.querySelector('.share-profile')?.addEventListener('click', shareProfile);
    document.querySelector('.avatar-edit-icon')?.addEventListener('click', (event) => {
        event.stopPropagation();
        showNotification('提示', '头像功能暂未开放，后续会与账号系统一起接入。', 'info');
    });
    document.querySelector('.view-report-btn')?.addEventListener('click', () => {
        window.location.href = 'analysis.html';
    });
    document.querySelector('.unlock-pro-btn')?.addEventListener('click', () => {
        showNotification('提示', 'PRO 区域当前作为预留能力展示。', 'info');
    });
}

async function ensureChartJs() {
    if (typeof Chart !== 'undefined') return;
    await new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = 'https://cdn.jsdelivr.net/npm/chart.js';
        script.onload = resolve;
        script.onerror = () => reject(new Error('Chart.js 加载失败'));
        document.head.appendChild(script);
    });
}

async function loadPersonalDashboard() {
    const response = await fetch(`/api/students/${personalState.studentId}/personal-dashboard`);
    const payload = await response.json();
    if (!response.ok) {
        throw new Error(payload.detail || '无法加载个人中心数据');
    }
    personalState.payload = payload;
    renderPersonalDashboard(payload);
}

function renderPersonalDashboard(payload) {
    renderProfile(payload);
    renderStats(payload.stats || {});
    renderToday(payload.today || {});
    renderProgressBars(payload.progress_bars || []);
    renderAchievements(payload.achievements || []);
    renderAdvice(payload.advice || []);
    renderLearningReport(payload.learning_report || {});
    renderWeaknessAnalysis(payload.weakness_analysis || {});
    renderPracticeRecords(payload.practice_records || []);
}

function renderProfile(payload) {
    const userName = document.querySelector('.user-name');
    if (userName) userName.textContent = payload.student_name;
    const userDescription = document.querySelector('.user-description');
    if (userDescription) {
        const joinedDate = new Date(payload.joined_at);
        userDescription.textContent = `初二数学画像用户 | 加入时间：${joinedDate.getFullYear()}年${joinedDate.getMonth() + 1}月${joinedDate.getDate()}日`;
    }
    const tagContainer = document.querySelector('.user-tags');
    if (tagContainer) {
        tagContainer.innerHTML = (payload.profile_tags || []).map((tag) => `<span class="tag">${tag}</span>`).join('');
    }
}

function renderStats(stats) {
    updateStatCard(0, stats.total_study_hours, '小时');
    updateStatCard(1, stats.study_days, '天');
    updateStatCard(2, stats.continuous_study, '天');
    updateStatCard(3, stats.achievements_count, '个');
}

function updateStatCard(index, value, unit) {
    const node = document.querySelector(`.stat-card:nth-child(${index + 1}) .stat-data p`);
    if (node) node.innerHTML = `${value ?? 0}<span>${unit}</span>`;
}

function renderToday(today) {
    const progressEl = document.querySelector('.circle-progress');
    if (progressEl) {
        const completion = today.completion || 0;
        progressEl.setAttribute('data-progress', completion);
        progressEl.style.setProperty('--progress', completion);
        progressEl.querySelector('.progress-value').textContent = `${completion}%`;
        const progressBar = progressEl.querySelector('.progress-bar');
        if (progressBar) {
            progressBar.style.strokeDashoffset = `calc(283 - (283 * ${completion}) / 100)`;
        }
    }
    setDetail('.detail-icon.time-spent + .detail-info p', today.time_spent_text || '今日暂未开始训练');
    setDetail('.detail-icon.subjects + .detail-info p', (today.subjects || []).join('、') || '数学成长训练');
    setDetail('.detail-icon.complete-tasks + .detail-info p', today.completed_tasks || '0/0');
}

function setDetail(selector, text) {
    const node = document.querySelector(selector);
    if (node) node.textContent = text;
}

function renderProgressBars(items) {
    const progressItems = document.querySelectorAll('.subject-progress-item');
    items.forEach((item, index) => {
        const wrapper = progressItems[index];
        if (!wrapper) return;
        const title = wrapper.querySelector('.subject-info h4');
        const bar = wrapper.querySelector('.progress-bar');
        if (title) title.textContent = item.label;
        if (bar) {
            bar.style.width = `${item.value}%`;
            const text = bar.querySelector('span');
            if (text) text.textContent = `${item.value}%`;
        }
    });
}

function renderAchievements(items) {
    const container = document.querySelector('.achievements-grid');
    if (!container) return;
    container.innerHTML = items.map((item) => `
        <div class="achievement-card ${item.unlocked ? 'unlocked' : ''}">
            <div class="achievement-icon ${item.unlocked ? '' : 'locked'}">
                <svg width="40" height="40" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/>
                    <path d="M8 12L11 15L16 9" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
            </div>
            <h4>${item.title}</h4>
            <p>${item.description}</p>
        </div>
    `).join('');
}

function renderAdvice(items) {
    const adviceList = document.querySelector('.advice-list');
    if (!adviceList) return;
    adviceList.innerHTML = items.map((item) => `
        <li>
            <span class="advice-badge math">${item.badge}</span>
            <p>${item.text}</p>
        </li>
    `).join('');
}

function renderLearningReport(report) {
    const title = document.querySelector('.report-header h3');
    if (title) title.textContent = report.title || '最近7天学习报告';
    const highlightContainer = document.querySelector('.report-highlights');
    if (highlightContainer) {
        highlightContainer.innerHTML = (report.highlights || []).map((item) => `
            <div class="highlight-item">
                <div class="highlight-icon growth"></div>
                <div class="highlight-content">
                    <h4>${item.title}</h4>
                    <p>${item.detail}</p>
                </div>
            </div>
        `).join('');
    }
    renderLearningChart(report.chart || { labels: [], values: [] });
}

function renderLearningChart(data) {
    const canvas = document.getElementById('learningChart');
    if (!canvas || typeof Chart === 'undefined') return;
    destroyChart('learning');
    const ctx = canvas.getContext('2d');
    const gradient = ctx.createLinearGradient(0, 0, 0, 220);
    gradient.addColorStop(0, 'rgba(137, 104, 255, 0.8)');
    gradient.addColorStop(1, 'rgba(137, 104, 255, 0.15)');
    personalState.charts.learning = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.labels,
            datasets: [
                {
                    label: '学习时长(小时)',
                    data: data.values,
                    backgroundColor: gradient,
                    borderColor: '#8968FF',
                    borderWidth: 2,
                    pointBackgroundColor: '#6040C8',
                    pointBorderColor: '#fff',
                    pointRadius: 4,
                    tension: 0.3,
                    fill: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback(value) {
                            return `${value}h`;
                        }
                    }
                },
                x: { grid: { display: false } }
            }
        }
    });
}

function renderWeaknessAnalysis(payload) {
    const textBlock = document.querySelector('.analysis-text');
    if (textBlock) {
        textBlock.innerHTML = `
            <h4>AI深度分析结果</h4>
            <p>${payload.summary_intro || '当前暂无弱项分析。'}</p>
            <ul class="weakness-list">
                ${(payload.weaknesses || []).map((item) => `
                    <li><span class="priority ${item.priority}">${priorityLabel(item.priority)}</span> ${item.text}</li>
                `).join('')}
            </ul>
        `;
    }
    const trainingCards = document.querySelector('.training-cards');
    if (trainingCards) {
        trainingCards.innerHTML = (payload.training_cards || []).map((item) => `
            <div class="training-card">
                <div class="training-subject math">${item.subject}</div>
                <h5>${item.title}</h5>
                <p>${item.description}</p>
                <div class="training-meta">
                    <span class="training-time">${item.time}</span>
                    <span class="training-difficulty">${item.difficulty}</span>
                </div>
                <button class="start-training-btn" data-url="${item.url}">开始训练</button>
            </div>
        `).join('');
    }
    document.querySelectorAll('.start-training-btn').forEach((button) => {
        button.addEventListener('click', () => {
            window.location.href = button.dataset.url || 'practice.html';
        });
    });
    renderWeaknessRadar(payload.radar || { labels: [], values: [] });
}

function renderWeaknessRadar(data) {
    const canvas = document.getElementById('weaknessRadar');
    if (!canvas || typeof Chart === 'undefined') return;
    destroyChart('radar');
    personalState.charts.radar = new Chart(canvas.getContext('2d'), {
        type: 'radar',
        data: {
            labels: data.labels,
            datasets: [
                {
                    label: '能力水平',
                    data: data.values,
                    backgroundColor: 'rgba(137, 104, 255, 0.28)',
                    borderColor: '#8968FF',
                    borderWidth: 2,
                    pointBackgroundColor: '#6040C8',
                    pointBorderColor: '#fff',
                    pointRadius: 4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                r: {
                    min: 0,
                    max: 100,
                    ticks: { display: false },
                    grid: { color: 'rgba(200,200,200,0.2)' },
                    angleLines: { color: 'rgba(200,200,200,0.2)' }
                }
            }
        }
    });
}

function renderPracticeRecords(records) {
    const filterButtons = document.querySelectorAll('.filter-btn');
    const filterMeta = [
        { label: '全部', key: 'all' },
        { label: '训练批次', key: 'plan' },
        { label: '画像更新', key: 'snapshot' },
        { label: '错题回流', key: 'wrong' }
    ];
    filterButtons.forEach((button, index) => {
        const meta = filterMeta[index];
        if (!meta) return;
        button.textContent = meta.label;
        button.dataset.filter = meta.key;
    });

    const container = document.querySelector('.records-list');
    if (!container) return;
    container.innerHTML = records.map((record) => {
        const date = new Date(record.date);
        const monthLabel = `${date.getMonth() + 1}月`;
        const scoreClass = record.score >= 85 ? 'excellent' : record.score >= 70 ? 'good' : 'needs-improvement';
        return `
            <div class="record-item" data-subject="${record.filter_key}">
                <div class="record-date">
                    <div class="record-day">${date.getDate()}</div>
                    <div class="record-month">${monthLabel}</div>
                </div>
                <div class="record-content">
                    <div class="record-title">
                        <h4>${record.title}</h4>
                        <span class="record-score ${scoreClass}">${record.score}分</span>
                    </div>
                    <div class="record-progress">
                        <div class="record-progress-bar" style="width: ${record.score}%"></div>
                    </div>
                    <div class="record-meta">
                        <span class="record-time">用时: ${record.duration_text}</span>
                        <span class="record-questions">题量: ${record.question_count}</span>
                        <span class="record-accuracy">综合表现: ${record.accuracy}%</span>
                    </div>
                </div>
                <div class="record-actions">
                    <button class="record-action-btn view">查看详情</button>
                    <button class="record-action-btn retry">继续练习</button>
                </div>
            </div>
        `;
    }).join('');

    bindRecordFilters();
    document.querySelectorAll('.record-action-btn.view').forEach((button) => {
        button.addEventListener('click', () => showNotification('提示', '当前可在学习分析页查看更完整的画像详情。', 'info'));
    });
    document.querySelectorAll('.record-action-btn.retry').forEach((button) => {
        button.addEventListener('click', () => {
            window.location.href = 'practice.html';
        });
    });
}

function bindRecordFilters() {
    const buttons = document.querySelectorAll('.filter-btn');
    const items = document.querySelectorAll('.record-item');
    buttons.forEach((button) => {
        button.addEventListener('click', () => {
            buttons.forEach((node) => node.classList.remove('active'));
            button.classList.add('active');
            const filter = button.dataset.filter;
            items.forEach((item) => {
                item.style.display = filter === 'all' || item.dataset.subject === filter ? 'flex' : 'none';
            });
        });
    });
}

async function shareProfile() {
    if (!personalState.payload) return;
    const text = `${personalState.payload.student_name} 当前画像标签：${(personalState.payload.profile_tags || []).join('、')}`;
    if (navigator.share) {
        await navigator.share({ title: '个人成长画像', text });
    } else if (navigator.clipboard) {
        await navigator.clipboard.writeText(text);
        showNotification('成功', '画像摘要已复制到剪贴板', 'success');
    }
}

function priorityLabel(priority) {
    if (priority === 'high') return '优先';
    if (priority === 'medium') return '中等';
    return '一般';
}

function destroyChart(key) {
    if (personalState.charts[key]) {
        personalState.charts[key].destroy();
    }
}

function showNotification(title, message, type = 'info') {
    let notification = document.querySelector('.notification-container');
    if (!notification) {
        notification = document.createElement('div');
        notification.className = 'notification-container';
        document.body.appendChild(notification);
        const style = document.createElement('style');
        style.textContent = `
            .notification-container {
                position: fixed;
                right: 20px;
                top: 20px;
                padding: 14px 18px;
                border-radius: 12px;
                color: #fff;
                background: rgba(38, 50, 56, 0.92);
                z-index: 9999;
                opacity: 0;
                transform: translateY(-12px);
                transition: all .25s ease;
                max-width: 360px;
                white-space: pre-wrap;
            }
            .notification-container.show { opacity: 1; transform: translateY(0); }
            .notification-container.success { background: rgba(76, 175, 80, 0.92); }
            .notification-container.error { background: rgba(244, 67, 54, 0.92); }
            .notification-container.info { background: rgba(33, 150, 243, 0.92); }
        `;
        document.head.appendChild(style);
    }
    notification.className = `notification-container ${type}`;
    notification.textContent = `${title}\n${message}`;
    notification.classList.add('show');
    setTimeout(() => notification.classList.remove('show'), 2800);
}
