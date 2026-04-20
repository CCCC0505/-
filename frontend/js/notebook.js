const notebookState = {
    studentId: '',
    records: [],
    filteredRecords: [],
    selectedTag: 'all',
    status: 'all',
    searchTerm: '',
    page: 1,
    pageSize: 8
};

document.addEventListener('DOMContentLoaded', async () => {
    bindNotebookEvents();
    await initializeNotebook();
});

async function initializeNotebook() {
    try {
        const context = await fetchContext();
        notebookState.studentId = context.current_student.student_id;
        await loadWrongQuestions();
    } catch (error) {
        renderNotebookError(error.message || '错题本加载失败，请稍后重试。');
    }
}

async function fetchContext() {
    const response = await fetch('/api/ui/context');
    const payload = await response.json();
    if (!response.ok || !payload.current_student?.student_id) {
        throw new Error(payload.detail || '无法获取当前学生信息');
    }
    return payload;
}

async function loadWrongQuestions() {
    const response = await fetch(`/api/students/${notebookState.studentId}/wrong-questions`);
    const payload = await response.json();
    if (!response.ok) {
        throw new Error(payload.detail || '无法获取错题记录');
    }

    notebookState.records = Array.isArray(payload) ? payload : [];
    notebookState.page = 1;
    renderNotebook();
}

function bindNotebookEvents() {
    document.getElementById('search-btn')?.addEventListener('click', applySearch);
    document.getElementById('search-input')?.addEventListener('keydown', (event) => {
        if (event.key === 'Enter') {
            applySearch();
        }
    });
    document.getElementById('status-filter')?.addEventListener('change', (event) => {
        notebookState.status = event.target.value;
        notebookState.page = 1;
        renderNotebook();
    });
    document.getElementById('prev-page')?.addEventListener('click', () => {
        if (notebookState.page > 1) {
            notebookState.page -= 1;
            renderMistakeList();
            renderPagination();
        }
    });
    document.getElementById('next-page')?.addEventListener('click', () => {
        const totalPages = getTotalPages();
        if (notebookState.page < totalPages) {
            notebookState.page += 1;
            renderMistakeList();
            renderPagination();
        }
    });
}

function applySearch() {
    notebookState.searchTerm = document.getElementById('search-input')?.value.trim().toLowerCase() || '';
    notebookState.page = 1;
    renderNotebook();
}

function renderNotebook() {
    updateStats();
    renderKnowledgeTags();
    applyFilters();
    renderMistakeList();
    renderPagination();
}

function updateStats() {
    const total = notebookState.records.length;
    const mastered = notebookState.records.filter((item) => item.status === 'resolved').length;
    const review = notebookState.records.filter((item) => item.status === 'open').length;

    document.getElementById('total-mistakes').textContent = total;
    document.getElementById('mastered-count').textContent = mastered;
    document.getElementById('review-count').textContent = review;
}

function renderKnowledgeTags() {
    const container = document.getElementById('knowledge-tags');
    if (!container) {
        return;
    }

    const tagCounts = new Map();
    getStatusAndSearchFilteredRecords().forEach((item) => {
        (item.knowledge_tags || []).forEach((tag) => {
            tagCounts.set(tag, (tagCounts.get(tag) || 0) + 1);
        });
    });

    const tags = Array.from(tagCounts.entries()).sort((left, right) => right[1] - left[1]);
    if (notebookState.selectedTag !== 'all' && !tagCounts.has(notebookState.selectedTag)) {
        notebookState.selectedTag = 'all';
    }
    const allCount = getStatusAndSearchFilteredRecords().length;
    container.innerHTML = [
        createTagButton('all', `全部知识点 (${allCount})`, notebookState.selectedTag === 'all'),
        ...tags.map(([tag, count]) => createTagButton(tag, `${tag} (${count})`, notebookState.selectedTag === tag))
    ].join('');

    container.querySelectorAll('.knowledge-tag').forEach((tagNode) => {
        tagNode.addEventListener('click', () => {
            notebookState.selectedTag = tagNode.dataset.tag;
            notebookState.page = 1;
            renderNotebook();
        });
    });
}

function createTagButton(tag, label, active) {
    return `<button type="button" class="knowledge-tag ${active ? 'active' : ''}" data-tag="${escapeHtml(tag)}">${escapeHtml(label)}</button>`;
}

function applyFilters() {
    notebookState.filteredRecords = getStatusAndSearchFilteredRecords().filter((item) => {
        if (notebookState.selectedTag === 'all') {
            return true;
        }
        return (item.knowledge_tags || []).includes(notebookState.selectedTag);
    });
}

function getStatusAndSearchFilteredRecords() {
    return notebookState.records.filter((item) => {
        const matchesStatus = notebookState.status === 'all' || item.status === notebookState.status;
        const haystack = [
            item.title,
            item.stem,
            item.explanation,
            item.root_cause_summary,
            item.qwen_summary,
            ...(item.knowledge_tags || [])
        ]
            .filter(Boolean)
            .join(' ')
            .toLowerCase();
        const matchesSearch = !notebookState.searchTerm || haystack.includes(notebookState.searchTerm);
        return matchesStatus && matchesSearch;
    });
}

function renderMistakeList() {
    const container = document.getElementById('mistake-list');
    if (!container) {
        return;
    }

    if (!notebookState.filteredRecords.length) {
        container.innerHTML = `
            <div class="mistake-item">
                <div class="mistake-content">
                    <div class="mistake-question">当前没有符合条件的错题记录</div>
                    <div class="mistake-answer">先去练习中心做题，答错后会自动记录到这里。</div>
                </div>
            </div>
        `;
        return;
    }

    const start = (notebookState.page - 1) * notebookState.pageSize;
    const pageItems = notebookState.filteredRecords.slice(start, start + notebookState.pageSize);
    container.innerHTML = pageItems.map(createMistakeItem).join('');

    container.querySelectorAll('[data-action-url]').forEach((button) => {
        button.addEventListener('click', () => {
            window.location.href = button.dataset.actionUrl;
        });
    });
}

function createMistakeItem(item) {
    const firstTag = item.knowledge_tags?.[0] || '一次函数';
    const actionUrl = `practice.html?subject=${encodeURIComponent('数学')}&grade=${encodeURIComponent('初二')}&level=${encodeURIComponent('初中')}&knowledge=${encodeURIComponent(firstTag)}`;
    const statusText = item.status === 'resolved' ? '已掌握' : '待复习';
    const reviewText = item.qwen_summary || item.root_cause_summary || '建议先回看解析，再做一次对应知识点练习。';

    return `
        <div class="mistake-item" data-id="${escapeHtml(item.question_id)}">
            <div class="mistake-header">
                <div class="mistake-meta">
                    <span class="mistake-subject">${statusText}</span>
                    <span class="mistake-difficulty difficulty-${escapeHtml(item.difficulty)}">${getDifficultyText(item.difficulty)}</span>
                </div>
                <span class="mistake-date">${formatDate(item.last_wrong_at)}</span>
            </div>
            <div class="mistake-content">
                <div class="mistake-question">${escapeHtml(item.title)}</div>
                <div class="mistake-answer"><strong>题目：</strong>${escapeHtml(item.stem)}</div>
                <div class="mistake-answer"><strong>解析：</strong>${escapeHtml(item.explanation || '暂无解析')}</div>
                <div class="mistake-answer"><strong>复盘建议：</strong>${escapeHtml(reviewText)}</div>
            </div>
            <div class="mistake-footer">
                <div class="mistake-tags">
                    ${(item.knowledge_tags || []).map((tag) => `<span class="mistake-tag">${escapeHtml(tag)}</span>`).join('')}
                </div>
                <div class="mistake-actions">
                    <button type="button" class="action-btn review-btn" data-action-url="${actionUrl}">
                        去练习
                    </button>
                </div>
            </div>
        </div>
    `;
}

function renderPagination() {
    const totalPages = getTotalPages();
    const prev = document.getElementById('prev-page');
    const next = document.getElementById('next-page');
    const current = document.getElementById('current-page');
    const total = document.getElementById('total-pages');
    const pagination = document.querySelector('.pagination');

    if (current) current.textContent = notebookState.filteredRecords.length ? notebookState.page : 0;
    if (total) total.textContent = notebookState.filteredRecords.length ? totalPages : 0;
    if (prev) prev.disabled = notebookState.page <= 1;
    if (next) next.disabled = notebookState.page >= totalPages;
    if (pagination) pagination.style.display = totalPages > 1 ? 'flex' : 'none';
}

function getTotalPages() {
    return Math.max(1, Math.ceil(notebookState.filteredRecords.length / notebookState.pageSize));
}

function renderNotebookError(message) {
    document.getElementById('mistake-list').innerHTML = `
        <div class="mistake-item">
            <div class="mistake-content">
                <div class="mistake-question">错题本加载失败</div>
                <div class="mistake-answer">${escapeHtml(message)}</div>
            </div>
        </div>
    `;
}

function getDifficultyText(difficulty) {
    const labels = {
        easy: '基础',
        medium: '中等',
        hard: '困难'
    };
    return labels[difficulty] || '未知';
}

function formatDate(value) {
    if (!value) {
        return '--';
    }
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
        return value;
    }
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}

function escapeHtml(value) {
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}
