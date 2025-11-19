<?php
/**
 * Plugin Name: WP AI Engine Pro
 * Plugin URI: https://seatechone.com
 * Description: Advanced AI Engine for WordPress with enhanced MCP support, realtime chatbots, and complete ChatGPT control. Production-ready with comprehensive security and testing.
 * Version: 4.3.5
 * Author: Saeed M. Vardani
 * Author URI: https://seatechone.com
 * Text Domain: wp-ai-engine-pro
 * Domain Path: /languages
 * Requires at least: 6.0
 * Requires PHP: 7.4
 * License: GPLv3 or later
 * License URI: https://www.gnu.org/licenses/gpl-3.0.html
 * 
 * @package WPAIEnginePro
 * @developer Saeed M. Vardani
 * @company SeaTechOne.com
 */

// Removed strict_types for better compatibility
// declare(strict_types=1);

/**
 * Handle OAuth discovery BEFORE WordPress loads (runs at plugin load time)
 * This intercepts requests at the PHP level before WordPress REST API processes them
 * MUST run BEFORE ABSPATH check!
 */
function wpai_intercept_oauth_discovery_before_wp() {
    // Only handle GET and OPTIONS requests
    $method = isset($_SERVER['REQUEST_METHOD']) ? $_SERVER['REQUEST_METHOD'] : '';
    if ($method !== 'GET' && $method !== 'OPTIONS') {
        return false;
    }
    
    $request_uri = isset($_SERVER['REQUEST_URI']) ? $_SERVER['REQUEST_URI'] : '';
    
    // Check if this is an OAuth discovery request OR PRM request
    $is_oauth = false;
    $is_prm_early = false;
    if ($request_uri) {
        // RFC 8414: Path-inserted AS discovery URL (ChatGPT tries FIRST)
        // Exact match: /.well-known/oauth-authorization-server/wp-json/wpai/v1
        if (preg_match('#/\.well-known/oauth-authorization-server/wp-json/wpai/v1#', $request_uri)) {
            $is_oauth = true;
        }
        
        // OAuth discovery patterns (fallbacks)
        if (!$is_oauth && (
            preg_match('#/\.well-known/oauth-authorization-server#', $request_uri) ||
            preg_match('#/wp-json/wpai/v1/\.well-known/oauth-authorization-server#', $request_uri) ||
            preg_match('#/wp-json/wpai/v1/oauth-authorization-server#', $request_uri) ||
            preg_match('#/wp-json/wpai/v1/well-known/oauth-authorization-server#', $request_uri) ||
            strpos($request_uri, 'oauth-authorization-server') !== false)) {
            $is_oauth = true;
        }
        
        // RFC 9728: PRM discovery patterns (exact paths ChatGPT looks for)
        // Exact match: /.well-known/oauth-protected-resource/wp-json/wpai/v1/mcp
        if (preg_match('#/\.well-known/oauth-protected-resource/wp-json/wpai/v1/mcp#', $request_uri)) {
            $is_prm_early = true;
        }
        // Root PRM: /.well-known/oauth-protected-resource
        if (!$is_prm_early && preg_match('#/\.well-known/oauth-protected-resource$#', $request_uri)) {
            $is_prm_early = true;
        }
    }
    
    if ($is_oauth) {
        // Set headers
        header('Content-Type: application/json');
        header('Access-Control-Allow-Origin: *');
        header('Access-Control-Allow-Methods: GET, OPTIONS');
        header('Access-Control-Allow-Headers: Content-Type, Authorization');
        
        // Handle OPTIONS (CORS preflight)
        if ($method === 'OPTIONS') {
            http_response_code(200);
            exit;
        }
        
        // Build URLs (WordPress might not be loaded yet)
        $protocol = (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off') ? 'https' : 'http';
        $host = isset($_SERVER['HTTP_HOST']) ? $_SERVER['HTTP_HOST'] : (isset($_SERVER['SERVER_NAME']) ? $_SERVER['SERVER_NAME'] : 'localhost');
        $site_url = $protocol . '://' . $host;
        $rest_base = $site_url . '/wp-json/wpai/v1';
        
        // Return RFC 8414 compliant OAuth 2.0 Authorization Server Metadata
        // MUST include registration_endpoint and jwks_uri for ChatGPT/MCP
        // MUST allow "none" for token_endpoint_auth_methods (public clients)
        // MUST only advertise S256 for PKCE
        $oauth_metadata = [
            'issuer' => $rest_base,
            'authorization_endpoint' => $rest_base . '/oauth/authorize',
            'token_endpoint' => $rest_base . '/oauth/token',
            'registration_endpoint' => $rest_base . '/oauth/register', // REQUIRED for DCR
            'jwks_uri' => $rest_base . '/oauth/jwks.json', // REQUIRED for JWT verification
            'response_types_supported' => ['code'],
            'grant_types_supported' => ['authorization_code', 'refresh_token'],
            'code_challenge_methods_supported' => ['S256'], // S256 only (PKCE required)
            'token_endpoint_auth_methods_supported' => ['none'], // MUST allow "none" for public clients
            'revocation_endpoint' => $rest_base . '/oauth/revoke',
            'revocation_endpoint_auth_methods_supported' => ['none'],
            'scopes_supported' => ['read', 'write'],
            'service_documentation' => $site_url,
            'ui_locales_supported' => ['en-US'],
            'op_policy_uri' => $site_url,
            'op_tos_uri' => $site_url,
        ];
        
        // Ensure Content-Type is application/json (critical for ChatGPT)
        header('Content-Type: application/json', true);
        // Output JSON (no pretty print for production - smaller response)
        echo json_encode($oauth_metadata, JSON_UNESCAPED_SLASHES);
        exit;
    }
    
    // Handle PRM discovery early (before WordPress loads)
    if ($is_prm_early) {
        header('Content-Type: application/json');
        header('Access-Control-Allow-Origin: *');
        header('Access-Control-Allow-Methods: GET, OPTIONS');
        header('Access-Control-Allow-Headers: Content-Type, Authorization');
        
        if ($method === 'OPTIONS') {
            http_response_code(200);
            exit;
        }
        
        // Build URLs
        $protocol = (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off') ? 'https' : 'http';
        $host = isset($_SERVER['HTTP_HOST']) ? $_SERVER['HTTP_HOST'] : (isset($_SERVER['SERVER_NAME']) ? $_SERVER['SERVER_NAME'] : 'localhost');
        $site_url = $protocol . '://' . $host;
        $mcp_url = $site_url . '/wp-json/wpai/v1/mcp';
        $issuer = $site_url . '/wp-json/wpai/v1';
        
        // Check if resource-specific PRM
        $is_resource_specific = preg_match('#/\.well-known/oauth-protected-resource/wp-json/wpai/v1/mcp#', $request_uri);
        
        // RFC 9728 Protected Resource Metadata (exact format required)
        // Must match exact field names per RFC 9728
        $prm = [
            'resource' => $mcp_url, // Exact MCP endpoint URL
            'authorization_servers' => [$issuer], // MCP requires this array - MUST be array
            'scopes_supported' => ['read', 'write'], // Required
        ];
        
        // Ensure Content-Type is application/json
        header('Content-Type: application/json', true);
        echo json_encode($prm, JSON_UNESCAPED_SLASHES); // No pretty print for production
        exit;
    }
    
    return false;
}

// Run immediately when plugin file is loaded (BEFORE ABSPATH check)
// This intercepts the request before WordPress REST API processes it
// CRITICAL: Must run before WordPress processes request to catch .well-known paths
// This runs at plugin load time, before WordPress routing
wpai_intercept_oauth_discovery_before_wp();

// Exit if accessed directly (normal WordPress security check)
if (!defined('ABSPATH')) {
    exit;
}

// Plugin Constants
define('WPAI_VERSION', '4.3.5');
define('WPAI_PREFIX', 'wpai');
define('WPAI_DOMAIN', 'wp-ai-engine-pro');
define('WPAI_ENTRY', __FILE__);
define('WPAI_PATH', dirname(__FILE__));
define('WPAI_URL', plugin_dir_url(__FILE__));
define('WPAI_MIN_PHP', '7.4.0'); // Lowered for better compatibility
define('WPAI_MIN_WP', '6.0');

// Timeout configurations
if (!defined('WPAI_TIMEOUT')) {
    define('WPAI_TIMEOUT', 120);
}

// Default models (2025 latest)
define('WPAI_FALLBACK_MODEL', 'gpt-4o');
define('WPAI_FALLBACK_MODEL_VISION', 'gpt-4o');
define('WPAI_FALLBACK_MODEL_JSON', 'gpt-4o-mini');
define('WPAI_FALLBACK_EMBEDDINGS', 'text-embedding-3-large');

/**
 * Check requirements
 * 
 * @return bool True if requirements are met
 */
function wpai_check_requirements() {
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

/**
 * Log errors for debugging
 * 
 * @param string $message Error message
 * @param array $context Additional context
 */
function wpai_log_error($message, $context = array()) {
    if (defined('WP_DEBUG') && WP_DEBUG && defined('WP_DEBUG_LOG') && WP_DEBUG_LOG) {
        error_log(sprintf(
            '[WP AI Engine Pro] %s %s',
            $message,
            !empty($context) ? json_encode($context) : ''
        ));
    }
}

/**
 * Simple Admin Menu Class
 */
class WPAI_Simple_Admin {
    
    public function __construct() {
        add_action('admin_menu', [$this, 'add_menu']);
        add_action('admin_init', [$this, 'init_settings']);
        add_action('admin_enqueue_scripts', [$this, 'enqueue_admin_assets']);
    }
    
    /**
     * Enqueue admin assets
     */
    public function enqueue_admin_assets($hook) {
        // Only load on our plugin pages
        if (strpos($hook, 'wpai') === false) {
            return;
        }
        
        wp_enqueue_style('wpai-admin', WPAI_URL . 'assets/admin.css', [], WPAI_VERSION);
        wp_enqueue_script('wpai-admin', WPAI_URL . 'assets/admin.js', ['jquery'], WPAI_VERSION, true);
        
        // Localize script with nonce
        wp_localize_script('wpai-admin', 'wpaiAdmin', [
            'nonce' => wp_create_nonce('wpai_admin_nonce'),
            'restUrl' => rest_url('wpai/v1/'),
            'ajaxUrl' => admin_url('admin-ajax.php'),
        ]);
    }
    
    /**
     * Add admin menu pages
     */
    public function add_menu() {
        // Main menu
        add_menu_page(
            'WP AI Engine Pro',
            'AI Engine',
            'manage_options',
            'wpai',
            [$this, 'render_dashboard'],
            'dashicons-admin-generic',
            30
        );
        
        // Submenu pages
        add_submenu_page(
            'wpai',
            'Dashboard',
            'Dashboard',
            'manage_options',
            'wpai',
            [$this, 'render_dashboard']
        );
        
        add_submenu_page(
            'wpai',
            'Settings',
            'Settings',
            'manage_options',
            'wpai-settings',
            [$this, 'render_settings']
        );
        
        add_submenu_page(
            'wpai',
            'MCP Setup',
            'MCP Setup',
            'manage_options',
            'wpai-mcp',
            [$this, 'render_mcp']
        );
        
        add_submenu_page(
            'wpai',
            'Test',
            'Test',
            'manage_options',
            'wpai-test',
            [$this, 'render_test']
        );
    }
    
    /**
     * Initialize settings
     */
    public function init_settings() {
        register_setting('wpai_settings', 'wpai_options', [
            'sanitize_callback' => [$this, 'sanitize_settings'],
        ]);
        
        add_settings_section(
            'wpai_main',
            'Main Settings',
            null,
            'wpai-settings'
        );
        
        add_settings_field(
            'openai_api_key',
            'OpenAI API Key',
            [$this, 'api_key_field'],
            'wpai-settings',
            'wpai_main'
        );
        
        add_settings_field(
            'default_model',
            'Default Model',
            [$this, 'model_field'],
            'wpai-settings',
            'wpai_main'
        );
        
        add_settings_field(
            'max_tokens',
            'Max Tokens',
            [$this, 'max_tokens_field'],
            'wpai-settings',
            'wpai_main'
        );
        
        add_settings_field(
            'temperature',
            'Temperature',
            [$this, 'temperature_field'],
            'wpai-settings',
            'wpai_main'
        );
    }
    
    /**
     * Sanitize settings before saving
     * 
     * @param array $input Raw input
     * @return array Sanitized input
     */
    public function sanitize_settings($input) {
        $sanitized = [];
        
        // Sanitize API key
        if (isset($input['openai_api_key'])) {
            $sanitized['openai_api_key'] = sanitize_text_field($input['openai_api_key']);
            
            // Validate API key format (starts with sk-)
            if (!empty($sanitized['openai_api_key']) && !preg_match('/^sk-[a-zA-Z0-9\-_]+$/', $sanitized['openai_api_key'])) {
                add_settings_error(
                    'wpai_options',
                    'invalid_api_key',
                    'Invalid API key format. OpenAI API keys should start with "sk-".',
                    'error'
                );
            }
        }
        
        // Sanitize model
        if (isset($input['default_model'])) {
            $allowed_models = ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-4', 'gpt-3.5-turbo'];
            $sanitized['default_model'] = in_array($input['default_model'], $allowed_models) 
                ? $input['default_model'] 
                : WPAI_FALLBACK_MODEL;
        }
        
        // Sanitize max_tokens
        if (isset($input['max_tokens'])) {
            $sanitized['max_tokens'] = absint($input['max_tokens']);
            if ($sanitized['max_tokens'] < 1 || $sanitized['max_tokens'] > 128000) {
                $sanitized['max_tokens'] = 4096;
            }
        }
        
        // Sanitize temperature
        if (isset($input['temperature'])) {
            $sanitized['temperature'] = floatval($input['temperature']);
            if ($sanitized['temperature'] < 0 || $sanitized['temperature'] > 2) {
                $sanitized['temperature'] = 0.7;
            }
        }
        
        return $sanitized;
    }
    
    /**
     * Render API key field
     */
    public function api_key_field() {
        $options = get_option('wpai_options', []);
        $value = $options['openai_api_key'] ?? '';
        $masked = !empty($value) ? 'sk-...' . substr($value, -4) : '';
        ?>
        <input type="password" 
               id="wpai_api_key" 
               name="wpai_options[openai_api_key]" 
               value="<?php echo esc_attr($value); ?>" 
               class="regular-text" 
               autocomplete="off" />
        <button type="button" class="button" onclick="document.getElementById('wpai_api_key').type = document.getElementById('wpai_api_key').type === 'password' ? 'text' : 'password'">
            Show/Hide
        </button>
        <p class="description">
            Get your API key from <a href="https://platform.openai.com/api-keys" target="_blank" rel="noopener">OpenAI</a>
            <?php if (!empty($masked)): ?>
                <br><strong>Current:</strong> <?php echo esc_html($masked); ?>
            <?php endif; ?>
        </p>
        <?php
    }
    
    /**
     * Render model field
     */
    public function model_field() {
        $options = get_option('wpai_options', []);
        $value = $options['default_model'] ?? WPAI_FALLBACK_MODEL;
        
        $models = [
            'gpt-4o' => 'GPT-4o (Recommended)',
            'gpt-4o-mini' => 'GPT-4o Mini (Faster & Cheaper)',
            'gpt-4-turbo' => 'GPT-4 Turbo',
            'gpt-4' => 'GPT-4',
            'gpt-3.5-turbo' => 'GPT-3.5 Turbo (Legacy)',
        ];
        
        echo '<select name="wpai_options[default_model]" class="regular-text">';
        foreach ($models as $key => $label) {
            printf(
                '<option value="%s" %s>%s</option>',
                esc_attr($key),
                selected($value, $key, false),
                esc_html($label)
            );
        }
        echo '</select>';
        echo '<p class="description">Select the default AI model for chat completions.</p>';
    }
    
    /**
     * Render max tokens field
     */
    public function max_tokens_field() {
        $options = get_option('wpai_options', []);
        $value = $options['max_tokens'] ?? 4096;
        ?>
        <input type="number" 
               name="wpai_options[max_tokens]" 
               value="<?php echo esc_attr($value); ?>" 
               min="1" 
               max="128000" 
               step="1" 
               class="small-text" />
        <p class="description">Maximum number of tokens to generate (1-128000). Default: 4096</p>
        <?php
    }
    
    /**
     * Render temperature field
     */
    public function temperature_field() {
        $options = get_option('wpai_options', []);
        $value = $options['temperature'] ?? 0.7;
        ?>
        <input type="number" 
               name="wpai_options[temperature]" 
               value="<?php echo esc_attr($value); ?>" 
               min="0" 
               max="2" 
               step="0.1" 
               class="small-text" />
        <p class="description">Sampling temperature (0-2). Higher values make output more random. Default: 0.7</p>
        <?php
    }
    
    /**
     * Render dashboard page
     */
    public function render_dashboard() {
        if (!current_user_can('manage_options')) {
            wp_die(esc_html__('You do not have sufficient permissions to access this page.', 'wp-ai-engine-pro'));
        }
        
        $options = get_option('wpai_options', []);
        $api_key_set = !empty($options['openai_api_key']);
        ?>
        <div class="wrap">
            <h1><?php echo esc_html(get_admin_page_title()); ?></h1>
            
            <div class="wpai-dashboard">
                <div class="wpai-stats">
                    <div class="wpai-stat-card">
                        <h3>Status</h3>
                        <p class="wpai-stat-number"><?php echo $api_key_set ? '✓ Active' : '⚠ Not Configured'; ?></p>
                    </div>
                    
                    <div class="wpai-stat-card">
                        <h3>Version</h3>
                        <p class="wpai-stat-number"><?php echo esc_html(WPAI_VERSION); ?></p>
                    </div>
                    
                    <div class="wpai-stat-card">
                        <h3>PHP Version</h3>
                        <p class="wpai-stat-number"><?php echo esc_html(PHP_VERSION); ?></p>
                    </div>
                    
                    <div class="wpai-stat-card">
                        <h3>WordPress</h3>
                        <p class="wpai-stat-number"><?php echo esc_html(get_bloginfo('version')); ?></p>
                    </div>
                </div>
                
                <?php if (!$api_key_set): ?>
                <div class="notice notice-warning">
                    <p><strong>Action Required:</strong> Please configure your OpenAI API key in <a href="<?php echo esc_url(admin_url('admin.php?page=wpai-settings')); ?>">Settings</a> to start using the plugin.</p>
                </div>
                <?php endif; ?>
                
                <div class="wpai-quick-actions">
                    <h2>Quick Actions</h2>
                    <a href="<?php echo esc_url(admin_url('admin.php?page=wpai-settings')); ?>" class="button button-primary">Configure Settings</a>
                    <a href="<?php echo esc_url(admin_url('admin.php?page=wpai-mcp')); ?>" class="button">Setup MCP</a>
                    <a href="<?php echo esc_url(admin_url('admin.php?page=wpai-test')); ?>" class="button">Test Plugin</a>
                </div>
                
                <div class="wpai-info">
                    <h2>Getting Started</h2>
                    <ol>
                        <li>Go to <strong>Settings</strong> and enter your OpenAI API key</li>
                        <li>Configure your preferred AI model</li>
                        <li>Add <code>[wpai_chatbot]</code> shortcode to any page</li>
                        <li>Optionally setup MCP for ChatGPT control</li>
                    </ol>
                    
                    <div class="wpai-credits">
                        <h3>Plugin Information</h3>
                        <p><strong>Developer:</strong> Saeed M. Vardani</p>
                        <p><strong>Company:</strong> <a href="https://seatechone.com" target="_blank" rel="noopener">SeaTechOne.com</a></p>
                        <p><strong>Version:</strong> <?php echo esc_html(WPAI_VERSION); ?></p>
                        <p><strong>Support:</strong> <a href="https://seatechone.com" target="_blank" rel="noopener">Visit SeaTechOne.com</a></p>
                    </div>
                </div>
            </div>
        </div>
        
        <style>
        .wpai-dashboard { max-width: 1200px; }
        .wpai-stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }
        .wpai-stat-card { background: #fff; border: 1px solid #ccd0d4; border-radius: 4px; padding: 20px; text-align: center; }
        .wpai-stat-card h3 { margin: 0 0 10px; font-size: 14px; color: #646970; }
        .wpai-stat-number { font-size: 24px; font-weight: bold; margin: 0; color: #1d2327; }
        .wpai-quick-actions { margin: 30px 0; }
        .wpai-quick-actions .button { margin-right: 10px; }
        .wpai-info { background: #fff; border: 1px solid #ccd0d4; border-radius: 4px; padding: 20px; margin: 20px 0; }
        .wpai-credits { margin-top: 30px; padding-top: 20px; border-top: 1px solid #dcdcde; }
        </style>
        <?php
    }
    
    /**
     * Render settings page
     */
    public function render_settings() {
        if (!current_user_can('manage_options')) {
            wp_die(esc_html__('You do not have sufficient permissions to access this page.', 'wp-ai-engine-pro'));
        }
        ?>
        <div class="wrap">
            <h1><?php echo esc_html(get_admin_page_title()); ?></h1>
            
            <form method="post" action="options.php">
                <?php
                settings_fields('wpai_settings');
                do_settings_sections('wpai-settings');
                submit_button();
                ?>
            </form>
            
            <div class="wpai-settings-info">
                <h3>Shortcode Usage</h3>
                <p>Add this shortcode to any page or post to display the chatbot:</p>
                <code>[wpai_chatbot]</code>
                
                <h3>Shortcode Options</h3>
                <ul>
                    <li><code>[wpai_chatbot title="My Assistant"]</code> - Custom title</li>
                    <li><code>[wpai_chatbot theme="dark"]</code> - Dark theme</li>
                    <li><code>[wpai_chatbot position="bottom-left"]</code> - Left position</li>
                </ul>
                
                <h3>REST API Endpoints</h3>
                <ul>
                    <li><strong>Chat:</strong> <code><?php echo esc_html(rest_url('wpai/v1/chat')); ?></code></li>
                    <li><strong>MCP:</strong> <code><?php echo esc_html(rest_url('wpai/v1/mcp')); ?></code></li>
                    <li><strong>OAuth:</strong> <code><?php echo esc_html(rest_url('wpai/v1/oauth/authorize')); ?></code></li>
                </ul>
            </div>
        </div>
        
        <style>
        .wpai-settings-info { background: #fff; border: 1px solid #ccd0d4; border-radius: 4px; padding: 20px; margin: 20px 0; max-width: 800px; }
        .wpai-settings-info h3 { margin-top: 20px; }
        .wpai-settings-info code { background: #f0f0f1; padding: 2px 6px; border-radius: 3px; }
        </style>
        <?php
    }
    
    /**
     * Render MCP setup page
     */
    public function render_mcp() {
        if (!current_user_can('manage_options')) {
            wp_die(esc_html__('You do not have sufficient permissions to access this page.', 'wp-ai-engine-pro'));
        }
        
        $plugin_path = WPAI_PATH;
        $mcp_server_path = $plugin_path . '/mcp-server.php';
        $site_url = get_site_url();
        $mcp_http_url = rest_url('wpai/v1/mcp');
        $oauth_config_url = rest_url('wpai/v1/.well-known/oauth-authorization-server');
        
        ?>
        <div class="wrap">
            <h1><?php echo esc_html(get_admin_page_title()); ?></h1>
            
            <div class="wpai-mcp-setup">
                
                <div style="background: #d4edda; border-left: 4px solid #28a745; padding: 20px; margin: 20px 0;">
                    <h2 style="margin-top: 0;">🌐 For ChatGPT Browser (Dev Mode)</h2>
                    <p><strong>Your MCP Server URL:</strong></p>
                    <input type="text" 
                           value="<?php echo esc_attr($mcp_http_url); ?>" 
                           readonly 
                           style="width: 100%; padding: 10px; font-family: monospace; font-size: 14px; margin: 10px 0;" 
                           onclick="this.select()" />
                    <button type="button" class="button button-primary" onclick="navigator.clipboard.writeText('<?php echo esc_js($mcp_http_url); ?>'); alert('Copied to clipboard!');">
                        📋 Copy URL
                    </button>
                    <p style="margin-top: 15px;"><strong>Status:</strong> <span style="color: green;">✓ HTTP endpoint ready with OAuth</span></p>
                    <p><strong>Protocol:</strong> MCP over HTTP with OAuth 2.0 + PKCE</p>
                    <p><strong>OAuth Discovery:</strong> <a href="<?php echo esc_url($oauth_config_url); ?>" target="_blank" rel="noopener"><?php echo esc_html($oauth_config_url); ?></a></p>
                </div>
                
                <h2>Browser Dev Mode Setup</h2>
                <p>Use this URL in your ChatGPT browser dev mode MCP configuration:</p>
                <ol>
                    <li>Open ChatGPT in your browser</li>
                    <li>Enable Developer Mode</li>
                    <li>Add MCP server with the URL above</li>
                    <li>ChatGPT will automatically discover OAuth configuration</li>
                    <li>Authorize the connection when prompted</li>
                </ol>
                
                <h3>Test the Endpoints</h3>
                <p>You can test if the endpoints are working:</p>
                <a href="<?php echo esc_url($mcp_http_url); ?>" target="_blank" rel="noopener" class="button">🔗 Test MCP Endpoint</a>
                <a href="<?php echo esc_url($oauth_config_url); ?>" target="_blank" rel="noopener" class="button">🔐 Test OAuth Discovery</a>
                
                <hr style="margin: 40px 0;" />
                
                <h2>Available WordPress Tools</h2>
                <div style="background: #fff; border: 1px solid #ccd0d4; border-radius: 4px; padding: 20px;">
                    <ul>
                        <li><strong>wp_get_site_info</strong> - Get WordPress site information</li>
                        <li><strong>wp_list_posts</strong> - List WordPress posts</li>
                        <li><strong>wp_create_post</strong> - Create new posts</li>
                        <li><strong>wp_get_stats</strong> - Get site statistics</li>
                    </ul>
                </div>
                
                <div style="margin-top: 30px; padding-top: 20px; border-top: 2px solid #eee;">
                    <p><strong>Developer:</strong> Saeed M. Vardani | <strong>Company:</strong> SeaTechOne.com</p>
                </div>
            </div>
        </div>
        <?php
    }
    
    /**
     * Render test page
     */
    public function render_test() {
        if (!current_user_can('manage_options')) {
            wp_die(esc_html__('You do not have sufficient permissions to access this page.', 'wp-ai-engine-pro'));
        }
        
        $options = get_option('wpai_options', []);
        $api_key = $options['openai_api_key'] ?? '';
        $model = $options['default_model'] ?? WPAI_FALLBACK_MODEL;
        $nonce = wp_create_nonce('wpai_test_nonce');
        
        ?>
        <div class="wrap">
            <h1><?php echo esc_html(get_admin_page_title()); ?></h1>
            
            <div class="wpai-test-results">
                <h2>Current Settings</h2>
                
                <table class="wp-list-table widefat fixed striped">
                    <thead>
                        <tr>
                            <th>Setting</th>
                            <th>Value</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>OpenAI API Key</td>
                            <td><?php echo !empty($api_key) ? '✓ Set' : '✗ Not Set'; ?></td>
                            <td><?php echo !empty($api_key) ? '<span style="color: green;">Ready</span>' : '<span style="color: red;">Missing</span>'; ?></td>
                        </tr>
                        <tr>
                            <td>Default Model</td>
                            <td><?php echo esc_html($model); ?></td>
                            <td><span style="color: green;">OK</span></td>
                        </tr>
                        <tr>
                            <td>Plugin Version</td>
                            <td><?php echo esc_html(WPAI_VERSION); ?></td>
                            <td><span style="color: green;">OK</span></td>
                        </tr>
                        <tr>
                            <td>PHP Version</td>
                            <td><?php echo esc_html(PHP_VERSION); ?></td>
                            <td><?php echo version_compare(PHP_VERSION, '8.1', '>=') ? '<span style="color: green;">OK</span>' : '<span style="color: orange;">Upgrade Recommended</span>'; ?></td>
                        </tr>
                        <tr>
                            <td>cURL Extension</td>
                            <td><?php echo function_exists('curl_init') ? 'Installed' : 'Missing'; ?></td>
                            <td><?php echo function_exists('curl_init') ? '<span style="color: green;">OK</span>' : '<span style="color: red;">Required</span>'; ?></td>
                        </tr>
                    </tbody>
                </table>
                
                <h2>Quick Test</h2>
                <p>Test the chatbot shortcode: <code>[wpai_chatbot]</code></p>
                <p>Add this to any page or post to test the chatbot functionality.</p>
                
                <?php if (!empty($api_key)): ?>
                <h2>API Test</h2>
                <button id="test-api" class="button button-primary">Test API Connection</button>
                <div id="api-test-result" style="margin-top: 15px;"></div>
                
                <script>
                document.getElementById('test-api').addEventListener('click', async function() {
                    const button = this;
                    const resultDiv = document.getElementById('api-test-result');
                    
                    button.disabled = true;
                    button.textContent = 'Testing...';
                    resultDiv.innerHTML = '<p>Connecting to OpenAI API...</p>';
                    
                    try {
                        const response = await fetch('<?php echo esc_js(rest_url('wpai/v1/chat')); ?>', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                'X-WP-Nonce': '<?php echo esc_js(wp_create_nonce('wp_rest')); ?>'
                            },
                            body: JSON.stringify({
                                message: 'Hello! Please respond with "API test successful" if you receive this message.',
                                model: '<?php echo esc_js($model); ?>'
                            })
                        });
                        
                        const data = await response.json();
                        
                        if (response.ok && data.success) {
                            resultDiv.innerHTML = '<div style="background: #d4edda; border-left: 4px solid #28a745; padding: 15px; border-radius: 4px;">' +
                                '<h3 style="margin-top: 0; color: #155724;">✓ API Test Successful!</h3>' +
                                '<p><strong>Model:</strong> ' + (data.model || 'N/A') + '</p>' +
                                '<p><strong>Tokens Used:</strong> ' + (data.tokens || 'N/A') + '</p>' +
                                '<p><strong>Response:</strong></p>' +
                                '<div style="background: #fff; padding: 10px; border-radius: 3px; margin-top: 10px;">' + 
                                (data.response || 'No response') + 
                                '</div>' +
                                '</div>';
                        } else {
                            resultDiv.innerHTML = '<div style="background: #f8d7da; border-left: 4px solid #dc3545; padding: 15px; border-radius: 4px;">' +
                                '<h3 style="margin-top: 0; color: #721c24;">✗ API Test Failed</h3>' +
                                '<p><strong>Error:</strong> ' + (data.error || data.message || 'Unknown error') + '</p>' +
                                '<p>Please check your API key in Settings.</p>' +
                                '</div>';
                        }
                    } catch (error) {
                        resultDiv.innerHTML = '<div style="background: #f8d7da; border-left: 4px solid #dc3545; padding: 15px; border-radius: 4px;">' +
                            '<h3 style="margin-top: 0; color: #721c24;">✗ Connection Error</h3>' +
                            '<p><strong>Error:</strong> ' + error.message + '</p>' +
                            '<p>Please check your network connection and WordPress REST API.</p>' +
                            '</div>';
                    } finally {
                        button.disabled = false;
                        button.textContent = 'Test API Connection';
                    }
                });
                </script>
                <?php else: ?>
                <div style="background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; border-radius: 4px; margin: 20px 0;">
                    <strong>⚠️ API Key Required</strong><br />
                    Please set your OpenAI API key in <a href="<?php echo esc_url(admin_url('admin.php?page=wpai-settings')); ?>">Settings</a> to test the API connection.
                </div>
                <?php endif; ?>
            </div>
        </div>
        <?php
    }
}

/**
 * Initialize the plugin
 */
function wpai_init() {
    // Initialize admin menu (register even if there are errors)
    try {
        new WPAI_Simple_Admin();
    } catch (Exception $e) {
        // Log error but don't break plugin
        wpai_log_error('Admin menu initialization error: ' . $e->getMessage());
        // Still try to add basic menu
        add_action('admin_menu', function() {
            add_menu_page(
                'WP AI Engine Pro',
                'AI Engine',
                'manage_options',
                'wpai',
                function() {
                    echo '<div class="wrap"><h1>WP AI Engine Pro</h1><p>Settings page unavailable. Check error logs.</p></div>';
                },
                'dashicons-admin-generic',
                30
            );
        });
    }
}

/**
 * Add rewrite rules (must be called after 'init' when $wp_rewrite is available)
 */
function wpai_add_rewrite_rules() {
    // Only add rules if $wp_rewrite is available and initialized
    global $wp_rewrite;
    if (!isset($wp_rewrite) || !is_object($wp_rewrite) || !method_exists($wp_rewrite, 'add_rule')) {
        return;
    }
    
    // RFC 8414: When issuer has a path, clients try: /.well-known/oauth-authorization-server/{issuer_path}
    // For issuer=https://searei.com/wp-json/wpai/v1, they try:
    // https://searei.com/.well-known/oauth-authorization-server/wp-json/wpai/v1
    add_rewrite_rule(
        '^\.well-known/oauth-authorization-server/wp-json/wpai/v1$',
        'index.php?wpai_oauth_discovery=1',
        'top'
    );
    
    // RFC 8414: OIDC fallback
    add_rewrite_rule(
        '^\.well-known/openid-configuration/wp-json/wpai/v1$',
        'index.php?wpai_oauth_discovery=1',
        'top'
    );
    
    // RFC 9728: Protected Resource Metadata (PRM)
    // ChatGPT looks for: /.well-known/oauth-protected-resource
    add_rewrite_rule(
        '^\.well-known/oauth-protected-resource$',
        'index.php?wpai_prm_discovery=1',
        'top'
    );
    
    // RFC 9728: PRM for specific resource
    add_rewrite_rule(
        '^\.well-known/oauth-protected-resource/wp-json/wpai/v1/mcp$',
        'index.php?wpai_prm_discovery=1',
        'top'
    );
    
    // Legacy paths for compatibility
    add_rewrite_rule(
        '^wp-json/wpai/v1/\.well-known/oauth-authorization-server$',
        'index.php?wpai_oauth_discovery=1',
        'top'
    );
    
    add_rewrite_rule(
        '^wp-json/wpai/v1/oauth-authorization-server$',
        'index.php?wpai_oauth_discovery=1',
        'top'
    );
    
    add_rewrite_rule(
        '^wp-json/wpai/v1/well-known/oauth-authorization-server$',
        'index.php?wpai_oauth_discovery=1',
        'top'
    );
    
    // Root level .well-known (without path)
    add_rewrite_rule(
        '^\.well-known/oauth-authorization-server$',
        'index.php?wpai_oauth_discovery=1',
        'top'
    );
}

/**
 * Handle OAuth discovery DIRECTLY (bypasses REST API entirely)
 * This runs VERY early, before WordPress loads
 * Uses static flag to prevent multiple executions on same request
 */
function wpai_handle_oauth_discovery_direct() {
    // Prevent multiple executions on same request (rate limiting protection)
    static $already_handled = false;
    if ($already_handled) {
        return;
    }
    
    // Only handle GET and OPTIONS requests
    $method = isset($_SERVER['REQUEST_METHOD']) ? $_SERVER['REQUEST_METHOD'] : '';
    if ($method !== 'GET' && $method !== 'OPTIONS') {
        return;
    }
    
    $request_uri = isset($_SERVER['REQUEST_URI']) ? $_SERVER['REQUEST_URI'] : '';
    
    // Check for OAuth discovery paths (must match EXACTLY what ChatGPT requests)
    $is_oauth_discovery = false;
    
    // Exact patterns ChatGPT looks for
    if ($request_uri) {
        // RFC 8414: Path-inserted discovery URL (ChatGPT tries this FIRST)
        // For issuer=https://searei.com/wp-json/wpai/v1, ChatGPT tries:
        // https://searei.com/.well-known/oauth-authorization-server/wp-json/wpai/v1
        if (preg_match('#/\.well-known/oauth-authorization-server/wp-json/wpai/v1#', $request_uri)) {
            $is_oauth_discovery = true;
        }
        
        // RFC 8414: OIDC fallback
        if (!$is_oauth_discovery && preg_match('#/\.well-known/openid-configuration/wp-json/wpai/v1#', $request_uri)) {
            $is_oauth_discovery = true;
        }
        
        // Pattern 1: /wp-json/wpai/v1/.well-known/oauth-authorization-server
        if (!$is_oauth_discovery && preg_match('#/wp-json/wpai/v1/\.well-known/oauth-authorization-server#', $request_uri)) {
            $is_oauth_discovery = true;
        }
        
        // Pattern 2: /wp-json/wpai/v1/oauth-authorization-server
        if (!$is_oauth_discovery && preg_match('#/wp-json/wpai/v1/oauth-authorization-server#', $request_uri)) {
            $is_oauth_discovery = true;
        }
        
        // Pattern 3: /wp-json/wpai/v1/well-known/oauth-authorization-server
        if (!$is_oauth_discovery && preg_match('#/wp-json/wpai/v1/well-known/oauth-authorization-server#', $request_uri)) {
            $is_oauth_discovery = true;
        }
        
        // Pattern 4: Any oauth-authorization-server in wpai/v1 path
        if (!$is_oauth_discovery && preg_match('#/wpai/v1/.*oauth-authorization-server#', $request_uri)) {
            $is_oauth_discovery = true;
        }
    }
    
    // Also check query var from rewrite rules (only if WordPress query is available)
    if (!$is_oauth_discovery) {
        global $wp_query;
        // Check if $wp_query exists and is initialized
        if (isset($wp_query) && is_object($wp_query) && isset($wp_query->query_vars)) {
            if (isset($wp_query->query_vars['wpai_oauth_discovery'])) {
                $is_oauth_discovery = true;
            }
        }
        // Only call get_query_var if we know WordPress query is available
        if (!$is_oauth_discovery && function_exists('get_query_var') && isset($GLOBALS['wp_query'])) {
            $query_var = get_query_var('wpai_oauth_discovery');
            if ($query_var) {
                $is_oauth_discovery = true;
            }
        }
    }
    
    // RFC 9728: Check for Protected Resource Metadata (PRM)
    $is_prm = false;
    if ($request_uri) {
        // ChatGPT looks for: /.well-known/oauth-protected-resource
        if (preg_match('#/\.well-known/oauth-protected-resource#', $request_uri)) {
            $is_prm = true;
        }
    }
    
    if (!$is_prm) {
        global $wp_query;
        if (isset($wp_query) && is_object($wp_query) && isset($wp_query->query_vars)) {
            if (isset($wp_query->query_vars['wpai_prm_discovery'])) {
                $is_prm = true;
            }
        }
    }
    
    // Handle PRM discovery (RFC 9728)
    if ($is_prm) {
        $already_handled = true; // Mark as handled before exit
        header('Content-Type: application/json');
        header('Access-Control-Allow-Origin: *');
        header('Access-Control-Allow-Methods: GET, OPTIONS');
        header('Access-Control-Allow-Headers: Content-Type, Authorization');
        
        if ($method === 'OPTIONS') {
            http_response_code(200);
            exit;
        }
        
        // Build URLs (WordPress might not be loaded yet)
        $protocol = (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off') ? 'https' : 'http';
        $host = isset($_SERVER['HTTP_HOST']) ? $_SERVER['HTTP_HOST'] : (isset($_SERVER['SERVER_NAME']) ? $_SERVER['SERVER_NAME'] : 'localhost');
        $site_url = $protocol . '://' . $host;
        $mcp_url = $site_url . '/wp-json/wpai/v1/mcp';
        $issuer = $site_url . '/wp-json/wpai/v1';
        
        // Check if this is resource-specific PRM or root PRM
        $is_resource_specific = false;
        if ($request_uri && preg_match('#/\.well-known/oauth-protected-resource/wp-json/wpai/v1/mcp#', $request_uri)) {
            $is_resource_specific = true;
        }
        
        // RFC 9728 Protected Resource Metadata (exact format required)
        // Both root and resource-specific return same format
        $prm = [
            'resource' => $mcp_url, // Exact MCP endpoint URL
            'authorization_servers' => [$issuer], // MCP requires this array - MUST be array
            'scopes_supported' => ['read', 'write'], // Required
        ];
        
        // Ensure Content-Type is application/json
        header('Content-Type: application/json', true);
        echo json_encode($prm, JSON_UNESCAPED_SLASHES); // No pretty print for production
        exit;
    }
    
    if ($is_oauth_discovery) {
        $already_handled = true; // Mark as handled before exit
        // Set headers
        header('Content-Type: application/json');
        header('Access-Control-Allow-Origin: *');
        header('Access-Control-Allow-Methods: GET, OPTIONS');
        header('Access-Control-Allow-Headers: Content-Type, Authorization');
        
        // Handle OPTIONS (CORS preflight)
        if ($method === 'OPTIONS') {
            http_response_code(200);
            exit;
        }
        
        // Get site URLs (need to load WordPress functions)
        if (!function_exists('get_site_url')) {
            // If WordPress not loaded, use direct URL construction
            $protocol = (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off') ? 'https' : 'http';
            $host = isset($_SERVER['HTTP_HOST']) ? $_SERVER['HTTP_HOST'] : $_SERVER['SERVER_NAME'];
            $site_url = $protocol . '://' . $host;
            $rest_base = $site_url . '/wp-json/wpai/v1';
            $oauth_authorize = $rest_base . '/oauth/authorize';
            $oauth_token = $rest_base . '/oauth/token';
            $oauth_revoke = $rest_base . '/oauth/revoke';
        } else {
            $site_url = get_site_url();
            $rest_base = rest_url('wpai/v1');
            $oauth_authorize = rest_url('wpai/v1/oauth/authorize');
            $oauth_token = rest_url('wpai/v1/oauth/token');
            $oauth_revoke = rest_url('wpai/v1/oauth/revoke');
        }
        
        // Return RFC 8414 compliant OAuth 2.0 Authorization Server Metadata
        // MUST include registration_endpoint and jwks_uri for ChatGPT/MCP
        // MUST allow "none" for token_endpoint_auth_methods (public clients)
        // MUST only advertise S256 for PKCE
        $oauth_metadata = [
            'issuer' => $rest_base,
            'authorization_endpoint' => $oauth_authorize,
            'token_endpoint' => $oauth_token,
            'registration_endpoint' => $rest_base . '/oauth/register', // REQUIRED for DCR
            'jwks_uri' => $rest_base . '/oauth/jwks.json', // REQUIRED for JWT verification
            'response_types_supported' => ['code'],
            'grant_types_supported' => ['authorization_code', 'refresh_token'],
            'code_challenge_methods_supported' => ['S256'], // S256 only (PKCE required)
            'token_endpoint_auth_methods_supported' => ['none'], // MUST allow "none" for public clients
            'revocation_endpoint' => $oauth_revoke,
            'revocation_endpoint_auth_methods_supported' => ['none'],
            'scopes_supported' => ['read', 'write'],
            'service_documentation' => $site_url,
            'ui_locales_supported' => ['en-US'],
            'op_policy_uri' => $site_url,
            'op_tos_uri' => $site_url,
        ];
        
        // Ensure Content-Type is application/json (critical for ChatGPT)
        header('Content-Type: application/json', true);
        // Output JSON (no pretty print for production)
        $already_handled = true; // Mark as handled before exit
        echo wp_json_encode($oauth_metadata, JSON_UNESCAPED_SLASHES);
        exit;
    }
}
/**
 * Handle OAuth discovery in REST API requests (catches REST API 404s)
 * This filter runs BEFORE REST API processes the request
 * MUST check for OAuth discovery FIRST before checking result
 */
function wpai_handle_rest_oauth_discovery($result, $server, $request) {
    // Get route and request URI - ALWAYS check these FIRST, even if result is set
    $route = $request ? $request->get_route() : '';
    $request_uri = isset($_SERVER['REQUEST_URI']) ? $_SERVER['REQUEST_URI'] : '';
    
    // Check multiple patterns for OAuth discovery routes (with and without dot)
    // ChatGPT looks for /.well-known/oauth-authorization-server (with dot)
    $is_oauth_discovery = false;
    
    // Check exact routes first (most reliable)
    if ($route) {
        if ($route === '/wpai/v1/oauth-authorization-server' ||
            $route === '/wpai/v1/well-known/oauth-authorization-server' ||
            $route === '/wpai/v1/_well-known/oauth-authorization-server' ||
            $route === '/wpai/v1/.well-known/oauth-authorization-server') {
            $is_oauth_discovery = true;
        }
    }
    
    // If not exact match, check patterns in route
    if (!$is_oauth_discovery && $route) {
        if (strpos($route, 'oauth-authorization-server') !== false ||
            strpos($route, '.well-known/oauth-authorization-server') !== false ||
            strpos($route, '/.well-known/oauth-authorization-server') !== false ||
            strpos($route, '/well-known/oauth-authorization-server') !== false) {
            $is_oauth_discovery = true;
        }
    }
    
    // Fallback to request URI check (CRITICAL - route might be empty!)
    if (!$is_oauth_discovery && $request_uri) {
        if (strpos($request_uri, 'oauth-authorization-server') !== false ||
            preg_match('#/wp-json/wpai/v1/.*oauth-authorization-server#', $request_uri) ||
            preg_match('#/wpai/v1/.*oauth-authorization-server#', $request_uri)) {
            $is_oauth_discovery = true;
        }
    }
    
    // If this is an OAuth discovery request, return metadata IMMEDIATELY
    if ($is_oauth_discovery) {
        // Get site URLs
        $site_url = get_site_url();
        $rest_base = rest_url('wpai/v1');
        
        // Return RFC 8414 compliant OAuth 2.0 Authorization Server Metadata
        // MUST include registration_endpoint and jwks_uri for ChatGPT/MCP
        // MUST allow "none" for token_endpoint_auth_methods (public clients)
        // MUST only advertise S256 for PKCE
        $oauth_metadata = [
            'issuer' => $rest_base,
            'authorization_endpoint' => rest_url('wpai/v1/oauth/authorize'),
            'token_endpoint' => rest_url('wpai/v1/oauth/token'),
            'registration_endpoint' => rest_url('wpai/v1/oauth/register'), // REQUIRED for DCR
            'jwks_uri' => rest_url('wpai/v1/oauth/jwks.json'), // REQUIRED for JWT verification
            'response_types_supported' => ['code'],
            'grant_types_supported' => ['authorization_code', 'refresh_token'],
            'code_challenge_methods_supported' => ['S256'], // S256 only (PKCE required)
            'token_endpoint_auth_methods_supported' => ['none'], // MUST allow "none" for public clients
            'revocation_endpoint' => rest_url('wpai/v1/oauth/revoke'),
            'revocation_endpoint_auth_methods_supported' => ['none'],
            'scopes_supported' => ['read', 'write'],
            'service_documentation' => $site_url,
            'ui_locales_supported' => ['en-US'],
            'op_policy_uri' => $site_url,
            'op_tos_uri' => $site_url,
        ];
        
        // Return response immediately - this bypasses WordPress REST API route lookup
        $already_handled = true; // Mark as handled
        return new WP_REST_Response($oauth_metadata, 200);
    }
    
    // If we have a result already and it's not OAuth discovery, return it
    if ($result !== null && !is_wp_error($result)) {
        return $result;
    }
    
    // If result is a WP_Error with rest_no_route, check if it might be OAuth discovery
    if (is_wp_error($result) && $result->get_error_code() === 'rest_no_route') {
        // Double-check if this might be an OAuth discovery request that was missed
        if ($request_uri && strpos($request_uri, 'oauth-authorization-server') !== false) {
            $site_url = get_site_url();
            $rest_base = rest_url('wpai/v1');
            // Return RFC 8414 compliant OAuth 2.0 Authorization Server Metadata
            $oauth_metadata = [
                'issuer' => $rest_base,
                'authorization_endpoint' => rest_url('wpai/v1/oauth/authorize'),
                'token_endpoint' => rest_url('wpai/v1/oauth/token'),
                'registration_endpoint' => rest_url('wpai/v1/oauth/register'), // REQUIRED for DCR
                'jwks_uri' => rest_url('wpai/v1/oauth/jwks.json'), // REQUIRED for JWT verification
                'response_types_supported' => ['code'],
                'grant_types_supported' => ['authorization_code', 'refresh_token'],
                'code_challenge_methods_supported' => ['S256'], // S256 only (PKCE required)
                'token_endpoint_auth_methods_supported' => ['none'], // MUST allow "none" for public clients
                'revocation_endpoint' => rest_url('wpai/v1/oauth/revoke'),
                'revocation_endpoint_auth_methods_supported' => ['none'],
                'scopes_supported' => ['read', 'write'],
                'service_documentation' => $site_url,
                'ui_locales_supported' => ['en-US'],
                'op_policy_uri' => $site_url,
                'op_tos_uri' => $site_url,
            ];
            $already_handled = true; // Mark as handled
            return new WP_REST_Response($oauth_metadata, 200);
        }
    }
    
    return $result;
}


/**
 * Additional handler during REST API init
 */
function wpai_handle_rest_oauth_discovery_early() {
    $request_uri = isset($_SERVER['REQUEST_URI']) ? $_SERVER['REQUEST_URI'] : '';
    
    // Check if this is OAuth discovery request during REST API init
    if (strpos($request_uri, 'oauth-authorization-server') !== false) {
        // This will be handled by other hooks, just ensure we're ready
        return;
    }
}

/**
 * Catch REST API 404 errors via shutdown hook (runs at the very end)
 */
function wpai_catch_rest_404_shutdown() {
    // Only run for REST API requests
    if (!defined('REST_REQUEST') || !REST_REQUEST) {
        return;
    }
    
    $request_uri = isset($_SERVER['REQUEST_URI']) ? $_SERVER['REQUEST_URI'] : '';
    
    // Check if this is an OAuth discovery request
    if ($request_uri && strpos($request_uri, 'oauth-authorization-server') !== false) {
        // Get the response that was sent
        $response_code = http_response_code();
        
        // If it's a 404, intercept it
        if ($response_code == 404) {
            // Build URLs
            $protocol = (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off') ? 'https' : 'http';
            $host = isset($_SERVER['HTTP_HOST']) ? $_SERVER['HTTP_HOST'] : (isset($_SERVER['SERVER_NAME']) ? $_SERVER['SERVER_NAME'] : 'localhost');
            $site_url = $protocol . '://' . $host;
            $rest_base = $site_url . '/wp-json/wpai/v1';
            
            // Clear any output
            if (ob_get_level()) {
                ob_clean();
            }
            
            // Set headers
            header('Content-Type: application/json', true);
            header('HTTP/1.1 200 OK', true, 200);
            
            // Return OAuth metadata
            $oauth_metadata = [
                'issuer' => $rest_base,
                'authorization_endpoint' => $rest_base . '/oauth/authorize',
                'token_endpoint' => $rest_base . '/oauth/token',
                'response_types_supported' => ['code'],
                'grant_types_supported' => ['authorization_code', 'refresh_token'],
                'code_challenge_methods_supported' => ['S256'],
                'token_endpoint_auth_methods_supported' => ['none'],
                'revocation_endpoint' => $rest_base . '/oauth/revoke',
                'revocation_endpoint_auth_methods_supported' => ['none'],
                'scopes_supported' => ['read', 'write'],
                'service_documentation' => $site_url,
                'ui_locales_supported' => ['en-US'],
                'op_policy_uri' => $site_url,
                'op_tos_uri' => $site_url,
            ];
            
            // Ensure Content-Type is application/json (critical for ChatGPT)
            header('Content-Type: application/json', true);
            $already_handled = true; // Mark as handled before exit
            echo json_encode($oauth_metadata, JSON_UNESCAPED_SLASHES);
            exit;
        }
    }
}
// Only hook shutdown as last resort (runs very late)
add_action('shutdown', 'wpai_catch_rest_404_shutdown', 999);

// Hook into parse_request VERY early (before REST API processes request)
// Single hook is sufficient - static flag prevents multiple executions
// Priority 1 ensures it runs FIRST, before WordPress REST API
add_action('parse_request', 'wpai_handle_oauth_discovery_direct', 1);
// Fallback hook only if parse_request didn't catch it (should rarely fire)
add_action('template_redirect', 'wpai_handle_oauth_discovery_direct', 5);
// Hook into REST API pre-dispatch (runs BEFORE REST API processes request)
// Single hook is sufficient - static flag prevents multiple executions
// Priority 1 ensures it runs FIRST, before REST API tries to find the route
add_filter('rest_pre_dispatch', 'wpai_handle_rest_oauth_discovery', 1, 3);
// Fallback only if pre_dispatch didn't catch it (should rarely fire)
add_filter('rest_post_dispatch', 'wpai_handle_rest_oauth_discovery', 999, 3);

/**
 * Activation hook
 */
function wpai_activate() {
    // Flush rewrite rules to ensure .well-known paths work
    flush_rewrite_rules();
    
    if (!wpai_check_requirements()) {
        wp_die(
            'WP AI Engine Pro requires PHP 7.4+ and WordPress 6.0+',
            'Plugin Activation Error',
            ['back_link' => true]
        );
    }
    
    // Set default options
    $defaults = [
        'openai_api_key' => '',
        'default_model' => WPAI_FALLBACK_MODEL,
        'max_tokens' => 4096,
        'temperature' => 0.7,
    ];
    
    // Only add defaults if not already set
    if (!get_option('wpai_options')) {
        add_option('wpai_options', $defaults);
    }
    
    // Flush rewrite rules to register .well-known paths
    flush_rewrite_rules();
    
    wpai_log_error('Plugin activated successfully');
}

/**
 * Deactivation hook
 */
function wpai_deactivate() {
    // Flush rewrite rules on deactivation
    flush_rewrite_rules();
    
    wpai_log_error('Plugin deactivated');
}

register_activation_hook(__FILE__, 'wpai_activate');
register_deactivation_hook(__FILE__, 'wpai_deactivate');

add_action('plugins_loaded', 'wpai_init', 10);
add_action('init', 'wpai_add_rewrite_rules', 10);

/**
 * Add custom query var for OAuth discovery
 */
function wpai_add_query_vars($vars) {
    $vars[] = 'wpai_oauth_discovery';
    $vars[] = 'wpai_prm_discovery';
    return $vars;
}
add_filter('query_vars', 'wpai_add_query_vars');

// Include shortcode handler
$shortcode_file = WPAI_PATH . '/includes/shortcode.php';
if (file_exists($shortcode_file)) {
    require_once $shortcode_file;
} else {
    wpai_log_error('Shortcode file not found: ' . $shortcode_file);
    add_action('admin_notices', function() {
        echo '<div class="error"><p>WP AI Engine Pro: Shortcode file is missing. Please reinstall the plugin.</p></div>';
    });
}

// Add REST API endpoints
// Use priority 20 to ensure routes are registered after core routes
add_action('rest_api_init', 'wpai_register_rest_routes', 20);

/**
 * Register REST API routes
 */
function wpai_register_rest_routes() {
    // Chat endpoint
    register_rest_route('wpai/v1', '/chat', [
        'methods' => 'POST',
        'callback' => 'wpai_handle_chat',
        'permission_callback' => 'wpai_check_permission',
        'args' => [
            'message' => [
                'required' => true,
                'type' => 'string',
                'sanitize_callback' => 'sanitize_textarea_field',
                'validate_callback' => function($param) {
                    return !empty($param) && strlen($param) <= 50000;
                }
            ],
            'model' => [
                'required' => false,
                'type' => 'string',
                'sanitize_callback' => 'sanitize_text_field',
            ],
        ],
    ]);
    
    // MCP HTTP endpoint (for browser dev mode)
    register_rest_route('wpai/v1', '/mcp', [
        'methods' => ['GET', 'POST', 'OPTIONS'],
        'callback' => 'wpai_handle_mcp_http',
        'permission_callback' => '__return_true', // OAuth handled in callback
    ]);
    
    // OAuth configuration endpoint (RFC 8414 - OAuth 2.0 Authorization Server Metadata)
    // Register multiple paths for maximum compatibility
    register_rest_route('wpai/v1', '/oauth-authorization-server', [
        'methods' => 'GET',
        'callback' => 'wpai_handle_oauth_config',
        'permission_callback' => '__return_true',
    ]);
    
    register_rest_route('wpai/v1', '/well-known/oauth-authorization-server', [
        'methods' => 'GET',
        'callback' => 'wpai_handle_oauth_config',
        'permission_callback' => '__return_true',
    ]);
    
    register_rest_route('wpai/v1', '/_well-known/oauth-authorization-server', [
        'methods' => 'GET',
        'callback' => 'wpai_handle_oauth_config',
        'permission_callback' => '__return_true',
    ]);
    
    // Try registering with dot prefix (might not work, but filter will catch it)
    // WordPress REST API has issues with dots in route paths
    register_rest_route('wpai/v1', '/.well-known/oauth-authorization-server', [
        'methods' => 'GET',
        'callback' => 'wpai_handle_oauth_config',
        'permission_callback' => '__return_true',
    ]);
    
    // OAuth endpoints
    register_rest_route('wpai/v1', '/oauth/authorize', [
        'methods' => ['GET', 'POST'],
        'callback' => 'wpai_handle_oauth_authorize',
        'permission_callback' => '__return_true',
        'args' => [
            'client_id' => [
                'required' => true,
                'type' => 'string',
                'sanitize_callback' => 'sanitize_text_field',
            ],
            'redirect_uri' => [
                'required' => true,
                'type' => 'string',
                'sanitize_callback' => 'esc_url_raw',
            ],
            'state' => [
                'required' => true,
                'type' => 'string',
                'sanitize_callback' => 'sanitize_text_field',
            ],
            'code_challenge' => [
                'required' => false,
                'type' => 'string',
                'sanitize_callback' => 'sanitize_text_field',
            ],
        ],
    ]);
    
    register_rest_route('wpai/v1', '/oauth/token', [
        'methods' => 'POST',
        'callback' => 'wpai_handle_oauth_token',
        'permission_callback' => '__return_true',
        'args' => [
            'grant_type' => [
                'required' => true,
                'type' => 'string',
                'sanitize_callback' => 'sanitize_text_field',
            ],
            'code' => [
                'required' => false,
                'type' => 'string',
                'sanitize_callback' => 'sanitize_text_field',
            ],
        ],
    ]);
    
    // Dynamic Client Registration endpoint (RFC 7591)
    register_rest_route('wpai/v1', '/oauth/register', [
        'methods' => ['POST', 'OPTIONS'],
        'callback' => 'wpai_handle_oauth_register',
        'permission_callback' => '__return_true',
    ]);
    
    // JWKS endpoint for JWT verification
    register_rest_route('wpai/v1', '/oauth/jwks.json', [
        'methods' => 'GET',
        'callback' => 'wpai_handle_oauth_jwks',
        'permission_callback' => '__return_true',
    ]);
}

/**
 * Check permission for chat endpoint
 * 
 * @return bool True if user has permission
 */
function wpai_check_permission() {
    return current_user_can('read') || wpai_check_api_key();
}

/**
 * Check API key for external access
 * 
 * @return bool True if API key is valid
 */
function wpai_check_api_key() {
    $api_key = $_SERVER['HTTP_X_WPAI_API_KEY'] ?? '';
    $options = get_option('wpai_options', []);
    $stored_key = $options['openai_api_key'] ?? '';
    
    if (empty($stored_key) || empty($api_key)) {
        return false;
    }
    
    return hash_equals($stored_key, $api_key);
}

/**
 * Handle OAuth configuration endpoint
 * 
 * @param WP_REST_Request $request Request object
 * @return WP_REST_Response Response object
 */
function wpai_handle_oauth_config($request) {
    // Set CORS headers
    header('Access-Control-Allow-Origin: *');
    header('Access-Control-Allow-Methods: GET, OPTIONS');
    header('Access-Control-Allow-Headers: Content-Type');
    header('Content-Type: application/json');
    
    $site_url = get_site_url();
    $rest_base = rest_url('wpai/v1');
    
    // RFC 8414 compliant OAuth 2.0 Authorization Server Metadata
    // Minimal "known-good" payload matching ChatGPT expectations exactly
    $response = new WP_REST_Response([
        'issuer' => $rest_base, // MUST match exactly: https://searei.com/wp-json/wpai/v1
        'authorization_endpoint' => rest_url('wpai/v1/oauth/authorize'),
        'token_endpoint' => rest_url('wpai/v1/oauth/token'),
        'jwks_uri' => rest_url('wpai/v1/oauth/jwks.json'), // REQUIRED
        'response_types_supported' => ['code'],
        'grant_types_supported' => ['authorization_code', 'refresh_token'],
        'code_challenge_methods_supported' => ['S256'], // S256 only - ChatGPT is public client using PKCE
        'token_endpoint_auth_methods_supported' => ['none'], // MUST include "none" for public clients
        'scopes_supported' => ['read', 'write'],
        // Optional but recommended:
        'registration_endpoint' => rest_url('wpai/v1/oauth/register'), // For Dynamic Client Registration
    ]);
    
    // Ensure Content-Type header is set correctly
    $response->header('Content-Type', 'application/json');
    return $response;
}

/**
 * Handle OAuth authorization endpoint
 * 
 * @param WP_REST_Request $request Request object
 * @return void Redirects to redirect_uri
 */
function wpai_handle_oauth_authorize($request) {
    // Set CORS headers
    header('Access-Control-Allow-Origin: *');
    header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
    header('Access-Control-Allow-Headers: Content-Type');
    
    try {
        $client_id = sanitize_text_field($request->get_param('client_id'));
        $redirect_uri = esc_url_raw($request->get_param('redirect_uri'));
        $state = sanitize_text_field($request->get_param('state'));
        $code_challenge = sanitize_text_field($request->get_param('code_challenge') ?? '');
        
        // Validate required parameters
        if (empty($client_id) || empty($redirect_uri) || empty($state)) {
            wp_die('Missing required OAuth parameters', 'OAuth Error', ['response' => 400]);
        }
        
        // Generate authorization code
        $auth_code = wp_generate_password(32, false);
        
        // Store code with metadata
        set_transient('wpai_oauth_code_' . $auth_code, [
            'client_id' => $client_id,
            'code_challenge' => $code_challenge,
            'redirect_uri' => $redirect_uri,
            'created_at' => time(),
        ], 300); // 5 minutes
        
        wpai_log_error('OAuth authorization code generated', ['client_id' => $client_id]);
        
        // Redirect back to ChatGPT with code
        $redirect_url = add_query_arg([
            'code' => $auth_code,
            'state' => $state,
        ], $redirect_uri);
        
        wp_redirect($redirect_url);
        exit;
    } catch (Exception $e) {
        wpai_log_error('OAuth authorization error: ' . $e->getMessage());
        wp_die('OAuth authorization failed', 'OAuth Error', ['response' => 500]);
    }
}

/**
 * Handle OAuth token endpoint
 * 
 * @param WP_REST_Request $request Request object
 * @return WP_REST_Response Response object
 */
function wpai_handle_oauth_token($request) {
    // Set CORS headers
    header('Access-Control-Allow-Origin: *');
    header('Access-Control-Allow-Methods: POST, OPTIONS');
    header('Access-Control-Allow-Headers: Content-Type');
    header('Content-Type: application/json');
    
    try {
        $grant_type = sanitize_text_field($request->get_param('grant_type'));
        $code = sanitize_text_field($request->get_param('code'));
        
        if ($grant_type !== 'authorization_code') {
            return new WP_REST_Response([
                'error' => 'unsupported_grant_type',
                'error_description' => 'Only authorization_code grant type is supported'
            ], 400);
        }
        
        if (empty($code)) {
            return new WP_REST_Response([
                'error' => 'invalid_request',
                'error_description' => 'Authorization code is required'
            ], 400);
        }
        
        // Verify code
        $code_data = get_transient('wpai_oauth_code_' . $code);
        
        if (!$code_data) {
            wpai_log_error('Invalid or expired OAuth code');
            return new WP_REST_Response([
                'error' => 'invalid_grant',
                'error_description' => 'Authorization code is invalid or expired'
            ], 400);
        }
        
        // Delete used code (one-time use)
        delete_transient('wpai_oauth_code_' . $code);
        
        // Generate access token
        $access_token = wp_generate_password(40, false);
        set_transient('wpai_oauth_token_' . $access_token, [
            'client_id' => $code_data['client_id'],
            'expires' => time() + 3600,
            'created_at' => time(),
        ], 3600); // 1 hour
        
        wpai_log_error('OAuth access token generated', ['client_id' => $code_data['client_id']]);
        
        return new WP_REST_Response([
            'access_token' => $access_token,
            'token_type' => 'Bearer',
            'expires_in' => 3600,
        ]);
    } catch (Exception $e) {
        wpai_log_error('OAuth token error: ' . $e->getMessage());
        return new WP_REST_Response([
            'error' => 'server_error',
            'error_description' => 'An error occurred while processing the token request'
        ], 500);
    }
}

/**
 * Handle MCP HTTP endpoint
 * 
 * @param WP_REST_Request $request Request object
 * @return WP_REST_Response Response object
 */
function wpai_handle_mcp_http($request) {
    // Set CORS headers
    header('Access-Control-Allow-Origin: *');
    header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
    header('Access-Control-Allow-Headers: Content-Type, Authorization, X-Requested-With');
    header('Access-Control-Max-Age: 86400');
    header('Content-Type: application/json');
    
    // Handle preflight
    if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
        return new WP_REST_Response(['status' => 'ok'], 200);
    }
    
    // Handle GET requests (server info with OAuth discovery)
    // ChatGPT needs to GET server info WITHOUT auth first to discover OAuth
    // Only POST requests require authentication
    $auth_header = $_SERVER['HTTP_AUTHORIZATION'] ?? '';
    
    // For POST requests, verify OAuth token
    if ($_SERVER['REQUEST_METHOD'] === 'POST') {
        if (empty($auth_header)) {
            $site_url = get_site_url();
            $prm_url = $site_url . '/.well-known/oauth-protected-resource/wp-json/wpai/v1/mcp';
            header('WWW-Authenticate: Bearer resource_metadata="' . esc_url($prm_url) . '"');
            return new WP_REST_Response([
                'error' => 'unauthorized',
                'error_description' => 'This resource requires OAuth authentication',
                'resource_metadata' => $prm_url
            ], 401);
        }
        
        $token = str_replace('Bearer ', '', $auth_header);
        $token_data = get_transient('wpai_oauth_token_' . $token);
        
        if (!$token_data) {
            wpai_log_error('Invalid or expired OAuth token');
            $site_url = get_site_url();
            $prm_url = $site_url . '/.well-known/oauth-protected-resource/wp-json/wpai/v1/mcp';
            header('WWW-Authenticate: Bearer resource_metadata="' . esc_url($prm_url) . '"');
            return new WP_REST_Response([
                'error' => 'invalid_token',
                'error_description' => 'The access token is invalid or expired',
                'resource_metadata' => $prm_url
            ], 401);
        }
    }
    
    // Handle POST requests (MCP calls)
    if ($_SERVER['REQUEST_METHOD'] === 'POST') {
        try {
            $body = $request->get_json_params();
            $method = sanitize_text_field($body['method'] ?? '');
            $params = $body['params'] ?? [];
            $id = $body['id'] ?? null;
            
            switch ($method) {
                case 'tools/list':
                    $tools = wpai_get_mcp_tools();
                    $tools_list = [];
                    foreach ($tools as $name => $tool) {
                        $tools_list[] = [
                            'name' => $name,
                            'description' => $tool['description'],
                            'inputSchema' => [
                                'type' => 'object',
                                'properties' => $tool['parameters']
                            ]
                        ];
                    }
                    return new WP_REST_Response([
                        'jsonrpc' => '2.0',
                        'id' => $id,
                        'result' => ['tools' => $tools_list]
                    ]);
                    
                case 'tools/call':
                    $tool_name = sanitize_text_field($params['name'] ?? '');
                    $arguments = $params['arguments'] ?? [];
                    
                    $result = wpai_execute_tool_direct($tool_name, $arguments);
                    return new WP_REST_Response([
                        'jsonrpc' => '2.0',
                        'id' => $id,
                        'result' => [
                            'content' => [
                                ['type' => 'text', 'text' => json_encode($result, JSON_PRETTY_PRINT)]
                            ]
                        ]
                    ]);
                    
                default:
                    return new WP_REST_Response([
                        'jsonrpc' => '2.0',
                        'id' => $id,
                        'error' => [
                            'code' => -32601,
                            'message' => 'Method not found'
                        ]
                    ], 404);
            }
        } catch (Exception $e) {
            wpai_log_error('MCP error: ' . $e->getMessage());
            return new WP_REST_Response([
                'jsonrpc' => '2.0',
                'id' => $id ?? null,
                'error' => [
                    'code' => -32000,
                    'message' => $e->getMessage()
                ]
            ], 500);
        }
    }
    
    // Handle GET requests (server info with OAuth discovery)
    $mcp_url = rest_url('wpai/v1/mcp');
    $issuer = rest_url('wpai/v1');
    $site_url = get_site_url();
    
    // RFC 8414: When issuer has a path, clients try: /.well-known/oauth-authorization-server/{issuer_path}
    // For issuer=https://searei.com/wp-json/wpai/v1, ChatGPT tries FIRST:
    // https://searei.com/.well-known/oauth-authorization-server/wp-json/wpai/v1
    $issuer_path = '/wp-json/wpai/v1';
    $oauth_discovery_url_rfc8414 = $site_url . '/.well-known/oauth-authorization-server' . $issuer_path;
    $oauth_discovery_url_oidc = $site_url . '/.well-known/openid-configuration' . $issuer_path;
    
    // RFC 9728: Protected Resource Metadata (PRM) URL
    $prm_url = $site_url . '/.well-known/oauth-protected-resource';
    
    // Also support legacy paths for compatibility
    $oauth_discovery_url = $issuer . '/oauth-authorization-server';
    $oauth_discovery_url_dot = $issuer . '/.well-known/oauth-authorization-server';
    
    // RFC 8414 compliant OAuth Authorization Server Metadata
    // Minimal "known-good" payload matching ChatGPT expectations exactly
    $oauth_metadata = [
        'issuer' => $issuer, // MUST match exactly: https://searei.com/wp-json/wpai/v1
        'authorization_endpoint' => rest_url('wpai/v1/oauth/authorize'),
        'token_endpoint' => rest_url('wpai/v1/oauth/token'),
        'jwks_uri' => rest_url('wpai/v1/oauth/jwks.json'), // REQUIRED
        'response_types_supported' => ['code'],
        'grant_types_supported' => ['authorization_code', 'refresh_token'],
        'code_challenge_methods_supported' => ['S256'], // S256 only - ChatGPT is public client using PKCE
        'token_endpoint_auth_methods_supported' => ['none'], // MUST include "none" for public clients
        'scopes_supported' => ['read', 'write'],
        // Optional but recommended:
        'registration_endpoint' => rest_url('wpai/v1/oauth/register'), // For Dynamic Client Registration
    ];
    
    // Add Link headers for OAuth discovery (ChatGPT checks these!)
    // Multiple Link headers for maximum compatibility
    header('Link: <' . $oauth_discovery_url_rfc8414 . '>; rel="oauth2-authorization-server"');
    header('Link: <' . $oauth_discovery_url . '>; rel="https://api.w.org/oauth"');
    header('Link: <' . $oauth_discovery_url . '>; rel="oauth2-authorization-server"');
    header('Link: <' . $oauth_discovery_url_dot . '>; rel="oauth2-authorization-server"');
    header('Link: <' . $oauth_discovery_url . '>; rel="authorization_server"');
    // RFC 9728: Link to PRM
    header('Link: <' . $prm_url . '>; rel="protected-resource"');
    
    $response = new WP_REST_Response([
        'name' => 'WP AI Engine Pro',
        'version' => WPAI_VERSION,
        'protocol' => 'mcp-http',
        'developer' => 'Saeed M. Vardani',
        'company' => 'SeaTechOne.com',
        'capabilities' => [
            'tools' => true,
            'resources' => false,
            'prompts' => false
        ],
        'endpoint' => $mcp_url,
        // OAuth metadata embedded directly (ChatGPT can use this without fetching!)
        // ChatGPT checks these fields to determine if OAuth is implemented
        'oauth' => $oauth_metadata,
        'authorization_server' => $oauth_metadata,
        'oauth_config' => $oauth_metadata, // Alternative field name
        // OAuth discovery URLs (ChatGPT fetches these - MUST use RFC 8414 path-inserted URL)
        'oauth_discovery_url' => $oauth_discovery_url_rfc8414, // RFC 8414 path-inserted URL (ChatGPT tries FIRST)
        'authorization_server' => $oauth_discovery_url_rfc8414, // Primary discovery URL (RFC 8414 compliant)
        'authorization_server_url' => $oauth_discovery_url_rfc8414, // Alternative field name
        'well_known_url' => $oauth_discovery_url_rfc8414, // Primary well-known URL
        'oauth_well_known_url' => $oauth_discovery_url_rfc8414, // Alternative field name
        'prm_url' => $prm_url . '/wp-json/wpai/v1/mcp', // RFC 9728 Protected Resource Metadata (resource-specific)
        'links' => [
            'oauth' => $oauth_discovery_url_rfc8414, // Use RFC 8414 path-inserted URL
            'oauth-discovery' => $oauth_discovery_url_rfc8414,
            'authorization_server' => $oauth_discovery_url_rfc8414, // Primary URL for discovery
            'prm' => $prm_url . '/wp-json/wpai/v1/mcp', // RFC 9728 PRM URL
            '.well-known/oauth-authorization-server' => $oauth_discovery_url_dot,
        ],
        'tools' => array_keys(wpai_get_mcp_tools()),
    ]);
    
    // Add Link headers to response (multiple for maximum compatibility)
    $response->header('Link', '<' . $oauth_discovery_url_rfc8414 . '>; rel="oauth2-authorization-server"');
    $response->header('Link', '<' . $oauth_discovery_url . '>; rel="https://api.w.org/oauth"');
    $response->header('Link', '<' . $oauth_discovery_url . '>; rel="oauth2-authorization-server"');
    $response->header('Link', '<' . $oauth_discovery_url_dot . '>; rel="oauth2-authorization-server"');
    $response->header('Link', '<' . $oauth_discovery_url . '>; rel="authorization_server"');
    // RFC 9728: Link to PRM
    $response->header('Link', '<' . $prm_url . '>; rel="protected-resource"');
    
    return $response;
}

/**
 * Execute MCP tool
 * 
 * @param string $name Tool name
 * @param array $arguments Tool arguments
 * @return mixed Tool result
 * @throws Exception If tool not found
 */
function wpai_execute_tool_direct($name, $arguments) {
    $tools = wpai_get_mcp_tools();
    
    if (!isset($tools[$name])) {
        throw new Exception("Unknown tool: $name");
    }
    
    // Sanitize arguments before execution
    $sanitized_args = [];
    foreach ($arguments as $key => $value) {
        if (is_string($value)) {
            $sanitized_args[$key] = sanitize_text_field($value);
        } else {
            $sanitized_args[$key] = $value;
        }
    }
    
    return call_user_func($tools[$name]['callback'], $sanitized_args);
}

/**
 * Handle chat endpoint
 * 
 * @param WP_REST_Request $request Request object
 * @return WP_REST_Response Response object
 */
function wpai_handle_chat($request) {
    try {
        $message = sanitize_textarea_field($request->get_param('message'));
        $options = get_option('wpai_options', []);
        $model = sanitize_text_field($request->get_param('model') ?? $options['default_model'] ?? WPAI_FALLBACK_MODEL);
        
        if (empty($message)) {
            return new WP_REST_Response(['error' => 'Message is required'], 400);
        }
        
        $api_key = $options['openai_api_key'] ?? '';
        
        if (empty($api_key)) {
            return new WP_REST_Response(['error' => 'OpenAI API key not configured'], 400);
        }
        
        $response = wpai_call_openai($api_key, $message, $model);
        
        return new WP_REST_Response([
            'success' => true,
            'response' => $response['content'],
            'tokens' => $response['tokens'],
            'model' => $model,
        ]);
    } catch (Exception $e) {
        wpai_log_error('Chat error: ' . $e->getMessage());
        return new WP_REST_Response([
            'success' => false,
            'error' => $e->getMessage()
        ], 500);
    }
}

/**
 * Call OpenAI API
 * 
 * @param string $api_key OpenAI API key
 * @param string $message User message
 * @param string $model Model to use
 * @return array Response with content and tokens
 * @throws Exception On API error
 */
function wpai_call_openai($api_key, $message, $model) {
    if (!function_exists('curl_init')) {
        throw new Exception('cURL extension is required but not installed');
    }
    
    $ch = curl_init('https://api.openai.com/v1/chat/completions');
    
    $options = get_option('wpai_options', []);
    $max_tokens = absint($options['max_tokens'] ?? 4096);
    $temperature = floatval($options['temperature'] ?? 0.7);
    
    $data = [
        'model' => $model,
        'messages' => [
            ['role' => 'user', 'content' => $message]
        ],
        'max_tokens' => $max_tokens,
        'temperature' => $temperature,
    ];
    
    curl_setopt_array($ch, [
        CURLOPT_POST => true,
        CURLOPT_POSTFIELDS => json_encode($data),
        CURLOPT_HTTPHEADER => [
            'Content-Type: application/json',
            'Authorization: Bearer ' . $api_key,
        ],
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_TIMEOUT => WPAI_TIMEOUT,
        CURLOPT_SSL_VERIFYPEER => true,
    ]);
    
    $response = curl_exec($ch);
    $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $error = curl_error($ch);
    
    curl_close($ch);
    
    if ($error) {
        throw new Exception('cURL error: ' . $error);
    }
    
    $decoded = json_decode($response, true);
    
    if ($http_code !== 200) {
        $message = $decoded['error']['message'] ?? 'Unknown error';
        throw new Exception('OpenAI API error (' . $http_code . '): ' . $message);
    }
    
    return [
        'content' => $decoded['choices'][0]['message']['content'] ?? '',
        'tokens' => $decoded['usage']['total_tokens'] ?? 0,
    ];
}

/**
 * Handle Dynamic Client Registration (RFC 7591)
 * ChatGPT uses this to register itself as a client
 * 
 * @param WP_REST_Request $request Request object
 * @return WP_REST_Response Response object
 */
function wpai_handle_oauth_register($request) {
    // Set CORS headers
    header('Access-Control-Allow-Origin: *');
    header('Access-Control-Allow-Methods: POST, OPTIONS');
    header('Access-Control-Allow-Headers: Content-Type');
    header('Content-Type: application/json');
    
    if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
        return new WP_REST_Response(['status' => 'ok'], 200);
    }
    
    try {
        $body = $request->get_json_params();
        $redirect_uris = $body['redirect_uris'] ?? [];
        $client_name = $body['client_name'] ?? 'ChatGPT MCP Client';
        
        // Generate client ID and client secret
        $client_id = wp_generate_password(32, false);
        $client_secret = wp_generate_password(40, false);
        
        // Store client registration
        $client_data = [
            'client_id' => $client_id,
            'client_secret' => $client_secret,
            'redirect_uris' => $redirect_uris,
            'client_name' => $client_name,
            'created_at' => time(),
        ];
        
        set_transient('wpai_oauth_client_' . $client_id, $client_data, 86400 * 365); // 1 year
        
        wpai_log_error('OAuth client registered', ['client_id' => $client_id]);
        
        // RFC 7591: DCR must return 201 Created (not 200)
        $response = new WP_REST_Response([
            'client_id' => $client_id,
            'client_secret' => $client_secret,
            'client_id_issued_at' => time(),
            'client_secret_expires_at' => 0, // No expiration
            'redirect_uris' => $redirect_uris,
            'client_name' => $client_name,
            'token_endpoint_auth_method' => 'none', // Public client (PKCE)
        ], 201); // 201 Created per RFC 7591
        
        $response->header('Content-Type', 'application/json');
        return $response;
    } catch (Exception $e) {
        wpai_log_error('OAuth registration error: ' . $e->getMessage());
        return new WP_REST_Response([
            'error' => 'invalid_client_metadata',
            'error_description' => $e->getMessage()
        ], 400);
    }
}

/**
 * Handle JWKS endpoint (JSON Web Key Set)
 * Required for JWT verification
 * 
 * @param WP_REST_Request $request Request object
 * @return WP_REST_Response Response object
 */
function wpai_handle_oauth_jwks($request) {
    // Set CORS headers
    header('Access-Control-Allow-Origin: *');
    header('Access-Control-Allow-Methods: GET, OPTIONS');
    header('Access-Control-Allow-Headers: Content-Type');
    header('Content-Type: application/json');
    
    if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
        return new WP_REST_Response(['status' => 'ok'], 200);
    }
    
    // Return JWKS format (required by ChatGPT even if we're not using JWT tokens yet)
    // ChatGPT requires this endpoint to exist and return valid JSON
    $response = new WP_REST_Response([
        'keys' => [] // Empty array is valid - indicates no JWT keys yet
    ]);
    
    $response->header('Content-Type', 'application/json');
    return $response;
}

/**
 * Get available MCP tools
 * 
 * @return array Array of tool definitions
 */
function wpai_get_mcp_tools() {
    return [
        'wp_get_site_info' => [
            'description' => 'Get WordPress site information including name, URL, version, and developer details',
            'parameters' => [],
            'callback' => function($params) {
                return [
                    'name' => get_bloginfo('name'),
                    'description' => get_bloginfo('description'),
                    'url' => get_site_url(),
                    'admin_email' => get_option('admin_email'),
                    'wp_version' => get_bloginfo('version'),
                    'php_version' => PHP_VERSION,
                    'theme' => wp_get_theme()->get('Name'),
                    'active_plugins' => count(get_option('active_plugins', [])),
                    'developer' => 'Saeed M. Vardani',
                    'company' => 'SeaTechOne.com',
                ];
            }
        ],
        
        'wp_list_posts' => [
            'description' => 'List WordPress posts with title, content, date, and author information',
            'parameters' => [
                'post_type' => ['type' => 'string', 'default' => 'post', 'description' => 'Type of posts to retrieve'],
                'posts_per_page' => ['type' => 'integer', 'default' => 10, 'description' => 'Number of posts to retrieve'],
                'status' => ['type' => 'string', 'default' => 'publish', 'description' => 'Post status'],
            ],
            'callback' => function($params) {
                $args = [
                    'post_type' => sanitize_text_field($params['post_type'] ?? 'post'),
                    'posts_per_page' => absint($params['posts_per_page'] ?? 10),
                    'post_status' => sanitize_text_field($params['status'] ?? 'publish'),
                ];
                
                $posts = get_posts($args);
                
                return array_map(function($post) {
                    return [
                        'id' => $post->ID,
                        'title' => $post->post_title,
                        'slug' => $post->post_name,
                        'status' => $post->post_status,
                        'date' => $post->post_date,
                        'author' => get_the_author_meta('display_name', $post->post_author),
                        'excerpt' => wp_trim_words($post->post_content, 30),
                        'url' => get_permalink($post->ID),
                    ];
                }, $posts);
            }
        ],
        
        'wp_create_post' => [
            'description' => 'Create a new WordPress post with title and content',
            'parameters' => [
                'title' => ['type' => 'string', 'required' => true, 'description' => 'Post title'],
                'content' => ['type' => 'string', 'required' => true, 'description' => 'Post content'],
                'status' => ['type' => 'string', 'default' => 'draft', 'description' => 'Post status'],
                'post_type' => ['type' => 'string', 'default' => 'post', 'description' => 'Type of post'],
            ],
            'callback' => function($params) {
                // Require admin capability for post creation
                if (!current_user_can('edit_posts')) {
                    throw new Exception('Insufficient permissions to create posts');
                }
                
                $post_id = wp_insert_post([
                    'post_title' => sanitize_text_field($params['title']),
                    'post_content' => wp_kses_post($params['content']),
                    'post_status' => sanitize_text_field($params['status'] ?? 'draft'),
                    'post_type' => sanitize_text_field($params['post_type'] ?? 'post'),
                ]);
                
                if (is_wp_error($post_id)) {
                    throw new Exception($post_id->get_error_message());
                }
                
                return [
                    'success' => true,
                    'post_id' => $post_id,
                    'url' => get_permalink($post_id),
                ];
            }
        ],
        
        'wp_get_stats' => [
            'description' => 'Get WordPress site statistics including posts, pages, comments, and users count',
            'parameters' => [],
            'callback' => function($params) {
                return [
                    'posts' => wp_count_posts('post')->publish,
                    'pages' => wp_count_posts('page')->publish,
                    'comments' => wp_count_comments()->approved,
                    'users' => count_users()['total_users'],
                    'media' => wp_count_posts('attachment')->inherit,
                ];
            }
        ],
    ];
}

/**
 * Enhanced exception handler for better error messages
 */
add_filter('wpai_ai_exception', function($exception) {
    if (!is_string($exception)) {
        return $exception;
    }
    
    // Remove service prefixes
    $prefixes = ['OpenAI:', 'Anthropic:', 'Google:', 'Azure:'];
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
        'API URL was not found' => 'API endpoint not found. Please check your OpenAI account status.',
        'quota' => 'API quota exceeded. Please check your usage limits.',
        'rate limit' => 'Rate limit reached. Please wait and try again.',
        'authentication' => 'Authentication failed. Please verify your API key.',
        'API key' => 'Invalid API key. Please check your configuration.',
        'model not found' => 'The selected AI model is not available.',
        'context length' => 'Message too long. Please reduce the length.',
    ];
    
    foreach ($error_mappings as $keyword => $message) {
        if (stripos($exception, $keyword) !== false) {
            return $message;
        }
    }
    
    return $exception;
}, 10, 1);

