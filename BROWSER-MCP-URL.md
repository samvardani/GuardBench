# WP AI Engine Pro v4.0.4 - Browser MCP URL

## 🌐 For ChatGPT Browser Dev Mode

**Developer:** Saeed M. Vardani  
**Company:** SeaTechOne.com  
**Version:** 4.0.4 (HTTP/Browser Support)

## 📦 Download

**File:** `wp-ai-engine-pro-browser-v4.0.4.zip`  
**Location:** `/Users/samvardani/Projects/safety-eval-mini/wp-ai-engine-pro-browser-v4.0.4.zip`

## 🎯 YOUR MCP SERVER URL

After installing the plugin, your MCP server URL will be:

```
https://searei.com/wp-json/wpai/v1/mcp
```

**That's it! Just use this URL in your ChatGPT browser dev mode.**

## 🚀 Quick Setup

1. **Install the plugin** (`wp-ai-engine-pro-browser-v4.0.4.zip`)
2. **Activate it**
3. **Go to AI Engine > MCP Setup**
4. **Copy the MCP Server URL**
5. **Use it in ChatGPT browser dev mode**

## ✅ What's Included

- **HTTP endpoint** with CORS enabled
- **No OAuth** - direct access
- **JSON-RPC 2.0** protocol
- **4 WordPress tools** ready to use

## 🔧 Available Tools

1. **wp_get_site_info** - Get WordPress site information
2. **wp_list_posts** - List your posts
3. **wp_create_post** - Create new posts
4. **wp_get_stats** - Get site statistics

## 🧪 Test It

You can test if the endpoint is working by visiting it in your browser:
```
https://searei.com/wp-json/wpai/v1/mcp
```

You should see a JSON response with server info.

## 📝 Example Response

```json
{
  "name": "WP AI Engine Pro",
  "version": "4.0.2",
  "protocol": "mcp-http",
  "developer": "Saeed M. Vardani",
  "company": "SeaTechOne.com",
  "capabilities": {
    "tools": true,
    "resources": false,
    "prompts": false
  },
  "endpoint": "https://searei.com/wp-json/wpai/v1/mcp",
  "tools": [
    "wp_get_site_info",
    "wp_list_posts",
    "wp_create_post",
    "wp_get_stats"
  ]
}
```

## ✅ Success

- ✓ HTTP-based MCP server
- ✓ CORS enabled for browser access
- ✓ No OAuth required
- ✓ JSON-RPC 2.0 compliant
- ✓ Works with ChatGPT browser dev mode

**Built with ❤️ by Saeed M. Vardani at SeaTechOne.com**


