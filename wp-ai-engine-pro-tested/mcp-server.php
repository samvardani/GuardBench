<?php
/**
 * MCP Server for ChatGPT Desktop (stdio transport)
 * 
 * This script is designed to be run as a subprocess by ChatGPT Desktop.
 * It uses standard input/output for JSON-RPC 2.0 communication.
 * 
 * @package WPAIEnginePro
 * @developer Saeed M. Vardani
 * @company SeaTechOne.com
 */

// Load WordPress environment
$wp_load_path = dirname(__FILE__, 4) . '/wp-load.php';

if (!file_exists($wp_load_path)) {
    fwrite(STDERR, "Error: WordPress not found at: $wp_load_path\n");
    exit(1);
}

require_once $wp_load_path;

// Set up standard I/O
$stdin = fopen('php://stdin', 'r');
$stdout = fopen('php://stdout', 'w');

if (!$stdin || !$stdout) {
    fwrite(STDERR, "Error: Failed to open stdin/stdout\n");
    exit(1);
}

/**
 * Send a JSON-RPC response
 * 
 * @param resource $stdout Output stream
 * @param mixed $id Request ID
 * @param mixed $result Result data
 * @param mixed $error Error data
 */
function wpai_mcp_send_response($stdout, $id, $result = null, $error = null): void {
    $response = [
        'jsonrpc' => '2.0',
        'id' => $id,
    ];
    
    if ($error !== null) {
        $response['error'] = $error;
    } else {
        $response['result'] = $result;
    }
    
    $json = json_encode($response);
    fwrite($stdout, $json . "\n");
    fflush($stdout);
}

/**
 * Get available MCP tools
 * 
 * @return array Tool definitions
 */
function wpai_mcp_get_tools(): array {
    return [
        'wp_get_site_info' => [
            'description' => 'Get WordPress site information',
            'parameters' => [],
        ],
        'wp_list_posts' => [
            'description' => 'List WordPress posts',
            'parameters' => [
                'post_type' => ['type' => 'string', 'default' => 'post'],
                'posts_per_page' => ['type' => 'integer', 'default' => 10],
                'status' => ['type' => 'string', 'default' => 'publish'],
            ],
        ],
        'wp_create_post' => [
            'description' => 'Create a new WordPress post',
            'parameters' => [
                'title' => ['type' => 'string', 'required' => true],
                'content' => ['type' => 'string', 'required' => true],
                'status' => ['type' => 'string', 'default' => 'draft'],
            ],
        ],
        'wp_get_stats' => [
            'description' => 'Get WordPress site statistics',
            'parameters' => [],
        ],
    ];
}

/**
 * Execute a tool
 * 
 * @param string $name Tool name
 * @param array $arguments Tool arguments
 * @return mixed Tool result
 */
function wpai_mcp_execute_tool(string $name, array $arguments) {
    switch ($name) {
        case 'wp_get_site_info':
            return [
                'name' => get_bloginfo('name'),
                'description' => get_bloginfo('description'),
                'url' => get_site_url(),
                'wp_version' => get_bloginfo('version'),
                'php_version' => PHP_VERSION,
                'theme' => wp_get_theme()->get('Name'),
                'developer' => 'Saeed M. Vardani',
                'company' => 'SeaTechOne.com',
            ];
            
        case 'wp_list_posts':
            $args = [
                'post_type' => $arguments['post_type'] ?? 'post',
                'posts_per_page' => $arguments['posts_per_page'] ?? 10,
                'post_status' => $arguments['status'] ?? 'publish',
            ];
            
            $posts = get_posts($args);
            
            return array_map(function($post) {
                return [
                    'id' => $post->ID,
                    'title' => $post->post_title,
                    'date' => $post->post_date,
                    'author' => get_the_author_meta('display_name', $post->post_author),
                    'url' => get_permalink($post->ID),
                ];
            }, $posts);
            
        case 'wp_create_post':
            $post_id = wp_insert_post([
                'post_title' => $arguments['title'],
                'post_content' => $arguments['content'],
                'post_status' => $arguments['status'] ?? 'draft',
            ]);
            
            if (is_wp_error($post_id)) {
                throw new Exception($post_id->get_error_message());
            }
            
            return [
                'success' => true,
                'post_id' => $post_id,
                'url' => get_permalink($post_id),
            ];
            
        case 'wp_get_stats':
            return [
                'posts' => wp_count_posts('post')->publish,
                'pages' => wp_count_posts('page')->publish,
                'comments' => wp_count_comments()->approved,
                'users' => count_users()['total_users'],
            ];
            
        default:
            throw new Exception("Unknown tool: $name");
    }
}

// Main loop to process requests
while (!feof($stdin)) {
    $line = trim(fgets($stdin));
    
    if (empty($line)) {
        continue;
    }
    
    $request = json_decode($line, true);
    
    if (json_last_error() !== JSON_ERROR_NONE) {
        wpai_mcp_send_response($stdout, null, null, [
            'code' => -32700,
            'message' => 'Parse error: ' . json_last_error_msg()
        ]);
        continue;
    }
    
    $method = $request['method'] ?? '';
    $params = $request['params'] ?? [];
    $id = $request['id'] ?? null;
    
    try {
        $result = null;
        $error = null;
        
        switch ($method) {
            case 'tools/list':
                $tools = wpai_mcp_get_tools();
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
                
                $result = ['tools' => $tools_list];
                break;
                
            case 'tools/call':
                $tool_name = $params['name'] ?? '';
                $arguments = $params['arguments'] ?? [];
                
                $tool_result = wpai_mcp_execute_tool($tool_name, $arguments);
                
                $result = [
                    'content' => [
                        [
                            'type' => 'text',
                            'text' => json_encode($tool_result, JSON_PRETTY_PRINT)
                        ]
                    ]
                ];
                break;
                
            default:
                $error = [
                    'code' => -32601,
                    'message' => 'Method not found: ' . $method
                ];
                break;
        }
        
        wpai_mcp_send_response($stdout, $id, $result, $error);
        
    } catch (Exception $e) {
        wpai_mcp_send_response($stdout, $id, null, [
            'code' => -32000,
            'message' => $e->getMessage()
        ]);
    }
}

fclose($stdin);
fclose($stdout);

