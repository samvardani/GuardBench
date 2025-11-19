<?php
/**
 * OpenAI Engine
 * 
 * @package WPAIEnginePro
 */

declare(strict_types=1);

namespace WPAI\Engines;

if (!defined('ABSPATH')) {
    exit;
}

class OpenAI implements EngineInterface {
    private string $api_key;
    private string $api_url = 'https://api.openai.com/v1';
    
    public function __construct() {
        $this->api_key = wpai()->get_option('openai_api_key', '');
        
        if (empty($this->api_key)) {
            throw new \Exception('OpenAI API key not configured');
        }
    }
    
    public function chat(array $params): array {
        $defaults = [
            'model' => WPAI_FALLBACK_MODEL,
            'messages' => [],
            'max_tokens' => 4096,
            'temperature' => 0.7,
            'stream' => false,
        ];
        
        $params = array_merge($defaults, $params);
        
        $response = $this->request('/chat/completions', $params);
        
        if (isset($response['error'])) {
            throw new \Exception($response['error']['message']);
        }
        
        $content = $response['choices'][0]['message']['content'] ?? '';
        $usage = $response['usage'] ?? [];
        
        return [
            'content' => $content,
            'tokens' => $usage['total_tokens'] ?? 0,
            'tokens_input' => $usage['prompt_tokens'] ?? 0,
            'tokens_output' => $usage['completion_tokens'] ?? 0,
            'cost' => $this->calculate_cost($params['model'], $usage),
            'model' => $params['model'],
        ];
    }
    
    public function stream_chat(array $params, callable $callback): void {
        $params['stream'] = true;
        
        $ch = curl_init($this->api_url . '/chat/completions');
        
        curl_setopt_array($ch, [
            CURLOPT_POST => true,
            CURLOPT_POSTFIELDS => json_encode($params),
            CURLOPT_HTTPHEADER => [
                'Content-Type: application/json',
                'Authorization: Bearer ' . $this->api_key,
            ],
            CURLOPT_WRITEFUNCTION => function($curl, $data) use ($callback) {
                if (strpos($data, 'data: ') === 0) {
                    $json = trim(substr($data, 6));
                    
                    if ($json === '[DONE]') {
                        return strlen($data);
                    }
                    
                    $decoded = json_decode($json, true);
                    if ($decoded && isset($decoded['choices'][0]['delta']['content'])) {
                        $callback($decoded['choices'][0]['delta']['content']);
                    }
                }
                return strlen($data);
            },
        ]);
        
        curl_exec($ch);
        curl_close($ch);
    }
    
    public function create_embedding(string $text, string $model): array {
        $response = $this->request('/embeddings', [
            'model' => $model,
            'input' => $text,
        ]);
        
        if (isset($response['error'])) {
            throw new \Exception($response['error']['message']);
        }
        
        return $response['data'][0]['embedding'] ?? [];
    }
    
    private function request(string $endpoint, array $data): array {
        $ch = curl_init($this->api_url . $endpoint);
        
        curl_setopt_array($ch, [
            CURLOPT_POST => true,
            CURLOPT_POSTFIELDS => json_encode($data),
            CURLOPT_HTTPHEADER => [
                'Content-Type: application/json',
                'Authorization: Bearer ' . $this->api_key,
            ],
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_TIMEOUT => WPAI_TIMEOUT,
        ]);
        
        $response = curl_exec($ch);
        $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        $error = curl_error($ch);
        
        curl_close($ch);
        
        if ($error) {
            throw new \Exception('cURL error: ' . $error);
        }
        
        $decoded = json_decode($response, true);
        
        if ($http_code !== 200) {
            $message = $decoded['error']['message'] ?? 'Unknown error';
            throw new \Exception('OpenAI API error: ' . $message);
        }
        
        return $decoded;
    }
    
    private function calculate_cost(string $model, array $usage): float {
        // Pricing per 1M tokens (2025 estimates)
        $pricing = [
            'gpt-5-chat-latest' => ['input' => 2.50, 'output' => 10.00],
            'gpt-5-mini' => ['input' => 0.10, 'output' => 0.40],
            'gpt-4.5-turbo' => ['input' => 5.00, 'output' => 15.00],
            'gpt-4-turbo' => ['input' => 10.00, 'output' => 30.00],
        ];
        
        $price = $pricing[$model] ?? ['input' => 2.50, 'output' => 10.00];
        
        $input_cost = ($usage['prompt_tokens'] ?? 0) / 1000000 * $price['input'];
        $output_cost = ($usage['completion_tokens'] ?? 0) / 1000000 * $price['output'];
        
        return $input_cost + $output_cost;
    }
}



