# WP AI Engine Pro v4.0.2 - Final Installation Guide

## 🎉 Plugin Ready!

**Developer:** Saeed M. Vardani  
**Company:** SeaTechOne.com  
**Website:** https://seatechone.com  
**Version:** 4.0.2  

## 📦 Installation Steps

### 1. Download
Download: `wp-ai-engine-pro-simple-v4.0.2-final.zip` (8.4 KB)

### 2. Install in WordPress
1. Go to **WordPress Admin > Plugins > Add New**
2. Click **Upload Plugin**
3. Choose the zip file
4. Click **Install Now**
5. Click **Activate Plugin**

### 3. Find the Menu
After activation, you should see **"AI Engine"** in your WordPress admin sidebar menu (left side).

### 4. Configure Settings
1. Go to **AI Engine > Settings**
2. Enter your **OpenAI API Key** (get from https://platform.openai.com/api-keys)
3. Select your preferred **Default Model**
4. Click **Save Changes**

### 5. Test the Plugin
1. Go to **AI Engine > Test**
2. Verify all settings show green checkmarks
3. Click **Test API Connection** (if API key is set)

### 6. Add Chatbot
Add this shortcode to any page or post:
```
[wpai_chatbot]
```

## 🎯 What You'll See

### Admin Menu Structure
```
AI Engine (main menu)
├── Dashboard - Overview and quick actions
├── Settings - Configure API key and models
├── MCP Setup - ChatGPT control setup
└── Test - Debug and test functionality
```

### Dashboard Features
- Plugin status and version info
- Quick action buttons
- Getting started guide
- Developer credits (Saeed M. Vardani / SeaTechOne.com)

## 🚀 Features Included

- ✅ **Simple Admin Menu** - Clean, reliable interface
- ✅ **OpenAI Integration** - GPT-5, GPT-4.5, GPT-4 models
- ✅ **Chatbot Shortcode** - `[wpai_chatbot]` with themes
- ✅ **MCP Setup** - Control WordPress from ChatGPT
- ✅ **Settings Page** - Proper WordPress standards
- ✅ **Test Page** - Debug and verify functionality
- ✅ **Developer Credits** - Saeed M. Vardani / SeaTechOne.com

## 🔧 Shortcode Options

```
[wpai_chatbot]                           # Basic chatbot
[wpai_chatbot title="My Assistant"]      # Custom title
[wpai_chatbot theme="dark"]              # Dark theme
[wpai_chatbot position="bottom-left"]    # Left position
```

## 🤖 ChatGPT Control (MCP)

1. Go to **AI Engine > MCP Setup**
2. Copy your MCP URL and API key
3. Edit ChatGPT config: `~/.config/OpenAI/ChatGPT/config.json`
4. Add the configuration shown in the admin
5. Restart ChatGPT Desktop
6. Test: "Show me my WordPress posts"

## 🐛 Troubleshooting

### Menu Not Appearing
- Check plugin is **Active** in Plugins page
- Clear WordPress cache
- Check user has **Administrator** role

### Settings Not Saving
- Check file permissions
- Clear browser cache
- Check PHP error logs

### API Errors
- Verify API key is correct
- Check OpenAI account has credits
- Ensure site URL is accessible

## 📞 Support

**Developer:** Saeed M. Vardani  
**Company:** SeaTechOne.com  
**Website:** https://seatechone.com  

For support and custom development, visit SeaTechOne.com

## ✅ Success Checklist

- [ ] Plugin installed and activated
- [ ] "AI Engine" menu appears in WordPress admin
- [ ] Settings page loads properly
- [ ] OpenAI API key entered and saved
- [ ] Test page shows green checkmarks
- [ ] Chatbot shortcode works on a page
- [ ] MCP setup completed (optional)

---

**Built with ❤️ by Saeed M. Vardani at SeaTechOne.com**

The plugin is now ready to use! The admin menu should appear immediately after activation.


