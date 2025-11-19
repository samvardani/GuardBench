<?php
/**
 * REST API
 * 
 * @package WPAIEnginePro
 */

declare(strict_types=1);

namespace WPAI\API;

if (!defined('ABSPATH')) {
    exit;
}

class Rest {
    private \WPAI\Core $core;
    private string $namespace = 'wpai/v1';
    
    public function __construct(\WPAI\Core $core) {
        $this->core = $core;
        add_action('rest_api_init', [$this, 'register_routes']);
    }
    
    public function register_routes(): void {
        // Chat/Completion endpoint
        register_rest_route($this->namespace, '/chat', [
            'methods' => 'POST',
            'callback' => [$this, 'chat'],
            'permission_callback' => [$this, 'check_permission'],
        ]);
        
        // Streaming chat endpoint
        register_rest_route($this->namespace, '/chat/stream', [
            'methods' => 'POST',
            'callback' => [$this, 'chat_stream'],
            'permission_callback' => [$this, 'check_permission'],
        ]);
        
        // Content generation
        register_rest_route($this->namespace, '/generate', [
            'methods' => 'POST',
            'callback' => [$this, 'generate_content'],
            'permission_callback' => [$this->core, 'can_access_features'],
        ]);
        
        // Embeddings
        register_rest_route($this->namespace, '/embeddings', [
            'methods' => 'POST',
            'callback' => [$this, 'create_embedding'],
            'permission_callback' => [$this->core, 'can_access_features'],
        ]);
        
        // Settings
        register_rest_route($this->namespace, '/settings', [
            'methods' => 'GET',
            'callback' => [$this, 'get_settings'],
            'permission_callback' => [$this->core, 'can_access_settings'],
        ]);
        
        register_rest_route($this->namespace, '/settings', [
            'methods' => 'POST',
            'callback' => [$this, 'update_settings'],
            'permission_callback' => [$this->core, 'can_access_settings'],
        ]);
        
        // Usage stats
        register_rest_route($this->namespace, '/usage', [
            'methods' => 'GET',
            'callback' => [$this, 'get_usage'],
            'permission_callback' => [$this->core, 'can_access_settings'],
        ]);
        
        // Discussions
        register_rest_route($this->namespace, '/discussions', [
            'methods' => 'GET',
            'callback' => [$this, 'list_discussions'],
            'permission_callback' => [$this, 'check_permission'],
        ]);
        
        register_rest_route($this->namespace, '/discussions/(?P<id>\d+)', [
            'methods' => 'GET',
            'callback' => [$this, 'get_discussion'],
            'permission_callback' => [$this, 'check_permission'],
        ]);
    }
    
    public function check_permission(): bool {
        // Allow logged in users or valid API key
        if (is_user_logged_in()) {
            return true;
        }
        
        // Check API key
        $api_key = $_SERVER['HTTP_X_WPAI_API_KEY'] ?? '';
        $stored_key = $this->core->get_option('api_key', '');
        
        if (!empty($stored_key) && hash_equals($stored_key, $api_key)) {
            return true;
        }
        
        // Check rate limit for public access
        if ($this->core->get_option('allow_public_chat', false)) {
            $ip = $_SERVER['REMOTE_ADDR'] ?? '';
            return wpai_check_rate_limit(0, 'public_chat_' . $ip, 100, 3600);
        }
        
        return false;
    }
    
    public function chat(\WP_REST_Request $request): \WP_REST_Response {
        $message = $request->get_param('message');
        $model = $request->get_param('model') ?? $this->core->get_option('default_model');
        $max_tokens = $request->get_param('max_tokens') ?? $this->core->get_option('max_tokens', 4096);
        $temperature = $request->get_param('temperature') ?? $this->core->get_option('temperature', 0.7);
        $discussion_id = $request->get_param('discussion_id');
        
        if (empty($message)) {
            return new \WP_REST_Response([
                'error' => 'Message is required',
            ], 400);
        }
        
        try {
            // Get conversation history if discussion_id provided
            $history = [];
            if ($discussion_id) {
                $history = $this->get_discussion_history($discussion_id);
            }
            
            // Call AI engine
            $engine = wpai_get_engine('openai');
            if (!$engine) {
                throw new \Exception('AI engine not available');
            }
            
            $response = $engine->chat([
                'messages' => array_merge($history, [
                    ['role' => 'user', 'content' => $message]
                ]),
                'model' => $model,
                'max_tokens' => $max_tokens,
                'temperature' => $temperature,
            ]);
            
            // Save to discussion
            if ($discussion_id) {
                $this->save_to_discussion($discussion_id, $message, $response['content'], $response['tokens'], $response['cost']);
            }
            
            // Log usage
            $this->log_usage($model, $response['tokens_input'], $response['tokens_output'], $response['cost']);
            
            return new \WP_REST_Response([
                'success' => true,
                'response' => $response['content'],
                'tokens' => $response['tokens'],
                'cost' => $response['cost'],
                'model' => $model,
            ]);
        } catch (\Exception $e) {
            wpai_log('api_error', 'Chat error', [
                'message' => $e->getMessage(),
                'trace' => $e->getTraceAsString(),
            ]);
            
            return new \WP_REST_Response([
                'error' => apply_filters('wpai_ai_exception', $e->getMessage()),
            ], 500);
        }
    }
    
    public function chat_stream(\WP_REST_Request $request): void {
        // Set headers for SSE
        header('Content-Type: text/event-stream');
        header('Cache-Control: no-cache');
        header('X-Accel-Buffering: no');
        
        if (ob_get_level()) {
            ob_end_clean();
        }
        
        $message = $request->get_param('message');
        $model = $request->get_param('model') ?? $this->core->get_option('default_model');
        
        try {
            $engine = wpai_get_engine('openai');
            
            $engine->stream_chat([
                'messages' => [['role' => 'user', 'content' => $message]],
                'model' => $model,
            ], function($chunk) {
                echo "data: " . json_encode(['content' => $chunk]) . "\n\n";
                flush();
            });
            
            echo "data: [DONE]\n\n";
            flush();
        } catch (\Exception $e) {
            echo "data: " . json_encode(['error' => $e->getMessage()]) . "\n\n";
            flush();
        }
    }
    
    public function generate_content(\WP_REST_Request $request): \WP_REST_Response {
        $prompt = $request->get_param('prompt');
        $type = $request->get_param('type') ?? 'post';
        
        if (empty($prompt)) {
            return new \WP_REST_Response(['error' => 'Prompt is required'], 400);
        }
        
        try {
            $engine = wpai_get_engine('openai');
            
            $system_prompts = [
                'post' => 'You are a professional content writer. Create engaging blog posts.',
                'product' => 'You are an expert product description writer. Write compelling product descriptions.',
                'email' => 'You are a professional email copywriter. Write effective emails.',
            ];
            
            $response = $engine->chat([
                'messages' => [
                    ['role' => 'system', 'content' => $system_prompts[$type] ?? $system_prompts['post']],
                    ['role' => 'user', 'content' => $prompt]
                ],
            ]);
            
            return new \WP_REST_Response([
                'success' => true,
                'content' => $response['content'],
                'tokens' => $response['tokens'],
            ]);
        } catch (\Exception $e) {
            return new \WP_REST_Response(['error' => $e->getMessage()], 500);
        }
    }
    
    public function create_embedding(\WP_REST_Request $request): \WP_REST_Response {
        $text = $request->get_param('text');
        $model = $request->get_param('model') ?? WPAI_FALLBACK_EMBEDDINGS;
        
        if (empty($text)) {
            return new \WP_REST_Response(['error' => 'Text is required'], 400);
        }
        
        try {
            $engine = wpai_get_engine('openai');
            $embedding = $engine->create_embedding($text, $model);
            
            return new \WP_REST_Response([
                'success' => true,
                'embedding' => $embedding,
                'dimensions' => count($embedding),
            ]);
        } catch (\Exception $e) {
            return new \WP_REST_Response(['error' => $e->getMessage()], 500);
        }
    }
    
    public function get_settings(): \WP_REST_Response {
        $settings = $this->core->get_all_options();
        
        // Remove sensitive data
        unset($settings['api_key']);
        unset($settings['mcp_api_key']);
        unset($settings['openai_api_key']);
        
        return new \WP_REST_Response($settings);
    }
    
    public function update_settings(\WP_REST_Request $request): \WP_REST_Response {
        $settings = $request->get_json_params();
        
        foreach ($settings as $key => $value) {
            $this->core->set_option($key, $value);
        }
        
        return new \WP_REST_Response(['success' => true]);
    }
    
    public function get_usage(): \WP_REST_Response {
        global $wpdb;
        
        $table = $wpdb->prefix . 'wpai_usage';
        
        // Get total usage
        $total = $wpdb->get_row("
            SELECT 
                SUM(tokens_input) as total_input,
                SUM(tokens_output) as total_output,
                SUM(cost) as total_cost,
                COUNT(*) as total_requests
            FROM {$table}
        ");
        
        // Get usage by model
        $by_model = $wpdb->get_results("
            SELECT 
                model,
                SUM(tokens_input + tokens_output) as total_tokens,
                SUM(cost) as total_cost,
                COUNT(*) as request_count
            FROM {$table}
            GROUP BY model
            ORDER BY total_cost DESC
        ");
        
        return new \WP_REST_Response([
            'total' => $total,
            'by_model' => $by_model,
        ]);
    }
    
    public function list_discussions(): \WP_REST_Response {
        global $wpdb;
        
        $table = $wpdb->prefix . 'wpai_discussions';
        $user_id = get_current_user_id();
        
        $discussions = $wpdb->get_results($wpdb->prepare("
            SELECT * FROM {$table}
            WHERE user_id = %d
            ORDER BY updated_at DESC
            LIMIT 50
        ", $user_id));
        
        return new \WP_REST_Response($discussions);
    }
    
    public function get_discussion(\WP_REST_Request $request): \WP_REST_Response {
        global $wpdb;
        
        $id = $request->get_param('id');
        $discussion_table = $wpdb->prefix . 'wpai_discussions';
        $messages_table = $wpdb->prefix . 'wpai_messages';
        
        $discussion = $wpdb->get_row($wpdb->prepare("
            SELECT * FROM {$discussion_table} WHERE id = %d
        ", $id));
        
        if (!$discussion) {
            return new \WP_REST_Response(['error' => 'Discussion not found'], 404);
        }
        
        $messages = $wpdb->get_results($wpdb->prepare("
            SELECT * FROM {$messages_table}
            WHERE discussion_id = %d
            ORDER BY created_at ASC
        ", $id));
        
        return new \WP_REST_Response([
            'discussion' => $discussion,
            'messages' => $messages,
        ]);
    }
    
    private function get_discussion_history(int $discussion_id): array {
        global $wpdb;
        
        $table = $wpdb->prefix . 'wpai_messages';
        $messages = $wpdb->get_results($wpdb->prepare("
            SELECT role, content FROM {$table}
            WHERE discussion_id = %d
            ORDER BY created_at ASC
            LIMIT 20
        ", $discussion_id), ARRAY_A);
        
        return $messages;
    }
    
    private function save_to_discussion(int $discussion_id, string $user_message, string $ai_response, int $tokens, float $cost): void {
        global $wpdb;
        
        $messages_table = $wpdb->prefix . 'wpai_messages';
        $discussions_table = $wpdb->prefix . 'wpai_discussions';
        
        // Save user message
        $wpdb->insert($messages_table, [
            'discussion_id' => $discussion_id,
            'role' => 'user',
            'content' => $user_message,
            'created_at' => current_time('mysql'),
        ]);
        
        // Save AI response
        $wpdb->insert($messages_table, [
            'discussion_id' => $discussion_id,
            'role' => 'assistant',
            'content' => $ai_response,
            'tokens' => $tokens,
            'cost' => $cost,
            'created_at' => current_time('mysql'),
        ]);
        
        // Update discussion
        $wpdb->query($wpdb->prepare("
            UPDATE {$discussions_table}
            SET updated_at = %s, message_count = message_count + 2
            WHERE id = %d
        ", current_time('mysql'), $discussion_id));
    }
    
    private function log_usage(string $model, int $tokens_input, int $tokens_output, float $cost): void {
        global $wpdb;
        
        $table = $wpdb->prefix . 'wpai_usage';
        
        $wpdb->insert($table, [
            'user_id' => get_current_user_id(),
            'model' => $model,
            'tokens_input' => $tokens_input,
            'tokens_output' => $tokens_output,
            'cost' => $cost,
            'endpoint' => 'chat',
            'created_at' => current_time('mysql'),
        ]);
    }
}



