/**
 * AI服务修复脚本
 * 用于解决ai-service.js中的错误并提供兼容性支持
 */
(function() {
    // 防止脚本多次加载
    if (window.aiServiceFixed) return;
    window.aiServiceFixed = true;
    
    console.log('AI服务修复脚本已加载');
    
    // 在页面加载完成后执行修复
    document.addEventListener('DOMContentLoaded', function() {
        fixMissingElements();
        fixHotspotGeneration();
    });
    
    // 修复缺失的DOM元素
    function fixMissingElements() {
        // 检查并修复幻灯片面板
        if (typeof initSlidePanel === 'function' && !document.querySelector('.ai-slide-panel')) {
            console.log('修复：创建缺失的幻灯片面板元素');
            const slidePanel = document.createElement('div');
            slidePanel.className = 'ai-slide-panel';
            slidePanel.innerHTML = `
                <div class="ai-slide-header">
                    <h3>AI学习助手</h3>
                    <button class="ai-slide-close">&times;</button>
                </div>
                <div class="ai-slide-messages"></div>
                <div class="ai-slide-input">
                    <input type="text" placeholder="有什么想问我的...">
                    <button>发送</button>
                </div>
            `;
            document.body.appendChild(slidePanel);
        }
        
        // 检查并修复练习中心对话框
        if (typeof initPracticeAICompanion === 'function' && !document.querySelector('.ai-practice-chat')) {
            console.log('修复：创建缺失的练习中心对话框元素');
            if (document.querySelector('.ai-help')) {
                const practiceChat = document.createElement('div');
                practiceChat.className = 'ai-practice-chat';
                practiceChat.innerHTML = `
                    <div class="ai-practice-messages"></div>
                    <div class="ai-practice-input">
                        <input type="text" placeholder="询问关于这道题的问题...">
                        <button>发送</button>
                    </div>
                `;
                document.querySelector('.ai-help').appendChild(practiceChat);
            }
        }
    }
    
    // 修复热点题目生成功能
    function fixHotspotGeneration() {
        if (window.AICompanion && AICompanion.prototype.generateHotspotQuestions) {
            console.log('修复：热点题目生成功能');
            const originalGenerate = AICompanion.prototype.generateHotspotQuestions;
            
            // 替换为更安全的版本
            AICompanion.prototype.generateHotspotQuestions = function(subject, grade, knowledge, count = 3) {
                try {
                    // 安全检查
                    if (!subject || !grade) {
                        console.warn('生成热点题目缺少必要参数');
                        return this.createFallbackQuestions(subject, grade, knowledge, count);
                    }
                    
                    return originalGenerate.call(this, subject, grade, knowledge, count);
                } catch (error) {
                    console.error('生成热点题目出错:', error);
                    return this.createFallbackQuestions(subject, grade, knowledge, count);
                }
            };
        }
    }
})();
