/**
 * Chatbot Frontend JavaScript
 */

(function($) {
    'use strict';
    
    class WPAIChatbot {
        constructor(element) {
            this.$element = $(element);
            this.$button = this.$element.find('.wpai-chatbot-button');
            this.$window = this.$element.find('.wpai-chatbot-window');
            this.$messages = this.$element.find('.wpai-chatbot-messages');
            this.$input = this.$element.find('.wpai-chatbot-input');
            this.$send = this.$element.find('.wpai-chatbot-send');
            this.$close = this.$element.find('.wpai-chatbot-close');
            
            this.model = this.$element.data('model');
            this.discussionId = null;
            
            this.init();
        }
        
        init() {
            this.$button.on('click', () => this.open());
            this.$close.on('click', () => this.close());
            this.$send.on('click', () => this.send());
            
            this.$input.on('keypress', (e) => {
                if (e.which === 13 && !e.shiftKey) {
                    e.preventDefault();
                    this.send();
                }
            });
        }
        
        open() {
            this.$window.fadeIn(200);
            this.$input.focus();
        }
        
        close() {
            this.$window.fadeOut(200);
        }
        
        async send() {
            const message = this.$input.val().trim();
            
            if (!message) return;
            
            this.$input.val('');
            this.addMessage('user', message);
            this.showTyping();
            
            try {
                const response = await fetch(wpaiData.restUrl + 'chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-WP-Nonce': wpaiData.nonce
                    },
                    body: JSON.stringify({
                        message: message,
                        model: this.model,
                        discussion_id: this.discussionId
                    })
                });
                
                const data = await response.json();
                
                this.hideTyping();
                
                if (data.success) {
                    this.addMessage('assistant', data.response);
                    this.discussionId = data.discussion_id || this.discussionId;
                } else {
                    this.addMessage('error', data.error || 'An error occurred');
                }
            } catch (error) {
                this.hideTyping();
                this.addMessage('error', 'Network error occurred');
                console.error('Chat error:', error);
            }
        }
        
        addMessage(role, content) {
            const $message = $('<div>')
                .addClass('wpai-message wpai-message-' + role)
                .html(this.formatMessage(content));
            
            this.$messages.append($message);
            this.scrollToBottom();
        }
        
        formatMessage(content) {
            // Basic markdown-like formatting
            content = content.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
            content = content.replace(/\*(.*?)\*/g, '<em>$1</em>');
            content = content.replace(/\n/g, '<br>');
            
            // Code blocks
            content = content.replace(/```(.*?)```/gs, '<pre><code>$1</code></pre>');
            content = content.replace(/`(.*?)`/g, '<code>$1</code>');
            
            return content;
        }
        
        showTyping() {
            const $typing = $('<div>')
                .addClass('wpai-message wpai-message-assistant wpai-typing')
                .html('<span></span><span></span><span></span>');
            
            this.$messages.append($typing);
            this.scrollToBottom();
        }
        
        hideTyping() {
            this.$messages.find('.wpai-typing').remove();
        }
        
        scrollToBottom() {
            this.$messages.scrollTop(this.$messages[0].scrollHeight);
        }
    }
    
    // Initialize chatbots
    $(document).ready(function() {
        $('[id^="wpai-chatbot-"]').each(function() {
            new WPAIChatbot(this);
        });
    });
    
})(jQuery);



