<?php
/**
 * Plugin Name: Virtual Staging Platform
 * Plugin URI: https://yourdomain.com
 * Description: Embed the Virtual Staging Platform in WordPress - Professional real estate staging services with AI-powered virtual staging, booking, and payment integration.
 * Version: 1.0.0
 * Author: Your Name
 * Author URI: https://yourdomain.com
 * License: GPL v2 or later
 * Text Domain: virtual-staging-platform
 */

// Prevent direct access
if (!defined('ABSPATH')) {
    exit;
}

// Define plugin constants
define('VSP_VERSION', '1.0.0');
define('VSP_PLUGIN_DIR', plugin_dir_path(__FILE__));
define('VSP_PLUGIN_URL', plugin_dir_url(__FILE__));
define('VSP_API_BASE', get_option('vsp_api_base', 'http://localhost:8001'));

// Register activation hook
register_activation_hook(__FILE__, 'vsp_activate');
function vsp_activate() {
    // Set default options
    if (!get_option('vsp_api_base')) {
        update_option('vsp_api_base', 'http://localhost:8001');
    }
}

// Register settings
function vsp_register_settings() {
    register_setting('vsp_settings', 'vsp_api_base');
    register_setting('vsp_settings', 'vsp_iframe_height');
    
    add_settings_section(
        'vsp_api_section',
        'API Configuration',
        'vsp_api_section_callback',
        'vsp_settings'
    );
    
    add_settings_field(
        'vsp_api_base',
        'API Base URL',
        'vsp_api_base_callback',
        'vsp_settings',
        'vsp_api_section'
    );
    
    add_settings_field(
        'vsp_iframe_height',
        'Iframe Height (px)',
        'vsp_iframe_height_callback',
        'vsp_settings',
        'vsp_api_section'
    );
}
add_action('admin_init', 'vsp_register_settings');

function vsp_api_section_callback() {
    echo '<p>Configure the Virtual Staging Platform API connection. The API should be running and accessible from your WordPress site.</p>';
}

function vsp_api_base_callback() {
    $value = get_option('vsp_api_base', 'http://localhost:8001');
    echo '<input type="text" name="vsp_api_base" value="' . esc_attr($value) . '" class="regular-text" />';
    echo '<p class="description">Base URL of your staging platform API (e.g., http://localhost:8001 or https://api.yourdomain.com)</p>';
}

function vsp_iframe_height_callback() {
    $value = get_option('vsp_iframe_height', '800');
    echo '<input type="number" name="vsp_iframe_height" value="' . esc_attr($value) . '" class="small-text" min="400" max="2000" />';
    echo '<p class="description">Height of the embedded platform in pixels (400-2000)</p>';
}

// Add admin menu
function vsp_add_admin_menu() {
    add_options_page(
        'Virtual Staging Platform Settings',
        'Staging Platform',
        'manage_options',
        'vsp-settings',
        'vsp_settings_page'
    );
}
add_action('admin_menu', 'vsp_add_admin_menu');

function vsp_settings_page() {
    if (!current_user_can('manage_options')) {
        return;
    }
    
    if (isset($_GET['settings-updated'])) {
        add_settings_error('vsp_messages', 'vsp_message', 'Settings Saved', 'updated');
    }
    
    settings_errors('vsp_messages');
    ?>
    <div class="wrap">
        <h1><?php echo esc_html(get_admin_page_title()); ?></h1>
        <form action="options.php" method="post">
            <?php
            settings_fields('vsp_settings');
            do_settings_sections('vsp_settings');
            submit_button('Save Settings');
            ?>
        </form>
        
        <div class="card" style="max-width: 800px; margin-top: 20px;">
            <h2>Usage Instructions</h2>
            <h3>Shortcode</h3>
            <p>Add the staging platform to any page or post using this shortcode:</p>
            <code>[virtual_staging]</code>
            
            <h3>Custom Height</h3>
            <p>You can specify a custom height:</p>
            <code>[virtual_staging height="1000px"]</code>
            
            <h3>Widget</h3>
            <p>Go to <strong>Appearance → Widgets</strong> and add the "Virtual Staging Platform" widget to your sidebar or widget area.</p>
            
            <h3>Page Template</h3>
            <p>Create a new page and select "Virtual Staging Platform" as the page template.</p>
        </div>
    </div>
    <?php
}

// Shortcode to embed the platform
function vsp_shortcode($atts) {
    $atts = shortcode_atts(array(
        'height' => get_option('vsp_iframe_height', '800') . 'px',
        'api_base' => VSP_API_BASE,
    ), $atts);
    
    $api_base = esc_url($atts['api_base']);
    $height = esc_attr($atts['height']);
    
    // Ensure height has units
    if (is_numeric($height)) {
        $height = $height . 'px';
    }
    
    ob_start();
    ?>
    <div id="vsp-container" style="width: 100%; height: <?php echo $height; ?>; border: 1px solid #e5e7eb; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
        <iframe 
            id="vsp-iframe" 
            src="<?php echo $api_base; ?>/staging/" 
            style="width: 100%; height: 100%; border: none; display: block;"
            allow="camera; microphone; payment; fullscreen"
            title="Virtual Staging Platform"
            loading="lazy"
        ></iframe>
    </div>
    <script>
        (function() {
            const iframe = document.getElementById('vsp-iframe');
            const container = document.getElementById('vsp-container');
            
            // Handle postMessage communication
            window.addEventListener('message', function(event) {
                // Verify origin for security
                const allowedOrigin = '<?php echo esc_js($api_base); ?>';
                if (event.origin !== allowedOrigin) {
                    return;
                }
                
                // Handle messages from iframe
                if (event.data && event.data.type === 'vsp-resize') {
                    // Allow iframe to request height changes
                    if (event.data.height) {
                        container.style.height = event.data.height;
                    }
                }
            });
            
            // Send configuration to iframe when loaded
            iframe.addEventListener('load', function() {
                try {
                    iframe.contentWindow.postMessage({
                        type: 'vsp-config',
                        apiBase: '<?php echo esc_js($api_base); ?>',
                        wpUrl: '<?php echo esc_js(home_url()); ?>'
                    }, '<?php echo esc_js($api_base); ?>');
                } catch (e) {
                    console.log('Could not send config to iframe:', e);
                }
            });
            
            // Handle iframe errors
            iframe.addEventListener('error', function() {
                container.innerHTML = '<div style="padding: 40px; text-align: center; color: #6b7280;"><p>Unable to load the staging platform.</p><p style="font-size: 14px; margin-top: 10px;">Please check that the API is running at: <?php echo esc_js($api_base); ?></p></div>';
            });
        })();
    </script>
    <?php
    return ob_get_clean();
}
add_shortcode('virtual_staging', 'vsp_shortcode');

// Add widget
class VSP_Widget extends WP_Widget {
    function __construct() {
        parent::__construct(
            'vsp_widget',
            'Virtual Staging Platform',
            array('description' => 'Embed the Virtual Staging Platform in your sidebar or widget area')
        );
    }
    
    function widget($args, $instance) {
        echo $args['before_widget'];
        if (!empty($instance['title'])) {
            echo $args['before_title'] . apply_filters('widget_title', $instance['title']) . $args['after_title'];
        }
        echo do_shortcode('[virtual_staging height="' . esc_attr($instance['height'] ?? '600') . 'px"]');
        echo $args['after_widget'];
    }
    
    function form($instance) {
        $title = !empty($instance['title']) ? $instance['title'] : 'Virtual Staging';
        $height = !empty($instance['height']) ? $instance['height'] : '600';
        ?>
        <p>
            <label for="<?php echo $this->get_field_id('title'); ?>">Title:</label>
            <input class="widefat" id="<?php echo $this->get_field_id('title'); ?>" 
                   name="<?php echo $this->get_field_name('title'); ?>" 
                   type="text" value="<?php echo esc_attr($title); ?>">
        </p>
        <p>
            <label for="<?php echo $this->get_field_id('height'); ?>">Height (px):</label>
            <input class="widefat" id="<?php echo $this->get_field_id('height'); ?>" 
                   name="<?php echo $this->get_field_name('height'); ?>" 
                   type="number" value="<?php echo esc_attr($height); ?>" min="400" max="2000">
        </p>
        <?php
    }
    
    function update($new_instance, $old_instance) {
        $instance = array();
        $instance['title'] = (!empty($new_instance['title'])) ? strip_tags($new_instance['title']) : '';
        $instance['height'] = (!empty($new_instance['height'])) ? intval($new_instance['height']) : 600;
        return $instance;
    }
}

function vsp_register_widget() {
    register_widget('VSP_Widget');
}
add_action('widgets_init', 'vsp_register_widget');

// Add custom page template
function vsp_add_page_template($templates) {
    $templates['page-staging.php'] = 'Virtual Staging Platform';
    return $templates;
}
add_filter('theme_page_templates', 'vsp_add_page_template');

function vsp_load_page_template($template) {
    global $post;
    
    if ($post && get_page_template_slug($post->ID) === 'page-staging.php') {
        $plugin_template = VSP_PLUGIN_DIR . 'templates/page-staging.php';
        if (file_exists($plugin_template)) {
            return $plugin_template;
        }
    }
    
    return $template;
}
add_filter('template_include', 'vsp_load_page_template');

// Create template file if it doesn't exist
function vsp_create_template_file() {
    $template_dir = VSP_PLUGIN_DIR . 'templates';
    if (!file_exists($template_dir)) {
        wp_mkdir_p($template_dir);
    }
    
    $template_file = $template_dir . '/page-staging.php';
    if (!file_exists($template_file)) {
        $template_content = '<?php
/**
 * Template Name: Virtual Staging Platform
 * 
 * This template displays the Virtual Staging Platform in full-page mode.
 */

get_header();
?>

<div id="staging-platform-container" style="width: 100%; min-height: calc(100vh - 200px);">
    <?php echo do_shortcode(\'[virtual_staging height="calc(100vh - 200px)"]\'); ?>
</div>

<?php
get_footer();
';
        file_put_contents($template_file, $template_content);
    }
}
add_action('admin_init', 'vsp_create_template_file');

// Add admin notice for first-time setup
function vsp_admin_notice() {
    if (get_option('vsp_api_base') === 'http://localhost:8001' && current_user_can('manage_options')) {
        ?>
        <div class="notice notice-info is-dismissible">
            <p><strong>Virtual Staging Platform:</strong> Please configure your API base URL in <a href="<?php echo admin_url('options-general.php?page=vsp-settings'); ?>">Settings → Staging Platform</a></p>
        </div>
        <?php
    }
}
add_action('admin_notices', 'vsp_admin_notice');




