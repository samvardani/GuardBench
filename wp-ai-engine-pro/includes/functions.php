<?php
/**
 * Helper functions
 * 
 * @package WPAIEnginePro
 */

declare(strict_types=1);

if (!defined('ABSPATH')) {
    exit;
}

/**
 * Get plugin instance
 */
function wpai(): \WPAI\Core {
    return \WPAI\Core::instance();
}

/**
 * Log message
 */
function wpai_log(string $type, string $message, array $context = []): void {
    global $wpdb;
    
    $wpdb->insert(
        $wpdb->prefix . 'wpai_logs',
        [
            'type' => $type,
            'message' => $message,
            'context' => json_encode($context),
            'user_id' => get_current_user_id(),
            'created_at' => current_time('mysql'),
        ],
        ['%s', '%s', '%s', '%d', '%s']
    );
    
    do_action('wpai_log', $type, $message, $context);
}

/**
 * Get AI model instance
 */
function wpai_get_engine(string $provider = 'openai'): ?\WPAI\Engines\EngineInterface {
    $class_map = [
        'openai' => \WPAI\Engines\OpenAI::class,
        'anthropic' => \WPAI\Engines\Anthropic::class,
        'google' => \WPAI\Engines\Google::class,
        'azure' => \WPAI\Engines\Azure::class,
    ];
    
    $class = $class_map[$provider] ?? null;
    
    if ($class && class_exists($class)) {
        return new $class();
    }
    
    return null;
}

/**
 * Sanitize AI content
 */
function wpai_sanitize_content(string $content): string {
    // Allow safe HTML tags
    $allowed_tags = wp_kses_allowed_html('post');
    $allowed_tags['pre'] = ['class' => true];
    $allowed_tags['code'] = ['class' => true];
    
    return wp_kses($content, $allowed_tags);
}

/**
 * Calculate token count (rough estimation)
 */
function wpai_estimate_tokens(string $text): int {
    // Rough estimation: 1 token ~= 4 characters
    return (int) ceil(strlen($text) / 4);
}

/**
 * Format cost
 */
function wpai_format_cost(float $cost): string {
    return '$' . number_format($cost, 4);
}

/**
 * Check rate limit
 */
function wpai_check_rate_limit(int $user_id, string $action, int $limit = 100, int $period = 3600): bool {
    $transient_key = 'wpai_rate_limit_' . $user_id . '_' . $action;
    $count = get_transient($transient_key);
    
    if ($count === false) {
        set_transient($transient_key, 1, $period);
        return true;
    }
    
    if ($count >= $limit) {
        return false;
    }
    
    set_transient($transient_key, $count + 1, $period);
    return true;
}

/**
 * Delete directory recursively
 */
function wpai_delete_directory(string $dir): bool {
    if (!file_exists($dir)) {
        return true;
    }
    
    if (!is_dir($dir)) {
        return unlink($dir);
    }
    
    foreach (scandir($dir) as $item) {
        if ($item == '.' || $item == '..') {
            continue;
        }
        
        if (!wpai_delete_directory($dir . DIRECTORY_SEPARATOR . $item)) {
            return false;
        }
    }
    
    return rmdir($dir);
}

/**
 * Get supported AI models
 */
function wpai_get_models(string $provider = 'all'): array {
    $models = [
        'openai' => [
            'gpt-5-chat-latest' => ['name' => 'GPT-5 Chat', 'type' => 'chat'],
            'gpt-5-mini' => ['name' => 'GPT-5 Mini', 'type' => 'chat'],
            'gpt-4.5-turbo' => ['name' => 'GPT-4.5 Turbo', 'type' => 'chat'],
            'gpt-4-turbo' => ['name' => 'GPT-4 Turbo', 'type' => 'chat'],
            'text-embedding-3-large' => ['name' => 'Embeddings 3 Large', 'type' => 'embedding'],
            'text-embedding-3-small' => ['name' => 'Embeddings 3 Small', 'type' => 'embedding'],
        ],
        'anthropic' => [
            'claude-4.5-sonnet' => ['name' => 'Claude 4.5 Sonnet', 'type' => 'chat'],
            'claude-4-opus' => ['name' => 'Claude 4 Opus', 'type' => 'chat'],
            'claude-3.5-sonnet' => ['name' => 'Claude 3.5 Sonnet', 'type' => 'chat'],
        ],
        'google' => [
            'gemini-2.5-pro' => ['name' => 'Gemini 2.5 Pro', 'type' => 'chat'],
            'gemini-2.0-pro' => ['name' => 'Gemini 2.0 Pro', 'type' => 'chat'],
        ],
    ];
    
    if ($provider === 'all') {
        return $models;
    }
    
    return $models[$provider] ?? [];
}

/**
 * Render template
 */
function wpai_render_template(string $template, array $data = []): string {
    $template_file = WPAI_PATH . '/templates/' . $template . '.php';
    
    if (!file_exists($template_file)) {
        return '';
    }
    
    extract($data);
    ob_start();
    include $template_file;
    return ob_get_clean();
}



