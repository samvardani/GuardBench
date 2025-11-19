# WP AI Engine Pro - Quick Start Guide

**Version:** 4.1.4  
**Developer:** Saeed M. Vardani  
**Company:** SeaTechOne.com

---

## 🚀 3-Minute Setup

### 1. Install Plugin (2 minutes)

```bash
1. Upload wp-ai-engine-pro-v4.1.4-oauth-working.zip
2. Activate plugin
3. Settings → Permalinks → Save Changes (CRITICAL!)
```

### 2. Configure API Key (1 minute)

```bash
1. AI Engine → Settings
2. Enter OpenAI API Key
3. Click "Test API Connection"
```

### 3. Connect ChatGPT (30 seconds)

```bash
1. ChatGPT → Settings → Integrations
2. Add MCP Server: https://searei.com/wp-json/wpai/v1/mcp
3. Authorize when prompted
```

**Done! ✅**

---

## 🔗 Essential URLs

Replace `searei.com` with your domain:

```
MCP Server:
https://searei.com/wp-json/wpai/v1/mcp

OAuth Discovery:
https://searei.com/wp-json/wpai/v1/.well-known/oauth-authorization-server

Test These URLs:
https://searei.com/wp-json/wpai/v1/mcp (should return JSON)
https://searei.com/wp-json/wpai/v1/.well-known/oauth-authorization-server (should return OAuth config)
```

---

## 🤖 ChatGPT Commands

Try these in ChatGPT after connecting:

```
"What's my WordPress site information?"
"Show me my latest 5 blog posts"
"Create a draft post about AI in WordPress"
"What are my site statistics?"
"List all my published pages"
```

---

## 🛠️ MCP Tools Available

1. **wp_get_site_info** - Get site details
2. **wp_list_posts** - List posts/pages (with filters)
3. **wp_create_post** - Create new content
4. **wp_get_stats** - Get detailed statistics

---

## ⚡ Quick Tests

### Test 1: OAuth Discovery
```bash
curl https://searei.com/wp-json/wpai/v1/.well-known/oauth-authorization-server
```
**Expected:** JSON with authorization_endpoint

### Test 2: MCP Server
```bash
curl https://searei.com/wp-json/wpai/v1/mcp
```
**Expected:** JSON with tools list

### Test 3: API Connection
Go to: **AI Engine → Test** → Click "Test API Connection"  
**Expected:** Success message with GPT response

---

## 🔧 Admin Pages

```
Settings:      /wp-admin/admin.php?page=wpai-settings
MCP Server:    /wp-admin/admin.php?page=wpai-mcp
Test:          /wp-admin/admin.php?page=wpai-test
Documentation: /wp-admin/admin.php?page=wpai-docs
```

---

## 🎯 Chatbot Widget

Add AI chatbot to any page:

```
[wpai_chatbot]
```

---

## 🐛 Troubleshooting

### "Does Not Implement OAuth"
1. Flush permalinks: Settings → Permalinks → Save
2. Test OAuth URL: `https://searei.com/wp-json/wpai/v1/.well-known/oauth-authorization-server`
3. Should return JSON (not 404)

### "No Route Was Found"
1. Flush permalinks again
2. Check permalink structure (must be "Post name")
3. Verify plugin is activated

### API Test Fails
1. Check API key is correct
2. Verify cURL is enabled
3. Check error message in Test page

---

## 📚 Full Documentation

- **CAPABILITIES.md** - Complete feature list (NEW!)
- **INSTALLATION-GUIDE.md** - Detailed setup
- **TESTING-GUIDE.md** - Test cases
- **OAUTH-FIXED-v4.1.4.md** - OAuth setup
- **README.md** - Overview

---

## 📊 What You Get

✅ Control WordPress from ChatGPT  
✅ OAuth 2.0 + PKCE security  
✅ 4 powerful MCP tools  
✅ OpenAI API integration  
✅ AI chatbot widget  
✅ Content generation  
✅ REST API endpoints  
✅ Admin interface  
✅ Production-ready  

---

## 💡 Example Workflow

**Scenario:** Create a blog post from ChatGPT

```
You: "Create a blog post about '10 WordPress Security Tips' 
      with an introduction, 10 numbered tips, and a conclusion. 
      Make it SEO-friendly and publish it."

ChatGPT: [Uses wp_create_post tool]
         "I've created and published your blog post! 
          You can view it at: https://searei.com/10-wordpress-security-tips"
```

**That's it!** 🎉

---

## 🔐 Security Features

- ✅ OAuth 2.0 Authorization
- ✅ PKCE (S256)
- ✅ Token expiration
- ✅ API key encryption
- ✅ Input sanitization
- ✅ CSRF protection
- ✅ Capability checks

---

## 🌟 Key Features

### For Users
- Natural language WordPress control
- AI-powered chatbot
- Automated content creation
- Real-time site information

### For Developers
- Clean, modular code
- Action/filter hooks
- REST API
- Error logging
- Extensible architecture

---

## 📞 Support

**Website:** https://seatechone.com  
**Developer:** Saeed M. Vardani  
**Email:** support@seatechone.com

---

## 🎯 Next Steps

After setup:

1. ✅ Test all 4 MCP tools in ChatGPT
2. ✅ Try creating a blog post
3. ✅ Add chatbot widget to a page
4. ✅ Explore admin interface
5. ✅ Read CAPABILITIES.md for advanced features

---

**Version:** 4.1.4  
**Status:** Production Ready ✅  
**Last Updated:** November 2, 2024

---

**Enjoy your AI-powered WordPress site!** 🚀

