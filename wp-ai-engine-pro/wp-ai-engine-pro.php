<?php
/**
 * Plugin Name: WP AI Engine Pro
 * Plugin URI: https://github.com/yourusername/wp-ai-engine-pro
 * Description: Advanced AI Engine for WordPress with enhanced MCP support, realtime chatbots, and complete ChatGPT control. Improved version with modern architecture.
 * Version: 4.0.0
 * Author: AI Development Team
 * Author URI: https://example.com
 * Text Domain: wp-ai-engine-pro
 * Domain Path: /languages
 * Requires at least: 6.0
 * Requires PHP: 8.1
 * License: GPLv3 or later
 * License URI: https://www.gnu.org/licenses/gpl-3.0.html
 * 
 * @package WPAIEnginePro
 */

declare(strict_types=1);

// Exit if accessed directly
if (!defined('ABSPATH')) {
    exit;
}

// Plugin Constants
define('WPAI_VERSION', '4.0.0');
define('WPAI_PREFIX', 'wpai');
define('WPAI_DOMAIN', 'wp-ai-engine-pro');
define('WPAI_ENTRY', __FILE__);
define('WPAI_PATH', dirname(__FILE__));
define('WPAI_URL', plugin_dir_url(__FILE__));
define('WPAI_MIN_PHP', '8.1.0');
define('WPAI_MIN_WP', '6.0');

// Timeout configurations
if (!defined('WPAI_TIMEOUT')) {
    define('WPAI_TIMEOUT', 120);
}

// Default models (2025 latest)
define('WPAI_FALLBACK_MODEL', 'gpt-5-chat-latest');
define('WPAI_FALLBACK_MODEL_VISION', 'gpt-5-chat-latest');
define('WPAI_FALLBACK_MODEL_JSON', 'gpt-5-mini');
define('WPAI_FALLBACK_EMBEDDINGS', 'text-embedding-3-large');

/**
 * Check requirements
 */
function wpai_check_requirements(): bool {
    global $wp_version;
    
    if (version_compare(PHP_VERSION, WPAI_MIN_PHP, '<')) {
        add_action('admin_notices', function() {
            printf(
                '<div class="error"><p>WP AI Engine Pro requires PHP %s or higher. You are running %s.</p></div>',
                esc_html(WPAI_MIN_PHP),
                esc_html(PHP_VERSION)
            );
        });
        return false;
    }
    
    if (version_compare($wp_version, WPAI_MIN_WP, '<')) {
        add_action('admin_notices', function() use ($wp_version) {
            printf(
                '<div class="error"><p>WP AI Engine Pro requires WordPress %s or higher. You are running %s.</p></div>',
                esc_html(WPAI_MIN_WP),
                esc_html($wp_version)
            );
        });
        return false;
    }
    
    return true;
}

if (!wpai_check_requirements()) {
    return;
}

// Load Composer autoloader
if (file_exists(WPAI_PATH . '/vendor/autoload.php')) {
    require_once WPAI_PATH . '/vendor/autoload.php';
}

// Load core files
require_once WPAI_PATH . '/includes/functions.php';
require_once WPAI_PATH . '/includes/class-autoloader.php';
require_once WPAI_PATH . '/includes/class-core.php';

/**
 * Initialize the plugin
 */
function wpai_init(): void {
    \WPAI\Autoloader::register();
    \WPAI\Core::instance();
}

/**
 * Activation hook
 */
function wpai_activate(): void {
    if (!wpai_check_requirements()) {
        wp_die(
            'WP AI Engine Pro requires PHP 8.1+ and WordPress 6.0+',
            'Plugin Activation Error',
            ['back_link' => true]
        );
    }
    
    require_once WPAI_PATH . '/includes/class-installer.php';
    \WPAI\Installer::activate();
}

/**
 * Deactivation hook
 */
function wpai_deactivate(): void {
    require_once WPAI_PATH . '/includes/class-installer.php';
    \WPAI\Installer::deactivate();
}

register_activation_hook(__FILE__, 'wpai_activate');
register_deactivation_hook(__FILE__, 'wpai_deactivate');

add_action('plugins_loaded', 'wpai_init', 10);

/**
 * Enhanced exception handler for better error messages
 */
add_filter('wpai_ai_exception', function($exception) {
    if (!is_string($exception)) {
        return $exception;
    }
    
    // Remove service prefixes
    $prefixes = ['OpenAI:', 'Anthropic:', 'Google:', 'Azure:', 'Mistral:', 'Perplexity:'];
    foreach ($prefixes as $prefix) {
        if (strpos($exception, $prefix) === 0) {
            $exception = trim(substr($exception, strlen($prefix)));
            break;
        }
    }
    
    // Parse JSON errors
    $json = json_decode($exception, true);
    if (is_array($json) && isset($json['error']['message'])) {
        $exception = $json['error']['message'];
    }
    
    // Provide helpful messages for common errors
    $error_mappings = [
        'API URL was not found' => 'API endpoint not found. Your OpenAI account may not be enabled for the API. Please add credits or link a payment method at https://platform.openai.com/account/billing',
        'quota' => 'API quota exceeded. Please check your usage limits at https://platform.openai.com/account/usage',
        'rate limit' => 'Rate limit reached. Please wait a moment and try again.',
        'authentication' => 'Authentication failed. Please verify your API key in Settings > WP AI Engine Pro.',
        'API key' => 'Invalid API key. Please check your API key configuration.',
        'model not found' => 'The selected AI model is not available. Please choose a different model or check your API access.',
        'context length' => 'Message too long. Please reduce the length of your message or conversation history.',
    ];
    
    foreach ($error_mappings as $keyword => $message) {
        if (stripos($exception, $keyword) !== false) {
            return $message;
        }
    }
    
    return $exception;
}, 10, 1);

/**
 * Add custom cron schedules
 */
add_filter('cron_schedules', function($schedules) {
    $schedules['wpai_every_5min'] = [
        'interval' => 300,
        'display' => __('Every 5 Minutes', 'wp-ai-engine-pro')
    ];
    
    $schedules['wpai_every_15min'] = [
        'interval' => 900,
        'display' => __('Every 15 Minutes', 'wp-ai-engine-pro')
    ];
    
    $schedules['wpai_every_30min'] = [
        'interval' => 1800,
        'display' => __('Every 30 Minutes', 'wp-ai-engine-pro')
    ];
    
    return $schedules;
});



