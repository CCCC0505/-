/**
 * 学科资料页面问题修复脚本
 * 用于解决学科资料无法显示的问题
 * 美化版本 - 增强用户体验
 */
(function() {
    // 确保页面完全加载后执行
    window.addEventListener('load', function() {
        console.log('页面完全加载，启动美化修复流程...');
        
        // 修复标题显示问题
        fixTitleDisplay();
        
        // 添加加载状态指示器
        addLoadingIndicator();
        
        // 添加学科点击调试
        debugSubjectClick();
        
        // 在页面完全加载后，检查是否有学科项目显示
        const checkSubjectItems = function() {
            const subjectItems = document.querySelectorAll('.subject-item');
            const subjectList = document.querySelector('.subject-list');
            
            console.log('检测到学科项目数量:', subjectItems.length);
            
            // 如果没有学科项目，但有加载动画，说明加载可能卡住了
            if (subjectItems.length === 0 && subjectList && subjectList.querySelector('.loading-spinner')) {
                console.log('检测到加载动画仍在显示，尝试强制加载学科列表');
                
                // 显示正在修复的通知
                showEnhancedNotification('正在优化加载...', '为您提供更流畅的浏览体验', 'info');
                
                // 尝试直接使用基础数据加载
                try {
                    // 清空加载动画
                    if (subjectList) {
                        subjectList.innerHTML = '';
                        
                        // 添加小学学科
                        const defaultSubjects = [
                            { name: '语文', icon: 'chinese-icon' },
                            { name: '数学', icon: 'math-icon' },
                            { name: '英语', icon: 'english-icon' }
                        ];
                        
                        // 创建并添加学科元素
                        defaultSubjects.forEach(subject => {
                            // 这里使用简单的DOM操作创建元素，避免依赖其他函数
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
                                showEnhancedNotification(`进入${subject.name}学科资料`, '加载中...', 'success');
                                
                                // 获取当前选中的年级
                                const activeGrade = document.querySelector('.grade-item.active span:last-child')?.textContent.trim() || '一年级';
                                const schoolType = document.querySelector('.grade-item.active')?.closest('.grade-category')?.querySelector('.grade-header span:last-child')?.textContent.trim() || '小学';
                                
                                // 获取学科的英文代码
                                let subjectCode = 'math'; // 默认为数学
                                if (subject.name === '语文') subjectCode = 'chinese';
                                else if (subject.name === '英语') subjectCode = 'english';
                                else if (subject.name === '物理') subjectCode = 'physics';
                                else if (subject.name === '化学') subjectCode = 'chemistry';
                                else if (subject.name === '生物') subjectCode = 'biology';
                                else if (subject.name === '政治') subjectCode = 'politics';
                                else if (subject.name === '历史') subjectCode = 'history';
                                else if (subject.name === '地理') subjectCode = 'geography';
                                
                                // 导航到学科知识点页面
                                window.location.href = `./subject-1.html?subject=${subject.name}&grade=${encodeURIComponent(activeGrade)}&level=${encodeURIComponent(schoolType)}`;
                            });
                            
                            subjectList.appendChild(subjectItem);
                        });
                        
                        showEnhancedNotification('加载成功', '已恢复学科列表显示', 'success');
                    }
                } catch (error) {
                    console.error('使用基础数据加载失败:', error);
                    showEnhancedNotification('加载遇到问题', '请刷新页面重试', 'error');
                }
            } else if (subjectItems.length > 0) {
                console.log('学科项目已正常加载');
                
                // 应用额外的动画效果增强用户体验
                applyExtraAnimations(subjectItems);
            }
        };
        
        // 延迟一段时间后检查，给原始脚本足够时间加载
        setTimeout(checkSubjectItems, 2000);
    });
    
    /**
     * 修复标题显示问题
     */
    function fixTitleDisplay() {
        // 查找标题元素
        const headerTitle = document.querySelector('.subject-page-header h1');
        if (!headerTitle) {
            console.error('未找到标题元素');
            return;
        }
        
        console.log('修复标题显示问题...');
        
        // 确保标题可见
        headerTitle.style.display = 'block';
        headerTitle.style.visibility = 'visible';
        headerTitle.style.opacity = '1';
        
        // 添加内联样式确保文字颜色
        headerTitle.style.color = '#7C4DFF';
        
        // 如果渐变不起作用，使用普通颜色
        if (window.getComputedStyle(headerTitle).webkitTextFillColor === 'transparent' &&
            window.getComputedStyle(headerTitle).color === 'rgba(0, 0, 0, 0)') {
            console.log('渐变文本不起作用，应用备选方案');
            headerTitle.style.webkitTextFillColor = '#7C4DFF';
            headerTitle.style.textFillColor = '#7C4DFF';
            headerTitle.style.background = 'none';
        }
        
        // 添加动画效果使标题更醒目
        headerTitle.classList.add('animate__animated', 'animate__fadeInDown');
        
        console.log('标题修复完成');
    }
    
    /**
     * 为已加载的学科项目添加美化效果
     * @param {NodeList} subjectItems 学科项目元素列表
     */
    function enhanceExistingSubjects(subjectItems) {
        subjectItems.forEach((item, index) => {
            // 如果没有过渡效果，添加过渡
            if (!item.style.transition) {
                item.style.transition = 'all 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275)';
            }
            
            // 添加鼠标悬停效果增强
            item.addEventListener('mouseenter', function() {
                this.style.transform = 'translateY(-12px) scale(1.05)';
                this.style.boxShadow = '0 15px 30px rgba(0, 0, 0, 0.1)';
                
                const icon = this.querySelector('.subject-icon');
                if (icon) {
                    icon.style.transform = 'scale(1.15) translateY(-5px)';
                }
            });
            
            item.addEventListener('mouseleave', function() {
                this.style.transform = '';
                this.style.boxShadow = '';
                
                const icon = this.querySelector('.subject-icon');
                if (icon) {
                    icon.style.transform = '';
                }
            });
            
            // 添加点击效果增强
            item.addEventListener('click', function() {
                const subjectName = this.querySelector('.subject-name').textContent;
                
                // 点击时的缩放效果
                this.style.transform = 'scale(0.95)';
                setTimeout(() => {
                    this.style.transform = '';
                }, 300);
                
                showEnhancedNotification(
                    `已选择: ${subjectName}`, 
                    `正在加载${subjectName}学习资料...`, 
                    'success'
                );
                
                // 获取当前选中的年级
                const activeGrade = document.querySelector('.grade-item.active span:last-child')?.textContent.trim() || '一年级';
                const schoolType = document.querySelector('.grade-item.active')?.closest('.grade-category')?.querySelector('.grade-header span:last-child')?.textContent.trim() || '小学';
                
                // 获取学科的英文代码
                let subjectCode = 'math'; // 默认为数学
                if (subjectName === '语文') subjectCode = 'chinese';
                else if (subjectName === '英语') subjectCode = 'english';
                else if (subjectName === '物理') subjectCode = 'physics';
                else if (subjectName === '化学') subjectCode = 'chemistry';
                else if (subjectName === '生物') subjectCode = 'biology';
                else if (subjectName === '政治') subjectCode = 'politics';
                else if (subjectName === '历史') subjectCode = 'history';
                else if (subjectName === '地理') subjectCode = 'geography';
                
                // 导航到学科知识点页面
                window.location.href = `./subject-1.html?subject=${encodeURIComponent(subjectName)}&grade=${encodeURIComponent(activeGrade)}&level=${encodeURIComponent(schoolType)}`;
            });
            
            // 应用交错动画效果
            if (item.style.opacity !== '1') {
                item.style.opacity = '0';
                item.style.transform = 'translateY(20px)';
                
                setTimeout(() => {
                    item.style.opacity = '1';
                    item.style.transform = 'translateY(0)';
                }, 100 + index * 100);
            }
        });
    }

    function applyExtraAnimations(subjectItems) {
        enhanceExistingSubjects(subjectItems);
    }
    
    /**
     * 显示增强版通知
     * @param {string} title 通知标题
     * @param {string} message 通知内容
     * @param {string} type 通知类型 (success, error, info)
     */
    function showEnhancedNotification(title, message, type = 'info') {
        // 移除旧通知
        const oldNotifications = document.querySelectorAll('.enhanced-notification');
        oldNotifications.forEach(notification => {
            notification.classList.add('notification-hide');
            setTimeout(() => {
                notification.remove();
            }, 300);
        });
        
        // 创建通知元素
        const notification = document.createElement('div');
        notification.className = `enhanced-notification ${type}`;
        
        // 添加图标
        const iconDiv = document.createElement('div');
        iconDiv.className = 'notification-icon';
        notification.appendChild(iconDiv);
        
        // 添加内容
        const contentDiv = document.createElement('div');
        contentDiv.className = 'notification-content';
        
        const titleElement = document.createElement('h4');
        titleElement.textContent = title;
        
        const messageElement = document.createElement('p');
        messageElement.textContent = message;
        
        contentDiv.appendChild(titleElement);
        contentDiv.appendChild(messageElement);
        notification.appendChild(contentDiv);
        
        // 添加关闭按钮
        const closeBtn = document.createElement('button');
        closeBtn.className = 'notification-close';
        closeBtn.innerHTML = '&times;';
        closeBtn.addEventListener('click', function() {
            notification.classList.add('notification-hide');
            setTimeout(() => {
                notification.remove();
            }, 300);
        });
        notification.appendChild(closeBtn);
        
        // 添加到body
        document.body.appendChild(notification);
        
        // 显示动画
        setTimeout(() => {
            notification.classList.add('notification-show');
        }, 10);
        
        // 自动关闭
        setTimeout(() => {
            notification.classList.add('notification-hide');
            setTimeout(() => {
                notification.remove();
            }, 300);
        }, 5000);
    }
    
    /**
     * 添加加载状态指示器
     */
    function addLoadingIndicator() {
        const styleEl = document.createElement('style');
        styleEl.textContent = `
            /* 增强版通知样式 */
            .enhanced-notification {
                position: fixed;
                top: 30px;
                right: -400px;
                padding: 16px 20px;
                background: white;
                border-radius: 12px;
                box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
                display: flex;
                align-items: center;
                width: 350px;
                max-width: 90vw;
                z-index: 9999;
                transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
                overflow: hidden;
            }
            
            .enhanced-notification.notification-show {
                right: 30px;
            }
            
            .enhanced-notification.notification-hide {
                right: -400px;
                opacity: 0;
            }
            
            .enhanced-notification.success {
                border-left: 4px solid #4CAF50;
            }
            
            .enhanced-notification.error {
                border-left: 4px solid #F44336;
            }
            
            .enhanced-notification.info {
                border-left: 4px solid #2196F3;
            }
            
            .notification-icon {
                width: 40px;
                height: 40px;
                border-radius: 50%;
                margin-right: 15px;
                position: relative;
                flex-shrink: 0;
            }
            
            .enhanced-notification.success .notification-icon {
                background-color: rgba(76, 175, 80, 0.1);
            }
            
            .enhanced-notification.success .notification-icon::before {
                content: '';
                position: absolute;
                width: 20px;
                height: 20px;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                background-color: #4CAF50;
                mask-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41L9 16.17z"/></svg>');
                mask-size: cover;
                -webkit-mask-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41L9 16.17z"/></svg>');
                -webkit-mask-size: cover;
            }
            
            .enhanced-notification.error .notification-icon {
                background-color: rgba(244, 67, 54, 0.1);
            }
            
            .enhanced-notification.error .notification-icon::before {
                content: '';
                position: absolute;
                width: 20px;
                height: 20px;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                background-color: #F44336;
                mask-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12 19 6.41z"/></svg>');
                mask-size: cover;
                -webkit-mask-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12 19 6.41z"/></svg>');
                -webkit-mask-size: cover;
            }
            
            .enhanced-notification.info .notification-icon {
                background-color: rgba(33, 150, 243, 0.1);
            }
            
            .enhanced-notification.info .notification-icon::before {
                content: '';
                position: absolute;
                width: 20px;
                height: 20px;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                background-color: #2196F3;
                mask-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/></svg>');
                mask-size: cover;
                -webkit-mask-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/></svg>');
                -webkit-mask-size: cover;
            }
            
            .notification-content {
                flex-grow: 1;
            }
            
            .notification-content h4 {
                font-size: 16px;
                margin: 0 0 5px 0;
                color: var(--text-color, #333);
                font-weight: 600;
            }
            
            .notification-content p {
                font-size: 14px;
                margin: 0;
                color: var(--text-light, #666);
            }
            
            .notification-close {
                background: none;
                border: none;
                font-size: 20px;
                color: #999;
                cursor: pointer;
                width: 24px;
                height: 24px;
                padding: 0;
                margin-left: 10px;
                border-radius: 50%;
                transition: all 0.2s;
                flex-shrink: 0;
            }
            
            .notification-close:hover {
                background-color: rgba(0, 0, 0, 0.05);
                color: #666;
            }
            
            /* 深色模式调整 */
            @media (prefers-color-scheme: dark) {
                .enhanced-notification {
                    background: #333;
                }
                
                .notification-content h4 {
                    color: #fff;
                }
                
                .notification-content p {
                    color: #ccc;
                }
                
                .notification-close {
                    color: #ccc;
                }
                
                .notification-close:hover {
                    background-color: rgba(255, 255, 255, 0.1);
                    color: #fff;
                }
            }
        `;
        document.head.appendChild(styleEl);
    }
    
    /**
     * 调试学科点击问题
     */
    function debugSubjectClick() {
        console.log('正在添加学科点击调试...');
        
        // 获取所有学科项
        const subjectItems = document.querySelectorAll('.subject-item');
        if (subjectItems.length > 0) {
            console.log(`找到 ${subjectItems.length} 个学科项`);
            
            // 重新绑定点击事件
            subjectItems.forEach((item, index) => {
                // 移除已有的点击事件
                const oldItem = item.cloneNode(true);
                item.parentNode.replaceChild(oldItem, item);
                
                // 重新绑定点击事件
                oldItem.addEventListener('click', function(e) {
                    console.log(`学科项 ${index + 1} 被点击`);
                    
                    const subjectName = this.querySelector('.subject-name').textContent.trim();
                    console.log(`学科名称: ${subjectName}`);
                    
                    // 获取当前选中的年级
                    const activeGrade = document.querySelector('.grade-item.active span:last-child')?.textContent.trim() || '一年级';
                    const schoolType = document.querySelector('.grade-item.active')?.closest('.grade-category')?.querySelector('.grade-header span:last-child')?.textContent.trim() || '小学';
                    console.log(`年级: ${activeGrade}, 学校类型: ${schoolType}`);
                    
                    // 获取学科的英文代码
                    let subjectCode = 'math'; // 默认为数学
                    if (subjectName === '语文') subjectCode = 'chinese';
                    else if (subjectName === '英语') subjectCode = 'english';
                    else if (subjectName === '物理') subjectCode = 'physics';
                    else if (subjectName === '化学') subjectCode = 'chemistry';
                    else if (subjectName === '生物') subjectCode = 'biology';
                    else if (subjectName === '政治') subjectCode = 'politics';
                    else if (subjectName === '历史') subjectCode = 'history';
                    else if (subjectName === '地理') subjectCode = 'geography';
                    
                    console.log(`学科代码: ${subjectCode}`);
                    console.log(`将跳转到: ./subject-1.html?subject=${subjectCode}&grade=${encodeURIComponent(activeGrade)}&level=${encodeURIComponent(schoolType)}`);
                    
                    // 显示通知
                    showEnhancedNotification(
                        `已选择: ${subjectName}`, 
                        `正在跳转到${schoolType}${activeGrade}${subjectName}学习资料...`, 
                        'success'
                    );
                    
                    // 设置一个短暂的延迟，确保通知显示后跳转
                    setTimeout(() => {
                        // 导航到学科知识点页面
                        window.location.href = `./subject-1.html?subject=${encodeURIComponent(subjectName)}&grade=${encodeURIComponent(activeGrade)}&level=${encodeURIComponent(schoolType)}`;
                    }, 500);
                });
                
                console.log(`已重新绑定学科项 ${index + 1} 的点击事件`);
            });
        } else {
            console.log('未找到学科项，等待学科项加载后重新检查');
            
            // 添加监听器，监控DOM变化
            const subjectList = document.querySelector('.subject-list');
            if (subjectList) {
                console.log('找到学科列表容器，添加DOM监控');
                
                // 创建观察器
                const observer = new MutationObserver(function(mutations) {
                    mutations.forEach(function(mutation) {
                        if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                            const newSubjectItems = document.querySelectorAll('.subject-item');
                            if (newSubjectItems.length > 0) {
                                console.log(`监测到新的学科项加载，数量: ${newSubjectItems.length}`);
                                observer.disconnect(); // 停止观察
                                debugSubjectClick(); // 重新执行调试
                            }
                        }
                    });
                });
                
                // 配置观察选项
                const config = { childList: true, subtree: true };
                
                // 开始观察
                observer.observe(subjectList, config);
            }
        }
    }
})(); 
