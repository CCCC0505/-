// 学科资料页面交互功能
document.addEventListener('DOMContentLoaded', function() {
    console.log('页面DOM加载完成，开始初始化...');
    
    // 添加诊断信息
    window.onerror = function(message, source, lineno, colno, error) {
        console.error('JavaScript错误:', message, '在', source, '第', lineno, '行');
        showNotification('加载出错，请刷新页面', 'error');
        return false;
    };
    
    // 诊断当前页面状态
    console.log('当前页面URL:', window.location.href);
    console.log('页面路径:', window.location.pathname);
    
    // 打印页面元素状态
    const subjectList = document.querySelector('.subject-list');
    if (subjectList) {
        console.log('找到学科列表容器');
    } else {
        console.error('没有找到学科列表容器!');
    }
    
    const gradeNav = document.querySelector('.grade-nav');
    if (gradeNav) {
        console.log('找到年级导航');
    } else {
        console.error('没有找到年级导航!');
    }
    
    // 初始化页面动画
    initPageAnimation();
    
    // 初始化标签页功能
    initTabs();
    
    // 初始化年级导航功能
    initGradeNavigation();
    
    // 初始化学科项目交互
    initSubjectItems();
    
    // 初始化搜索功能
    initSearchFeature();
    
    // 初始化排序功能
    initSortButtons();
    
    // 设置标签指示器初始位置
    updateTabIndicator(document.querySelector('.tab-btn.active'));
    
    // 直接加载初始数据，不使用延迟
    console.log('开始加载初始学科数据...');
    
    // 添加延迟确保DOM完全加载
    setTimeout(function() {
        updateSubjectList('小学', '一年级');
    }, 500);
});

/**
 * 根据学校类型和年级获取对应的学科列表
 * @param {string} schoolType 学校类型（小学/初中/高中）
 * @param {string} gradeText 年级文本（如"一年级"、"初一"等）
 * @returns {Array} 学科列表
 */
function getSubjectsForGrade(schoolType, gradeText) {
    console.log('获取学科数据:', schoolType, gradeText);
    return [];
}

/**
 * 创建学科元素
 * @param {Object} subject 学科信息
 * @returns {HTMLElement} 学科元素
 */
function createSubjectElement(subject) {
    console.log('创建学科元素:', subject.name);
    const subjectItem = document.createElement('div');
    subjectItem.className = 'subject-item';
    
    const iconDiv = document.createElement('div');
    iconDiv.className = `subject-icon ${subject.icon}`;
    
    const nameDiv = document.createElement('div');
    nameDiv.className = 'subject-name';
    nameDiv.textContent = subject.name;
    
    subjectItem.appendChild(iconDiv);
    subjectItem.appendChild(nameDiv);
    
    // 添加点击事件
    subjectItem.addEventListener('click', function() {
        showNotification(`进入${subject.name}学科资料`, 'success');
        
        // 获取当前选中的年级
        const activeGrade = document.querySelector('.grade-item.active span:last-child')?.textContent.trim() || '一年级';
        const schoolType = document.querySelector('.grade-item.active')?.closest('.grade-category')?.querySelector('.grade-header span:last-child')?.textContent.trim() || '小学';
        
        console.log(`跳转到学科详情页: 学科=${subject.name}, 年级=${activeGrade}, 学校类型=${schoolType}`);
        
        // 导航到学科知识点页面
        window.location.href = `./subject-1.html?subject=${encodeURIComponent(subject.name)}&grade=${encodeURIComponent(activeGrade)}&level=${encodeURIComponent(schoolType)}`;
    });
    
    return subjectItem;
}

/**
 * 初始化搜索功能
 */
function initSearchFeature() {
    const searchInput = document.querySelector('.subject-search');
    if (!searchInput) return;
    
    searchInput.addEventListener('input', function() {
        const query = this.value.trim().toLowerCase();
        const subjectItems = document.querySelectorAll('.subject-item');
        
        subjectItems.forEach(item => {
            const subjectName = item.querySelector('.subject-name').textContent.toLowerCase();
            
            if (query === '' || subjectName.includes(query)) {
                item.style.display = 'flex';
                item.classList.add('animate__animated', 'animate__fadeIn');
                setTimeout(() => {
                    item.classList.remove('animate__animated', 'animate__fadeIn');
                }, 500);
            } else {
                item.style.display = 'none';
            }
        });
        
        // 显示搜索结果数量通知
        const visibleCount = [...subjectItems].filter(item => item.style.display !== 'none').length;
        const totalCount = subjectItems.length;
        
        if (query !== '') {
            showNotification(`搜索结果: ${visibleCount}/${totalCount}`, 'info');
        }
    });
    
    // 添加搜索框焦点效果
    searchInput.addEventListener('focus', function() {
        this.parentElement.classList.add('search-active');
    });
    
    searchInput.addEventListener('blur', function() {
        this.parentElement.classList.remove('search-active');
    });
}

/**
 * 初始化排序按钮功能
 */
function initSortButtons() {
    const sortButtons = document.querySelectorAll('.sort-btn');
    if (!sortButtons.length) return;
    
    sortButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            // 更新激活状态
            sortButtons.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            
            const sortType = this.textContent.trim();
            const subjectItems = Array.from(document.querySelectorAll('.subject-item'));
            const subjectList = document.querySelector('.subject-list');
            
            if (!subjectList || !subjectItems.length) return;
            
            // 移除所有项目
            subjectItems.forEach(item => item.remove());
            
            // 根据排序类型进行排序
            let sortedItems;
            if (sortType === '按名称') {
                sortedItems = subjectItems.sort((a, b) => {
                    const nameA = a.querySelector('.subject-name').textContent;
                    const nameB = b.querySelector('.subject-name').textContent;
                    return nameA.localeCompare(nameB, 'zh-CN');
                });
            } else if (sortType === '按热度') {
                // 这里可以添加真实的热度排序逻辑
                // 暂时使用随机排序模拟
                sortedItems = subjectItems.sort(() => Math.random() - 0.5);
            } else {
                // 默认排序，保持原始顺序
                sortedItems = subjectItems;
            }
            
            // 添加排序动画效果
            sortedItems.forEach((item, index) => {
                item.style.opacity = '0';
                item.style.transform = 'translateY(20px)';
                
                setTimeout(() => {
                    subjectList.appendChild(item);
                    
                    // 动画显示排序后的项目
                    setTimeout(() => {
                        item.style.transition = 'all 0.5s cubic-bezier(0.215, 0.610, 0.355, 1.000)';
                        item.style.opacity = '1';
                        item.style.transform = 'translateY(0)';
                    }, 50);
                }, index * 50);
            });
            
            showNotification(`已按${sortType}排序`, 'success');
        });
    });
}

// 标签页功能增强
function initTabs() {
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabIndicator = document.querySelector('.tab-indicator');
    
    tabButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            // 移除所有标签的活动状态
            tabButtons.forEach(tab => tab.classList.remove('active'));
            
            // 设置当前标签为活动状态
            this.classList.add('active');
            
            // 更新标签指示器位置
            updateTabIndicator(this);
            
            // 获取当前标签文本
            const tabText = this.textContent.trim();
            
            // 过滤显示相应的学段分类
            filterGradeCategories(tabText);
            
            // 添加点击涟漪效果
            addRippleEffect(this);
        });
    });
}

/**
 * 更新标签指示器位置
 * @param {HTMLElement} activeTab 当前激活的标签
 */
function updateTabIndicator(activeTab) {
    const tabIndicator = document.querySelector('.tab-indicator');
    if (!tabIndicator || !activeTab) return;
    
    const tabRect = activeTab.getBoundingClientRect();
    const tabsRect = activeTab.parentElement.getBoundingClientRect();
    
    tabIndicator.style.left = `${tabRect.left - tabsRect.left + 10}px`;
    tabIndicator.style.width = `${tabRect.width - 20}px`;
}

/**
 * 页面加载动画增强
 */
function initPageAnimation() {
    // 为标题添加动画
    const header = document.querySelector('.subject-page-header');
    if (header) {
        header.style.opacity = '0';
        header.style.transform = 'translateY(20px)';
        
        setTimeout(() => {
            header.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
            header.style.opacity = '1';
            header.style.transform = 'translateY(0)';
        }, 100);
        
        // 添加字符动画效果
        const title = header.querySelector('h1');
        if (title) {
            const text = title.textContent;
            title.textContent = '';
            
            [...text].forEach((char, index) => {
                const span = document.createElement('span');
                span.textContent = char;
                span.style.opacity = '0';
                span.style.transform = 'translateY(20px)';
                span.style.display = 'inline-block';
                span.style.transition = `opacity 0.3s ease ${index * 0.03}s, transform 0.3s ease ${index * 0.03}s`;
                
                title.appendChild(span);
                
                setTimeout(() => {
                    span.style.opacity = '1';
                    span.style.transform = 'translateY(0)';
                }, 300 + index * 30);
            });
        }
    }
    
    // 为标签页添加动画
    const tabs = document.querySelector('.subject-tabs');
    if (tabs) {
        tabs.style.opacity = '0';
        tabs.style.transform = 'translateY(20px)';
        
        setTimeout(() => {
            tabs.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
            tabs.style.opacity = '1';
            tabs.style.transform = 'translateY(0)';
        }, 200);
    }
    
    // 为主内容区添加动画
    const content = document.querySelector('.subject-content');
    if (content) {
        content.style.opacity = '0';
        content.style.transform = 'translateY(20px)';
        
        setTimeout(() => {
            content.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
            content.style.opacity = '1';
            content.style.transform = 'translateY(0)';
        }, 300);
    }
}

// 根据标签过滤年级分类
function filterGradeCategories(tabText) {
    const gradeCategories = document.querySelectorAll('.grade-category');
    
    if (tabText === '全部') {
        // 显示所有分类
        gradeCategories.forEach(category => {
            category.style.display = 'block';
        });
    } else {
        // 根据标签文本过滤
        gradeCategories.forEach(category => {
            const categoryHeader = category.querySelector('.grade-header span:last-child').textContent.trim();
            
            if (categoryHeader === tabText) {
                category.style.display = 'block';
            } else {
                category.style.display = 'none';
            }
        });
    }
    
    // 更新右侧内容标题
    updateSubjectListTitle(tabText);
}

// 更新右侧学科列表标题
function updateSubjectListTitle(tabText) {
    const activeGradeItem = document.querySelector('.grade-item.active');
    const subjectListTitle = document.querySelector('.subject-list-title');
    
    if (activeGradeItem && subjectListTitle) {
        const gradeText = activeGradeItem.querySelector('span:last-child').textContent.trim();
        const schoolType = activeGradeItem.closest('.grade-category').querySelector('.grade-header span:last-child').textContent.trim();
        
        if (tabText === '全部' || tabText === schoolType) {
            subjectListTitle.textContent = `${schoolType}${gradeText} - 学科列表`;
        } else {
            // 找到对应学段的第一个年级
            const firstGradeInTab = document.querySelector(`.grade-category:not([style*="display: none"]) .grade-list .grade-item:first-child span:last-child`);
            if (firstGradeInTab) {
                const firstGradeText = firstGradeInTab.textContent.trim();
                subjectListTitle.textContent = `${tabText}${firstGradeText} - 学科列表`;
                
                // 更新活动状态
                document.querySelectorAll('.grade-item').forEach(item => item.classList.remove('active'));
                firstGradeInTab.closest('.grade-item').classList.add('active');
                
                // 更新学科列表
                const newSchoolType = tabText;
                updateSubjectList(newSchoolType, firstGradeText);
            }
        }
    }
}

// 年级导航功能
function initGradeNavigation() {
    const gradeItems = document.querySelectorAll('.grade-item');
    
    gradeItems.forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            
            // 移除所有年级的活动状态
            gradeItems.forEach(grade => grade.classList.remove('active'));
            
            // 设置当前年级为活动状态
            this.classList.add('active');
            
            // 获取年级信息
            const gradeText = this.querySelector('span:last-child').textContent.trim();
            const schoolType = this.closest('.grade-category').querySelector('.grade-header span:last-child').textContent.trim();
            
            // 更新学科列表
            updateSubjectList(schoolType, gradeText);
            
            // 显示通知
            showNotification(`已切换到${schoolType}${gradeText}`, 'success');
            
            // 添加点击涟漪效果
            addRippleEffect(this);
        });
    });
}

/**
 * 更新学科列表
 * @param {string} schoolType 学校类型
 * @param {string} gradeText 年级文本
 */
function updateSubjectList(schoolType, gradeText) {
    console.log('更新学科列表:', schoolType, gradeText);
    const subjectList = document.querySelector('.subject-list');
    if (!subjectList) {
        console.error('找不到学科列表容器元素');
        return;
    }
    
    // 显示加载动画
    subjectList.innerHTML = '<div class="loading-spinner"></div>';
    
    // 更新标题
    const subjectListTitle = document.querySelector('.subject-list-title');
    if (subjectListTitle) {
        subjectListTitle.textContent = `${schoolType}${gradeText} - 学科列表`;
    }
    
    fetch(`/api/ui/subjects?school_type=${encodeURIComponent(schoolType)}`)
        .then(response => response.json())
        .then(data => {
            const subjects = data.subjects || [];
            subjectList.innerHTML = '';
            if (!subjects.length) {
                subjectList.innerHTML = '<div class="no-subject-tip">暂无学科数据</div>';
                return;
            }
            subjects.forEach(subject => {
                const subjectElement = createSubjectElement(subject);
                subjectList.appendChild(subjectElement);
            });
            document.querySelectorAll('.subject-item').forEach(item => {
                item.style.opacity = '1';
                item.style.transform = 'translateY(0)';
            });
        })
        .catch(error => {
            console.error('更新学科列表时出错:', error);
            showNotification('加载过程中出错，请刷新页面', 'error');
        });
}

// 学科项目交互
function initSubjectItems() {
    const subjectItems = document.querySelectorAll('.subject-item');
    
    subjectItems.forEach(item => {
        item.addEventListener('click', function() {
            const subjectName = this.querySelector('.subject-name').textContent.trim();
            const activeGrade = document.querySelector('.grade-item.active span:last-child').textContent.trim();
            const schoolType = document.querySelector('.grade-item.active').closest('.grade-category').querySelector('.grade-header span:last-child').textContent.trim();
            
            // 显示通知
            showNotification(`已选择: ${subjectName}`, `正在加载${schoolType}${activeGrade}${subjectName}学习资料...`);
            
            // 添加点击效果
            this.style.transform = 'scale(0.95) translateY(-5px)';
            setTimeout(() => {
                this.style.transform = '';
            }, 300);
            
            // 在实际应用中，这里可能需要跳转到相应的学科详情页面
            // window.location.href = `./subject-detail.html?type=${schoolType}&grade=${activeGrade}&subject=${subjectName}`;
        });
    });
}

/**
 * 添加点击涟漪效果
 * @param {HTMLElement} element 需要添加效果的元素
 */
function addRippleEffect(element) {
    // 创建涟漪元素
    const ripple = document.createElement('span');
    ripple.className = 'ripple';
    element.appendChild(ripple);
    
    // 获取点击位置相对于元素的坐标
    const rect = element.getBoundingClientRect();
    const size = Math.max(rect.width, rect.height);
    
    // 设置涟漪大小和位置
    ripple.style.width = ripple.style.height = `${size}px`;
    ripple.style.left = `${rect.width / 2 - size / 2}px`;
    ripple.style.top = `${rect.height / 2 - size / 2}px`;
    
    // 涟漪动画结束后移除元素
    ripple.addEventListener('animationend', function() {
        ripple.remove();
    });
}

/**
 * 显示通知消息
 * @param {string} message 消息内容
 * @param {string} type 消息类型 (success, error, info)
 */
function showNotification(message, type = 'info') {
    // 创建通知元素
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    
    // 添加到body
    document.body.appendChild(notification);
    
    // 显示动画
    setTimeout(() => {
        notification.style.transform = 'translateX(0)';
        notification.style.opacity = '1';
    }, 10);
    
    // 自动关闭
    setTimeout(() => {
        notification.style.transform = 'translateX(100%)';
        notification.style.opacity = '0';
        
        // 移除元素
        setTimeout(() => {
            notification.remove();
        }, 500);
    }, 3000);
}

// 添加CSS样式
const subjectStyleEl = document.createElement('style');
subjectStyleEl.textContent = `
    /* 加载效果 */
    .subject-list.loading {
        opacity: 0.6;
        pointer-events: none;
        position: relative;
        min-height: 200px;
    }
    
    .subject-list.loading::after {
        content: '';
        position: absolute;
        top: 30%;
        left: 50%;
        width: 50px;
        height: 50px;
        border: 3px solid rgba(124, 77, 255, 0.2);
        border-top: 3px solid var(--primary-color);
        border-radius: 50%;
        animation: spin 1s linear infinite;
        transform: translate(-50%, -50%);
    }
    
    @keyframes spin {
        0% { transform: translate(-50%, -50%) rotate(0deg); }
        100% { transform: translate(-50%, -50%) rotate(360deg); }
    }
    
    /* 涟漪效果 */
    .tab-btn {
        position: relative;
        overflow: hidden;
    }
    
    .ripple {
        position: absolute;
        background: rgba(255, 255, 255, 0.4);
        border-radius: 50%;
        transform: scale(0);
        animation: rippleEffect 0.5s linear;
        pointer-events: none;
    }
    
    @keyframes rippleEffect {
        to {
            transform: scale(2);
            opacity: 0;
        }
    }
    
    /* 通知样式 */
    .subject-notification {
        position: fixed;
        right: -400px;
        top: 30px;
        background: white;
        border-radius: 12px;
        padding: 16px;
        display: flex;
        align-items: center;
        width: 350px;
        max-width: 90vw;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
        z-index: 1000;
        transition: right 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        border-left: 4px solid var(--primary-color);
    }
    
    .subject-notification.show {
        right: 30px;
    }
    
    .notification-icon {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        background-color: rgba(124, 77, 255, 0.1);
        margin-right: 15px;
        flex-shrink: 0;
        position: relative;
    }
    
    .notification-icon::before {
        content: '';
        position: absolute;
        width: 20px;
        height: 20px;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background-color: var(--primary-color);
        mask-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41L9 16.17z"/></svg>');
        mask-size: cover;
        -webkit-mask-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41L9 16.17z"/></svg>');
        -webkit-mask-size: cover;
    }
    
    .notification-content {
        flex-grow: 1;
    }
    
    .notification-content h4 {
        font-size: 16px;
        margin-bottom: 4px;
        color: var(--text-color);
    }
    
    .notification-content p {
        font-size: 14px;
        color: var(--text-light);
        margin: 0;
    }
    
    .notification-close {
        background: none;
        border: none;
        font-size: 20px;
        color: #999;
        cursor: pointer;
        width: 24px;
        height: 24px;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 0;
        margin-left: 10px;
        border-radius: 50%;
        transition: background-color 0.3s;
    }
    
    .notification-close:hover {
        background-color: rgba(0, 0, 0, 0.05);
        color: #666;
    }
    
    /* 深色模式调整 */
    @media (prefers-color-scheme: dark) {
        .subject-notification {
            background: var(--card-bg);
        }
        
        .notification-content h4 {
            color: #fff;
        }
        
        .notification-content p {
            color: #ccc;
        }
    }
`;

document.head.appendChild(subjectStyleEl); 
