<?php
/**
 * Embeddings Module
 * 
 * @package WPAIEnginePro
 */

declare(strict_types=1);

namespace WPAI\Modules;

if (!defined('ABSPATH')) {
    exit;
}

class Embeddings {
    private \WPAI\Core $core;
    
    public function __construct(\WPAI\Core $core) {
        $this->core = $core;
        
        // Auto-generate embeddings on post save
        add_action('save_post', [$this, 'generate_on_save'], 10, 2);
        
        // Semantic search
        add_filter('posts_search', [$this, 'semantic_search'], 10, 2);
    }
    
    public function generate_on_save(int $post_id, \WP_Post $post): void {
        // Skip autosave and revisions
        if (wp_is_post_autosave($post_id) || wp_is_post_revision($post_id)) {
            return;
        }
        
        // Only for published posts
        if ($post->post_status !== 'publish') {
            return;
        }
        
        // Generate embedding
        $this->generate_embedding($post_id);
    }
    
    public function generate_embedding(int $post_id): bool {
        global $wpdb;
        
        $post = get_post($post_id);
        if (!$post) {
            return false;
        }
        
        try {
            $content = $post->post_title . "\n\n" . $post->post_content;
            $content = wp_strip_all_tags($content);
            $content = substr($content, 0, 8000); // Limit length
            
            $engine = wpai_get_engine('openai');
            $vector = $engine->create_embedding($content, WPAI_FALLBACK_EMBEDDINGS);
            
            $table = $wpdb->prefix . 'wpai_embeddings';
            
            // Check if embedding exists
            $exists = $wpdb->get_var($wpdb->prepare(
                "SELECT id FROM {$table} WHERE post_id = %d",
                $post_id
            ));
            
            if ($exists) {
                $wpdb->update(
                    $table,
                    [
                        'content' => $content,
                        'vector' => json_encode($vector),
                        'updated_at' => current_time('mysql'),
                    ],
                    ['post_id' => $post_id]
                );
            } else {
                $wpdb->insert($table, [
                    'post_id' => $post_id,
                    'content' => $content,
                    'vector' => json_encode($vector),
                    'model' => WPAI_FALLBACK_EMBEDDINGS,
                    'tokens' => wpai_estimate_tokens($content),
                    'created_at' => current_time('mysql'),
                    'updated_at' => current_time('mysql'),
                ]);
            }
            
            return true;
        } catch (\Exception $e) {
            wpai_log('embedding_error', 'Failed to generate embedding', [
                'post_id' => $post_id,
                'error' => $e->getMessage(),
            ]);
            return false;
        }
    }
    
    public function semantic_search(string $search, \WP_Query $query): string {
        if (!$this->core->get_option('semantic_search_enabled', false)) {
            return $search;
        }
        
        if (empty($query->query_vars['s'])) {
            return $search;
        }
        
        // This is a simplified version - production would need vector similarity search
        return $search;
    }
}



