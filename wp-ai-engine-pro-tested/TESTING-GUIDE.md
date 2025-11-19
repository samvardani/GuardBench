# WP AI Engine Pro - Testing Guide

**Version:** 4.1.0  
**Developer:** Saeed M. Vardani  
**Company:** SeaTechOne.com

## Table of Contents

1. [Pre-Installation Testing](#pre-installation-testing)
2. [Installation Testing](#installation-testing)
3. [Configuration Testing](#configuration-testing)
4. [Admin Interface Testing](#admin-interface-testing)
5. [OpenAI API Testing](#openai-api-testing)
6. [MCP & OAuth Testing](#mcp--oauth-testing)
7. [Shortcode Testing](#shortcode-testing)
8. [Security Testing](#security-testing)
9. [Performance Testing](#performance-testing)
10. [Compatibility Testing](#compatibility-testing)
11. [Troubleshooting](#troubleshooting)

---

## Pre-Installation Testing

### System Requirements Check

- [ ] **PHP Version:** 8.1 or higher
  ```bash
  php -v
  ```
  
- [ ] **WordPress Version:** 6.0 or higher
  - Check in WP Admin → Dashboard

- [ ] **cURL Extension:** Installed and enabled
  ```bash
  php -m | grep curl
  ```

- [ ] **Server Permissions:** Write access to wp-content/plugins/

### Expected Results
✅ All requirements met  
✅ No warnings or errors

---

## Installation Testing

### Test 1: Plugin Upload

**Steps:**
1. Go to WP Admin → Plugins → Add New → Upload Plugin
2. Choose `wp-ai-engine-pro-v4.1.0.zip`
3. Click "Install Now"
4. Wait for installation to complete

**Expected Results:**
- ✅ Upload successful
- ✅ No PHP errors
- ✅ "Plugin installed successfully" message appears

### Test 2: Plugin Activation

**Steps:**
1. Click "Activate Plugin" button
2. Check for any error messages
3. Verify plugin appears in Plugins list

**Expected Results:**
- ✅ Plugin activates without errors
- ✅ "AI Engine" menu appears in admin sidebar
- ✅ Plugin status shows "Active"

### Test 3: Rewrite Rules

**Steps:**
1. After activation, go to Settings → Permalinks
2. Click "Save Changes" (don't change anything)
3. Test OAuth discovery URL in browser:
   ```
   https://yoursite.com/wp-json/wpai/v1/.well-known/oauth-authorization-server
   ```

**Expected Results:**
- ✅ Permalinks saved successfully
- ✅ OAuth discovery URL returns JSON response
- ✅ No 404 errors

---

## Configuration Testing

### Test 4: Settings Page Access

**Steps:**
1. Go to AI Engine → Settings
2. Verify all fields are visible
3. Check form structure

**Expected Results:**
- ✅ Settings page loads without errors
- ✅ OpenAI API Key field visible
- ✅ Default Model dropdown visible
- ✅ Max Tokens field visible
- ✅ Temperature field visible
- ✅ Save button present

### Test 5: API Key Validation

**Steps:**
1. Enter invalid API key (e.g., "test123")
2. Click "Save Changes"
3. Check for validation error

**Expected Results:**
- ✅ Error message: "Invalid API key format"
- ✅ Settings not saved
- ✅ User redirected back to form

### Test 6: Valid API Key Save

**Steps:**
1. Enter valid OpenAI API key (starts with "sk-")
2. Select model (e.g., "GPT-4o")
3. Set Max Tokens: 4096
4. Set Temperature: 0.7
5. Click "Save Changes"

**Expected Results:**
- ✅ "Settings saved" success message
- ✅ API key stored securely
- ✅ Settings persist after page reload
- ✅ API key displayed as "sk-...XXXX" (masked)

### Test 7: Show/Hide API Key

**Steps:**
1. Click "Show/Hide" button next to API key field
2. Verify key visibility toggles

**Expected Results:**
- ✅ Button toggles between password and text input
- ✅ Full API key visible when shown
- ✅ API key hidden when toggled back

---

## Admin Interface Testing

### Test 8: Dashboard Page

**Steps:**
1. Go to AI Engine → Dashboard
2. Check all dashboard elements

**Expected Results:**
- ✅ Status card shows "Active" (if API key set) or "Not Configured"
- ✅ Version card shows "4.1.0"
- ✅ PHP Version card shows current PHP version
- ✅ WordPress card shows current WP version
- ✅ Quick Actions buttons work
- ✅ Getting Started instructions visible
- ✅ Plugin Information shows developer/company details

### Test 9: MCP Setup Page

**Steps:**
1. Go to AI Engine → MCP Setup
2. Verify MCP URL is displayed
3. Test "Copy URL" button
4. Click "Test MCP Endpoint" link

**Expected Results:**
- ✅ MCP URL displayed correctly
- ✅ Copy button copies URL to clipboard
- ✅ Test link opens MCP endpoint in new tab
- ✅ MCP endpoint returns JSON with server info
- ✅ OAuth discovery link works

### Test 10: Test Page

**Steps:**
1. Go to AI Engine → Test
2. Review current settings table
3. Check system status

**Expected Results:**
- ✅ All settings displayed correctly
- ✅ API Key status shows "Ready" (green) if set
- ✅ Model shows selected model
- ✅ Plugin version correct
- ✅ PHP version check passes
- ✅ cURL extension shows "Installed"

---

## OpenAI API Testing

### Test 11: API Connection Test

**Steps:**
1. Go to AI Engine → Test
2. Click "Test API Connection" button
3. Wait for response

**Expected Results:**
- ✅ Button shows "Testing..." while processing
- ✅ Success message appears with green background
- ✅ Response text displayed
- ✅ Model name shown
- ✅ Token count displayed
- ✅ Button re-enabled after test

### Test 12: API Error Handling

**Steps:**
1. Go to Settings
2. Enter invalid API key
3. Save settings
4. Go to Test page
5. Click "Test API Connection"

**Expected Results:**
- ✅ Error message with red background
- ✅ Clear error description
- ✅ Helpful guidance provided
- ✅ No PHP errors or warnings

### Test 13: Chat Endpoint Direct Test

**Steps:**
1. Use a REST API client (Postman, Insomnia, or cURL)
2. Send POST request to:
   ```
   POST https://yoursite.com/wp-json/wpai/v1/chat
   Headers:
     Content-Type: application/json
     X-WP-Nonce: [get from logged-in session]
   Body:
     {
       "message": "Hello, this is a test"
     }
   ```

**Expected Results:**
- ✅ HTTP 200 response
- ✅ JSON response with `success: true`
- ✅ Response contains `response` field with AI reply
- ✅ Response contains `tokens` field
- ✅ Response contains `model` field

---

## MCP & OAuth Testing

### Test 14: OAuth Discovery

**Steps:**
1. Open browser
2. Navigate to:
   ```
   https://yoursite.com/wp-json/wpai/v1/.well-known/oauth-authorization-server
   ```

**Expected Results:**
- ✅ HTTP 200 response
- ✅ JSON response with OAuth configuration
- ✅ Contains `issuer`, `authorization_endpoint`, `token_endpoint`
- ✅ Contains `response_types_supported: ["code"]`
- ✅ Contains `grant_types_supported`
- ✅ Contains `code_challenge_methods_supported: ["S256"]`
- ✅ Developer and company info present

### Test 15: MCP Server Info

**Steps:**
1. Send GET request to:
   ```
   GET https://yoursite.com/wp-json/wpai/v1/mcp
   ```

**Expected Results:**
- ✅ HTTP 200 response
- ✅ JSON response with server info
- ✅ Contains `name: "WP AI Engine Pro"`
- ✅ Contains `version: "4.1.0"`
- ✅ Contains `protocol: "mcp-http"`
- ✅ Contains `capabilities` object
- ✅ Contains `oauth_config` URL
- ✅ Contains list of available tools

### Test 16: MCP Tools List

**Steps:**
1. Send POST request to:
   ```
   POST https://yoursite.com/wp-json/wpai/v1/mcp
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

**Expected Results:**
- ✅ HTTP 200 response
- ✅ JSON-RPC 2.0 compliant response
- ✅ Contains `result.tools` array
- ✅ Each tool has `name`, `description`, `inputSchema`
- ✅ Tools include: `wp_get_site_info`, `wp_list_posts`, `wp_create_post`, `wp_get_stats`

### Test 17: MCP Tool Execution

**Steps:**
1. Send POST request to:
   ```
   POST https://yoursite.com/wp-json/wpai/v1/mcp
   Headers:
     Content-Type: application/json
   Body:
     {
       "jsonrpc": "2.0",
       "id": 2,
       "method": "tools/call",
       "params": {
         "name": "wp_get_site_info",
         "arguments": {}
       }
     }
   ```

**Expected Results:**
- ✅ HTTP 200 response
- ✅ JSON-RPC 2.0 compliant response
- ✅ Contains `result.content` array
- ✅ Content contains site information
- ✅ Includes site name, URL, WP version, etc.

### Test 18: ChatGPT Browser Integration

**Steps:**
1. Open ChatGPT in browser
2. Enable Developer Mode
3. Add MCP server with URL:
   ```
   https://yoursite.com/wp-json/wpai/v1/mcp
   ```
4. ChatGPT will discover OAuth automatically
5. Authorize when prompted
6. Ask ChatGPT: "What's my WordPress site information?"

**Expected Results:**
- ✅ OAuth discovery successful
- ✅ Authorization flow completes
- ✅ Access token generated
- ✅ ChatGPT can call WordPress tools
- ✅ Site information returned correctly

---

## Shortcode Testing

### Test 19: Basic Shortcode

**Steps:**
1. Create new page or post
2. Add shortcode: `[wpai_chatbot]`
3. Publish and view page

**Expected Results:**
- ✅ Chatbot widget appears
- ✅ Widget positioned bottom-right
- ✅ Header shows "AI Assistant"
- ✅ Welcome message displayed
- ✅ Input field and send button visible
- ✅ Footer shows "Powered by SeaTechOne.com"

### Test 20: Shortcode with Attributes

**Steps:**
1. Create new page
2. Add shortcode:
   ```
   [wpai_chatbot title="My Custom Bot" theme="dark" position="bottom-left"]
   ```
3. Publish and view page

**Expected Results:**
- ✅ Custom title "My Custom Bot" displayed
- ✅ Dark theme applied
- ✅ Widget positioned bottom-left
- ✅ All functionality works

### Test 21: Chatbot Interaction

**Steps:**
1. On page with chatbot
2. Type message: "Hello"
3. Click send button
4. Wait for response

**Expected Results:**
- ✅ User message appears (right side, blue)
- ✅ Loading indicator shows "Thinking..."
- ✅ AI response appears (left side, white)
- ✅ Input field clears after send
- ✅ Input re-enabled after response
- ✅ Messages scroll automatically

### Test 22: Chatbot Error Handling

**Steps:**
1. Temporarily set invalid API key
2. Try sending message in chatbot
3. Check error display

**Expected Results:**
- ✅ Error message displayed in chat
- ✅ User-friendly error text
- ✅ No JavaScript console errors
- ✅ Chatbot remains functional

---

## Security Testing

### Test 23: Nonce Verification

**Steps:**
1. Try to submit settings form without nonce
2. Try to call REST API without nonce
3. Try with invalid nonce

**Expected Results:**
- ✅ Requests rejected without nonce
- ✅ Requests rejected with invalid nonce
- ✅ HTTP 403 or 401 response
- ✅ No data saved/modified

### Test 24: Capability Checks

**Steps:**
1. Log in as Subscriber role
2. Try to access AI Engine menu
3. Try to access settings page directly

**Expected Results:**
- ✅ Menu not visible to non-admins
- ✅ Direct URL access blocked
- ✅ "You do not have sufficient permissions" message
- ✅ No sensitive data exposed

### Test 25: Input Sanitization

**Steps:**
1. Try to save settings with malicious input:
   - API Key: `<script>alert('xss')</script>`
   - Model: `'; DROP TABLE wp_options; --`
2. Check if data is sanitized

**Expected Results:**
- ✅ Script tags removed/escaped
- ✅ SQL injection attempts blocked
- ✅ Data sanitized before storage
- ✅ No XSS vulnerabilities

### Test 26: OAuth Security

**Steps:**
1. Test OAuth authorization with invalid client_id
2. Test token endpoint with expired code
3. Test MCP with invalid token

**Expected Results:**
- ✅ Invalid requests rejected
- ✅ Proper error responses
- ✅ Codes are one-time use
- ✅ Tokens expire after 1 hour

---

## Performance Testing

### Test 27: Page Load Time

**Steps:**
1. Use browser DevTools Network tab
2. Load admin dashboard
3. Load page with chatbot shortcode
4. Measure load times

**Expected Results:**
- ✅ Admin pages load < 2 seconds
- ✅ Frontend pages load < 1 second
- ✅ Assets properly cached
- ✅ No blocking resources

### Test 28: API Response Time

**Steps:**
1. Send test message via chatbot
2. Measure response time
3. Check server logs

**Expected Results:**
- ✅ Response within 5-10 seconds (depends on OpenAI)
- ✅ No PHP timeout errors
- ✅ Proper timeout handling
- ✅ No memory issues

---

## Compatibility Testing

### Test 29: WordPress Core Compatibility

**Steps:**
1. Test with WordPress 6.0, 6.1, 6.2, 6.3, 6.4, 6.5
2. Check for any deprecation warnings
3. Verify all features work

**Expected Results:**
- ✅ Works with all WP 6.x versions
- ✅ No deprecation warnings
- ✅ All features functional

### Test 30: Theme Compatibility

**Steps:**
1. Test with default WordPress themes:
   - Twenty Twenty-Four
   - Twenty Twenty-Three
   - Twenty Twenty-Two
2. Test with popular themes (Astra, GeneratePress, etc.)

**Expected Results:**
- ✅ Chatbot displays correctly
- ✅ Admin interface unaffected
- ✅ No CSS conflicts
- ✅ Responsive on all screen sizes

### Test 31: Plugin Compatibility

**Steps:**
1. Test with popular plugins:
   - Yoast SEO
   - WooCommerce
   - Contact Form 7
   - Jetpack
2. Check for conflicts

**Expected Results:**
- ✅ No JavaScript conflicts
- ✅ No REST API conflicts
- ✅ No database conflicts
- ✅ All plugins work together

---

## Troubleshooting

### Common Issues

#### Issue 1: "AI Engine" menu not appearing

**Possible Causes:**
- User doesn't have admin role
- Plugin not activated
- PHP error during initialization

**Solutions:**
1. Check user role (must be Administrator)
2. Verify plugin is activated
3. Check PHP error logs
4. Deactivate and reactivate plugin

#### Issue 2: OAuth discovery returns 404

**Possible Causes:**
- Rewrite rules not flushed
- Permalink structure issue
- .htaccess problems

**Solutions:**
1. Go to Settings → Permalinks → Save Changes
2. Check .htaccess file permissions
3. Try different permalink structure
4. Check server error logs

#### Issue 3: API test fails

**Possible Causes:**
- Invalid API key
- Network/firewall blocking OpenAI
- cURL not installed
- SSL certificate issues

**Solutions:**
1. Verify API key is correct
2. Check firewall rules
3. Install/enable cURL extension
4. Update SSL certificates
5. Check OpenAI API status

#### Issue 4: Chatbot not responding

**Possible Causes:**
- JavaScript errors
- REST API blocked
- API key issues
- CORS problems

**Solutions:**
1. Check browser console for errors
2. Test REST API directly
3. Verify API key in settings
4. Check server CORS configuration

---

## Test Results Template

Use this template to document your test results:

```
Test Date: _______________
Tester: _______________
WordPress Version: _______________
PHP Version: _______________
Server: _______________

| Test # | Test Name | Status | Notes |
|--------|-----------|--------|-------|
| 1 | Plugin Upload | ☐ Pass ☐ Fail | |
| 2 | Plugin Activation | ☐ Pass ☐ Fail | |
| 3 | Rewrite Rules | ☐ Pass ☐ Fail | |
| ... | ... | ... | |

Overall Result: ☐ All Tests Passed ☐ Some Tests Failed

Issues Found:
1. _______________
2. _______________

Recommendations:
1. _______________
2. _______________
```

---

## Support

For issues or questions:
- **Developer:** Saeed M. Vardani
- **Company:** SeaTechOne.com
- **Website:** https://seatechone.com

---

**Document Version:** 1.0  
**Last Updated:** 2025-01-01  
**Plugin Version:** 4.1.0

