# WP AI Engine Pro - Quick Setup Guide

## 🚀 Quick Start (5 Minutes)

### Step 1: Install Plugin
1. Copy the `wp-ai-engine-pro` folder to your WordPress `/wp-content/plugins/` directory
2. Go to WordPress Admin > Plugins
3. Find "WP AI Engine Pro" and click **Activate**

### Step 2: Configure API Key
1. Get your OpenAI API key from: https://platform.openai.com/api-keys
2. Go to **Settings > AI Engine**
3. Paste your API key in the "OpenAI API Key" field
4. Click **Save Settings**

### Step 3: Test the Chatbot
1. Add this shortcode to any page or post:
   ```
   [wpai_chatbot]
   ```
2. View the page
3. Click the chatbot button (bottom-right)
4. Ask a question!

## 🤖 Enable ChatGPT Control

### For ChatGPT Desktop (Recommended)

1. **Get Your MCP Credentials**
   - Go to **AI Engine > MCP Setup** in WordPress admin
   - Copy your MCP URL and API Key

2. **Edit ChatGPT Config**
   - Mac/Linux: `~/.config/OpenAI/ChatGPT/config.json`
   - Windows: `%APPDATA%\OpenAI\ChatGPT\config.json`
   
3. **Add Configuration**
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

4. **Restart ChatGPT Desktop**

5. **Test Commands**
   Try these in ChatGPT:
   - "Show me my WordPress posts"
   - "Create a new blog post about AI"
   - "What plugins are installed on my site?"
   - "Show me site statistics"

## 💡 Features Overview

### Chatbot
- Beautiful, customizable UI
- Realtime responses
- Markdown support
- Conversation history

### Content Generation
- AI-powered post creation
- Gutenberg integration
- Classic editor support
- Multiple content types

### MCP Control
- Full WordPress control from ChatGPT
- Manage posts, pages, media
- Check site stats
- View plugins and themes
- User management

### Embeddings
- Automatic vector generation
- Semantic search (coming soon)
- Content recommendations

## 📊 Usage Tracking

View your AI usage:
1. Go to **AI Engine > Usage Stats**
2. See requests, tokens, and costs by model

## 🎨 Customization

### Chatbot Themes
Use the `theme` parameter:
```
[wpai_chatbot theme="dark"]
```

Available themes: `modern`, `dark`

### Position
```
[wpai_chatbot position="bottom-left"]
```

Available positions: `bottom-right`, `bottom-left`

### Custom Title
```
[wpai_chatbot title="My AI Helper"]
```

## 🔧 Advanced Configuration

### Rate Limiting
Edit in code:
```php
define('WPAI_RATE_LIMIT', 100); // requests per hour
```

### Timeout
```php
define('WPAI_TIMEOUT', 120); // seconds
```

### Models
Change default model in Settings or per-request:
```javascript
fetch('/wp-json/wpai/v1/chat', {
  body: JSON.stringify({
    message: 'Hello',
    model: 'gpt-5-mini'  // Use different model
  })
});
```

## 🐛 Common Issues

### "API key not configured"
- Verify you entered the API key in Settings
- Check for extra spaces
- Ensure the key starts with `sk-`

### Chatbot not showing
- Check if JavaScript is enabled
- Verify shortcode syntax
- Clear WordPress cache
- Check browser console for errors

### MCP not connecting
- Verify config.json syntax (use JSON validator)
- Check URL is correct (with https://)
- Ensure API key matches exactly
- Restart ChatGPT Desktop completely
- Check WordPress permalinks are enabled

### Rate limit errors
- Check your OpenAI account has credits
- Visit https://platform.openai.com/account/billing
- Add payment method if needed

## 📱 Support

Need help?
- Check the main README.md file
- Visit the WordPress admin dashboard
- Check PHP error logs: `/wp-content/debug.log`
- Browser console for JavaScript errors

## 🎯 Next Steps

1. ✅ Test the chatbot on your site
2. ✅ Enable MCP for ChatGPT control
3. ✅ Generate your first AI content
4. ✅ Customize the appearance
5. ✅ Monitor your usage stats

Enjoy your AI-powered WordPress site! 🚀



