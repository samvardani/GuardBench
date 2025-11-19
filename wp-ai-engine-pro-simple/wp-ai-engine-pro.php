<?php
/**
 * Plugin Name: WP AI Engine Pro
 * Plugin URI: https://seatechone.com
 * Description: Advanced AI Engine for WordPress with enhanced MCP support, realtime chatbots, and complete ChatGPT control. Improved version with modern architecture.
 * Version: 4.0.2
 * Author: Saeed M. Vardani
 * Author URI: https://seatechone.com
 * Text Domain: wp-ai-engine-pro
 * Domain Path: /languages
 * Requires at least: 6.0
 * Requires PHP: 8.1
 * License: GPLv3 or later
 * License URI: https://www.gnu.org/licenses/gpl-3.0.html
 * 
 * @package WPAIEnginePro
 * @developer Saeed M. Vardani
 * @company SeaTechOne.com
 */

declare(strict_types=1);

// Exit if accessed directly
if (!defined('ABSPATH')) {
    exit;
}

// Plugin Constants
define('WPAI_VERSION', '4.0.2');
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

/**
 * Simple Admin Menu Class
 */
class WPAI_Simple_Admin {
    
    public function __construct() {
        add_action('admin_menu', [$this, 'add_menu']);
        add_action('admin_init', [$this, 'init_settings']);
    }
    
    public function add_menu(): void {
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
    
    public function init_settings(): void {
        register_setting('wpai_settings', 'wpai_options');
        
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
    }
    
    public function api_key_field(): void {
        $options = get_option('wpai_options', []);
        $value = $options['openai_api_key'] ?? '';
        echo '<input type="password" name="wpai_options[openai_api_key]" value="' . esc_attr($value) . '" class="regular-text" />';
        echo '<p class="description">Get your API key from <a href="https://platform.openai.com/api-keys" target="_blank">OpenAI</a></p>';
    }
    
    public function model_field(): void {
        $options = get_option('wpai_options', []);
        $value = $options['default_model'] ?? WPAI_FALLBACK_MODEL;
        
        $models = [
            'gpt-5-chat-latest' => 'GPT-5 Chat Latest',
            'gpt-5-mini' => 'GPT-5 Mini',
            'gpt-4.5-turbo' => 'GPT-4.5 Turbo',
            'gpt-4-turbo' => 'GPT-4 Turbo',
        ];
        
        echo '<select name="wpai_options[default_model]">';
        foreach ($models as $key => $label) {
            echo '<option value="' . esc_attr($key) . '" ' . selected($value, $key, false) . '>' . esc_html($label) . '</option>';
        }
        echo '</select>';
    }
    
    public function render_dashboard(): void {
        ?>
        <div class="wrap">
            <h1>WP AI Engine Pro - Dashboard</h1>
            
            <div class="wpai-dashboard">
                <div class="wpai-stats">
                    <div class="wpai-stat-card">
                        <h3>Status</h3>
                        <p class="wpai-stat-number">✓ Active</p>
                    </div>
                    
                    <div class="wpai-stat-card">
                        <h3>Version</h3>
                        <p class="wpai-stat-number"><?php echo WPAI_VERSION; ?></p>
                    </div>
                    
                    <div class="wpai-stat-card">
                        <h3>PHP Version</h3>
                        <p class="wpai-stat-number"><?php echo PHP_VERSION; ?></p>
                    </div>
                    
                    <div class="wpai-stat-card">
                        <h3>WordPress</h3>
                        <p class="wpai-stat-number"><?php echo get_bloginfo('version'); ?></p>
                    </div>
                </div>
                
                <div class="wpai-quick-actions">
                    <h2>Quick Actions</h2>
                    <a href="<?php echo admin_url('admin.php?page=wpai-settings'); ?>" class="button button-primary">Configure Settings</a>
                    <a href="<?php echo admin_url('admin.php?page=wpai-mcp'); ?>" class="button">Setup MCP</a>
                    <a href="<?php echo admin_url('admin.php?page=wpai-test'); ?>" class="button">Test Plugin</a>
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
                        <p><strong>Company:</strong> <a href="https://seatechone.com" target="_blank">SeaTechOne.com</a></p>
                        <p><strong>Version:</strong> <?php echo WPAI_VERSION; ?></p>
                        <p><strong>Support:</strong> <a href="https://seatechone.com" target="_blank">Visit SeaTechOne.com</a></p>
                    </div>
                </div>
            </div>
        </div>
        <?php
    }
    
    public function render_settings(): void {
        ?>
        <div class="wrap">
            <h1>WP AI Engine Pro - Settings</h1>
            
            <form method="post" action="options.php">
                <?php
                settings_fields('wpai_settings');
                do_settings_sections('wpai-settings');
                submit_button();
                ?>
            </form>
            
            <div class="wpai-settings-info">
                <h3>Additional Settings</h3>
                <p>More advanced settings will be available in future updates.</p>
                
                <h3>Shortcode Usage</h3>
                <p>Add this shortcode to any page or post to display the chatbot:</p>
                <code>[wpai_chatbot]</code>
                
                <h3>Shortcode Options</h3>
                <ul>
                    <li><code>[wpai_chatbot title="My Assistant"]</code> - Custom title</li>
                    <li><code>[wpai_chatbot theme="dark"]</code> - Dark theme</li>
                    <li><code>[wpai_chatbot position="bottom-left"]</code> - Left position</li>
                </ul>
            </div>
        </div>
        <?php
    }
    
    public function render_mcp(): void {
        $plugin_path = WPAI_PATH;
        $mcp_server_path = $plugin_path . '/mcp-server.php';
        $site_url = get_site_url();
        $mcp_http_url = rest_url('wpai/v1/mcp');
        
        ?>
        <div class="wrap">
            <h1>MCP Setup - Control WordPress from ChatGPT</h1>
            
            <div class="wpai-mcp-setup">
                
                <div style="background: #d4edda; border-left: 4px solid #28a745; padding: 20px; margin: 20px 0;">
                    <h2 style="margin-top: 0;">🌐 For ChatGPT Browser (Dev Mode)</h2>
                    <p><strong>Your MCP Server URL:</strong></p>
                    <code style="background: #fff; padding: 10px; display: block; font-size: 16px; margin: 10px 0;"><?php echo esc_html($mcp_http_url); ?></code>
                    <button type="button" class="button button-primary" onclick="navigator.clipboard.writeText('<?php echo esc_js($mcp_http_url); ?>')">
                        📋 Copy URL
                    </button>
                    <p style="margin-top: 15px;"><strong>Status:</strong> <span style="color: green;">✓ HTTP endpoint ready</span></p>
                    <p><strong>Protocol:</strong> MCP over HTTP with CORS enabled</p>
                </div>
                
                <h2>Browser Dev Mode Setup</h2>
                <p>Use this URL in your ChatGPT browser dev mode MCP configuration:</p>
                <pre style="background: #f5f5f5; padding: 15px; border-radius: 5px;"><code><?php echo esc_html($mcp_http_url); ?></code></pre>
                
                <h3>Test the Endpoint</h3>
                <p>You can test if it's working by visiting the URL directly:</p>
                <a href="<?php echo esc_url($mcp_http_url); ?>" target="_blank" class="button">🔗 Test MCP Endpoint</a>
                
                <hr style="margin: 40px 0;" />
                
                <h2 style="color: #666;">💻 For ChatGPT Desktop (Alternative)</h2>
                <p><strong>MCP servers for desktop use stdio (standard input/output) transport.</strong></p>
                
                <h3>Step 1: Locate ChatGPT Config File</h3>
                <p>Edit your ChatGPT Desktop configuration file:</p>
                <ul>
                    <li><strong>Mac/Linux:</strong> <code>~/.config/OpenAI/ChatGPT/config.json</code></li>
                    <li><strong>Windows:</strong> <code>%APPDATA%\OpenAI\ChatGPT\config.json</code></li>
                </ul>
                
                <h3>Step 2: Add MCP Server Configuration</h3>
                <p>Add this to your config.json:</p>
                <pre><code>{
  "mcpServers": {
    "wordpress": {
      "command": "php",
      "args": ["<?php echo esc_js($mcp_server_path); ?>"]
    }
  }
}</code></pre>
                
                <h3>Alternative: Using npx</h3>
                <p>If you prefer to use npx (for projects that support it):</p>
                <pre><code>{
  "mcpServers": {
    "wordpress": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-wordpress"]
    }
  }
}</code></pre>
                
                <div class="wpai-info-box" style="background: #e7f3ff; border-left: 4px solid #2196F3; padding: 15px; margin: 20px 0;">
                    <strong>📋 Your MCP Server Path:</strong><br />
                    <code style="background: #fff; padding: 5px 10px; display: inline-block; margin: 10px 0;"><?php echo esc_html($mcp_server_path); ?></code><br />
                    <button type="button" class="button" onclick="navigator.clipboard.writeText('<?php echo esc_js($mcp_server_path); ?>')">
                        Copy Path
                    </button>
                </div>
                
                <div class="wpai-warning-box" style="background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0;">
                    <strong>⚠️ Important Notes:</strong>
                    <ul>
                        <li>MCP servers use <strong>stdio transport</strong> (not HTTP/SSE)</li>
                        <li>ChatGPT Desktop runs the PHP script as a subprocess</li>
                        <li>Make sure PHP is in your system PATH</li>
                        <li>The script needs read access to WordPress files</li>
                    </ul>
                </div>
                
                <h3>Step 3: Verify PHP Path</h3>
                <p>Make sure PHP is accessible from command line:</p>
                <pre><code># Test in terminal:
php -v

# Should show PHP version 8.1 or higher</code></pre>
                
                <h3>Step 4: Restart ChatGPT</h3>
                <p>Completely quit and restart ChatGPT Desktop application to load the new configuration.</p>
                
                <h3>Step 5: Test Connection</h3>
                <p>In ChatGPT, try asking:</p>
                <ul>
                    <li>"What's my WordPress site information?"</li>
                    <li>"Show me my recent posts"</li>
                    <li>"Create a new post about AI"</li>
                    <li>"What are my site statistics?"</li>
                </ul>
                
                <div class="wpai-success-box" style="background: #d4edda; border-left: 4px solid #28a745; padding: 15px; margin: 20px 0;">
                    <strong>✅ Available WordPress Tools:</strong>
                    <ul>
                        <li><code>wp_get_site_info</code> - Get site information</li>
                        <li><code>wp_list_posts</code> - List WordPress posts</li>
                        <li><code>wp_create_post</code> - Create new posts</li>
                        <li><code>wp_get_stats</code> - Get site statistics</li>
                    </ul>
                </div>
                
                <div style="background: #f8f9fa; border: 1px solid #dee2e6; padding: 15px; margin: 20px 0; border-radius: 5px;">
                    <strong>🔧 Troubleshooting:</strong>
                    <ul>
                        <li>If ChatGPT can't find PHP, use full path: <code>/usr/bin/php</code> or <code>/usr/local/bin/php</code></li>
                        <li>Check ChatGPT logs for connection errors</li>
                        <li>Verify the mcp-server.php file is executable</li>
                        <li>Make sure WordPress is accessible from the script</li>
                    </ul>
                </div>
                
                <div style="margin-top: 30px; padding-top: 20px; border-top: 2px solid #eee;">
                    <p><strong>Developer:</strong> Saeed M. Vardani | <strong>Company:</strong> SeaTechOne.com</p>
                </div>
            </div>
        </div>
        <?php
    }
    
    public function render_test(): void {
        $options = get_option('wpai_options', []);
        $api_key = $options['openai_api_key'] ?? '';
        $model = $options['default_model'] ?? WPAI_FALLBACK_MODEL;
        
        ?>
        <div class="wrap">
            <h1>WP AI Engine Pro - Test</h1>
            
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
                            <td><?php echo WPAI_VERSION; ?></td>
                            <td><span style="color: green;">OK</span></td>
                        </tr>
                        <tr>
                            <td>PHP Version</td>
                            <td><?php echo PHP_VERSION; ?></td>
                            <td><span style="color: green;">OK</span></td>
                        </tr>
                    </tbody>
                </table>
                
                <h2>Quick Test</h2>
                <p>Test the chatbot shortcode: <code>[wpai_chatbot]</code></p>
                <p>Add this to any page or post to test the chatbot functionality.</p>
                
                <?php if (!empty($api_key)): ?>
                <h2>API Test</h2>
                <button id="test-api" class="button button-primary">Test API Connection</button>
                <div id="api-test-result"></div>
                
                <script>
                document.getElementById('test-api').addEventListener('click', async function() {
                    const resultDiv = document.getElementById('api-test-result');
                    resultDiv.innerHTML = 'Testing...';
                    
                    try {
                        const response = await fetch('<?php echo rest_url('wpai/v1/chat'); ?>', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                'X-WP-Nonce': '<?php echo wp_create_nonce('wp_rest'); ?>'
                            },
                            body: JSON.stringify({
                                message: 'Hello, this is a test message.'
                            })
                        });
                        
                        const data = await response.json();
                        
                        if (data.success) {
                            resultDiv.innerHTML = '<div style="color: green;">✓ API Test Successful! Response: ' + data.response.substring(0, 100) + '...</div>';
                        } else {
                            resultDiv.innerHTML = '<div style="color: red;">✗ API Test Failed: ' + (data.error || 'Unknown error') + '</div>';
                        }
                    } catch (error) {
                        resultDiv.innerHTML = '<div style="color: red;">✗ API Test Failed: ' + error.message + '</div>';
                    }
                });
                </script>
                <?php else: ?>
                <div style="color: orange;">
                    <strong>⚠️ API Key Required</strong><br />
                    Please set your OpenAI API key in Settings to test the API connection.
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
function wpai_init(): void {
    new WPAI_Simple_Admin();
    
    // Add rewrite rule for .well-known at root
    add_rewrite_rule(
        '^\.well-known/oauth-authorization-server$',
        'index.php?rest_route=/.well-known/oauth-authorization-server',
        'top'
    );
    
    // Add rewrite rule for MCP OAuth discovery
    add_rewrite_rule(
        '^wp-json/wpai/v1/mcp/\.well-known/oauth-authorization-server$',
        'index.php?rest_route=/wpai/v1/mcp/.well-known/oauth-authorization-server',
        'top'
    );
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
    
    // Set default options
    $defaults = [
        'openai_api_key' => '',
        'default_model' => WPAI_FALLBACK_MODEL,
        'max_tokens' => 4096,
        'temperature' => 0.7,
    ];
    
    add_option('wpai_options', $defaults);
    
    // Flush rewrite rules to register .well-known paths
    flush_rewrite_rules();
}

/**
 * Deactivation hook
 */
function wpai_deactivate(): void {
    // Clean up if needed
}

register_activation_hook(__FILE__, 'wpai_activate');
register_deactivation_hook(__FILE__, 'wpai_deactivate');

add_action('plugins_loaded', 'wpai_init', 10);

// Include shortcode handler
require_once WPAI_PATH . '/includes/shortcode.php';

// Add REST API endpoints
add_action('rest_api_init', 'wpai_register_rest_routes');

function wpai_register_rest_routes() {
    // Chat endpoint
    register_rest_route('wpai/v1', '/chat', [
        'methods' => 'POST',
        'callback' => 'wpai_handle_chat',
        'permission_callback' => 'wpai_check_permission',
    ]);
    
    // MCP HTTP endpoint (for browser dev mode)
    register_rest_route('wpai/v1', '/mcp', [
        'methods' => ['GET', 'POST', 'OPTIONS'],
        'callback' => 'wpai_handle_mcp_http',
        'permission_callback' => '__return_true',
    ]);
    
    // OAuth configuration endpoints (ChatGPT checks multiple locations)
    // Location 1: Relative to MCP endpoint
    register_rest_route('wpai/v1/mcp', '/.well-known/oauth-authorization-server', [
        'methods' => 'GET',
        'callback' => 'wpai_handle_oauth_config',
        'permission_callback' => '__return_true',
    ]);
    
    // Location 2: Standard .well-known location
    register_rest_route('wpai/v1', '/.well-known/oauth-authorization-server', [
        'methods' => 'GET',
        'callback' => 'wpai_handle_oauth_config',
        'permission_callback' => '__return_true',
    ]);
    
    // Location 3: Root .well-known
    register_rest_route('.well-known', '/oauth-authorization-server', [
        'methods' => 'GET',
        'callback' => 'wpai_handle_oauth_config',
        'permission_callback' => '__return_true',
    ]);
    
    // MCP SSE endpoint
    register_rest_route('wpai/v1', '/mcp/sse', [
        'methods' => 'GET',
        'callback' => 'wpai_handle_mcp_sse',
        'permission_callback' => 'wpai_check_mcp_permission',
    ]);
    
    // MCP tools endpoint
    register_rest_route('wpai/v1', '/mcp/tools', [
        'methods' => 'GET',
        'callback' => 'wpai_list_mcp_tools',
        'permission_callback' => 'wpai_check_mcp_permission',
    ]);
    
    // MCP execute endpoint
    register_rest_route('wpai/v1', '/mcp/execute', [
        'methods' => 'POST',
        'callback' => 'wpai_execute_mcp_tool',
        'permission_callback' => 'wpai_check_mcp_permission',
    ]);
    
    // OAuth endpoints (for ChatGPT browser)
    register_rest_route('wpai/v1', '/oauth/authorize', [
        'methods' => ['GET', 'POST'],
        'callback' => 'wpai_handle_oauth_authorize',
        'permission_callback' => '__return_true',
    ]);
    
    register_rest_route('wpai/v1', '/oauth/token', [
        'methods' => 'POST',
        'callback' => 'wpai_handle_oauth_token',
        'permission_callback' => '__return_true',
    ]);
}

function wpai_check_permission() {
    return is_user_logged_in() || wpai_check_api_key();
}

function wpai_handle_oauth_authorize($request) {
    // Set CORS headers
    header('Access-Control-Allow-Origin: *');
    header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
    header('Access-Control-Allow-Headers: Content-Type');
    
    $client_id = $request->get_param('client_id');
    $redirect_uri = $request->get_param('redirect_uri');
    $state = $request->get_param('state');
    $code_challenge = $request->get_param('code_challenge');
    
    // Generate authorization code
    $auth_code = wp_generate_password(32, false);
    set_transient('wpai_oauth_code_' . $auth_code, [
        'client_id' => $client_id,
        'code_challenge' => $code_challenge,
        'redirect_uri' => $redirect_uri,
    ], 300); // 5 minutes
    
    // Redirect back to ChatGPT with code
    $redirect_url = add_query_arg([
        'code' => $auth_code,
        'state' => $state,
    ], $redirect_uri);
    
    wp_redirect($redirect_url);
    exit;
}

function wpai_handle_oauth_token($request) {
    // Set CORS headers
    header('Access-Control-Allow-Origin: *');
    header('Access-Control-Allow-Methods: POST, OPTIONS');
    header('Access-Control-Allow-Headers: Content-Type');
    header('Content-Type: application/json');
    
    $grant_type = $request->get_param('grant_type');
    $code = $request->get_param('code');
    
    if ($grant_type === 'authorization_code') {
        // Verify code
        $code_data = get_transient('wpai_oauth_code_' . $code);
        
        if (!$code_data) {
            return new WP_REST_Response([
                'error' => 'invalid_grant',
                'error_description' => 'Authorization code is invalid or expired'
            ], 400);
        }
        
        // Delete used code
        delete_transient('wpai_oauth_code_' . $code);
        
        // Generate access token
        $access_token = wp_generate_password(40, false);
        set_transient('wpai_oauth_token_' . $access_token, [
            'client_id' => $code_data['client_id'],
            'expires' => time() + 3600,
        ], 3600); // 1 hour
        
        return new WP_REST_Response([
            'access_token' => $access_token,
            'token_type' => 'Bearer',
            'expires_in' => 3600,
        ]);
    }
    
    return new WP_REST_Response([
        'error' => 'unsupported_grant_type'
    ], 400);
}

function wpai_check_mcp_permission() {
    // For MCP, we'll allow access without authentication for now
    // In production, you might want to implement proper MCP auth
    return true;
    
    // Original auth code (commented out for MCP compatibility)
    /*
    $api_key = $_SERVER['HTTP_AUTHORIZATION'] ?? '';
    $stored_key = get_option('wpai_mcp_key', '');
    
    if (empty($stored_key)) {
        return current_user_can('manage_options');
    }
    
    $api_key = str_replace('Bearer ', '', $api_key);
    return hash_equals($stored_key, $api_key);
    */
}

function wpai_check_api_key() {
    $api_key = $_SERVER['HTTP_X_WPAI_API_KEY'] ?? '';
    $stored_key = get_option('wpai_options')['openai_api_key'] ?? '';
    
    return !empty($stored_key) && hash_equals($stored_key, $api_key);
}

function wpai_handle_chat($request) {
    $message = $request->get_param('message');
    $model = $request->get_param('model') ?? get_option('wpai_options')['default_model'] ?? WPAI_FALLBACK_MODEL;
    
    if (empty($message)) {
        return new WP_REST_Response(['error' => 'Message is required'], 400);
    }
    
    $options = get_option('wpai_options', []);
    $api_key = $options['openai_api_key'] ?? '';
    
    if (empty($api_key)) {
        return new WP_REST_Response(['error' => 'OpenAI API key not configured'], 400);
    }
    
    try {
        $response = wpai_call_openai($api_key, $message, $model);
        return new WP_REST_Response([
            'success' => true,
            'response' => $response['content'],
            'tokens' => $response['tokens'],
            'model' => $model,
        ]);
    } catch (Exception $e) {
        return new WP_REST_Response(['error' => $e->getMessage()], 500);
    }
}

function wpai_call_openai($api_key, $message, $model) {
    $ch = curl_init('https://api.openai.com/v1/chat/completions');
    
    $data = [
        'model' => $model,
        'messages' => [
            ['role' => 'user', 'content' => $message]
        ],
        'max_tokens' => 1000,
        'temperature' => 0.7,
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
        throw new Exception('OpenAI API error: ' . $message);
    }
    
    return [
        'content' => $decoded['choices'][0]['message']['content'] ?? '',
        'tokens' => $decoded['usage']['total_tokens'] ?? 0,
    ];
}

function wpai_handle_oauth_config($request) {
    // Set CORS headers
    header('Access-Control-Allow-Origin: *');
    header('Access-Control-Allow-Methods: GET, OPTIONS');
    header('Access-Control-Allow-Headers: Content-Type');
    header('Content-Type: application/json');
    
    $site_url = get_site_url();
    
    return new WP_REST_Response([
        'issuer' => $site_url,
        'authorization_endpoint' => rest_url('wpai/v1/oauth/authorize'),
        'token_endpoint' => rest_url('wpai/v1/oauth/token'),
        'response_types_supported' => ['code'],
        'grant_types_supported' => ['authorization_code', 'client_credentials'],
        'code_challenge_methods_supported' => ['S256'],
        'service_documentation' => $site_url,
        'developer' => 'Saeed M. Vardani',
        'company' => 'SeaTechOne.com',
    ]);
}

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
    
    // Check if OAuth token is present (but accept without it)
    $auth_header = $_SERVER['HTTP_AUTHORIZATION'] ?? '';
    // We'll accept requests with or without auth for now
    
    // Handle POST requests (MCP calls)
    if ($_SERVER['REQUEST_METHOD'] === 'POST') {
        $body = $request->get_json_params();
        $method = $body['method'] ?? '';
        $params = $body['params'] ?? [];
        
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
                    'id' => $body['id'] ?? null,
                    'result' => ['tools' => $tools_list]
                ]);
                
            case 'tools/call':
                $tool_name = $params['name'] ?? '';
                $arguments = $params['arguments'] ?? [];
                
                try {
                    $result = wpai_execute_tool_direct($tool_name, $arguments);
                    return new WP_REST_Response([
                        'jsonrpc' => '2.0',
                        'id' => $body['id'] ?? null,
                        'result' => [
                            'content' => [
                                ['type' => 'text', 'text' => json_encode($result, JSON_PRETTY_PRINT)]
                            ]
                        ]
                    ]);
                } catch (Exception $e) {
                    return new WP_REST_Response([
                        'jsonrpc' => '2.0',
                        'id' => $body['id'] ?? null,
                        'error' => [
                            'code' => -32000,
                            'message' => $e->getMessage()
                        ]
                    ], 500);
                }
        }
    }
    
    // Handle GET requests (server info with OAuth discovery link)
    return new WP_REST_Response([
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
        'endpoint' => rest_url('wpai/v1/mcp'),
        'oauth_config' => rest_url('wpai/v1/.well-known/oauth-authorization-server'),
        'tools' => array_keys(wpai_get_mcp_tools()),
        'links' => [
            'oauth' => rest_url('wpai/v1/.well-known/oauth-authorization-server')
        ]
    ]);
}

function wpai_execute_tool_direct($name, $arguments) {
    $tools = wpai_get_mcp_tools();
    
    if (!isset($tools[$name])) {
        throw new Exception("Unknown tool: $name");
    }
    
    return call_user_func($tools[$name]['callback'], $arguments);
}

function wpai_handle_mcp_sse($request) {
    // Set CORS headers for MCP
    header('Access-Control-Allow-Origin: *');
    header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
    header('Access-Control-Allow-Headers: Content-Type, Authorization');
    header('Access-Control-Max-Age: 86400');
    
    // Handle preflight requests
    if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
        http_response_code(200);
        exit;
    }
    
    // Set SSE headers
    header('Content-Type: text/event-stream');
    header('Cache-Control: no-cache');
    header('Connection: keep-alive');
    header('X-Accel-Buffering: no');
    
    if (ob_get_level()) {
        ob_end_clean();
    }
    
    // Send MCP protocol compliant response
    echo "event: connected\n";
    echo "data: " . json_encode([
        'protocolVersion' => '2024-11-05',
        'capabilities' => [
            'tools' => true,
            'resources' => false,
            'prompts' => false,
            'logging' => false
        ],
        'serverInfo' => [
            'name' => 'WP AI Engine Pro',
            'version' => WPAI_VERSION,
            'developer' => 'Saeed M. Vardani',
            'company' => 'SeaTechOne.com'
        ]
    ]) . "\n\n";
    flush();
    
    // Send tools list
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
    
    echo "event: tools\n";
    echo "data: " . json_encode(['tools' => $tools_list]) . "\n\n";
    flush();
    
    // Keep connection alive with minimal pings
    $ping_count = 0;
    while ($ping_count < 120) { // 1 hour with 30-second intervals
        echo "event: ping\n";
        echo "data: " . json_encode(['timestamp' => time()]) . "\n\n";
        flush();
        
        sleep(30);
        $ping_count++;
        
        if (connection_aborted()) {
            break;
        }
    }
}

function wpai_list_mcp_tools($request) {
    $tools = wpai_get_mcp_tools();
    $tools_list = [];
    
    foreach ($tools as $name => $tool) {
        $tools_list[] = [
            'name' => $name,
            'description' => $tool['description'],
            'parameters' => $tool['parameters'],
        ];
    }
    
    return new WP_REST_Response([
        'tools' => $tools_list,
        'count' => count($tools_list),
    ]);
}

function wpai_execute_mcp_tool($request) {
    $tool_name = $request->get_param('tool');
    $params = $request->get_param('parameters') ?? [];
    
    $tools = wpai_get_mcp_tools();
    
    if (!isset($tools[$tool_name])) {
        return new WP_REST_Response(['error' => 'Tool not found'], 404);
    }
    
    $tool = $tools[$tool_name];
    
    try {
        $result = call_user_func($tool['callback'], $params);
        return new WP_REST_Response(['success' => true, 'result' => $result]);
    } catch (Exception $e) {
        return new WP_REST_Response(['error' => $e->getMessage()], 500);
    }
}

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
                'status' => ['type' => 'string', 'default' => 'publish', 'description' => 'Post status (publish, draft, etc.)'],
            ],
            'callback' => function($params) {
                $args = [
                    'post_type' => $params['post_type'] ?? 'post',
                    'posts_per_page' => $params['posts_per_page'] ?? 10,
                    'post_status' => $params['status'] ?? 'publish',
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
                'status' => ['type' => 'string', 'default' => 'draft', 'description' => 'Post status (draft, publish, etc.)'],
                'post_type' => ['type' => 'string', 'default' => 'post', 'description' => 'Type of post to create'],
            ],
            'callback' => function($params) {
                $post_id = wp_insert_post([
                    'post_title' => $params['title'],
                    'post_content' => $params['content'],
                    'post_status' => $params['status'] ?? 'draft',
                    'post_type' => $params['post_type'] ?? 'post',
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

