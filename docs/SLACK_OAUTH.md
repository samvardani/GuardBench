# Slack App OAuth Integration Guide

Enable easy Slack workspace installation via OAuth for viral product adoption.

## Overview

The Slack OAuth integration allows any Slack workspace to install the Safety-Eval-Mini bot with a simple "Add to Slack" button, enabling:
- Easy onboarding without manual configuration
- Multi-workspace support
- Secure token storage per workspace
- Compliance with Slack App Directory requirements

## Quick Start

### 1. Create Slack App

1. Go to https://api.slack.com/apps
2. Click "Create New App" → "From scratch"
3. Name: "Safety-Eval-Mini"
4. Choose development workspace

### 2. Configure OAuth & Permissions

**OAuth Scopes** (Bot Token Scopes):
- `commands` - Slash commands
- `chat:write` - Send messages
- `chat:write.public` - Send to public channels
- `app_mentions:read` - Read @mentions

**Redirect URLs**:
- Development: `http://localhost:8001/slack/oauth_callback`
- Production: `https://your-domain.com/slack/oauth_callback`

### 3. Get Credentials

From **Basic Information** page:
- **Client ID**: Copy this
- **Client Secret**: Copy this (show, then copy)
- **Signing Secret**: For command verification

### 4. Configure Environment

```bash
export SLACK_CLIENT_ID="123456789012.123456789012"
export SLACK_CLIENT_SECRET="your-client-secret-here"
export SLACK_SIGNING_SECRET="your-signing-secret-here"
export SLACK_REDIRECT_URI="http://localhost:8001/slack/oauth_callback"
```

### 5. Start Service

```bash
PYTHONPATH=src uvicorn service.api:app --port 8001
```

### 6. Install to Workspace

Visit: http://localhost:8001/slack/add-to-slack

Or click: http://localhost:8001/slack/install

## OAuth Flow

### Step 1: User Clicks "Add to Slack"

`GET /slack/add-to-slack` → Renders page with button

`GET /slack/install` → Redirects to Slack with OAuth params

### Step 2: User Authorizes

Slack shows permission consent page

User clicks "Allow"

### Step 3: Callback & Token Exchange

Slack redirects to `/slack/oauth_callback?code=...&state=...`

Server exchanges code for access token via Slack API

Token and workspace info stored in database

### Step 4: Success Page

User sees success message with instructions

Bot is now active in their workspace

## Database Schema

```sql
CREATE TABLE slack_installations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id TEXT NOT NULL UNIQUE,
    team_name TEXT,
    access_token TEXT NOT NULL,
    bot_user_id TEXT,
    scope TEXT,
    app_id TEXT,
    installed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Initialization**:
```python
from service.db_slack import init_slack_tables
import sqlite3

conn = sqlite3.connect("history.db")
init_slack_tables(conn)
```

## Using Stored Tokens

### Retrieve Installation

```python
from service.db_slack import get_slack_installation

installation = get_slack_installation(conn, team_id="T123456")
if installation:
    access_token = installation["access_token"]
    # Use token for Slack API calls
```

### Update Bot to Use Token

```python
# In slack_app.py
from service.db_slack import get_slack_installation

@app.command("/safety-check")
def handle_safety_check(ack, command, respond):
    team_id = command["team_id"]
    
    # Get installation for this workspace
    installation = get_slack_installation(conn, team_id)
    
    if not installation:
        respond("Bot not properly installed. Please reinstall.")
        return
    
    # Use workspace-specific token
    token = installation["access_token"]
    # ... rest of command handling
```

## Multi-Workspace Support

Each workspace gets its own:
- Access token
- Bot user ID
- Scope grants
- Installation record

Commands from different workspaces automatically use the correct token.

## Add to Slack Button

### In Documentation

```markdown
## Install

<a href="https://your-domain.com/slack/install">
  <img 
    alt="Add to Slack" 
    height="40" 
    width="139" 
    src="https://platform.slack-edge.com/img/add_to_slack.png"
  />
</a>
```

### In Web Dashboard

Add button to UI:
```html
<a href="/slack/add-to-slack">
  <button>Add to Slack</button>
</a>
```

The `/slack/add-to-slack` endpoint renders a full-page UI with the button.

## Error Handling

### Expired Code

**Symptom**: `invalid_code` error in callback

**Solution**: OAuth codes expire after 10 minutes. User must restart flow.

**Handled**: Returns user-friendly error page with "Try again" link

### Duplicate Installation

**Behavior**: `ON CONFLICT` updates existing installation

**Result**: Latest token replaces old token (re-installation supported)

### Network Failures

**Symptom**: Timeout during token exchange

**Handled**: Catches exception, returns error page, logs details

### Invalid State

**Symptom**: CSRF state mismatch

**Handled**: Returns 400 error (potential CSRF attack)

## Security

### CSRF Protection

- State token generated per install request
- Validated in callback
- Cleaned up after use

### Token Storage

- Access tokens encrypted in database (production: use encryption)
- Never logged in plain text
- Not included in to_dict() responses

### HTTPS Required

Production must use HTTPS:
- Protects tokens in transit
- Required by Slack for App Directory

## Testing

### Unit Tests

```bash
pytest tests/test_slack_oauth.py -v
# 19 tests: 16 pass, 3 async-related failures
```

### Integration Test

**Scenario**: Full OAuth flow

1. Start service with OAuth configured
2. Visit `/slack/add-to-slack`
3. Click "Add to Slack"
4. Authorize in Slack
5. Verify callback succeeds
6. Check database for installation
7. Test `/safety-check` command in Slack
8. Verify bot responds using stored token

### Mock Testing

```python
from unittest.mock import AsyncMock, patch

# Mock OAuth exchange
mock_response = {
    "ok": True,
    "access_token": "xoxb-test",
    "team": {"id": "T123", "name": "Test"}
}

with patch("integrations.slack_oauth.SlackOAuthConfig.exchange_code", 
           new_callable=AsyncMock) as mock_exchange:
    mock_exchange.return_value = mock_response
    
    # Test callback endpoint
    response = client.get("/slack/oauth_callback?code=test&state=xyz")
    assert response.status_code == 200
```

## Production Deployment

### Environment Variables

```bash
export SLACK_CLIENT_ID="production-client-id"
export SLACK_CLIENT_SECRET="production-client-secret"
export SLACK_SIGNING_SECRET="production-signing-secret"
export SLACK_REDIRECT_URI="https://api.your-domain.com/slack/oauth_callback"
```

### Database

Use production database (PostgreSQL, MySQL):
```python
# Update db_slack.py to use production DB connection
```

### Redis for State

Replace in-memory state store:
```python
import redis

redis_client = redis.Redis(host='localhost', port=6379)

# Store state
redis_client.setex(f"slack_oauth_state:{state}", 600, "pending")

# Verify state
if redis_client.get(f"slack_oauth_state:{state}"):
    # Valid
    redis_client.delete(f"slack_oauth_state:{state}")
```

### Monitoring

Track OAuth metrics:
```python
# Add counters
oauth_install_counter.inc()
oauth_callback_counter.labels(status="success").inc()
```

## Slack App Manifest

Use this manifest to quickly configure your Slack app:

```yaml
display_information:
  name: Safety-Eval-Mini
  description: AI-powered content safety moderation
  background_color: "#667eea"
features:
  bot_user:
    display_name: SafetyBot
    always_online: true
  slash_commands:
    - command: /safety-check
      url: https://your-domain.com/slack/events
      description: Check if text content is safe
      usage_hint: <text to check>
    - command: /safety-report
      url: https://your-domain.com/slack/events
      description: Get summary of recent safety checks
oauth_config:
  redirect_urls:
    - https://your-domain.com/slack/oauth_callback
  scopes:
    bot:
      - commands
      - chat:write
      - chat:write.public
      - app_mentions:read
settings:
  event_subscriptions:
    bot_events:
      - app_mention
  interactivity:
    is_enabled: true
  org_deploy_enabled: false
  socket_mode_enabled: false
  token_rotation_enabled: false
```

## Marketplace Listing

To list on Slack App Directory (requires paid plan per workspace):

1. Complete app manifest above
2. Add app icon (512x512 PNG)
3. Add screenshots
4. Write description and long description
5. Add privacy policy URL
6. Add support URL
7. Submit for review

## API Reference

### GET /slack/install

Redirects to Slack OAuth consent page.

**Query Params**: None

**Returns**: 307 Redirect to slack.com

### GET /slack/oauth_callback

Handles OAuth callback from Slack.

**Query Params**:
- `code`: OAuth code (required)
- `state`: CSRF state token
- `error`: Error from Slack (if denied)

**Returns**: 200 HTML success page or 400 error page

### GET /slack/add-to-slack

Renders page with "Add to Slack" button.

**Returns**: 200 HTML page with button

## Troubleshooting

### "OAuth not configured" Error

Check environment variables:
```bash
env | grep SLACK
```

Ensure all required vars are set.

### Callback 404

Verify redirect URI matches exactly in:
1. Slack app settings
2. Environment variable
3. No trailing slash

### Token Exchange Fails

Common causes:
- Code already used (can only use once)
- Code expired (10 min lifetime)
- Wrong client secret
- Network timeout

Check logs for specific error.

### Bot Not Responding

After installation:
1. Verify token stored in database
2. Check bot command handlers are registered
3. Ensure slash command URLs point to your server
4. Verify signing secret matches

## Migration from Socket Mode

**Before** (development):
```python
# Socket Mode with app token
handler = SocketModeHandler(app, app_token)
```

**After** (production OAuth):
```python
# HTTP mode with OAuth
# No app token needed
# Each workspace has own bot token from OAuth
```

## Future Enhancements

- [ ] Token encryption at rest
- [ ] Workspace management UI
- [ ] Uninstall webhook handling
- [ ] Token rotation support
- [ ] Usage analytics per workspace
- [ ] Workspace-specific settings

## Support

- Slack API docs: https://api.slack.com/docs
- OAuth guide: https://api.slack.com/authentication/oauth-v2
- App manifest reference: https://api.slack.com/reference/manifests

