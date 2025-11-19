<?php
/**
 * Shortcode Handler
 * 
 * @package WPAIEnginePro
 */

// Exit if accessed directly
if (!defined('ABSPATH')) {
    exit;
}

/**
 * Register chatbot shortcode
 */
add_shortcode('wpai_chatbot', 'wpai_chatbot_shortcode');

/**
 * Render chatbot shortcode
 * 
 * @param array $atts Shortcode attributes
 * @return string HTML output
 */
function wpai_chatbot_shortcode($atts) {
    // Parse attributes with defaults
    $atts = shortcode_atts([
        'title' => 'AI Assistant',
        'theme' => 'light',
        'position' => 'bottom-right',
        'width' => '400px',
        'height' => '600px',
    ], $atts, 'wpai_chatbot');
    
    // Sanitize attributes
    $title = sanitize_text_field($atts['title']);
    $theme = in_array($atts['theme'], ['light', 'dark']) ? $atts['theme'] : 'light';
    $position = in_array($atts['position'], ['bottom-right', 'bottom-left']) ? $atts['position'] : 'bottom-right';
    $width = sanitize_text_field($atts['width']);
    $height = sanitize_text_field($atts['height']);
    
    // Check if API key is configured
    $options = get_option('wpai_options', []);
    $api_key_set = !empty($options['openai_api_key']);
    
    if (!$api_key_set) {
        if (current_user_can('manage_options')) {
            return '<div class="wpai-error" style="padding: 20px; background: #f8d7da; border: 1px solid #f5c6cb; border-radius: 4px; color: #721c24;">
                <strong>WP AI Engine Pro:</strong> Please configure your OpenAI API key in 
                <a href="' . esc_url(admin_url('admin.php?page=wpai-settings')) . '">Settings</a>.
            </div>';
        }
        return ''; // Don't show error to non-admins
    }
    
    // Enqueue chatbot assets
    wp_enqueue_style('wpai-chatbot', WPAI_URL . 'assets/chatbot.css', [], WPAI_VERSION);
    wp_enqueue_script('wpai-chatbot', WPAI_URL . 'assets/chatbot.js', ['jquery'], WPAI_VERSION, true);
    
    // Localize script with settings
    wp_localize_script('wpai-chatbot', 'wpaiChatbot', [
        'restUrl' => rest_url('wpai/v1/chat'),
        'nonce' => wp_create_nonce('wp_rest'),
        'title' => $title,
        'theme' => $theme,
    ]);
    
    // Generate unique ID for this chatbot instance
    $chatbot_id = 'wpai-chatbot-' . wp_generate_password(8, false);
    
    // Build HTML
    ob_start();
    ?>
    <div id="<?php echo esc_attr($chatbot_id); ?>" 
         class="wpai-chatbot-container wpai-theme-<?php echo esc_attr($theme); ?> wpai-position-<?php echo esc_attr($position); ?>"
         style="max-width: <?php echo esc_attr($width); ?>; max-height: <?php echo esc_attr($height); ?>;">
        
        <div class="wpai-chatbot-header">
            <h3><?php echo esc_html($title); ?></h3>
            <button class="wpai-minimize" aria-label="Minimize">−</button>
        </div>
        
        <div class="wpai-chatbot-messages" id="<?php echo esc_attr($chatbot_id); ?>-messages">
            <div class="wpai-message wpai-message-assistant">
                <div class="wpai-message-content">
                    Hello! I'm your AI assistant. How can I help you today?
                </div>
            </div>
        </div>
        
        <div class="wpai-chatbot-input">
            <form class="wpai-chat-form" data-chatbot-id="<?php echo esc_attr($chatbot_id); ?>">
                <input type="text" 
                       class="wpai-input" 
                       placeholder="Type your message..." 
                       required 
                       maxlength="5000"
                       autocomplete="off" />
                <button type="submit" class="wpai-send-btn" aria-label="Send">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="22" y1="2" x2="11" y2="13"></line>
                        <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                    </svg>
                </button>
            </form>
        </div>
        
        <div class="wpai-chatbot-footer">
            <small>Powered by <a href="https://seatechone.com" target="_blank" rel="noopener">SeaTechOne.com</a></small>
        </div>
    </div>
    <?php
    
    return ob_get_clean();
}

