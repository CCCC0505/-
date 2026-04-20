const SUBJECT_SCHOOL_TYPE = '初中';
const DEFAULT_GRADE = '初二';
const GRADE_OPTIONS = ['初一', '初二', '初三'];
const FALLBACK_SUBJECTS = [
    { name: '数学', icon: 'math-icon', available: true },
    { name: '语文', icon: 'chinese-icon', available: false },
    { name: '英语', icon: 'english-icon', available: false },
    { name: '物理', icon: 'physics-icon', available: false },
    { name: '化学', icon: 'chemistry-icon', available: false },
    { name: '生物', icon: 'biology-icon', available: false },
    { name: '历史', icon: 'history-icon', available: false },
    { name: '地理', icon: 'geography-icon', available: false },
    { name: '政治', icon: 'politics-icon', available: false }
];

document.addEventListener('DOMContentLoaded', async () => {
    const initialGrade = getInitialGrade();
    bindGradeNavigation(initialGrade);
    await loadSubjects(initialGrade);
});

function getInitialGrade() {
    const params = new URLSearchParams(window.location.search);
    const requestedGrade = params.get('grade');
    return GRADE_OPTIONS.includes(requestedGrade) ? requestedGrade : DEFAULT_GRADE;
}

function bindGradeNavigation(initialGrade) {
    document.querySelectorAll('.grade-item').forEach((item) => {
        const grade = item.dataset.grade || item.textContent.trim();
        if (grade === initialGrade) {
            item.classList.add('active');
        } else {
            item.classList.remove('active');
        }

        item.addEventListener('click', async (event) => {
            event.preventDefault();
            setActiveGrade(grade);
            updateQueryGrade(grade);
            await loadSubjects(grade);
        });
    });
}

function setActiveGrade(grade) {
    document.querySelectorAll('.grade-item').forEach((item) => {
        item.classList.toggle('active', (item.dataset.grade || item.textContent.trim()) === grade);
    });
}

function updateQueryGrade(grade) {
    const url = new URL(window.location.href);
    url.searchParams.set('grade', grade);
    window.history.replaceState({}, '', url);
}

async function loadSubjects(grade) {
    const subjectList = document.querySelector('.subject-list');
    if (!subjectList) {
        return;
    }

    updateSubjectHeading(grade);
    subjectList.innerHTML = '<div class="loading-spinner"></div>';

    try {
        const response = await fetch(`/api/ui/subjects?school_type=${encodeURIComponent(SUBJECT_SCHOOL_TYPE)}`);
        const payload = await response.json();
        const subjects = normalizeSubjects(payload.subjects);
        renderSubjects(subjectList, subjects, grade);
    } catch (error) {
        console.error('加载学科入口失败:', error);
        renderSubjects(subjectList, normalizeSubjects(FALLBACK_SUBJECTS), grade);
        showNotification('学科入口加载失败，已回退到本地默认展示。', 'error');
    }
}

function normalizeSubjects(subjects) {
    const rawSubjects = Array.isArray(subjects) && subjects.length ? subjects : FALLBACK_SUBJECTS;
    return rawSubjects
        .map((subject) => ({
            name: subject.name,
            icon: subject.icon || 'course-icon',
            available: Boolean(subject.available)
        }))
        .sort((left, right) => Number(right.available) - Number(left.available));
}

function updateSubjectHeading(grade) {
    const title = document.querySelector('.subject-list-title');
    if (title) {
        title.textContent = `${grade}学科入口`;
    }
}

function renderSubjects(container, subjects, grade) {
    container.innerHTML = '';

    subjects.forEach((subject) => {
        const card = document.createElement('div');
        card.className = `subject-item ${subject.available ? 'is-available' : 'is-locked'}`;
        card.innerHTML = `
            <div class="subject-icon ${subject.icon}"></div>
            <div class="subject-name">${subject.name}</div>
            <span class="subject-status">${subject.available ? '当前可用' : '后续开放'}</span>
            <p class="subject-summary">${subject.available ? '进入数学知识点与练习入口。' : '当前版本暂不开放该学科内容。'}</p>
        `;

        if (subject.available) {
            card.addEventListener('click', () => {
                window.location.href = `./subject-1.html?subject=${encodeURIComponent(subject.name)}&grade=${encodeURIComponent(grade)}&level=${encodeURIComponent(SUBJECT_SCHOOL_TYPE)}`;
            });
        } else {
            card.addEventListener('click', () => {
                showNotification(`${subject.name}内容后续开放`, 'info');
            });
        }

        container.appendChild(card);
    });
}

function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    document.body.appendChild(notification);

    requestAnimationFrame(() => {
        notification.classList.add('show');
    });

    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => notification.remove(), 220);
    }, 1800);
}
