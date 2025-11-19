<?php
/**
 * Chatbot Module
 * 
 * @package WPAIEnginePro
 */

declare(strict_types=1);

namespace WPAI\Modules;

if (!defined('ABSPATH')) {
    exit;
}

class Chatbot {
    private \WPAI\Core $core;
    
    public function __construct(\WPAI\Core $core) {
        $this->core = $core;
        
        // Register shortcode
        add_shortcode('wpai_chatbot', [$this, 'render_shortcode']);
        
        // Enqueue scripts when needed
        add_action('wp_footer', [$this, 'maybe_render_chatbot']);
    }
    
    public function render_shortcode($atts): string {
        $atts = shortcode_atts([
            'id' => 'default',
            'model' => $this->core->get_option('default_model'),
            'theme' => 'modern',
            'position' => 'bottom-right',
            'title' => 'AI Assistant',
        ], $atts);
        
        wp_enqueue_script('wpai-chatbot');
        wp_enqueue_style('wpai-chatbot');
        
        ob_start();
        ?>
        <div id="wpai-chatbot-<?php echo esc_attr($atts['id']); ?>" 
             class="wpai-chatbot wpai-theme-<?php echo esc_attr($atts['theme']); ?> wpai-position-<?php echo esc_attr($atts['position']); ?>"
             data-model="<?php echo esc_attr($atts['model']); ?>"
             data-title="<?php echo esc_attr($atts['title']); ?>">
            
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
        <?php
        return ob_get_clean();
    }
    
    public function maybe_render_chatbot(): void {
        if ($this->core->get_option('show_chatbot_globally', false)) {
            echo $this->render_shortcode([]);
        }
    }
}



