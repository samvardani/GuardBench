<?php
/**
 * Engine Interface
 * 
 * @package WPAIEnginePro
 */

declare(strict_types=1);

namespace WPAI\Engines;

if (!defined('ABSPATH')) {
    exit;
}

interface EngineInterface {
    public function chat(array $params): array;
    public function stream_chat(array $params, callable $callback): void;
    public function create_embedding(string $text, string $model): array;
}



