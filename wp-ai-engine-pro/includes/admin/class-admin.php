<?php
/**
 * Admin Interface
 * 
 * @package WPAIEnginePro
 */

declare(strict_types=1);

namespace WPAI\Admin;

if (!defined('ABSPATH')) {
    exit;
}

class Admin {
    private \WPAI\Core $core;
    
    public function __construct(\WPAI\Core $core) {
        $this->core = $core;
        
        add_action('admin_menu', [$this, 'add_menu']);
        add_action('admin_enqueue_scripts', [$this, 'enqueue_assets']);
        
        // Add test page
        new \WPAI\Admin\TestPage($core);
    }
    
    public function add_menu(): void {
        add_menu_page(
            'WP AI Engine Pro',
            'AI Engine',
            'manage_options',
            'wpai',
            [$this, 'render_dashboard'],
            'dashicons-admin-generic',
            30
        );
        
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
            [$this, 'render_mcp_setup']
        );
        
        add_submenu_page(
            'wpai',
            'Usage Stats',
            'Usage Stats',
            'manage_options',
            'wpai-usage',
            [$this, 'render_usage']
        );
    }
    
    public function enqueue_assets($hook): void {
        if (strpos($hook, 'wpai') !== false) {
            wp_enqueue_style('wpai-admin');
            wp_enqueue_script('wpai-admin');
        }
    }
    
    public function render_dashboard(): void {
        global $wpdb;
        
        $stats = [
            'total_conversations' => $wpdb->get_var("SELECT COUNT(*) FROM {$wpdb->prefix}wpai_discussions"),
            'total_messages' => $wpdb->get_var("SELECT COUNT(*) FROM {$wpdb->prefix}wpai_messages"),
            'total_cost' => $wpdb->get_var("SELECT SUM(cost) FROM {$wpdb->prefix}wpai_usage"),
            'embeddings_count' => $wpdb->get_var("SELECT COUNT(*) FROM {$wpdb->prefix}wpai_embeddings"),
        ];
        
        ?>
        <div class="wrap">
            <h1>WP AI Engine Pro - Dashboard</h1>
            
            <div class="wpai-dashboard">
                <div class="wpai-stats">
                    <div class="wpai-stat-card">
                        <h3>Conversations</h3>
                        <p class="wpai-stat-number"><?php echo number_format($stats['total_conversations']); ?></p>
                    </div>
                    
                    <div class="wpai-stat-card">
                        <h3>Messages</h3>
                        <p class="wpai-stat-number"><?php echo number_format($stats['total_messages']); ?></p>
                    </div>
                    
                    <div class="wpai-stat-card">
                        <h3>Total Cost</h3>
                        <p class="wpai-stat-number"><?php echo wpai_format_cost($stats['total_cost'] ?? 0); ?></p>
                    </div>
                    
                    <div class="wpai-stat-card">
                        <h3>Embeddings</h3>
                        <p class="wpai-stat-number"><?php echo number_format($stats['embeddings_count']); ?></p>
                    </div>
                </div>
                
                <div class="wpai-quick-actions">
                    <h2>Quick Actions</h2>
                    <a href="<?php echo admin_url('admin.php?page=wpai-settings'); ?>" class="button button-primary">Configure Settings</a>
                    <a href="<?php echo admin_url('admin.php?page=wpai-mcp'); ?>" class="button">Setup MCP</a>
                    <a href="<?php echo admin_url('post-new.php'); ?>" class="button">Create Post with AI</a>
                </div>
            </div>
        </div>
        <?php
    }
    
    public function render_settings(): void {
        if (isset($_POST['wpai_save_settings']) && check_admin_referer('wpai_settings')) {
            $settings = [
                'openai_api_key' => sanitize_text_field($_POST['openai_api_key'] ?? ''),
                'default_model' => sanitize_text_field($_POST['default_model'] ?? WPAI_FALLBACK_MODEL),
                'max_tokens' => intval($_POST['max_tokens'] ?? 4096),
                'temperature' => floatval($_POST['temperature'] ?? 0.7),
                'mcp_enabled' => isset($_POST['mcp_enabled']),
                'module_chatbot' => isset($_POST['module_chatbot']),
                'module_content' => isset($_POST['module_content']),
                'module_embeddings' => isset($_POST['module_embeddings']),
                'allow_public_chat' => isset($_POST['allow_public_chat']),
                'show_chatbot_globally' => isset($_POST['show_chatbot_globally']),
            ];
            
            foreach ($settings as $key => $value) {
                $this->core->set_option($key, $value);
            }
            
            echo '<div class="notice notice-success"><p>Settings saved successfully!</p></div>';
        }
        
        $openai_key = $this->core->get_option('openai_api_key', '');
        $default_model = $this->core->get_option('default_model', WPAI_FALLBACK_MODEL);
        $max_tokens = $this->core->get_option('max_tokens', 4096);
        $temperature = $this->core->get_option('temperature', 0.7);
        $mcp_enabled = $this->core->get_option('mcp_enabled', true);
        $module_chatbot = $this->core->get_option('module_chatbot', true);
        $module_content = $this->core->get_option('module_content', true);
        $module_embeddings = $this->core->get_option('module_embeddings', true);
        $allow_public_chat = $this->core->get_option('allow_public_chat', false);
        $show_chatbot_globally = $this->core->get_option('show_chatbot_globally', false);
        
        ?>
        <div class="wrap">
            <h1>WP AI Engine Pro - Settings</h1>
            
            <form method="post" action="">
                <?php wp_nonce_field('wpai_settings'); ?>
                
                <table class="form-table">
                    <tr>
                        <th scope="row"><label for="openai_api_key">OpenAI API Key</label></th>
                        <td>
                            <input type="password" id="openai_api_key" name="openai_api_key" 
                                   value="<?php echo esc_attr($openai_key); ?>" 
                                   class="regular-text" />
                            <p class="description">Get your API key from <a href="https://platform.openai.com/api-keys" target="_blank">OpenAI</a></p>
                        </td>
                    </tr>
                    
                    <tr>
                        <th scope="row"><label for="default_model">Default Model</label></th>
                        <td>
                            <select id="default_model" name="default_model">
                                <?php foreach (wpai_get_models('openai') as $model => $info): ?>
                                    <?php if ($info['type'] === 'chat'): ?>
                                        <option value="<?php echo esc_attr($model); ?>" 
                                                <?php selected($default_model, $model); ?>>
                                            <?php echo esc_html($info['name']); ?>
                                        </option>
                                    <?php endif; ?>
                                <?php endforeach; ?>
                            </select>
                        </td>
                    </tr>
                    
                    <tr>
                        <th scope="row"><label for="max_tokens">Max Tokens</label></th>
                        <td>
                            <input type="number" id="max_tokens" name="max_tokens" 
                                   value="<?php echo esc_attr($max_tokens); ?>" 
                                   min="1" max="128000" />
                        </td>
                    </tr>
                    
                    <tr>
                        <th scope="row"><label for="temperature">Temperature</label></th>
                        <td>
                            <input type="number" id="temperature" name="temperature" 
                                   value="<?php echo esc_attr($temperature); ?>" 
                                   min="0" max="2" step="0.1" />
                            <p class="description">0 = focused, 2 = creative</p>
                        </td>
                    </tr>
                    
                    <tr>
                        <th scope="row">Modules</th>
                        <td>
                            <label>
                                <input type="checkbox" name="mcp_enabled" <?php checked($mcp_enabled); ?> />
                                Enable MCP (ChatGPT Control)
                            </label><br />
                            
                            <label>
                                <input type="checkbox" name="module_chatbot" <?php checked($module_chatbot); ?> />
                                Enable Chatbot
                            </label><br />
                            
                            <label>
                                <input type="checkbox" name="module_content" <?php checked($module_content); ?> />
                                Enable Content Generator
                            </label><br />
                            
                            <label>
                                <input type="checkbox" name="module_embeddings" <?php checked($module_embeddings); ?> />
                                Enable Embeddings
                            </label><br />
                            
                            <label>
                                <input type="checkbox" name="allow_public_chat" <?php checked($allow_public_chat); ?> />
                                Allow Public Chat (no login required)
                            </label><br />
                            
                            <label>
                                <input type="checkbox" name="show_chatbot_globally" <?php checked($show_chatbot_globally); ?> />
                                Show Chatbot on All Pages
                            </label>
                        </td>
                    </tr>
                </table>
                
                <p class="submit">
                    <button type="submit" name="wpai_save_settings" class="button button-primary">Save Settings</button>
                </p>
            </form>
        </div>
        <?php
    }
    
    public function render_mcp_setup(): void {
        $api_key = $this->core->get_option('mcp_api_key', '');
        
        if (empty($api_key)) {
            $api_key = wp_generate_password(32, false);
            $this->core->set_option('mcp_api_key', $api_key);
        }
        
        $mcp_url = rest_url('wpai/v1/mcp/sse');
        
        ?>
        <div class="wrap">
            <h1>MCP Setup - Control WordPress from ChatGPT</h1>
            
            <div class="wpai-mcp-setup">
                <h2>Setup Instructions</h2>
                
                <h3>Step 1: Install MCP Client</h3>
                <p>For ChatGPT Desktop, edit your configuration file:</p>
                <pre>~/.config/OpenAI/ChatGPT/config.json</pre>
                
                <h3>Step 2: Add Configuration</h3>
                <p>Add this to your config.json:</p>
                <pre><code>{
  "mcpServers": {
    "wordpress": {
      "url": "<?php echo esc_js($mcp_url); ?>",
      "headers": {
        "Authorization": "Bearer <?php echo esc_js($api_key); ?>"
      }
    }
  }
}</code></pre>
                
                <h3>Step 3: Restart ChatGPT</h3>
                <p>Restart ChatGPT Desktop application to load the configuration.</p>
                
                <h3>Step 4: Test Connection</h3>
                <p>In ChatGPT, try asking: "What posts do I have on my WordPress site?"</p>
                
                <h3>Available Commands</h3>
                <ul>
                    <li>List posts: "Show me my recent posts"</li>
                    <li>Create post: "Create a new blog post about AI"</li>
                    <li>Update post: "Update post 123 with new content"</li>
                    <li>Site info: "What's my WordPress site information?"</li>
                    <li>List users: "Show me all users"</li>
                    <li>Manage plugins: "What plugins are installed?"</li>
                </ul>
                
                <div class="wpai-info-box">
                    <strong>Your MCP Endpoint:</strong><br />
                    <code><?php echo esc_html($mcp_url); ?></code><br /><br />
                    
                    <strong>Your API Key:</strong><br />
                    <code><?php echo esc_html($api_key); ?></code><br />
                    <button type="button" class="button" onclick="navigator.clipboard.writeText('<?php echo esc_js($api_key); ?>')">
                        Copy API Key
                    </button>
                </div>
            </div>
        </div>
        <?php
    }
    
    public function render_usage(): void {
        global $wpdb;
        
        $table = $wpdb->prefix . 'wpai_usage';
        
        $usage_data = $wpdb->get_results("
            SELECT 
                model,
                SUM(tokens_input + tokens_output) as total_tokens,
                SUM(cost) as total_cost,
                COUNT(*) as request_count
            FROM {$table}
            GROUP BY model
            ORDER BY total_cost DESC
        ");
        
        ?>
        <div class="wrap">
            <h1>Usage Statistics</h1>
            
            <table class="wp-list-table widefat fixed striped">
                <thead>
                    <tr>
                        <th>Model</th>
                        <th>Requests</th>
                        <th>Total Tokens</th>
                        <th>Total Cost</th>
                    </tr>
                </thead>
                <tbody>
                    <?php foreach ($usage_data as $row): ?>
                        <tr>
                            <td><?php echo esc_html($row->model); ?></td>
                            <td><?php echo number_format($row->request_count); ?></td>
                            <td><?php echo number_format($row->total_tokens); ?></td>
                            <td><?php echo wpai_format_cost($row->total_cost); ?></td>
                        </tr>
                    <?php endforeach; ?>
                </tbody>
            </table>
        </div>
        <?php
    }
}

