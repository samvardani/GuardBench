<?php
/**
 * Simple Chatbot Shortcode
 */

// Add shortcode handler
add_shortcode('wpai_chatbot', 'wpai_chatbot_shortcode');

function wpai_chatbot_shortcode($atts) {
    $atts = shortcode_atts([
        'title' => 'AI Assistant',
        'theme' => 'modern',
        'position' => 'bottom-right',
    ], $atts);
    
    // Enqueue scripts
    wp_enqueue_script('jquery');
    
    // Generate unique ID
    $id = 'wpai-chatbot-' . uniqid();
    
    ob_start();
    ?>
    <div id="<?php echo esc_attr($id); ?>" 
         class="wpai-chatbot wpai-theme-<?php echo esc_attr($atts['theme']); ?> wpai-position-<?php echo esc_attr($atts['position']); ?>">
        
        <div class="wpai-chatbot-button">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
            </svg>
        </div>
        
        <div class="wpai-chatbot-window" style="display: none;">
            <div class="wpai-chatbot-header">
                <span class="wpai-chatbot-title"><?php echo esc_html($atts['title']); ?></span>
                <button class="wpai-chatbot-close">&times;</button>
            </div>
            
            <div class="wpai-chatbot-messages"></div>
            
            <div class="wpai-chatbot-input-container">
                <textarea class="wpai-chatbot-input" placeholder="Type your message..."></textarea>
                <button class="wpai-chatbot-send">
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <line x1="22" y1="2" x2="11" y2="13"></line>
                        <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                    </svg>
                </button>
            </div>
        </div>
    </div>
    
    <style>
    .wpai-chatbot {
        position: fixed;
        z-index: 9999;
    }
    
    .wpai-chatbot.wpai-position-bottom-right {
        bottom: 20px;
        right: 20px;
    }
    
    .wpai-chatbot-button {
        width: 60px;
        height: 60px;
        border-radius: 50%;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        transition: transform 0.2s;
    }
    
    .wpai-chatbot-button:hover {
        transform: scale(1.05);
    }
    
    .wpai-chatbot-window {
        position: absolute;
        bottom: 80px;
        right: 0;
        width: 380px;
        max-width: calc(100vw - 40px);
        height: 600px;
        max-height: calc(100vh - 120px);
        background: white;
        border-radius: 12px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        display: flex;
        flex-direction: column;
        overflow: hidden;
    }
    
    .wpai-chatbot-header {
        padding: 16px 20px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .wpai-chatbot-title {
        font-size: 16px;
        font-weight: 600;
    }
    
    .wpai-chatbot-close {
        background: none;
        border: none;
        color: white;
        font-size: 24px;
        cursor: pointer;
        padding: 0;
        width: 30px;
        height: 30px;
        line-height: 1;
    }
    
    .wpai-chatbot-messages {
        flex: 1;
        overflow-y: auto;
        padding: 20px;
        background: #f7f9fc;
    }
    
    .wpai-message {
        margin-bottom: 16px;
        padding: 12px 16px;
        border-radius: 12px;
        max-width: 80%;
        word-wrap: break-word;
    }
    
    .wpai-message-user {
        background: #667eea;
        color: white;
        margin-left: auto;
        border-bottom-right-radius: 4px;
    }
    
    .wpai-message-assistant {
        background: white;
        color: #333;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
        border-bottom-left-radius: 4px;
    }
    
    .wpai-chatbot-input-container {
        padding: 16px;
        background: white;
        border-top: 1px solid #e0e0e0;
        display: flex;
        gap: 12px;
    }
    
    .wpai-chatbot-input {
        flex: 1;
        border: 1px solid #ddd;
        border-radius: 20px;
        padding: 10px 16px;
        font-size: 14px;
        resize: none;
        max-height: 120px;
        min-height: 40px;
    }
    
    .wpai-chatbot-send {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        background: #667eea;
        color: white;
        border: none;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    </style>
    
    <script>
    jQuery(document).ready(function($) {
        const $chatbot = $('#<?php echo esc_js($id); ?>');
        const $button = $chatbot.find('.wpai-chatbot-button');
        const $window = $chatbot.find('.wpai-chatbot-window');
        const $messages = $chatbot.find('.wpai-chatbot-messages');
        const $input = $chatbot.find('.wpai-chatbot-input');
        const $send = $chatbot.find('.wpai-chatbot-send');
        const $close = $chatbot.find('.wpai-chatbot-close');
        
        $button.on('click', function() {
            $window.fadeIn(200);
            $input.focus();
        });
        
        $close.on('click', function() {
            $window.fadeOut(200);
        });
        
        $send.on('click', function() {
            sendMessage();
        });
        
        $input.on('keypress', function(e) {
            if (e.which === 13 && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
        
        function sendMessage() {
            const message = $input.val().trim();
            if (!message) return;
            
            $input.val('');
            addMessage('user', message);
            
            // Simulate AI response for now
            setTimeout(function() {
                addMessage('assistant', 'Hello! This is a demo response. Please configure your OpenAI API key in Settings to enable real AI responses.');
            }, 1000);
        }
        
        function addMessage(role, content) {
            const $message = $('<div>')
                .addClass('wpai-message wpai-message-' + role)
                .text(content);
            
            $messages.append($message);
            $messages.scrollTop($messages[0].scrollHeight);
        }
    });
    </script>
    <?php
    
    return ob_get_clean();
}


