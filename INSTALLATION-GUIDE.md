# WP AI Engine Pro v4.0.1 - Installation Guide

## 📦 Installation Steps

### 1. Download
Download the `wp-ai-engine-pro-v4.0.1.zip` file

### 2. Install Plugin
1. Go to your WordPress Admin Dashboard
2. Navigate to **Plugins > Add New**
3. Click **Upload Plugin**
4. Choose the `wp-ai-engine-pro-v4.0.1.zip` file
5. Click **Install Now**
6. Click **Activate Plugin**

### 3. Configure Settings
1. Go to **AI Engine > Settings** in WordPress admin
2. Enter your **OpenAI API Key** (get from https://platform.openai.com/api-keys)
3. Configure other settings as needed
4. Click **Save Settings**

### 4. Test Installation
1. Go to **AI Engine > Test Settings**
2. Verify all settings are correct
3. Click **Test API Connection** to verify OpenAI integration

### 5. Add Chatbot
Add this shortcode to any page or post:
```
[wpai_chatbot]
```

## 🔧 Quick Setup Checklist

- [ ] Plugin installed and activated
- [ ] OpenAI API key entered
- [ ] Settings saved
- [ ] Test page shows green checkmarks
- [ ] API test successful
- [ ] Chatbot shortcode added to a page

## 🚀 Next Steps

### Enable ChatGPT Control (Optional)
1. Go to **AI Engine > MCP Setup**
2. Copy your MCP URL and API key
3. Edit ChatGPT config file
4. Restart ChatGPT Desktop
5. Test with: "Show me my WordPress posts"

### Customize Chatbot
- Use `[wpai_chatbot theme="dark"]` for dark theme
- Use `[wpai_chatbot position="bottom-left"]` for left position
- Use `[wpai_chatbot title="My Assistant"]` for custom title

## 🐛 Troubleshooting

### Settings Not Saving
- Check file permissions
- Clear WordPress cache
- Check PHP error logs

### API Errors
- Verify API key is correct
- Check OpenAI account has credits
- Ensure site URL is accessible

### Chatbot Not Showing
- Check JavaScript is enabled
- Verify shortcode syntax
- Check browser console for errors

## 📞 Support

If you encounter issues:
1. Check the **Test Settings** page
2. Review WordPress debug logs
3. Check browser console
4. Verify all requirements are met

## ✅ Requirements

- WordPress 6.0+
- PHP 8.1+
- OpenAI API Key
- HTTPS recommended for production

---

**Enjoy your AI-powered WordPress site! 🚀**


