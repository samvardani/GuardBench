/**
 * Chatbot JavaScript
 * 
 * @package WPAIEnginePro
 */

(function($) {
    'use strict';
    
    /**
     * Initialize chatbot
     */
    function initChatbot() {
        $('.wpai-chat-form').on('submit', function(e) {
            e.preventDefault();
            
            const $form = $(this);
            const $input = $form.find('.wpai-input');
            const $button = $form.find('.wpai-send-btn');
            const message = $input.val().trim();
            const chatbotId = $form.data('chatbot-id');
            const $messagesContainer = $('#' + chatbotId + '-messages');
            
            if (!message) {
                return;
            }
            
            // Disable input
            $input.prop('disabled', true);
            $button.prop('disabled', true);
            
            // Add user message
            addMessage($messagesContainer, message, 'user');
            
            // Clear input
            $input.val('');
            
            // Add loading indicator
            const $loadingMsg = $('<div class="wpai-message wpai-message-assistant"><div class="wpai-message-content wpai-message-loading">Thinking</div></div>');
            $messagesContainer.append($loadingMsg);
            scrollToBottom($messagesContainer);
            
            // Send to API
            $.ajax({
                url: wpaiChatbot.restUrl,
                method: 'POST',
                headers: {
                    'X-WP-Nonce': wpaiChatbot.nonce
                },
                contentType: 'application/json',
                data: JSON.stringify({
                    message: message
                }),
                success: function(response) {
                    $loadingMsg.remove();
                    
                    if (response.success && response.response) {
                        addMessage($messagesContainer, response.response, 'assistant');
                    } else {
                        addMessage($messagesContainer, 'Sorry, I encountered an error. Please try again.', 'assistant');
                    }
                },
                error: function(xhr) {
                    $loadingMsg.remove();
                    
                    let errorMsg = 'Sorry, I encountered an error. Please try again.';
                    
                    if (xhr.responseJSON && xhr.responseJSON.error) {
                        errorMsg = xhr.responseJSON.error;
                    } else if (xhr.responseJSON && xhr.responseJSON.message) {
                        errorMsg = xhr.responseJSON.message;
                    }
                    
                    addMessage($messagesContainer, errorMsg, 'assistant');
                },
                complete: function() {
                    // Re-enable input
                    $input.prop('disabled', false);
                    $button.prop('disabled', false);
                    $input.focus();
                }
            });
        });
        
        // Minimize button
        $('.wpai-minimize').on('click', function() {
            const $container = $(this).closest('.wpai-chatbot-container');
            $container.toggleClass('wpai-minimized');
        });
    }
    
    /**
     * Add message to chat
     */
    function addMessage($container, text, type) {
        const $message = $('<div class="wpai-message wpai-message-' + type + '"><div class="wpai-message-content"></div></div>');
        $message.find('.wpai-message-content').text(text);
        $container.append($message);
        scrollToBottom($container);
    }
    
    /**
     * Scroll to bottom of messages
     */
    function scrollToBottom($container) {
        $container.scrollTop($container[0].scrollHeight);
    }
    
    // Initialize on document ready
    $(document).ready(function() {
        initChatbot();
    });
    
})(jQuery);

