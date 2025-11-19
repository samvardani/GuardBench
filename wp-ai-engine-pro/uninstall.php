<?php
/**
 * Uninstall script
 * 
 * @package WPAIEnginePro
 */

// Exit if not called from WordPress
if (!defined('WP_UNINSTALL_PLUGIN')) {
    exit;
}

require_once plugin_dir_path(__FILE__) . 'includes/class-installer.php';

\WPAI\Installer::uninstall();



