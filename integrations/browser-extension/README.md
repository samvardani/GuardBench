# SeaRei Browser Extension

Real-time AI safety content scanner for Chrome, Edge, and Firefox.

## Features

- 🔍 **One-Click Scanning** - Scan any webpage instantly
- 🤖 **Auto-Scan Mode** - Automatically check pages on load
- 📊 **Usage Statistics** - Track scanned pages and flagged content
- ⚙️ **Customizable** - Configure API endpoint and behavior
- 🔔 **Notifications** - Get alerts when unsafe content is detected
- 🎨 **Highlighting** - Visually mark unsafe content (optional)

## Installation

### Method 1: Load Unpacked (For Development)

1. **Open Chrome Extensions Page:**
   ```
   chrome://extensions/
   ```
   Or: Menu → Extensions → Manage Extensions

2. **Enable Developer Mode:**
   - Toggle the switch in the top-right corner

3. **Load the Extension:**
   - Click "Load unpacked"
   - Select this directory: `integrations/browser-extension/`

4. **You're Done!**
   - The SeaRei icon should appear in your toolbar
   - Click it to open the popup

### Method 2: Chrome Web Store (Coming Soon)

Search for "SeaRei Safety Scanner" in the Chrome Web Store.

## Quick Start

### 1. Start the SeaRei API

```bash
# Make sure the API is running
uvicorn src.service.api:app --port 8001
```

### 2. Open the Extension

Click the SeaRei icon in your Chrome toolbar.

### 3. Scan a Page

Click the **"🔍 Scan Current Page"** button.

### 4. View Results

- ✅ **Safe**: Content appears safe
- ⚠️ **Flagged**: Unsafe content detected

## Configuration

### Access Settings

1. Right-click the extension icon
2. Select "Options"

### Available Settings

- **API Endpoint**: URL where SeaRei API is running (default: `http://localhost:8001`)
- **Auto-scan on Load**: Automatically scan every page you visit
- **Desktop Notifications**: Show alerts when unsafe content is detected
- **Highlight Content**: Visually mark unsafe text on pages

## Usage

### Scan Current Page

1. Navigate to any webpage
2. Click the extension icon
3. Click "🔍 Scan Current Page"
4. View results in popup

### Scan Selected Text

1. Select text on any page
2. Right-click
3. Choose "Scan with SeaRei"
4. View notification

### Auto-Scan Mode

1. Enable in Settings (Options page)
2. Browse normally
3. Get automatic notifications if unsafe content is detected

## Features Explained

### Statistics

Track your usage:
- **Scanned**: Total pages/text scanned
- **Flagged**: Number of times unsafe content was detected

### API Configuration

The extension can connect to:
- **Local API**: `http://localhost:8001` (default)
- **Cloud API**: `https://api.searei.ai` (if deployed)
- **Custom**: Any URL where SeaRei is hosted

### Notifications

Types of notifications:
- **✅ Content Safe**: No issues detected
- **⚠️ Unsafe Content**: Potential safety issues found
- **❌ Scan Error**: API connection failed

## Troubleshooting

### Extension Not Loading

**Error**: "Could not load javascript 'content.js'"

**Solution**: Make sure all files are present:
```bash
ls -la integrations/browser-extension/
# Should show: manifest.json, popup.html, popup.js, 
#              content.js, content.css, background.js, 
#              options.html, options.js
```

### API Connection Failed

**Error**: "Cannot connect to API"

**Solutions**:
1. Check if API is running: `curl http://localhost:8001/healthz`
2. Verify API URL in Settings
3. Check CORS settings in API (should allow `chrome-extension://`)

### Scans Not Working

**Issue**: Button does nothing

**Solutions**:
1. Open browser console (F12) and check for errors
2. Verify API is accessible
3. Reload the extension

## Development

### File Structure

```
browser-extension/
├── manifest.json       # Extension manifest
├── popup.html          # Main popup UI
├── popup.js            # Popup logic
├── content.js          # Runs on web pages
├── content.css         # Page styling
├── background.js       # Service worker
├── options.html        # Settings page
├── options.js          # Settings logic
└── icons/              # Extension icons (optional)
```

### Testing Locally

1. Make changes to any file
2. Go to `chrome://extensions/`
3. Click "Reload" button on SeaRei extension
4. Test your changes

### Debugging

**View Popup Logs:**
1. Right-click extension icon
2. Select "Inspect popup"
3. Check Console tab

**View Content Script Logs:**
1. Open any webpage
2. Press F12 (DevTools)
3. Check Console for SeaRei messages

**View Background Script Logs:**
1. Go to `chrome://extensions/`
2. Find SeaRei extension
3. Click "service worker" link
4. Check Console tab

## Privacy & Security

- **No Data Collection**: Extension doesn't collect or store any personal data
- **Local Processing**: All API calls go directly to your configured endpoint
- **No Tracking**: No analytics or tracking scripts
- **Open Source**: All code is available for review

## Advanced Usage

### Custom API Headers

To add custom headers (e.g., API keys), modify `popup.js`:

```javascript
const response = await fetch(`${API_URL}/score`, {
    method: 'POST',
    headers: { 
        'Content-Type': 'application/json',
        'X-API-Key': 'your-api-key'  // Add this
    },
    body: JSON.stringify({ text: pageText })
});
```

### Keyboard Shortcuts

Add to `manifest.json`:

```json
"commands": {
  "scan-page": {
    "suggested_key": {
      "default": "Ctrl+Shift+S",
      "mac": "Command+Shift+S"
    },
    "description": "Scan current page"
  }
}
```

### Custom Highlighting

Modify `content.js` to change highlight colors:

```javascript
span.style.cssText = 'background-color: rgba(239, 68, 68, 0.3); border-bottom: 2px solid #ef4444;';
```

## FAQ

**Q: Does this work offline?**
A: No, the extension needs to connect to a running SeaRei API.

**Q: Can I use this with a remote API?**
A: Yes! Just change the API URL in Settings to your deployed endpoint.

**Q: Does it slow down browsing?**
A: No. Scans only happen when you click the button or enable auto-scan.

**Q: What browsers are supported?**
A: Chrome, Edge, Brave, and other Chromium-based browsers. Firefox support coming soon.

**Q: Can I customize what's flagged?**
A: Yes! Use the Policy Editor at `http://localhost:8001/policy-editor.html` to customize detection rules.

## Support

- **Documentation**: See `INTEGRATIONS_COMPLETE.md`
- **Issues**: Create an issue on GitHub
- **API Docs**: `http://localhost:8001/docs`

## License

Same license as SeaRei platform.

---

**Version**: 1.0.0  
**Last Updated**: January 13, 2025  
**Status**: Production Ready 🚀












