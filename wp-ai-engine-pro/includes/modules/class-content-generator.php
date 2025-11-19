<?php
/**
 * Content Generator Module
 * 
 * @package WPAIEnginePro
 */

declare(strict_types=1);

namespace WPAI\Modules;

if (!defined('ABSPATH')) {
    exit;
}

class ContentGenerator {
    private \WPAI\Core $core;
    
    public function __construct(\WPAI\Core $core) {
        $this->core = $core;
        
        // Add meta box to post editor
        add_action('add_meta_boxes', [$this, 'add_meta_box']);
        
        // Add Gutenberg integration
        add_action('enqueue_block_editor_assets', [$this, 'enqueue_block_editor']);
    }
    
    public function add_meta_box(): void {
        add_meta_box(
            'wpai_content_generator',
            'AI Content Generator',
            [$this, 'render_meta_box'],
            ['post', 'page'],
            'side',
            'high'
        );
    }
    
    public function render_meta_box(): void {
        ?>
        <div id="wpai-content-generator">
            <textarea id="wpai-prompt" placeholder="Describe what you want to write about..."></textarea>
            <button id="wpai-generate" class="button button-primary">Generate Content</button>
            <div id="wpai-status"></div>
        </div>
        <?php
    }
    
    public function enqueue_block_editor(): void {
        wp_enqueue_script(
            'wpai-block-editor',
            WPAI_URL . 'assets/js/block-editor.js',
            ['wp-blocks', 'wp-element', 'wp-editor'],
            WPAI_VERSION
        );
    }
}



