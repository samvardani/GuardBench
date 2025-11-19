# WP AI Engine Pro

**Advanced AI Engine for WordPress with ChatGPT Control via MCP**

Version: 4.0.0  
Author: AI Development Team  
License: GPLv3 or later

## 🚀 Features

### Core Features
- **MCP Integration** - Control WordPress directly from ChatGPT Desktop
- **Advanced Chatbot** - Beautiful, customizable AI chatbot with realtime responses
- **Content Generation** - AI-powered content creation tools
- **Embeddings & Search** - Vector embeddings for semantic search
- **Multi-Model Support** - OpenAI, Anthropic, Google, and more
- **Usage Tracking** - Comprehensive analytics and cost tracking

### ChatGPT Control (MCP)
Control your entire WordPress site from ChatGPT:
- Create, read, update, and delete posts
- Manage media files
- View and manage users
- Check site statistics
- List plugins and themes
- And much more!

### Modern Architecture
- PHP 8.1+ with strict typing
- RESTful API with security
- Modern WordPress coding standards
- Extensible architecture
- Comprehensive error handling

## 📋 Requirements

- **WordPress:** 6.0 or higher
- **PHP:** 8.1 or higher
- **OpenAI API Key:** Required for AI features

## 🔧 Installation

1. **Download** the plugin
2. **Upload** to `/wp-content/plugins/wp-ai-engine-pro/`
3. **Activate** through the 'Plugins' menu in WordPress
4. **Configure** your API keys in Settings > AI Engine

## ⚙️ Configuration

### Basic Setup

1. Go to **Settings > AI Engine**
2. Enter your **OpenAI API Key** (get it from https://platform.openai.com/api-keys)
3. Select your preferred **Default Model**
4. Adjust **Max Tokens** and **Temperature** as needed
5. Enable desired **Modules**

### MCP Setup for ChatGPT Control

1. Go to **AI Engine > MCP Setup** in WordPress admin
2. Copy your **MCP API Key**
3. Edit your ChatGPT config file:
   - Mac/Linux: `~/.config/OpenAI/ChatGPT/config.json`
   - Windows: `%APPDATA%\OpenAI\ChatGPT\config.json`

4. Add this configuration:

```json
{
  "mcpServers": {
    "wordpress": {
      "url": "https://yoursite.com/wp-json/wpai/v1/mcp/sse",
      "headers": {
        "Authorization": "Bearer YOUR_API_KEY_HERE"
      }
    }
  }
}
```

5. **Restart ChatGPT Desktop**
6. Test by asking: "Show me my WordPress posts"

## 💬 Chatbot Usage

### Add Chatbot to Any Page

Use the shortcode:

```
[wpai_chatbot title="AI Assistant" theme="modern" position="bottom-right"]
```

### Shortcode Parameters

- `id` - Unique chatbot ID (default: "default")
- `title` - Chatbot title (default: "AI Assistant")
- `theme` - Visual theme: "modern", "dark" (default: "modern")
- `position` - Position: "bottom-right", "bottom-left" (default: "bottom-right")
- `model` - AI model to use (default: your settings)

### Global Chatbot

Enable "Show Chatbot Globally" in settings to display on all pages.

## 📝 Content Generation

### From Post Editor

1. Create or edit a post
2. Look for **AI Content Generator** meta box (sidebar)
3. Enter your prompt
4. Click **Generate Content**
5. Content will be inserted into the editor

### Via REST API

```javascript
fetch('/wp-json/wpai/v1/generate', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-WP-Nonce': wpNonce
  },
  body: JSON.stringify({
    prompt: 'Write a blog post about AI in healthcare',
    type: 'post'
  })
});
```

## 🔍 Embeddings

### Auto-Generate Embeddings

Embeddings are automatically generated when you publish or update posts.

### Manual Generation

```php
$embeddings = new \WPAI\Modules\Embeddings(wpai());
$embeddings->generate_embedding($post_id);
```

## 🛡️ Security

- API key encryption
- Rate limiting
- Nonce verification
- Input sanitization
- Permission checks
- Secure file handling

## 📊 Usage Tracking

View detailed usage statistics:
- Go to **AI Engine > Usage Stats**
- See requests by model
- Track token usage
- Monitor costs

## 🔌 REST API Endpoints

### Chat
```
POST /wp-json/wpai/v1/chat
```

Parameters:
- `message` - User message (required)
- `model` - AI model (optional)
- `max_tokens` - Max response tokens (optional)
- `temperature` - Creativity level 0-2 (optional)

### Content Generation
```
POST /wp-json/wpai/v1/generate
```

Parameters:
- `prompt` - Generation prompt (required)
- `type` - Content type: "post", "product", "email" (optional)

### Embeddings
```
POST /wp-json/wpai/v1/embeddings
```

Parameters:
- `text` - Text to embed (required)
- `model` - Embedding model (optional)

### Settings
```
GET  /wp-json/wpai/v1/settings
POST /wp-json/wpai/v1/settings
```

## 📚 Developer Documentation

### Filters

```php
// Modify AI response
add_filter('wpai_ai_response', function($response, $context) {
    // Modify response
    return $response;
}, 10, 2);

// Modify exception messages
add_filter('wpai_ai_exception', function($exception) {
    // Handle exception
    return $exception;
}, 10, 1);

// Access control
add_filter('wpai_can_access_settings', function($can_access) {
    return current_user_can('my_custom_capability');
});
```

### Actions

```php
// After core initialization
add_action('wpai_core_init', function($core) {
    // Your code here
});

// Log events
add_action('wpai_log', function($type, $message, $context) {
    // Custom logging
}, 10, 3);
```

### Custom AI Engine

```php
use WPAI\Engines\EngineInterface;

class MyCustomEngine implements EngineInterface {
    public function chat(array $params): array {
        // Implement chat
    }
    
    public function stream_chat(array $params, callable $callback): void {
        // Implement streaming
    }
    
    public function create_embedding(string $text, string $model): array {
        // Implement embeddings
    }
}
```

## 🎯 MCP Commands

Once MCP is configured, you can use these commands in ChatGPT:

### Posts
- "Show me my recent posts"
- "Create a new blog post about [topic]"
- "Update post 123 with new content"
- "Get details of post 456"
- "Delete post 789"

### Site Management
- "What's my WordPress site information?"
- "Show me site statistics"
- "What plugins are installed?"
- "What themes are available?"

### Users
- "List all users"
- "Show me administrator users"

### Media
- "List recent media files"

## 🐛 Troubleshooting

### Chatbot Not Appearing
1. Check if JavaScript is enabled
2. Verify shortcode is correct
3. Check browser console for errors
4. Ensure REST API is accessible

### API Errors
1. Verify API key is correct
2. Check API key has sufficient credits
3. Ensure your WordPress site URL is correct
4. Check firewall/security plugin settings

### MCP Not Connecting
1. Verify config.json syntax is correct
2. Check API key matches
3. Ensure REST API endpoint is accessible
4. Restart ChatGPT Desktop
5. Check WordPress permalinks are enabled

## 🔄 Updates

The plugin checks for updates automatically. You can manually check:
1. Go to **Dashboard > Updates**
2. Check for plugin updates

## 📄 License

This plugin is licensed under GPLv3 or later.

## 🤝 Support

For support and documentation:
- Visit our [GitHub repository](https://github.com/yourusername/wp-ai-engine-pro)
- Report issues on [GitHub Issues](https://github.com/yourusername/wp-ai-engine-pro/issues)

## 🎉 Credits

Improved version of AI Engine with modern architecture and enhanced MCP support.

---

Made with ❤️ for the WordPress community



