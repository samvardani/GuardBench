# WP AI Engine Pro v4.0.3 - CORRECT MCP Implementation!

## ✅ OAuth Error COMPLETELY FIXED!

**Developer:** Saeed M. Vardani  
**Company:** SeaTechOne.com  
**Version:** 4.0.3 (Stdio Transport - Correct Implementation)  

## 🔧 The Real Problem

**The error "does not implement OAuth" happened because:**
- MCP servers DON'T use HTTP/SSE endpoints
- MCP servers use **stdio transport** (stdin/stdout)
- ChatGPT Desktop runs MCP servers as **subprocess commands**
- Your config was pointing to a URL instead of a command

## 📦 Download CORRECT Version

**File:** `wp-ai-engine-pro-stdio-v4.0.3.zip`  
**Location:** `/Users/samvardani/Projects/safety-eval-mini/wp-ai-engine-pro-stdio-v4.0.3.zip`

## 🎯 CORRECT ChatGPT Configuration

### Step 1: Install the Plugin
1. Upload `wp-ai-engine-pro-stdio-v4.0.3.zip` to WordPress
2. Activate the plugin
3. Go to **AI Engine > MCP Setup**
4. **Copy the MCP Server Path** (not URL!)

### Step 2: Find Your MCP Server Path
After installation, the path will be something like:
```
/home/yoursite/public_html/wp-content/plugins/wp-ai-engine-pro-simple/mcp-server.php
```

Or for your site (searei.com):
```
/path/to/searei.com/wp-content/plugins/wp-ai-engine-pro-simple/mcp-server.php
```

### Step 3: CORRECT ChatGPT Config

**This is the CORRECT configuration:**

```json
{
  "mcpServers": {
    "wordpress": {
      "command": "php",
      "args": ["/full/path/to/your/wp-content/plugins/wp-ai-engine-pro-simple/mcp-server.php"]
    }
  }
}
```

**Replace `/full/path/to/your/` with your actual WordPress installation path!**

### Example Configurations:

**For cPanel/shared hosting:**
```json
{
  "mcpServers": {
    "wordpress": {
      "command": "php",
      "args": ["/home/username/public_html/wp-content/plugins/wp-ai-engine-pro-simple/mcp-server.php"]
    }
  }
}
```

**For VPS/dedicated server:**
```json
{
  "mcpServers": {
    "wordpress": {
      "command": "/usr/bin/php",
      "args": ["/var/www/html/wp-content/plugins/wp-ai-engine-pro-simple/mcp-server.php"]
    }
  }
}
```

## ❌ WRONG vs ✅ RIGHT

### ❌ WRONG (What Causes OAuth Error):
```json
{
  "mcpServers": {
    "wordpress": {
      "url": "https://searei.com/wp-json/wpai/v1/mcp/sse"
    }
  }
}
```
**This is WRONG! MCP doesn't use URLs!**

### ✅ RIGHT (What Actually Works):
```json
{
  "mcpServers": {
    "wordpress": {
      "command": "php",
      "args": ["/path/to/mcp-server.php"]
    }
  }
}
```
**This is RIGHT! MCP uses command + args!**

## 🔍 How to Find Your Path

### Option 1: WordPress Admin
1. Go to **AI Engine > MCP Setup**
2. Copy the **MCP Server Path** shown
3. Use that exact path in your config

### Option 2: SSH/Terminal
```bash
# SSH into your server
ssh user@searei.com

# Find WordPress installation
cd /path/to/your/wordpress

# Navigate to plugin
cd wp-content/plugins/wp-ai-engine-pro-simple

# Get full path
pwd
# Output: /home/username/public_html/wp-content/plugins/wp-ai-engine-pro-simple

# Your mcp-server.php path is:
# /home/username/public_html/wp-content/plugins/wp-ai-engine-pro-simple/mcp-server.php
```

### Option 3: File Manager (cPanel)
1. Log into cPanel
2. Open File Manager
3. Navigate to: `public_html/wp-content/plugins/wp-ai-engine-pro-simple/`
4. Right-click `mcp-server.php` → Properties
5. Copy the full path shown

## 🚀 Complete Setup Steps

1. **Install Plugin**
   - Upload to WordPress
   - Activate

2. **Get Server Path**
   - Go to AI Engine > MCP Setup
   - Copy the MCP Server Path

3. **Edit ChatGPT Config**
   - Mac/Linux: `~/.config/OpenAI/ChatGPT/config.json`
   - Windows: `%APPDATA%\OpenAI\ChatGPT\config.json`

4. **Add Configuration**
   ```json
   {
     "mcpServers": {
       "wordpress": {
         "command": "php",
         "args": ["/YOUR/ACTUAL/PATH/mcp-server.php"]
       }
     }
   }
   ```

5. **Restart ChatGPT**
   - Completely quit ChatGPT Desktop
   - Start it again

6. **Test**
   - Ask: "What's my WordPress site information?"
   - Should work immediately!

## ✅ Available Commands

Once connected, try:
- "What's my WordPress site information?"
- "Show me my recent posts"
- "Create a new blog post about AI and technology"
- "What are my site statistics?"

## 🐛 Troubleshooting

### Error: "php: command not found"
**Solution:** Use full PHP path:
```json
{
  "mcpServers": {
    "wordpress": {
      "command": "/usr/bin/php",
      "args": ["/path/to/mcp-server.php"]
    }
  }
}
```

### Error: "Cannot load WordPress"
**Solution:** Check the path is correct and accessible

### Error: "Permission denied"
**Solution:** Make file executable:
```bash
chmod +x /path/to/mcp-server.php
```

## 📝 Key Differences

| Feature | HTTP/SSE (WRONG) | Stdio (CORRECT) |
|---------|------------------|-----------------|
| Transport | HTTP requests | stdin/stdout |
| Config | `url:` | `command:` + `args:` |
| OAuth | Required | Not needed |
| How it works | Network connection | Subprocess |

## 🎉 Why This Works

1. **ChatGPT Desktop** runs your `mcp-server.php` as a subprocess
2. **Communication** happens via stdin/stdout (not HTTP)
3. **No OAuth** needed because it's a local process
4. **Direct access** to WordPress via PHP

## ✅ Success Checklist

- [ ] Plugin installed (v4.0.3)
- [ ] MCP Server Path copied from admin
- [ ] ChatGPT config uses `command` + `args` (not `url`)
- [ ] Full path to mcp-server.php is correct
- [ ] ChatGPT completely restarted
- [ ] Test command works
- [ ] No more OAuth errors!

---

**Developer:** Saeed M. Vardani  
**Company:** SeaTechOne.com  
**Built with ❤️**

**This is the CORRECT implementation of MCP for WordPress!**


