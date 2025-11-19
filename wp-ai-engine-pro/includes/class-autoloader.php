<?php
/**
 * Autoloader
 * 
 * @package WPAIEnginePro
 */

declare(strict_types=1);

namespace WPAI;

if (!defined('ABSPATH')) {
    exit;
}

class Autoloader {
    private const NAMESPACE_PREFIX = 'WPAI\\';
    
    public static function register(): void {
        spl_autoload_register([__CLASS__, 'autoload']);
    }
    
    public static function autoload(string $class): void {
        if (strpos($class, self::NAMESPACE_PREFIX) !== 0) {
            return;
        }
        
        $relative_class = substr($class, strlen(self::NAMESPACE_PREFIX));
        $relative_class = str_replace('\\', '/', $relative_class);
        
        $file_name = self::convert_to_filename($relative_class);
        
        $base_dirs = [
            WPAI_PATH . '/includes/',
            WPAI_PATH . '/includes/admin/',
            WPAI_PATH . '/includes/api/',
            WPAI_PATH . '/includes/engines/',
            WPAI_PATH . '/includes/modules/',
            WPAI_PATH . '/includes/mcp/',
            WPAI_PATH . '/includes/query/',
            WPAI_PATH . '/includes/services/',
        ];
        
        foreach ($base_dirs as $base_dir) {
            $variations = [
                $base_dir . 'class-' . $file_name . '.php',
                $base_dir . $file_name . '.php',
            ];
            
            foreach ($variations as $file) {
                if (file_exists($file)) {
                    require_once $file;
                    return;
                }
            }
        }
    }
    
    private static function convert_to_filename(string $class_name): string {
        $parts = explode('/', $class_name);
        $class_name = end($parts);
        
        $filename = strtolower(preg_replace('/([a-z])([A-Z])/', '$1-$2', $class_name));
        return str_replace('_', '-', $filename);
    }
}



