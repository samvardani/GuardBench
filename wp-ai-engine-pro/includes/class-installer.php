<?php
/**
 * Installer
 * 
 * @package WPAIEnginePro
 */

declare(strict_types=1);

namespace WPAI;

if (!defined('ABSPATH')) {
    exit;
}

class Installer {
    public static function activate(): void {
        global $wpdb;
        
        $charset_collate = $wpdb->get_charset_collate();
        
        // Create tables
        $tables = [
            // Discussions table for chat history
            "CREATE TABLE IF NOT EXISTS {$wpdb->prefix}wpai_discussions (
                id bigint(20) NOT NULL AUTO_INCREMENT,
                user_id bigint(20) DEFAULT NULL,
                session_id varchar(100) NOT NULL,
                chatbot_id varchar(100) DEFAULT NULL,
                title varchar(255) DEFAULT NULL,
                created_at datetime NOT NULL,
                updated_at datetime NOT NULL,
                message_count int(11) DEFAULT 0,
                PRIMARY KEY (id),
                KEY user_id (user_id),
                KEY session_id (session_id),
                KEY created_at (created_at)
            ) $charset_collate;",
            
            // Messages table
            "CREATE TABLE IF NOT EXISTS {$wpdb->prefix}wpai_messages (
                id bigint(20) NOT NULL AUTO_INCREMENT,
                discussion_id bigint(20) NOT NULL,
                role varchar(20) NOT NULL,
                content longtext NOT NULL,
                tokens int(11) DEFAULT 0,
                cost decimal(10,6) DEFAULT 0,
                model varchar(100) DEFAULT NULL,
                created_at datetime NOT NULL,
                PRIMARY KEY (id),
                KEY discussion_id (discussion_id),
                KEY created_at (created_at)
            ) $charset_collate;",
            
            // Embeddings table
            "CREATE TABLE IF NOT EXISTS {$wpdb->prefix}wpai_embeddings (
                id bigint(20) NOT NULL AUTO_INCREMENT,
                post_id bigint(20) DEFAULT NULL,
                content longtext NOT NULL,
                vector longtext NOT NULL,
                model varchar(100) NOT NULL,
                tokens int(11) DEFAULT 0,
                created_at datetime NOT NULL,
                updated_at datetime NOT NULL,
                PRIMARY KEY (id),
                KEY post_id (post_id),
                KEY created_at (created_at)
            ) $charset_collate;",
            
            // Logs table
            "CREATE TABLE IF NOT EXISTS {$wpdb->prefix}wpai_logs (
                id bigint(20) NOT NULL AUTO_INCREMENT,
                type varchar(50) NOT NULL,
                message text NOT NULL,
                context longtext DEFAULT NULL,
                user_id bigint(20) DEFAULT NULL,
                created_at datetime NOT NULL,
                PRIMARY KEY (id),
                KEY type (type),
                KEY created_at (created_at)
            ) $charset_collate;",
            
            // Usage stats table
            "CREATE TABLE IF NOT EXISTS {$wpdb->prefix}wpai_usage (
                id bigint(20) NOT NULL AUTO_INCREMENT,
                user_id bigint(20) DEFAULT NULL,
                model varchar(100) NOT NULL,
                tokens_input int(11) DEFAULT 0,
                tokens_output int(11) DEFAULT 0,
                cost decimal(10,6) DEFAULT 0,
                endpoint varchar(100) DEFAULT NULL,
                created_at datetime NOT NULL,
                PRIMARY KEY (id),
                KEY user_id (user_id),
                KEY model (model),
                KEY created_at (created_at)
            ) $charset_collate;",
        ];
        
        require_once(ABSPATH . 'wp-admin/includes/upgrade.php');
        
        foreach ($tables as $sql) {
            dbDelta($sql);
        }
        
        // Set default options
        $defaults = [
            'version' => WPAI_VERSION,
            'installed_at' => current_time('mysql'),
            'mcp_enabled' => true,
            'module_chatbot' => true,
            'module_content' => true,
            'module_embeddings' => true,
        ];
        
        add_option('wpai_options', $defaults);
        
        // Create upload directory
        $upload_dir = wp_upload_dir();
        $wpai_dir = $upload_dir['basedir'] . '/wpai-files';
        
        if (!file_exists($wpai_dir)) {
            wp_mkdir_p($wpai_dir);
            
            // Add .htaccess for security
            $htaccess = $wpai_dir . '/.htaccess';
            if (!file_exists($htaccess)) {
                file_put_contents($htaccess, 'deny from all');
            }
            
            // Add index.php
            $index = $wpai_dir . '/index.php';
            if (!file_exists($index)) {
                file_put_contents($index, '<?php // Silence is golden');
            }
        }
        
        // Schedule cron jobs
        if (!wp_next_scheduled('wpai_cleanup_old_data')) {
            wp_schedule_event(time(), 'daily', 'wpai_cleanup_old_data');
        }
        
        // Flush rewrite rules
        flush_rewrite_rules();
    }
    
    public static function deactivate(): void {
        // Clear scheduled cron jobs
        wp_clear_scheduled_hook('wpai_cleanup_old_data');
        
        flush_rewrite_rules();
    }
    
    public static function uninstall(): void {
        global $wpdb;
        
        // Delete tables
        $tables = [
            $wpdb->prefix . 'wpai_discussions',
            $wpdb->prefix . 'wpai_messages',
            $wpdb->prefix . 'wpai_embeddings',
            $wpdb->prefix . 'wpai_logs',
            $wpdb->prefix . 'wpai_usage',
        ];
        
        foreach ($tables as $table) {
            $wpdb->query("DROP TABLE IF EXISTS {$table}");
        }
        
        // Delete options
        delete_option('wpai_options');
        delete_option('wpai_chatbots');
        delete_option('wpai_themes');
        
        // Delete transients
        $wpdb->query("DELETE FROM {$wpdb->options} WHERE option_name LIKE '_transient_wpai_%'");
        $wpdb->query("DELETE FROM {$wpdb->options} WHERE option_name LIKE '_transient_timeout_wpai_%'");
        
        // Delete upload directory (optional, commented for safety)
        // $upload_dir = wp_upload_dir();
        // $wpai_dir = $upload_dir['basedir'] . '/wpai-files';
        // if (file_exists($wpai_dir)) {
        //     wpai_delete_directory($wpai_dir);
        // }
    }
}



