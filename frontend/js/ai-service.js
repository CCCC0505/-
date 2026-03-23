// AI陪伴服务
class AICompanion {
    constructor(apiKey, baseURL) {
        this.apiKey = '';
        this.baseURL = '/api/ai';
        this.systemPrompt = "你是一个友好的学习陪伴AI，你的主要任务是：1)关心用户的学习状态；2)适时提供鼓励；3)提醒用户注意休息。保持回复简短、友好，像朋友一样陪伴用户学习。";
        this.conversationHistory = [];
        this.minuteCounter = 0;
        this.studyStartTime = new Date();
        this.checkInterval = null;
        this.restReminderInterval = null;
        this.messageCallbacks = []; // 存储多个消息回调函数
        this.subject = '';
        this.grade = '';
    }

    // 初始化会话历史
    initConversation() {
        this.conversationHistory = [
            {
                role: "system",
                content: this.systemPrompt
            }
        ];
    }

    // 添加用户消息到历史
    addUserMessage(message) {
        this.conversationHistory.push({
            role: "user",
            content: message
        });
    }

    // 添加AI回复到历史
    addAIResponse(message) {
        this.conversationHistory.push({
            role: "assistant",
            content: message
        });
    }

    // 发送请求到后端Qwen代理
    async sendRequest(onChunkReceived, customSystemPrompt = null) {
        try {
            console.log("开始调用AI助手后端代理...");
            const systemPrompt = customSystemPrompt || this.systemPrompt;
            const latestUserMessage = [...this.conversationHistory].reverse().find(item => item.role === 'user');
            const response = await fetch(`${this.baseURL}/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: latestUserMessage ? latestUserMessage.content : '',
                    subject: this.subject,
                    grade: this.grade,
                    custom_system_prompt: systemPrompt
                })
            });

            if (!response.ok) {
                throw new Error(`API请求失败: ${response.status} ${response.statusText}`);
            }
            const data = await response.json();
            const fullResponse = data.reply || '';
            if (onChunkReceived) {
                onChunkReceived(fullResponse, fullResponse);
            }

            // 添加完整回复到历史
            this.addAIResponse(fullResponse);
            return fullResponse;
            
        } catch (error) {
            console.error("API请求出错:", error);
            throw error;
        }
    }

    // 发送消息并获取回复
    async sendMessage(message, onChunkReceived) {
        // 添加用户消息
        this.addUserMessage(message);
        
        try {
            // 发送请求并处理流式响应
            return await this.sendRequest(onChunkReceived);
        } catch (error) {
            console.error("发送消息时出错:", error);
            throw error;
        }
    }

    // 根据学科和年级调整系统提示
    setSubjectAndGrade(subject, grade) {
        this.subject = subject;
        this.grade = grade;
        if (subject && grade) {
            this.systemPrompt = `你是一个友好的${subject}学习陪伴AI，面向${grade}阶段学生。你的主要任务是：1)关心用户的学习状态；2)适时提供鼓励；3)提醒用户注意休息。保持回复简短、友好，像朋友一样陪伴用户学习。`;
            
            // 更新会话历史中的系统提示
            if (this.conversationHistory.length > 0 && this.conversationHistory[0].role === "system") {
                this.conversationHistory[0].content = this.systemPrompt;
            } else {
                this.initConversation();
            }
        }
    }

    // 添加消息回调函数
    addMessageCallback(callback) {
        if (typeof callback === 'function') {
            this.messageCallbacks.push(callback);
        }
    }

    // 启动定时检查
    startTimedChecks() {
        this.minuteCounter = 0;
        this.studyStartTime = new Date();
        
        // 每分钟检查
        this.checkInterval = setInterval(() => {
            this.minuteCounter++;
            
            // 每20分钟提醒休息
            if (this.minuteCounter % 25 === 0) {
                const studyDuration = Math.floor((new Date() - this.studyStartTime) / 60000);
                const restMessage = `你已经学习了${studyDuration}分钟，建议休息一下眼睛，站起来活动几分钟，喝点水吧！`;
                
                // 向所有已注册的消息回调发送消息
                this.messageCallbacks.forEach(callback => {
                    callback('ai', restMessage, 'rest-reminder');
                });
            }
            // 每隔5分钟询问学习情况（但不在休息提醒的同一分钟）
            else if (this.minuteCounter % 5 === 0 && this.minuteCounter % 25 !== 0) {
                // 随机选择一个关心问题
                const questions = [
                    "学习进展如何？需要帮忙吗？",
                    "遇到什么难题了吗？",
                    "学习状态还好吗？",
                    "需要我解释什么概念吗？",
                    "有什么我能帮到你的吗？",
                    "你今天学习了什么？",
                    "你今天有什么收获吗？",
                    "你有什么问题吗？",
                    "你今天有什么计划吗？",
                    "你今天有什么目标吗？",
                    "遇到了什么烦心事都可以和我倾诉哟!"
                ];
                const randomQuestion = questions[Math.floor(Math.random() * questions.length)];
                
                // 向所有已注册的消息回调发送消息
                this.messageCallbacks.forEach(callback => {
                    callback('ai', randomQuestion, 'study-check');
                });
            }
        }, 60000); // 每分钟检查一次
    }

    // 停止定时检查
    stopTimedChecks() {
        if (this.checkInterval) {
            clearInterval(this.checkInterval);
            this.checkInterval = null;
        }
    }

    // 生成AI热点题目
    async generateHotspotQuestions(subject, grade, knowledge, count = 3) {
        try {
            const response = await fetch(`${this.baseURL}/hotspot-questions`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    subject,
                    grade,
                    knowledge,
                    count
                })
            });

            if (!response.ok) {
                throw new Error(`AI热点题目生成请求失败: ${response.status} ${response.statusText}`);
            }

            const data = await response.json();
            return {
                questions: data.questions || this.createFallbackQuestions(subject, grade, knowledge, count),
                aiStatus: data.ai_status || {
                    enabled: false,
                    attempted: false,
                    success: false,
                    fallback_used: true,
                    model_name: '',
                    message: '未返回AI状态'
                }
            };
        } catch (error) {
            console.error("生成热点题目时出错:", error);
            return {
                questions: this.createFallbackQuestions(subject, grade, knowledge, count),
                aiStatus: {
                    enabled: false,
                    attempted: true,
                    success: false,
                    fallback_used: true,
                    model_name: '',
                    message: '热点题接口调用失败，已使用备用题目'
                }
            };
        }
    }

    // 创建备用题目（当API请求失败时使用）
    createFallbackQuestions(subject, grade, knowledge, count) {
        const difficulties = ['简单', '中等', '困难'];
        const tags = ['热点应用', '学科交叉', '生活实例'];
        const questions = [];
        
        for (let i = 0; i < count; i++) {
            questions.push({
                id: `h00${i+1}`,
                badge: "AI推荐",
                difficulty: difficulties[Math.floor(Math.random() * difficulties.length)],
                content: `关于${knowledge}的应用题（AI生成失败，这是一个备用题目）。考虑${grade}${subject}中${knowledge}的应用场景。`,
                tag: tags[Math.floor(Math.random() * tags.length)]
            });
        }
        
        return questions;
    }
}

document.addEventListener('DOMContentLoaded', function() {
    // 创建AI服务实例，统一走后端Qwen代理
    window.aiService = new AICompanion("", "/api/ai");
    
    // 初始化对话历史
    window.aiService.initConversation();
    
    // 初始化各个AI陪伴区域
    initSlidePanel();
    initPracticeAICompanion();
    initSidebarAI(); // 新增：初始化侧边栏AI助手
});

// 初始化侧边栏AI助手
function initSidebarAI() {
    const aiAvatarContainer = document.getElementById('ai-avatar-container');
    const aiSidebarChat = document.getElementById('ai-sidebar-chat');
    const aiSidebarMessages = document.getElementById('ai-sidebar-messages');
    const aiSidebarInput = document.getElementById('ai-sidebar-input');
    const aiSidebarSend = document.getElementById('ai-sidebar-send');
    const mainContent = document.querySelector('.main-content');
    
    if (!aiAvatarContainer || !aiSidebarChat || !aiSidebarMessages) {
        console.debug('侧边栏AI助手元素未找到');
        return;
    }
    
    // 清空现有消息
    aiSidebarMessages.innerHTML = '';
    
    // 添加欢迎消息
    addSidebarMessage('ai', '你好！👋 我是你的AI学习伙伴。点击下方输入框向我提问，我会尽力帮助你解决学习中的问题！');
    
    // 点击头像容器时打开聊天窗口
    aiAvatarContainer.addEventListener('click', function(e) {
        e.stopPropagation(); // 阻止事件冒泡
        aiSidebarChat.classList.add('active');
        aiAvatarContainer.style.opacity = '0';
        
        // 聚焦到输入框
        setTimeout(() => {
            aiSidebarInput.focus();
        }, 400);
    });
    
    // 点击聊天区域时阻止事件冒泡，防止点击聊天区域时关闭
    aiSidebarChat.addEventListener('click', function(e) {
        e.stopPropagation();
    });
    
    // 点击文档其他区域时关闭聊天窗口
    document.addEventListener('click', function() {
        if (aiSidebarChat.classList.contains('active')) {
            aiSidebarChat.classList.remove('active');
            aiAvatarContainer.style.opacity = '1';
        }
    });
    
    // 发送消息功能
    if (aiSidebarSend && aiSidebarInput) {
        aiSidebarSend.addEventListener('click', sendSidebarMessage);
        aiSidebarInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendSidebarMessage();
            }
        });
    }
    
    // 发送消息函数
    function sendSidebarMessage() {
        const message = aiSidebarInput.value.trim();
        
        if (message === '') {
            return;
        }
        
        // 添加用户消息
        addSidebarMessage('user', message);
        
        // 清空输入框
        aiSidebarInput.value = '';
        
        // 调用AI回复
        getSidebarAIResponse(message);
    }
    
    // 添加消息到侧边栏聊天窗口
    function addSidebarMessage(type, text, className = '') {
        const messageDiv = document.createElement('div');
        messageDiv.className = `${type}-message`;
        
        if (className) {
            messageDiv.classList.add(className);
        }
        
        const messageParagraph = document.createElement('p');
        messageParagraph.textContent = text;
        
        messageDiv.appendChild(messageParagraph);
        aiSidebarMessages.appendChild(messageDiv);
        
        // 滚动到底部
        aiSidebarMessages.scrollTop = aiSidebarMessages.scrollHeight;
    }
    
    // 获取AI回复
    async function getSidebarAIResponse(message) {
        // 添加AI思考动画
        const thinkingDiv = document.createElement('div');
        thinkingDiv.className = 'ai-message';
        
        const thinkingContent = document.createElement('div');
        thinkingContent.className = 'ai-thinking';
        thinkingContent.innerHTML = '<span></span><span></span><span></span>';
        
        thinkingDiv.appendChild(thinkingContent);
        aiSidebarMessages.appendChild(thinkingDiv);
        
        // 滚动到底部
        aiSidebarMessages.scrollTop = aiSidebarMessages.scrollHeight;
        
        try {
            // 发送消息到AI服务并获取流式响应
            let responseText = '';
            await window.aiService.sendRequest(onChunkReceived => {
                responseText = onChunkReceived;
            });
            
            // 移除思考动画
            aiSidebarMessages.removeChild(thinkingDiv);
            
            // 添加AI回复
            addSidebarMessage('ai', responseText);
            
        } catch (error) {
            // 移除思考动画
            aiSidebarMessages.removeChild(thinkingDiv);
            
            // 添加错误消息
            addSidebarMessage('ai', '抱歉，我遇到了问题，无法回答您的问题。请稍后再试。', 'error-message');
            console.error('侧边栏AI响应错误:', error);
        }
    }
}

// 初始化侧边滑出面板
function initSlidePanel() {
    const aiAssistantTrigger = document.getElementById('ai-assistant-trigger');
    const chatSlidePanel = document.getElementById('chat-slide-panel');
    const closeChatBtn = document.getElementById('close-chat-btn');
    const chatBackdrop = document.getElementById('chat-backdrop');
    const slideUserMessageInput = document.getElementById('slide-user-message');
    const slideSendBtn = document.getElementById('slide-send-btn');
    const slideChatMessages = document.getElementById('slide-chat-messages');
    
    if (!chatSlidePanel || !slideChatMessages) {
        console.debug('聊天面板元素未找到');
        return;
    }
    
    // 清空现有消息
    slideChatMessages.innerHTML = '';
    
    // 添加欢迎消息
    addSlideMessage('ai', '你好！👋 我是你的AI学习伙伴。我会陪伴你学习，定时关心你的进度，并提醒你休息。现在开始学习吧！');
    
    // 注册滑出面板的消息回调
    window.aiService.addMessageCallback(addSlideMessage);
    
    // 点击AI助手时打开聊天窗口
    if (aiAssistantTrigger) {
        aiAssistantTrigger.addEventListener('click', function() {
            chatSlidePanel.classList.add('active');
            chatBackdrop.classList.add('active');
            
            // 聚焦到输入框
            setTimeout(() => {
                slideUserMessageInput.focus();
            }, 400);
        });
    }
    
    // 点击关闭按钮时关闭聊天窗口
    if (closeChatBtn) {
        closeChatBtn.addEventListener('click', function() {
            chatSlidePanel.classList.remove('active');
            chatBackdrop.classList.remove('active');
        });
    }
    
    // 点击背景遮罩时关闭聊天窗口
    if (chatBackdrop) {
        chatBackdrop.addEventListener('click', function() {
            chatSlidePanel.classList.remove('active');
            chatBackdrop.classList.remove('active');
        });
    }
    
    // 发送消息功能
    if (slideSendBtn && slideUserMessageInput) {
        slideSendBtn.addEventListener('click', sendSlideMessage);
        slideUserMessageInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendSlideMessage();
            }
        });
    }
    
    // 发送消息函数
    function sendSlideMessage() {
        const message = slideUserMessageInput.value.trim();
        
        if (message === '') {
            return;
        }
        
        // 添加用户消息
        addSlideMessage('user', message);
        
        // 清空输入框
        slideUserMessageInput.value = '';
        
        // 调用AI回复
        getAIResponse(message);
    }
    
    // 添加消息到聊天窗口
    function addSlideMessage(type, text, className = '') {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}-message`;
        
        if (className) {
            messageDiv.classList.add(className);
        }
        
        const messageParagraph = document.createElement('p');
        messageParagraph.textContent = text;
        
        messageDiv.appendChild(messageParagraph);
        slideChatMessages.appendChild(messageDiv);
        
        // 如果是提醒消息，添加动画
        if (className === 'rest-reminder' || className === 'study-check') {
            messageDiv.style.animation = 'remind-pulse 1s ease-in-out';
        }
        
        // 滚动到底部
        slideChatMessages.scrollTop = slideChatMessages.scrollHeight;
        
        // 如果是休息提醒，播放轻微提示音
        if (className === 'rest-reminder') {
            try {
                // 创建一个简单的提示音
                const context = new (window.AudioContext || window.webkitAudioContext)();
                const oscillator = context.createOscillator();
                const gainNode = context.createGain();
                
                oscillator.type = 'sine';
                oscillator.frequency.value = 520;
                gainNode.gain.value = 0.1;
                
                oscillator.connect(gainNode);
                gainNode.connect(context.destination);
                
                oscillator.start(0);
                
                // 0.5秒后停止
                setTimeout(() => {
                    oscillator.stop();
                }, 500);
            } catch (e) {
                console.log('浏览器不支持Web Audio API');
            }
        }
    }
    
    // 获取AI回复
    async function getAIResponse(message) {
        // 添加AI消息占位符
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message ai-message';
        const messageParagraph = document.createElement('p');
        messageParagraph.textContent = '正在思考...';
        messageDiv.appendChild(messageParagraph);
        slideChatMessages.appendChild(messageDiv);
        
        // 滚动到底部
        slideChatMessages.scrollTop = slideChatMessages.scrollHeight;
        
        try {
            // 发送消息到AI服务并获取流式响应
            await window.aiService.sendRequest(onChunkReceived => {
                // 更新消息内容
                messageParagraph.textContent = onChunkReceived;
                // 滚动到底部
                slideChatMessages.scrollTop = slideChatMessages.scrollHeight;
            });
        } catch (error) {
            messageParagraph.textContent = '抱歉，我遇到了问题，无法回答您的问题。请稍后再试。';
            console.error('AI响应错误:', error);
        }
    }
}

// 初始化练习中心内嵌AI陪伴区域
function initPracticeAICompanion() {
    const practiceAIMessages = document.getElementById('practice-ai-messages');
    const practiceAIMessage = document.getElementById('practice-ai-message');
    const practiceAISendBtn = document.getElementById('practice-ai-send-btn');
    
    if (!practiceAIMessages || !practiceAIMessage || !practiceAISendBtn) {
        console.debug('练习中心AI陪伴元素未找到');
        return;
    }
    
    // 注册练习中心AI陪伴的消息回调
    window.aiService.addMessageCallback(addPracticeAIMessage);
    
    // 当进入练习中心页面时，启动定时检查
    const navLinks = document.querySelectorAll('.nav-links a');
    navLinks.forEach(link => {
        link.addEventListener('click', function() {
            const targetId = this.getAttribute('href').substring(1);
            if (targetId === 'practice') {
                // 启动定时检查
                if (!window.aiService.checkInterval) {
                    window.aiService.startTimedChecks();
                }
            } else {
                // 停止定时检查
                window.aiService.stopTimedChecks();
            }
        });
    });
    
    // 如果当前在练习中心页面，立即启动定时检查
    if (document.querySelector('#practice.active-section')) {
        window.aiService.startTimedChecks();
    }
    
    // 添加发送消息功能
    practiceAISendBtn.addEventListener('click', sendPracticeAIMessage);
    practiceAIMessage.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendPracticeAIMessage();
        }
    });
    
    // 发送消息函数
    function sendPracticeAIMessage() {
        const message = practiceAIMessage.value.trim();
        
        if (message === '') {
            return;
        }
        
        // 添加用户消息
        addPracticeAIMessage('user', message);
        
        // 清空输入框
        practiceAIMessage.value = '';
        
        // 调用AI回复
        getPracticeAIResponse(message);
    }
    
    // 添加消息到练习中心AI陪伴区域
    function addPracticeAIMessage(type, text, className = '') {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}-message`;
        
        if (className) {
            messageDiv.classList.add(className);
        }
        
        const messageParagraph = document.createElement('p');
        messageParagraph.textContent = text;
        
        messageDiv.appendChild(messageParagraph);
        practiceAIMessages.appendChild(messageDiv);
        
        // 如果是提醒消息，添加动画
        if (className === 'rest-reminder' || className === 'study-check') {
            messageDiv.style.animation = 'remind-pulse 1s ease-in-out';
        }
        
        // 滚动到底部
        practiceAIMessages.scrollTop = practiceAIMessages.scrollHeight;
    }
    
    // 获取AI回复
    async function getPracticeAIResponse(message) {
        // 添加AI消息占位符
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message ai-message';
        const messageParagraph = document.createElement('p');
        messageParagraph.textContent = '正在思考...';
        messageDiv.appendChild(messageParagraph);
        practiceAIMessages.appendChild(messageDiv);
        
        // 滚动到底部
        practiceAIMessages.scrollTop = practiceAIMessages.scrollHeight;
        
        try {
            // 发送消息到AI服务并获取流式响应
            await window.aiService.sendRequest(onChunkReceived => {
                // 更新消息内容
                messageParagraph.textContent = onChunkReceived;
                // 滚动到底部
                practiceAIMessages.scrollTop = practiceAIMessages.scrollHeight;
            });
        } catch (error) {
            messageParagraph.textContent = '抱歉，我遇到了问题，无法回答您的问题。请稍后再试。';
            console.error('AI响应错误:', error);
        }
    }
} 
