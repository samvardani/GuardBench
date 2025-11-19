# WP AI Engine Pro - Installation Guide

**Version:** 4.1.0  
**Developer:** Saeed M. Vardani  
**Company:** SeaTechOne.com

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Installation Methods](#installation-methods)
3. [Initial Configuration](#initial-configuration)
4. [ChatGPT Integration Setup](#chatgpt-integration-setup)
5. [Using the Chatbot](#using-the-chatbot)
6. [Troubleshooting](#troubleshooting)
7. [FAQ](#faq)

---

## System Requirements

### Minimum Requirements

- **WordPress:** 6.0 or higher
- **PHP:** 8.1 or higher
- **MySQL:** 5.7 or higher (or MariaDB 10.2+)
- **PHP Extensions:**
  - cURL (required for OpenAI API)
  - JSON (usually enabled by default)
  - OpenSSL (for secure connections)

### Recommended Requirements

- **WordPress:** 6.5 or higher
- **PHP:** 8.2 or higher
- **Memory Limit:** 256MB or higher
- **Max Execution Time:** 120 seconds or higher
- **HTTPS:** SSL certificate installed

### Server Compatibility

- ✅ Apache 2.4+
- ✅ Nginx 1.18+
- ✅ LiteSpeed 5.4+
- ✅ Shared hosting (if requirements met)
- ✅ VPS/Dedicated servers
- ✅ WordPress.com Business plan or higher

---

## Installation Methods

### Method 1: WordPress Admin Upload (Recommended)

1. **Download the Plugin**
   - Download `wp-ai-engine-pro-v4.1.0.zip`
   - Do NOT unzip the file

2. **Upload to WordPress**
   - Log in to your WordPress admin panel
   - Navigate to **Plugins → Add New**
   - Click **Upload Plugin** button at the top
   - Click **Choose File** and select the ZIP file
   - Click **Install Now**

3. **Activate the Plugin**
   - Wait for installation to complete
   - Click **Activate Plugin**
   - You should see "AI Engine" in the admin sidebar

4. **Flush Permalinks (Important!)**
   - Go to **Settings → Permalinks**
   - Click **Save Changes** (don't change anything)
   - This ensures OAuth endpoints work correctly

### Method 2: FTP Upload

1. **Extract the ZIP File**
   - Unzip `wp-ai-engine-pro-v4.1.0.zip` on your computer
   - You should see a folder named `wp-ai-engine-pro-tested`

2. **Upload via FTP**
   - Connect to your server via FTP client
   - Navigate to `/wp-content/plugins/`
   - Upload the entire `wp-ai-engine-pro-tested` folder

3. **Activate via WordPress**
   - Log in to WordPress admin
   - Go to **Plugins**
   - Find "WP AI Engine Pro"
   - Click **Activate**

4. **Flush Permalinks**
   - Go to **Settings → Permalinks**
   - Click **Save Changes**

### Method 3: WP-CLI

```bash
# Upload the ZIP file to your server first, then:
wp plugin install /path/to/wp-ai-engine-pro-v4.1.0.zip --activate

# Flush rewrite rules
wp rewrite flush
```

---

## Initial Configuration

### Step 1: Get OpenAI API Key

1. **Create OpenAI Account**
   - Visit https://platform.openai.com/
   - Sign up or log in

2. **Generate API Key**
   - Go to https://platform.openai.com/api-keys
   - Click **Create new secret key**
   - Give it a name (e.g., "WordPress Plugin")
   - Copy the key (starts with `sk-`)
   - **Important:** Save it securely, you won't see it again!

3. **Add Billing Information**
   - Go to https://platform.openai.com/account/billing
   - Add payment method
   - Set usage limits if desired

### Step 2: Configure Plugin Settings

1. **Access Settings**
   - In WordPress admin, go to **AI Engine → Settings**

2. **Enter API Key**
   - Paste your OpenAI API key in the "OpenAI API Key" field
   - Use the "Show/Hide" button to verify it's correct
   - The key will be masked as `sk-...XXXX` after saving

3. **Select Model**
   - Choose your preferred AI model:
     - **GPT-4o** (Recommended) - Best quality, balanced cost
     - **GPT-4o Mini** - Faster and cheaper
     - **GPT-4 Turbo** - Previous generation
     - **GPT-4** - Original GPT-4
     - **GPT-3.5 Turbo** - Legacy, cheapest

4. **Configure Advanced Settings**
   - **Max Tokens:** 4096 (default) - Maximum response length
   - **Temperature:** 0.7 (default) - Creativity level (0-2)
     - Lower = more focused and deterministic
     - Higher = more creative and random

5. **Save Settings**
   - Click **Save Changes**
   - Verify success message appears

### Step 3: Test the Configuration

1. **Go to Test Page**
   - Navigate to **AI Engine → Test**

2. **Review System Status**
   - Check that all status indicators are green
   - Verify API key shows as "Ready"

3. **Run API Test**
   - Click **Test API Connection** button
   - Wait for response (5-10 seconds)
   - Verify you see a success message with AI response

4. **Troubleshoot if Needed**
   - If test fails, check error message
   - Verify API key is correct
   - Check OpenAI account has credits
   - See [Troubleshooting](#troubleshooting) section

---

## ChatGPT Integration Setup

### For ChatGPT Browser (Dev Mode)

1. **Get Your MCP URL**
   - Go to **AI Engine → MCP Setup**
   - Copy the MCP Server URL shown (should be like `https://yoursite.com/wp-json/wpai/v1/mcp`)

2. **Open ChatGPT in Browser**
   - Visit https://chat.openai.com/
   - Log in to your account

3. **Enable Developer Mode**
   - Click on your profile icon
   - Go to Settings
   - Find "Developer Mode" or "Beta Features"
   - Enable MCP support

4. **Add MCP Server**
   - In ChatGPT settings, find "MCP Servers"
   - Click "Add Server"
   - Enter your MCP URL
   - ChatGPT will automatically discover OAuth configuration

5. **Authorize Connection**
   - ChatGPT will redirect you to your WordPress site
   - You'll see an authorization page
   - Click "Authorize" or you'll be automatically redirected
   - You'll be redirected back to ChatGPT

6. **Test the Connection**
   - Ask ChatGPT: "What's my WordPress site information?"
   - ChatGPT should use the `wp_get_site_info` tool
   - You should see your site details in the response

### For ChatGPT Desktop (Alternative)

1. **Locate Config File**
   - **Mac/Linux:** `~/.config/OpenAI/ChatGPT/config.json`
   - **Windows:** `%APPDATA%\OpenAI\ChatGPT\config.json`

2. **Get MCP Server Path**
   - Go to **AI Engine → MCP Setup** in WordPress
   - Copy the "MCP Server Path" shown

3. **Edit Config File**
   - Open the config file in a text editor
   - Add this configuration:
   ```json
   {
     "mcpServers": {
       "wordpress": {
         "command": "php",
         "args": ["/full/path/to/your/wp-content/plugins/wp-ai-engine-pro-tested/mcp-server.php"]
       }
     }
   }
   ```

4. **Restart ChatGPT**
   - Completely quit ChatGPT Desktop
   - Start it again
   - The WordPress server should now be available

---

## Using the Chatbot

### Adding Chatbot to Pages

1. **Basic Usage**
   - Edit any page or post
   - Add this shortcode:
   ```
   [wpai_chatbot]
   ```
   - Publish/Update the page
   - View the page to see the chatbot

2. **Customization Options**
   ```
   [wpai_chatbot title="My Assistant" theme="dark" position="bottom-left"]
   ```
   
   Available attributes:
   - `title` - Custom chatbot title (default: "AI Assistant")
   - `theme` - "light" or "dark" (default: "light")
   - `position` - "bottom-right" or "bottom-left" (default: "bottom-right")
   - `width` - Custom width (default: "400px")
   - `height` - Custom height (default: "600px")

3. **Examples**
   ```
   [wpai_chatbot title="Support Bot"]
   [wpai_chatbot theme="dark"]
   [wpai_chatbot position="bottom-left"]
   [wpai_chatbot title="Help Desk" theme="dark" position="bottom-left"]
   ```

### Testing the Chatbot

1. **Open a Page with Chatbot**
   - Navigate to a page where you added the shortcode

2. **Interact with Chatbot**
   - Type a message in the input field
   - Click the send button or press Enter
   - Wait for AI response

3. **Verify Functionality**
   - Messages should appear in chat
   - AI should respond within 5-10 seconds
   - Chat should scroll automatically
   - Input should clear after sending

---

## Troubleshooting

### Plugin Won't Activate

**Problem:** Error message during activation

**Solutions:**
1. Check PHP version: `php -v` (must be 8.1+)
2. Check WordPress version (must be 6.0+)
3. Check PHP error logs
4. Increase PHP memory limit in wp-config.php:
   ```php
   define('WP_MEMORY_LIMIT', '256M');
   ```

### "AI Engine" Menu Not Appearing

**Problem:** Can't see plugin menu in admin

**Solutions:**
1. Verify you're logged in as Administrator
2. Check if plugin is activated
3. Try deactivating and reactivating
4. Check for PHP errors in debug.log

### API Test Fails

**Problem:** "Test API Connection" returns error

**Solutions:**

1. **Invalid API Key**
   - Verify key starts with `sk-`
   - Check for extra spaces
   - Generate new key if needed

2. **No Credits**
   - Visit https://platform.openai.com/account/billing
   - Add payment method
   - Add credits

3. **Network Issues**
   - Check if server can reach api.openai.com
   - Test with: `curl https://api.openai.com/v1/models`
   - Check firewall rules

4. **cURL Not Installed**
   - Install cURL: `apt-get install php-curl` (Ubuntu/Debian)
   - Restart web server

### OAuth Discovery Returns 404

**Problem:** OAuth URL returns "Not Found"

**Solutions:**
1. **Flush Permalinks**
   - Go to Settings → Permalinks
   - Click "Save Changes"
   - Test URL again

2. **Check Permalink Structure**
   - Try changing to "Post name"
   - Save changes
   - Test again

3. **Check .htaccess**
   - Verify file exists and is writable
   - Check for mod_rewrite enabled

4. **Server Configuration**
   - For Nginx, add rewrite rules
   - For LiteSpeed, check .htaccess

### Chatbot Not Responding

**Problem:** Chatbot shows but doesn't respond

**Solutions:**
1. **Check Browser Console**
   - Open DevTools (F12)
   - Look for JavaScript errors
   - Check Network tab for failed requests

2. **Verify REST API**
   - Test directly: `https://yoursite.com/wp-json/wpai/v1/chat`
   - Should return authentication error (expected)

3. **Check API Key**
   - Go to Settings
   - Verify API key is set
   - Test API connection

4. **CORS Issues**
   - Check server CORS configuration
   - Add CORS headers if needed

### ChatGPT Can't Connect to MCP

**Problem:** ChatGPT shows "Connection failed"

**Solutions:**
1. **Verify MCP URL**
   - Test in browser
   - Should return JSON with server info

2. **Check OAuth**
   - Test OAuth discovery URL
   - Should return OAuth configuration

3. **Firewall/Security**
   - Ensure ChatGPT can reach your site
   - Check if site is publicly accessible
   - Verify no IP blocking

4. **SSL Certificate**
   - Ensure valid SSL certificate
   - Test with: https://www.ssllabs.com/ssltest/

---

## FAQ

### Q: Is this plugin free?

A: The plugin itself is free, but you need an OpenAI API account with credits. OpenAI charges based on usage (pay-as-you-go).

### Q: How much does OpenAI API cost?

A: Pricing varies by model:
- GPT-4o: ~$2.50 per 1M input tokens, ~$10 per 1M output tokens
- GPT-4o Mini: ~$0.15 per 1M input tokens, ~$0.60 per 1M output tokens
- See https://openai.com/api/pricing/ for current rates

### Q: Can I use this with other AI providers?

A: Currently, the plugin only supports OpenAI. Future versions may add support for other providers.

### Q: Is my API key secure?

A: Yes, the API key is stored securely in WordPress database and never exposed to frontend. All API calls are made server-side.

### Q: Can I customize the chatbot appearance?

A: Yes, you can use the `theme` attribute and add custom CSS to further customize the appearance.

### Q: Does this work with page builders?

A: Yes, the shortcode works with all major page builders (Elementor, Divi, Beaver Builder, etc.).

### Q: Can I limit chatbot access to logged-in users?

A: Currently, the chatbot is available to all visitors. You can add custom code to restrict access if needed.

### Q: How many chatbots can I add?

A: You can add unlimited chatbots to different pages using the shortcode.

### Q: Does this affect my site performance?

A: The plugin is lightweight and only loads assets on pages where the chatbot is used. API calls are asynchronous and don't block page loading.

### Q: Can ChatGPT create/edit posts on my site?

A: Yes, when connected via MCP, ChatGPT can use tools like `wp_create_post`, `wp_list_posts`, etc. Posts are created as drafts by default for safety.

### Q: Is this compatible with multisite?

A: The plugin can be installed on multisite, but each site needs its own configuration. Network activation is not currently supported.

### Q: Can I translate the plugin?

A: Yes, the plugin is translation-ready. You can use tools like Loco Translate or WPML.

### Q: Where can I get support?

A: Visit https://seatechone.com for support and documentation.

---

## Next Steps

After successful installation:

1. ✅ Configure your OpenAI API key
2. ✅ Test the API connection
3. ✅ Add chatbot to a page
4. ✅ Set up ChatGPT integration (optional)
5. ✅ Customize chatbot appearance
6. ✅ Monitor usage and costs

---

## Support & Resources

- **Developer:** Saeed M. Vardani
- **Company:** SeaTechOne.com
- **Website:** https://seatechone.com
- **Documentation:** See TESTING-GUIDE.md and README.md
- **OpenAI Documentation:** https://platform.openai.com/docs

---

**Document Version:** 1.0  
**Last Updated:** 2025-01-01  
**Plugin Version:** 4.1.0

---

## Quick Start Checklist

- [ ] Plugin installed and activated
- [ ] Permalinks flushed (Settings → Permalinks → Save)
- [ ] OpenAI API key obtained
- [ ] API key configured in plugin settings
- [ ] API connection tested successfully
- [ ] Chatbot shortcode added to a page
- [ ] Chatbot tested and working
- [ ] ChatGPT MCP integration set up (optional)
- [ ] OAuth endpoints tested (optional)

**Congratulations! Your WP AI Engine Pro is ready to use! 🎉**

