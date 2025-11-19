#!/usr/bin/env php
<?php
/**
 * MCP Server Stdio Transport for WordPress
 * This script handles MCP protocol communication via stdio (stdin/stdout)
 * 
 * @developer Saeed M. Vardani
 * @company SeaTechOne.com
 */

// Load WordPress
$wp_load_paths = [
    __DIR__ . '/../../../../wp-load.php',
    __DIR__ . '/../../../wp-load.php',
    __DIR__ . '/../../wp-load.php',
    __DIR__ . '/../wp-load.php',
];

foreach ($wp_load_paths as $path) {
    if (file_exists($path)) {
        require_once $path;
        break;
    }
}

if (!defined('ABSPATH')) {
    fwrite(STDERR, "Error: Could not load WordPress\n");
    exit(1);
}

// Set up stdio communication
$stdin = fopen('php://stdin', 'r');
$stdout = fopen('php://stdout', 'w');
$stderr = fopen('php://stderr', 'w');

// Error handler
set_error_handler(function($errno, $errstr, $errfile, $errline) use ($stderr) {
    fwrite($stderr, "Error: $errstr in $errfile on line $errline\n");
});

// Log function
function log_message($message) {
    global $stderr;
    fwrite($stderr, date('[Y-m-d H:i:s] ') . $message . "\n");
}

// Send JSON-RPC response
function send_response($id, $result = null, $error = null) {
    global $stdout;
    
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

// Handle MCP requests
function handle_request($request) {
    $method = $request['method'] ?? '';
    $params = $request['params'] ?? [];
    $id = $request['id'] ?? null;
    
    log_message("Received request: $method");
    
    switch ($method) {
        case 'initialize':
            send_response($id, [
                'protocolVersion' => '2024-11-05',
                'capabilities' => [
                    'tools' => ['listChanged' => true],
                ],
                'serverInfo' => [
                    'name' => 'WP AI Engine Pro',
                    'version' => '4.0.2',
                    'developer' => 'Saeed M. Vardani',
                    'company' => 'SeaTechOne.com',
                ],
            ]);
            break;
            
        case 'tools/list':
            $tools = get_wordpress_tools();
            send_response($id, ['tools' => $tools]);
            break;
            
        case 'tools/call':
            $tool_name = $params['name'] ?? '';
            $arguments = $params['arguments'] ?? [];
            
            $result = execute_tool($tool_name, $arguments);
            send_response($id, ['content' => [
                ['type' => 'text', 'text' => json_encode($result, JSON_PRETTY_PRINT)]
            ]]);
            break;
            
        default:
            send_response($id, null, [
                'code' => -32601,
                'message' => 'Method not found: ' . $method
            ]);
    }
}

// Get available WordPress tools
function get_wordpress_tools() {
    return [
        [
            'name' => 'wp_get_site_info',
            'description' => 'Get WordPress site information including name, URL, version, and developer details',
            'inputSchema' => [
                'type' => 'object',
                'properties' => [],
            ],
        ],
        [
            'name' => 'wp_list_posts',
            'description' => 'List WordPress posts with title, content, date, and author information',
            'inputSchema' => [
                'type' => 'object',
                'properties' => [
                    'post_type' => ['type' => 'string', 'description' => 'Type of posts', 'default' => 'post'],
                    'posts_per_page' => ['type' => 'number', 'description' => 'Number of posts', 'default' => 10],
                    'status' => ['type' => 'string', 'description' => 'Post status', 'default' => 'publish'],
                ],
            ],
        ],
        [
            'name' => 'wp_create_post',
            'description' => 'Create a new WordPress post with title and content',
            'inputSchema' => [
                'type' => 'object',
                'properties' => [
                    'title' => ['type' => 'string', 'description' => 'Post title'],
                    'content' => ['type' => 'string', 'description' => 'Post content'],
                    'status' => ['type' => 'string', 'description' => 'Post status', 'default' => 'draft'],
                ],
                'required' => ['title', 'content'],
            ],
        ],
        [
            'name' => 'wp_get_stats',
            'description' => 'Get WordPress site statistics including posts, pages, comments, and users count',
            'inputSchema' => [
                'type' => 'object',
                'properties' => [],
            ],
        ],
    ];
}

// Execute WordPress tool
function execute_tool($name, $arguments) {
    switch ($name) {
        case 'wp_get_site_info':
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
                    'slug' => $post->post_name,
                    'status' => $post->post_status,
                    'date' => $post->post_date,
                    'author' => get_the_author_meta('display_name', $post->post_author),
                    'excerpt' => wp_trim_words($post->post_content, 30),
                    'url' => get_permalink($post->ID),
                ];
            }, $posts);
            
        case 'wp_create_post':
            $post_id = wp_insert_post([
                'post_title' => $arguments['title'],
                'post_content' => $arguments['content'],
                'post_status' => $arguments['status'] ?? 'draft',
                'post_type' => 'post',
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
                'media' => wp_count_posts('attachment')->inherit,
            ];
            
        default:
            throw new Exception("Unknown tool: $name");
    }
}

// Main loop
log_message("MCP Server started - Saeed M. Vardani / SeaTechOne.com");

while (!feof($stdin)) {
    $line = trim(fgets($stdin));
    
    if (empty($line)) {
        continue;
    }
    
    $request = json_decode($line, true);
    
    if (json_last_error() !== JSON_ERROR_NONE) {
        log_message("JSON decode error: " . json_last_error_msg());
        continue;
    }
    
    try {
        handle_request($request);
    } catch (Exception $e) {
        log_message("Error: " . $e->getMessage());
        send_response($request['id'] ?? null, null, [
            'code' => -32000,
            'message' => $e->getMessage()
        ]);
    }
}

log_message("MCP Server stopped");

