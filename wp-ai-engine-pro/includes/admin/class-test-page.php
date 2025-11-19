<?php
/**
 * Test Settings Page
 * 
 * @package WPAIEnginePro
 */

declare(strict_types=1);

namespace WPAI\Admin;

if (!defined('ABSPATH')) {
    exit;
}

class TestPage {
    private \WPAI\Core $core;
    
    public function __construct(\WPAI\Core $core) {
        $this->core = $core;
        
        add_action('admin_menu', [$this, 'add_test_page']);
    }
    
    public function add_test_page(): void {
        add_submenu_page(
            'wpai',
            'Test Settings',
            'Test Settings',
            'manage_options',
            'wpai-test',
            [$this, 'render_test_page']
        );
    }
    
    public function render_test_page(): void {
        ?>
        <div class="wrap">
            <h1>WP AI Engine Pro - Test Settings</h1>
            
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
                            <td><?php echo !empty($this->core->get_option('openai_api_key')) ? '✓ Set' : '✗ Not Set'; ?></td>
                            <td><?php echo !empty($this->core->get_option('openai_api_key')) ? '<span style="color: green;">Ready</span>' : '<span style="color: red;">Missing</span>'; ?></td>
                        </tr>
                        <tr>
                            <td>Default Model</td>
                            <td><?php echo esc_html($this->core->get_option('default_model', WPAI_FALLBACK_MODEL)); ?></td>
                            <td><span style="color: green;">OK</span></td>
                        </tr>
                        <tr>
                            <td>Max Tokens</td>
                            <td><?php echo esc_html($this->core->get_option('max_tokens', 4096)); ?></td>
                            <td><span style="color: green;">OK</span></td>
                        </tr>
                        <tr>
                            <td>Temperature</td>
                            <td><?php echo esc_html($this->core->get_option('temperature', 0.7)); ?></td>
                            <td><span style="color: green;">OK</span></td>
                        </tr>
                        <tr>
                            <td>MCP Enabled</td>
                            <td><?php echo $this->core->get_option('mcp_enabled', true) ? 'Yes' : 'No'; ?></td>
                            <td><?php echo $this->core->get_option('mcp_enabled', true) ? '<span style="color: green;">Enabled</span>' : '<span style="color: orange;">Disabled</span>'; ?></td>
                        </tr>
                        <tr>
                            <td>Chatbot Module</td>
                            <td><?php echo $this->core->get_option('module_chatbot', true) ? 'Yes' : 'No'; ?></td>
                            <td><?php echo $this->core->get_option('module_chatbot', true) ? '<span style="color: green;">Enabled</span>' : '<span style="color: orange;">Disabled</span>'; ?></td>
                        </tr>
                        <tr>
                            <td>Content Generator</td>
                            <td><?php echo $this->core->get_option('module_content', true) ? 'Yes' : 'No'; ?></td>
                            <td><?php echo $this->core->get_option('module_content', true) ? '<span style="color: green;">Enabled</span>' : '<span style="color: orange;">Disabled</span>'; ?></td>
                        </tr>
                        <tr>
                            <td>Embeddings Module</td>
                            <td><?php echo $this->core->get_option('module_embeddings', true) ? 'Yes' : 'No'; ?></td>
                            <td><?php echo $this->core->get_option('module_embeddings', true) ? '<span style="color: green;">Enabled</span>' : '<span style="color: orange;">Disabled</span>'; ?></td>
                        </tr>
                    </tbody>
                </table>
                
                <h2>Quick Test</h2>
                <p>Test the chatbot shortcode: <code>[wpai_chatbot]</code></p>
                <p>Add this to any page or post to test the chatbot functionality.</p>
                
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
            </div>
        </div>
        <?php
    }
}



