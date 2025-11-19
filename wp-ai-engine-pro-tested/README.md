# WP AI Engine Pro

**Version:** 4.1.0  
**Developer:** Saeed M. Vardani  
**Company:** [SeaTechOne.com](https://seatechone.com)  
**License:** GPLv3 or later

Advanced AI Engine for WordPress with enhanced MCP support, realtime chatbots, and complete ChatGPT control. Production-ready with comprehensive security and testing.

---

## 🚀 Features

### Core Features
- ✅ **OpenAI Integration** - Full support for GPT-4o, GPT-4o Mini, GPT-4 Turbo
- ✅ **Chatbot Shortcode** - Easy-to-use `[wpai_chatbot]` shortcode
- ✅ **MCP Protocol** - Model Context Protocol for ChatGPT integration
- ✅ **OAuth 2.0 + PKCE** - Secure authentication for ChatGPT browser
- ✅ **REST API** - Complete REST API for external integrations
- ✅ **Admin Interface** - Beautiful, intuitive admin dashboard
- ✅ **Security Hardened** - Nonces, sanitization, capability checks
- ✅ **Error Handling** - Comprehensive error handling and logging
- ✅ **Responsive Design** - Works on all devices

### ChatGPT Integration
- 🤖 **Browser Dev Mode** - Connect ChatGPT browser to WordPress
- 🤖 **Desktop App** - stdio transport for ChatGPT Desktop
- 🤖 **WordPress Tools** - Get site info, list/create posts, get stats
- 🤖 **OAuth Discovery** - Automatic OAuth configuration discovery
- 🤖 **JSON-RPC 2.0** - Full MCP protocol compliance

### Chatbot Features
- 💬 **Customizable** - Title, theme, position, size
- 💬 **Light/Dark Theme** - Built-in theme support
- 💬 **Responsive** - Mobile-friendly design
- 💬 **Real-time** - Instant AI responses
- 💬 **Error Handling** - Graceful error messages

---

## 📋 Requirements

- **WordPress:** 6.0 or higher
- **PHP:** 8.1 or higher
- **cURL Extension:** Required
- **OpenAI API Key:** Required
- **HTTPS:** Recommended for production

---

## 📦 Installation

### Quick Install

1. Download `wp-ai-engine-pro-v4.1.0.zip`
2. Go to WordPress Admin → Plugins → Add New → Upload Plugin
3. Choose the ZIP file and click "Install Now"
4. Click "Activate Plugin"
5. Go to Settings → Permalinks → Save Changes (important!)

### Detailed Installation

See [INSTALLATION-GUIDE.md](INSTALLATION-GUIDE.md) for complete instructions.

---

## ⚙️ Configuration

### 1. Get OpenAI API Key

1. Visit https://platform.openai.com/api-keys
2. Create new secret key
3. Copy the key (starts with `sk-`)

### 2. Configure Plugin

1. Go to **AI Engine → Settings**
2. Paste your API key
3. Select your preferred model (GPT-4o recommended)
4. Adjust Max Tokens and Temperature if needed
5. Click **Save Changes**

### 3. Test Configuration

1. Go to **AI Engine → Test**
2. Click **Test API Connection**
3. Verify you see a success message

---

## 🎯 Usage

### Adding Chatbot to Pages

Basic usage:
```
[wpai_chatbot]
```

With customization:
```
[wpai_chatbot title="Support Bot" theme="dark" position="bottom-left"]
```

### Available Shortcode Attributes

| Attribute | Options | Default | Description |
|-----------|---------|---------|-------------|
| `title` | Any text | "AI Assistant" | Chatbot title |
| `theme` | light, dark | light | Color theme |
| `position` | bottom-right, bottom-left | bottom-right | Screen position |
| `width` | CSS value | 400px | Chatbot width |
| `height` | CSS value | 600px | Chatbot height |

### Examples

```
[wpai_chatbot title="Help Desk"]
[wpai_chatbot theme="dark"]
[wpai_chatbot position="bottom-left"]
[wpai_chatbot title="Customer Support" theme="dark" position="bottom-left"]
```

---

## 🔗 ChatGPT Integration

### For ChatGPT Browser (Recommended)

1. Go to **AI Engine → MCP Setup**
2. Copy your MCP Server URL
3. Open ChatGPT in browser
4. Enable Developer Mode
5. Add MCP server with your URL
6. Authorize when prompted
7. Ask ChatGPT about your WordPress site!

### Available WordPress Tools

When connected to ChatGPT, these tools are available:

- `wp_get_site_info` - Get site information
- `wp_list_posts` - List WordPress posts
- `wp_create_post` - Create new posts (as draft)
- `wp_get_stats` - Get site statistics

### Example ChatGPT Prompts

```
"What's my WordPress site information?"
"Show me my 5 most recent posts"
"Create a new blog post about AI in WordPress"
"What are my site statistics?"
```

---

## 🔌 REST API Endpoints

### Chat Endpoint

```
POST /wp-json/wpai/v1/chat
Headers:
  Content-Type: application/json
  X-WP-Nonce: [nonce]
Body:
  {
    "message": "Your message here",
    "model": "gpt-4o" (optional)
  }
```

### MCP Endpoint

```
POST /wp-json/wpai/v1/mcp
Headers:
  Content-Type: application/json
Body:
  {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list",
    "params": {}
  }
```

### OAuth Endpoints

```
GET /wp-json/wpai/v1/.well-known/oauth-authorization-server
GET /wp-json/wpai/v1/oauth/authorize
POST /wp-json/wpai/v1/oauth/token
```

---

## 🛡️ Security Features

- ✅ **Nonce Verification** - All forms and AJAX requests
- ✅ **Input Sanitization** - All user inputs sanitized
- ✅ **Output Escaping** - All outputs properly escaped
- ✅ **Capability Checks** - Admin-only access to settings
- ✅ **API Key Validation** - Format validation on save
- ✅ **OAuth Security** - PKCE support, one-time codes
- ✅ **Rate Limiting** - OpenAI API timeout protection
- ✅ **Error Logging** - Detailed error logs for debugging

---

## 📊 Performance

- ⚡ **Lightweight** - Minimal impact on site performance
- ⚡ **Async Loading** - Non-blocking API calls
- ⚡ **Asset Optimization** - Only loads where needed
- ⚡ **Caching Ready** - Compatible with caching plugins
- ⚡ **Database Optimized** - Efficient queries

---

## 🧪 Testing

Comprehensive testing guide available in [TESTING-GUIDE.md](TESTING-GUIDE.md).

### Quick Test Checklist

- [ ] Plugin activates without errors
- [ ] Admin menu appears
- [ ] Settings save correctly
- [ ] API test succeeds
- [ ] Chatbot displays on page
- [ ] Chatbot responds to messages
- [ ] OAuth discovery works
- [ ] MCP endpoint accessible
- [ ] ChatGPT can connect

---

## 🐛 Troubleshooting

### Common Issues

#### API Test Fails
- Verify API key is correct
- Check OpenAI account has credits
- Ensure cURL is installed
- Check firewall/network settings

#### OAuth Returns 404
- Go to Settings → Permalinks → Save Changes
- Check .htaccess file permissions
- Verify mod_rewrite is enabled

#### Chatbot Not Responding
- Check browser console for errors
- Verify API key is configured
- Test REST API directly
- Check for JavaScript conflicts

See [INSTALLATION-GUIDE.md](INSTALLATION-GUIDE.md) for detailed troubleshooting.

---

## 📚 Documentation

- **Installation Guide:** [INSTALLATION-GUIDE.md](INSTALLATION-GUIDE.md)
- **Testing Guide:** [TESTING-GUIDE.md](TESTING-GUIDE.md)
- **README:** This file

---

## 🔄 Changelog

### Version 4.1.0 (2025-01-01)

**New Features:**
- Complete security hardening with nonces, sanitization, validation
- Comprehensive error handling with try-catch blocks
- Enhanced OAuth 2.0 implementation with PKCE
- Improved admin interface with better UX
- Production-ready code with full testing

**Improvements:**
- Better API key validation
- Enhanced error messages
- Improved chatbot UI/UX
- Better mobile responsiveness
- Optimized performance

**Security:**
- Added nonce verification to all forms
- Implemented input sanitization
- Added capability checks
- Enhanced OAuth security
- Improved error logging

**Bug Fixes:**
- Fixed OAuth discovery endpoints
- Fixed permalink issues
- Fixed chatbot responsiveness
- Fixed API error handling

---

## 💰 Pricing

### Plugin
- **Free** - The plugin itself is completely free

### OpenAI API Costs
- **GPT-4o:** ~$2.50 per 1M input tokens, ~$10 per 1M output tokens
- **GPT-4o Mini:** ~$0.15 per 1M input tokens, ~$0.60 per 1M output tokens
- **Pay-as-you-go** - Only pay for what you use
- See https://openai.com/api/pricing/ for current rates

### Typical Usage Costs
- **Small site (100 chats/day):** ~$5-10/month
- **Medium site (500 chats/day):** ~$20-40/month
- **Large site (2000 chats/day):** ~$80-150/month

*Actual costs depend on conversation length and model used*

---

## 🤝 Support

### Get Help
- **Website:** https://seatechone.com
- **Developer:** Saeed M. Vardani
- **Email:** Contact via website

### Report Issues
- Check documentation first
- Review troubleshooting guide
- Contact via website for support

---

## 📄 License

This plugin is licensed under GPLv3 or later.

```
WP AI Engine Pro
Copyright (C) 2025 Saeed M. Vardani / SeaTechOne.com

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
```

---

## 🙏 Credits

- **Developer:** Saeed M. Vardani
- **Company:** SeaTechOne.com
- **OpenAI:** For providing the AI API
- **WordPress Community:** For the amazing platform

---

## 🚀 What's Next?

### Planned Features (Future Versions)

- [ ] Support for additional AI providers (Anthropic, Google, etc.)
- [ ] Advanced conversation history
- [ ] User authentication for chatbot
- [ ] Custom training on site content
- [ ] Analytics dashboard
- [ ] Multi-language support
- [ ] Voice input/output
- [ ] Image generation
- [ ] More MCP tools
- [ ] Webhook integrations

---

## 📞 Contact

**Saeed M. Vardani**  
**SeaTechOne.com**  
https://seatechone.com

---

**Made with ❤️ by Saeed M. Vardani**

---

## Quick Links

- [Installation Guide](INSTALLATION-GUIDE.md)
- [Testing Guide](TESTING-GUIDE.md)
- [OpenAI Platform](https://platform.openai.com/)
- [SeaTechOne.com](https://seatechone.com)

---

**Version:** 4.1.0  
**Last Updated:** 2025-01-01  
**Status:** ✅ Production Ready

