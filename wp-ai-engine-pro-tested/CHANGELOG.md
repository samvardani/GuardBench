# Changelog

All notable changes to WP AI Engine Pro will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [4.1.0] - 2025-01-01

### Added
- **Security Hardening**
  - Nonce verification for all forms and AJAX requests
  - Input sanitization for all user inputs
  - Output escaping for all displayed data
  - Capability checks for all admin pages and endpoints
  - API key format validation
  - Enhanced OAuth security with PKCE

- **Error Handling**
  - Try-catch blocks around all API calls
  - Proper WP_Error returns for REST endpoints
  - Detailed error logging with wpai_log_error()
  - User-friendly error messages
  - Graceful degradation on failures

- **Admin Interface Improvements**
  - Enhanced dashboard with status cards
  - Better settings page layout
  - Improved MCP setup instructions
  - Enhanced test page with detailed checks
  - Show/Hide API key toggle
  - Copy-to-clipboard functionality

- **Documentation**
  - Comprehensive TESTING-GUIDE.md
  - Detailed INSTALLATION-GUIDE.md
  - Updated README.md with all features
  - Inline code documentation
  - PHPDoc blocks for all functions

- **Features**
  - Max Tokens configuration
  - Temperature configuration
  - Enhanced chatbot UI
  - Better mobile responsiveness
  - Improved error messages in chatbot

### Changed
- **Models Updated**
  - Changed default model from gpt-5-chat-latest to gpt-4o
  - Updated model list to current OpenAI offerings
  - Removed non-existent GPT-5 models
  - Added GPT-4o and GPT-4o Mini

- **Security**
  - All REST endpoint parameters now validated
  - Sanitization callbacks added to all register_rest_route calls
  - Enhanced OAuth token validation
  - Improved transient storage security

- **Performance**
  - Optimized asset loading
  - Better caching strategy
  - Reduced database queries
  - Improved REST API response times

- **UI/UX**
  - Cleaner admin interface
  - Better error messaging
  - Improved form validation feedback
  - Enhanced mobile experience

### Fixed
- OAuth discovery endpoint accessibility
- Permalink flush on activation
- API key masking in admin
- Chatbot scroll behavior
- REST API nonce validation
- Settings sanitization
- Error handling in MCP tools
- CORS headers for MCP endpoints

### Security
- Fixed XSS vulnerabilities through proper escaping
- Fixed SQL injection risks through sanitization
- Fixed CSRF through nonce verification
- Fixed capability bypass through proper checks
- Enhanced OAuth security with one-time codes
- Improved token expiration handling

---

## [4.0.6] - 2024-12-XX

### Added
- Multiple OAuth discovery endpoints
- WordPress rewrite rules for .well-known paths
- Enhanced CORS support

### Fixed
- OAuth discovery not found by ChatGPT
- Permalink structure issues

---

## [4.0.5] - 2024-12-XX

### Added
- OAuth 2.0 implementation
- Authorization endpoint
- Token endpoint
- OAuth discovery endpoint

### Changed
- MCP endpoint to support OAuth authentication

---

## [4.0.4] - 2024-12-XX

### Added
- Browser-compatible MCP HTTP endpoint
- JSON-RPC 2.0 support
- CORS headers for browser access

### Changed
- Switched from SSE to HTTP for browser compatibility

---

## [4.0.3] - 2024-12-XX

### Added
- stdio transport MCP server for ChatGPT Desktop
- mcp-server.php for subprocess communication

---

## [4.0.2] - 2024-12-XX

### Added
- Developer attribution (Saeed M. Vardani)
- Company attribution (SeaTechOne.com)
- MCP Server-Sent Events (SSE) endpoint
- Enhanced MCP setup page

### Fixed
- Admin menu not appearing
- API test functionality
- Settings page display

---

## [4.0.1] - 2024-12-XX

### Added
- Initial MCP support
- REST API endpoints
- Basic admin interface

---

## [4.0.0] - 2024-12-XX

### Added
- Initial release
- OpenAI API integration
- Chatbot shortcode
- Admin dashboard
- Settings page
- Test page

---

## Upgrade Notes

### Upgrading to 4.1.0

1. **Backup Your Site**
   - Always backup before upgrading

2. **Deactivate Old Version**
   - Deactivate the current plugin

3. **Delete Old Version**
   - Delete the old plugin files

4. **Install New Version**
   - Upload and activate v4.1.0

5. **Flush Permalinks**
   - Go to Settings → Permalinks
   - Click "Save Changes"

6. **Test Configuration**
   - Go to AI Engine → Test
   - Run API test
   - Test chatbot on a page
   - Test OAuth endpoints

7. **Update ChatGPT Connection**
   - If using ChatGPT integration
   - May need to re-authorize

### Breaking Changes

None. Version 4.1.0 is fully backward compatible with 4.0.x.

### Database Changes

None. No database migrations required.

---

## Support

For issues or questions:
- **Developer:** Saeed M. Vardani
- **Company:** SeaTechOne.com
- **Website:** https://seatechone.com

---

## Links

- [Installation Guide](INSTALLATION-GUIDE.md)
- [Testing Guide](TESTING-GUIDE.md)
- [README](README.md)
- [License](LICENSE)

---

**Developer:** Saeed M. Vardani  
**Company:** SeaTechOne.com  
**License:** GPLv3 or later

