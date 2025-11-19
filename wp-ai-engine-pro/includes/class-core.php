<?php
/**
 * Core class
 * 
 * @package WPAIEnginePro
 */

declare(strict_types=1);

namespace WPAI;

if (!defined('ABSPATH')) {
    exit;
}

final class Core {
    private static ?Core $instance = null;
    
    public ?object $admin = null;
    public ?object $api = null;
    public ?object $chatbot = null;
    public ?object $mcp = null;
    public ?object $content_generator = null;
    public ?object $embeddings = null;
    
    private array $options = [];
    private string $option_name = 'wpai_options';
    public bool $is_rest = false;
    public bool $is_cli = false;
    
    private function __construct() {
        $this->is_rest = $this->check_if_rest();
        $this->is_cli = defined('WP_CLI') && WP_CLI;
        
        $this->load_options();
        
        add_action('plugins_loaded', [$this, 'init'], 5);
        add_action('wp_enqueue_scripts', [$this, 'register_scripts']);
        add_action('admin_enqueue_scripts', [$this, 'register_admin_scripts']);
    }
    
    public static function instance(): Core {
        if (self::$instance === null) {
            self::$instance = new self();
        }
        return self::$instance;
    }
    
    public function init(): void {
        load_plugin_textdomain('wp-ai-engine-pro', false, dirname(plugin_basename(WPAI_ENTRY)) . '/languages');
        
        // Initialize admin first
        if (is_admin()) {
            $this->admin = new \WPAI\Admin\Admin($this);
        }
        
        // Initialize REST API
        if ($this->is_rest) {
            $this->api = new \WPAI\API\Rest($this);
        }
        
        // Initialize MCP (Model Context Protocol) for ChatGPT control
        if ($this->get_option('mcp_enabled', true)) {
            $this->mcp = new \WPAI\MCP\Server($this);
        }
        
        // Initialize modules
        if ($this->get_option('module_chatbot', true)) {
            $this->chatbot = new \WPAI\Modules\Chatbot($this);
        }
        
        if ($this->get_option('module_content', true)) {
            $this->content_generator = new \WPAI\Modules\ContentGenerator($this);
        }
        
        if ($this->get_option('module_embeddings', true)) {
            $this->embeddings = new \WPAI\Modules\Embeddings($this);
        }
        
        do_action('wpai_core_init', $this);
    }
    
    public function register_scripts(): void {
        wp_register_script(
            'wpai-chatbot',
            WPAI_URL . 'assets/js/chatbot.js',
            ['jquery'],
            WPAI_VERSION,
            true
        );
        
        wp_register_style(
            'wpai-chatbot',
            WPAI_URL . 'assets/css/chatbot.css',
            [],
            WPAI_VERSION
        );
        
        wp_localize_script('wpai-chatbot', 'wpaiData', [
            'ajaxUrl' => admin_url('admin-ajax.php'),
            'restUrl' => rest_url('wpai/v1/'),
            'nonce' => wp_create_nonce('wpai_nonce'),
            'version' => WPAI_VERSION,
        ]);
    }
    
    public function register_admin_scripts(): void {
        wp_register_script(
            'wpai-admin',
            WPAI_URL . 'assets/js/admin.js',
            ['jquery', 'wp-i18n'],
            WPAI_VERSION,
            true
        );
        
        wp_register_style(
            'wpai-admin',
            WPAI_URL . 'assets/css/admin.css',
            [],
            WPAI_VERSION
        );
    }
    
    private function load_options(): void {
        $defaults = [
            'version' => WPAI_VERSION,
            'mcp_enabled' => true,
            'module_chatbot' => true,
            'module_content' => true,
            'module_embeddings' => true,
            'default_model' => WPAI_FALLBACK_MODEL,
            'max_tokens' => 4096,
            'temperature' => 0.7,
            'timeout' => WPAI_TIMEOUT,
        ];
        
        $this->options = array_merge($defaults, get_option($this->option_name, []));
    }
    
    public function get_option(string $key, $default = null) {
        return $this->options[$key] ?? $default;
    }
    
    public function set_option(string $key, $value): bool {
        $this->options[$key] = $value;
        return update_option($this->option_name, $this->options);
    }
    
    public function get_all_options(): array {
        return $this->options;
    }
    
    public function can_access_settings(): bool {
        return apply_filters('wpai_can_access_settings', current_user_can('manage_options'));
    }
    
    public function can_access_features(): bool {
        $can = current_user_can('editor') || current_user_can('administrator');
        return apply_filters('wpai_can_access_features', $can);
    }
    
    private function check_if_rest(): bool {
        if (defined('REST_REQUEST') && REST_REQUEST) {
            return true;
        }
        
        if (isset($_SERVER['REQUEST_URI'])) {
            $rest_prefix = trailingslashit(rest_get_url_prefix());
            return strpos($_SERVER['REQUEST_URI'], $rest_prefix) !== false;
        }
        
        return false;
    }
    
    private function __clone() {}
    
    public function __wakeup() {
        throw new \Exception("Cannot unserialize singleton");
    }
}

