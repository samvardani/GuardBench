<?php
/**
 * MCP Server - Model Context Protocol for ChatGPT WordPress Control
 * 
 * @package WPAIEnginePro
 */

declare(strict_types=1);

namespace WPAI\MCP;

if (!defined('ABSPATH')) {
    exit;
}

class Server {
    private \WPAI\Core $core;
    private array $tools = [];
    
    public function __construct(\WPAI\Core $core) {
        $this->core = $core;
        
        // Register MCP endpoints
        add_action('rest_api_init', [$this, 'register_endpoints']);
        
        // Register tools
        $this->register_core_tools();
        $this->register_post_tools();
        $this->register_media_tools();
        $this->register_plugin_tools();
        $this->register_theme_tools();
        $this->register_user_tools();
    }
    
    public function register_endpoints(): void {
        // SSE endpoint for ChatGPT/Claude
        register_rest_route('wpai/v1', '/mcp/sse', [
            'methods' => 'GET',
            'callback' => [$this, 'handle_sse'],
            'permission_callback' => [$this, 'check_mcp_permission'],
        ]);
        
        // Tools listing
        register_rest_route('wpai/v1', '/mcp/tools', [
            'methods' => 'GET',
            'callback' => [$this, 'list_tools'],
            'permission_callback' => [$this, 'check_mcp_permission'],
        ]);
        
        // Tool execution
        register_rest_route('wpai/v1', '/mcp/execute', [
            'methods' => 'POST',
            'callback' => [$this, 'execute_tool'],
            'permission_callback' => [$this, 'check_mcp_permission'],
        ]);
    }
    
    public function check_mcp_permission(): bool {
        // Check if MCP is enabled
        if (!$this->core->get_option('mcp_enabled', true)) {
            return false;
        }
        
        // Check authentication
        $api_key = $_SERVER['HTTP_AUTHORIZATION'] ?? '';
        $stored_key = $this->core->get_option('mcp_api_key', '');
        
        if (empty($stored_key)) {
            // No API key set, check WordPress authentication
            return current_user_can('manage_options');
        }
        
        // Validate API key
        $api_key = str_replace('Bearer ', '', $api_key);
        return hash_equals($stored_key, $api_key);
    }
    
    public function handle_sse(\WP_REST_Request $request): void {
        // Set SSE headers
        header('Content-Type: text/event-stream');
        header('Cache-Control: no-cache');
        header('Connection: keep-alive');
        header('X-Accel-Buffering: no');
        
        // Disable output buffering
        if (ob_get_level()) {
            ob_end_clean();
        }
        
        // Send initial connection message
        $this->send_sse_event('connected', [
            'server' => 'WP AI Engine Pro',
            'version' => WPAI_VERSION,
            'capabilities' => array_keys($this->tools),
        ]);
        
        // Keep connection alive
        $max_duration = 3600; // 1 hour
        $start_time = time();
        
        while (time() - $start_time < $max_duration) {
            // Send ping every 30 seconds
            $this->send_sse_event('ping', ['timestamp' => time()]);
            
            // Check for new requests in queue
            $this->process_mcp_queue();
            
            sleep(30);
            
            if (connection_aborted()) {
                break;
            }
        }
    }
    
    private function send_sse_event(string $event, array $data): void {
        echo "event: {$event}\n";
        echo "data: " . json_encode($data) . "\n\n";
        flush();
    }
    
    public function list_tools(): \WP_REST_Response {
        $tools_list = [];
        
        foreach ($this->tools as $name => $tool) {
            $tools_list[] = [
                'name' => $name,
                'description' => $tool['description'],
                'parameters' => $tool['parameters'],
            ];
        }
        
        return new \WP_REST_Response([
            'tools' => $tools_list,
            'count' => count($tools_list),
        ]);
    }
    
    public function execute_tool(\WP_REST_Request $request): \WP_REST_Response {
        $tool_name = $request->get_param('tool');
        $params = $request->get_param('parameters') ?? [];
        
        if (!isset($this->tools[$tool_name])) {
            return new \WP_REST_Response([
                'success' => false,
                'error' => 'Tool not found',
            ], 404);
        }
        
        $tool = $this->tools[$tool_name];
        
        try {
            $result = call_user_func($tool['callback'], $params);
            
            wpai_log('mcp_execute', "Executed tool: {$tool_name}", [
                'params' => $params,
                'result' => $result,
            ]);
            
            return new \WP_REST_Response([
                'success' => true,
                'result' => $result,
            ]);
        } catch (\Exception $e) {
            wpai_log('mcp_error', "Tool execution failed: {$tool_name}", [
                'error' => $e->getMessage(),
            ]);
            
            return new \WP_REST_Response([
                'success' => false,
                'error' => $e->getMessage(),
            ], 500);
        }
    }
    
    private function register_tool(string $name, string $description, array $parameters, callable $callback): void {
        $this->tools[$name] = [
            'description' => $description,
            'parameters' => $parameters,
            'callback' => $callback,
        ];
    }
    
    private function register_core_tools(): void {
        // Get site info
        $this->register_tool(
            'wp_get_site_info',
            'Get WordPress site information',
            [],
            function($params) {
                return [
                    'name' => get_bloginfo('name'),
                    'description' => get_bloginfo('description'),
                    'url' => get_site_url(),
                    'admin_email' => get_option('admin_email'),
                    'wp_version' => get_bloginfo('version'),
                    'php_version' => PHP_VERSION,
                    'theme' => wp_get_theme()->get('Name'),
                    'active_plugins' => count(get_option('active_plugins', [])),
                ];
            }
        );
        
        // Get site stats
        $this->register_tool(
            'wp_get_stats',
            'Get site statistics',
            [],
            function($params) {
                return [
                    'posts' => wp_count_posts('post')->publish,
                    'pages' => wp_count_posts('page')->publish,
                    'comments' => wp_count_comments()->approved,
                    'users' => count_users()['total_users'],
                    'media' => wp_count_posts('attachment')->inherit,
                ];
            }
        );
    }
    
    private function register_post_tools(): void {
        // List posts
        $this->register_tool(
            'wp_list_posts',
            'List WordPress posts',
            [
                'post_type' => ['type' => 'string', 'default' => 'post'],
                'posts_per_page' => ['type' => 'integer', 'default' => 10],
                'status' => ['type' => 'string', 'default' => 'publish'],
            ],
            function($params) {
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
        );
        
        // Get post
        $this->register_tool(
            'wp_get_post',
            'Get a specific post',
            [
                'id' => ['type' => 'integer', 'required' => true],
            ],
            function($params) {
                $post = get_post($params['id']);
                
                if (!$post) {
                    throw new \Exception('Post not found');
                }
                
                return [
                    'id' => $post->ID,
                    'title' => $post->post_title,
                    'content' => $post->post_content,
                    'excerpt' => $post->post_excerpt,
                    'status' => $post->post_status,
                    'date' => $post->post_date,
                    'modified' => $post->post_modified,
                    'author' => get_the_author_meta('display_name', $post->post_author),
                    'categories' => wp_get_post_categories($post->ID, ['fields' => 'names']),
                    'tags' => wp_get_post_tags($post->ID, ['fields' => 'names']),
                    'featured_image' => get_the_post_thumbnail_url($post->ID, 'full'),
                    'url' => get_permalink($post->ID),
                ];
            }
        );
        
        // Create post
        $this->register_tool(
            'wp_create_post',
            'Create a new post',
            [
                'title' => ['type' => 'string', 'required' => true],
                'content' => ['type' => 'string', 'required' => true],
                'status' => ['type' => 'string', 'default' => 'draft'],
                'post_type' => ['type' => 'string', 'default' => 'post'],
            ],
            function($params) {
                $post_id = wp_insert_post([
                    'post_title' => $params['title'],
                    'post_content' => $params['content'],
                    'post_status' => $params['status'] ?? 'draft',
                    'post_type' => $params['post_type'] ?? 'post',
                ]);
                
                if (is_wp_error($post_id)) {
                    throw new \Exception($post_id->get_error_message());
                }
                
                return [
                    'success' => true,
                    'post_id' => $post_id,
                    'url' => get_permalink($post_id),
                ];
            }
        );
        
        // Update post
        $this->register_tool(
            'wp_update_post',
            'Update an existing post',
            [
                'id' => ['type' => 'integer', 'required' => true],
                'title' => ['type' => 'string'],
                'content' => ['type' => 'string'],
                'status' => ['type' => 'string'],
            ],
            function($params) {
                $post_data = ['ID' => $params['id']];
                
                if (isset($params['title'])) {
                    $post_data['post_title'] = $params['title'];
                }
                if (isset($params['content'])) {
                    $post_data['post_content'] = $params['content'];
                }
                if (isset($params['status'])) {
                    $post_data['post_status'] = $params['status'];
                }
                
                $result = wp_update_post($post_data);
                
                if (is_wp_error($result)) {
                    throw new \Exception($result->get_error_message());
                }
                
                return [
                    'success' => true,
                    'post_id' => $result,
                ];
            }
        );
        
        // Delete post
        $this->register_tool(
            'wp_delete_post',
            'Delete a post',
            [
                'id' => ['type' => 'integer', 'required' => true],
                'force' => ['type' => 'boolean', 'default' => false],
            ],
            function($params) {
                $result = wp_delete_post($params['id'], $params['force'] ?? false);
                
                return [
                    'success' => (bool)$result,
                ];
            }
        );
    }
    
    private function register_media_tools(): void {
        // List media
        $this->register_tool(
            'wp_list_media',
            'List media files',
            [
                'per_page' => ['type' => 'integer', 'default' => 20],
            ],
            function($params) {
                $attachments = get_posts([
                    'post_type' => 'attachment',
                    'posts_per_page' => $params['per_page'] ?? 20,
                    'post_status' => 'inherit',
                ]);
                
                return array_map(function($attachment) {
                    return [
                        'id' => $attachment->ID,
                        'title' => $attachment->post_title,
                        'url' => wp_get_attachment_url($attachment->ID),
                        'type' => get_post_mime_type($attachment->ID),
                        'date' => $attachment->post_date,
                    ];
                }, $attachments);
            }
        );
    }
    
    private function register_plugin_tools(): void {
        // List plugins
        $this->register_tool(
            'wp_list_plugins',
            'List installed plugins',
            [],
            function($params) {
                $plugins = get_plugins();
                $active = get_option('active_plugins', []);
                
                $result = [];
                foreach ($plugins as $path => $plugin) {
                    $result[] = [
                        'name' => $plugin['Name'],
                        'version' => $plugin['Version'],
                        'active' => in_array($path, $active),
                        'path' => $path,
                    ];
                }
                
                return $result;
            }
        );
    }
    
    private function register_theme_tools(): void {
        // List themes
        $this->register_tool(
            'wp_list_themes',
            'List installed themes',
            [],
            function($params) {
                $themes = wp_get_themes();
                $current = get_stylesheet();
                
                $result = [];
                foreach ($themes as $slug => $theme) {
                    $result[] = [
                        'name' => $theme->get('Name'),
                        'version' => $theme->get('Version'),
                        'active' => $slug === $current,
                        'slug' => $slug,
                    ];
                }
                
                return $result;
            }
        );
    }
    
    private function register_user_tools(): void {
        // List users
        $this->register_tool(
            'wp_list_users',
            'List WordPress users',
            [
                'role' => ['type' => 'string'],
                'number' => ['type' => 'integer', 'default' => 10],
            ],
            function($params) {
                $args = [
                    'number' => $params['number'] ?? 10,
                ];
                
                if (isset($params['role'])) {
                    $args['role'] = $params['role'];
                }
                
                $users = get_users($args);
                
                return array_map(function($user) {
                    return [
                        'id' => $user->ID,
                        'username' => $user->user_login,
                        'email' => $user->user_email,
                        'display_name' => $user->display_name,
                        'roles' => $user->roles,
                    ];
                }, $users);
            }
        );
    }
    
    private function process_mcp_queue(): void {
        // Check for queued MCP requests
        // This can be extended to handle async operations
    }
}



