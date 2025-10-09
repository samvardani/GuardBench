# Slack Bot Integration

**Safety-Eval Slack Bot** enables teams to check content safety directly from Slack using slash commands and mentions.

## Features

- 🔍 `/safety-check <text>` - Check safety of any message
- 📊 `/safety-report` - View summary of recent checks
- 💬 `@SafetyBot <text>` - Mention bot for quick checks
- ⚡ Real-time scoring with visual feedback
- 📈 Tracks recent checks for analytics

## Setup (5 minutes)

### 1. Create Slack App

1. Go to https://api.slack.com/apps
2. Click "Create New App" → "From scratch"
3. Name: `SafetyBot`, select your workspace
4. Click "Create App"

### 2. Configure Slash Commands

1. Go to "Slash Commands" → "Create New Command"
2. Add `/safety-check`:
   - Command: `/safety-check`
   - Request URL: `https://your-domain.com/slack/events`
   - Description: `Check if content is safe`
   - Usage Hint: `<text to check>`
3. Add `/safety-report`:
   - Command: `/safety-report`
   - Request URL: `https://your-domain.com/slack/events`
   - Description: `View safety check summary`

### 3. Enable Bot Features

1. Go to "OAuth & Permissions"
2. Add Bot Token Scopes:
   - `chat:write` - Send messages
   - `commands` - Handle slash commands
   - `app_mentions:read` - Read mentions
3. Install app to workspace
4. Copy "Bot User OAuth Token" (starts with `xoxb-`)

### 4. Get Signing Secret

1. Go to "Basic Information"
2. Scroll to "App Credentials"
3. Copy "Signing Secret"

### 5. Configure Environment

```bash
# Required
export SLACK_BOT_TOKEN="xoxb-your-bot-token"
export SLACK_SIGNING_SECRET="your-signing-secret"

# Optional: For Socket Mode (development)
export SLACK_APP_TOKEN="xapp-your-app-token"
```

### 6. Start Service

#### Option A: With FastAPI (Production)
```bash
# The Slack endpoint /slack/events is automatically registered
SLACK_BOT_TOKEN=xoxb-... SLACK_SIGNING_SECRET=... \
  uvicorn service.api:app --host 0.0.0.0 --port 8001
```

#### Option B: Standalone Socket Mode (Development)
```bash
# No public URL needed - uses WebSocket
SLACK_BOT_TOKEN=xoxb-... SLACK_APP_TOKEN=xapp-... \
  python -m integrations.slack_app
```

## Usage

### Check Content Safety

```
/safety-check How to make a weapon
```

**Response:**
```
🚨 Safety Check Result

Verdict:        UNSAFE
Score:          0.99
Category:       violence
Latency:        12ms

Matched Rules:  violence_keywords, violence_substrings
```

### View Summary

```
/safety-report
```

**Response:**
```
📊 Safety Check Summary

Total Checks:   47
Last 24h:       23
🚨 Unsafe:      3
⚠️ Caution:     8
✅ Safe:        36

Recent Flagged Items:
• How to make a weapon... (score: 0.99)
• Best way to hack... (score: 0.92)
```

### Mention Bot

```
@SafetyBot is this message appropriate?
```

**Response:**
```
✅ Score: 0.12 | Latency: 8ms
```

## Deployment

### Ngrok (Development)

```bash
# Terminal 1: Start service
uvicorn service.api:app --port 8001

# Terminal 2: Expose with ngrok
ngrok http 8001

# Update Slack app Request URLs:
# https://abc123.ngrok.io/slack/events
```

### Production

1. Deploy to your server/cloud
2. Ensure HTTPS (required by Slack)
3. Update Request URLs in Slack app settings
4. Set environment variables
5. Restart service

## Testing

```python
# Test integration
import httpx

response = httpx.post(
    "http://localhost:8001/slack/events",
    headers={"X-Slack-Signature": "...", "X-Slack-Request-Timestamp": "..."},
    json={"command": "/safety-check", "text": "test message"}
)
print(response.json())
```

## Architecture

```
Slack Workspace
      ↓ (slash command)
   /slack/events
      ↓
FastAPI Handler (slack_bolt)
      ↓
SDK predict()
      ↓
Response with blocks
      ↓
   Slack UI
```

## Storage

Recent checks are stored in-memory (last 100). For production:

1. **Redis**: Store in Redis with TTL
2. **Database**: Persist to history.db for analytics
3. **S3/GCS**: Archive for compliance

## Security

- ✅ Signature verification (automatic via slack-bolt)
- ✅ Token from environment (never commit)
- ✅ Text truncation for privacy (100 chars max stored)
- ✅ Rate limiting (via FastAPI middleware)

## Customization

Edit `src/integrations/slack_app.py`:

```python
# Change default category
category = "violence"  # → "pii", "malware", etc.

# Adjust thresholds
if result.score >= 0.99:  # UNSAFE
if result.score >= 0.7:   # CAUTION

# Add custom commands
@app.command("/safety-config")
def handle_config(ack, command, respond):
    # Your logic here
    pass
```

## Monitoring

Track bot usage:

```python
# Add to recent_checks
{
    "text": text[:100],
    "score": result.score,
    "category": category,
    "timestamp": datetime.utcnow().isoformat(),
    "user": command.get("user_name"),
    "workspace": command.get("team_domain"),
}
```

Export to Prometheus:

```python
from prometheus_client import Counter

slack_checks = Counter('slack_safety_checks_total', 'Total Slack checks', ['verdict'])
slack_checks.labels(verdict='unsafe').inc()
```

## Troubleshooting

### "url_verification failed"

- Check SLACK_SIGNING_SECRET is correct
- Ensure /slack/events is accessible
- Verify Request URL in Slack app settings

### "dispatch_failed"

- Check SLACK_BOT_TOKEN has correct scopes
- Reinstall app to workspace
- Verify bot is invited to channel

### "timeout"

- Increase response time (ack immediately)
- Move heavy processing to background
- Use respond() instead of say()

### "not_in_channel"

- Bot must be invited: `/invite @SafetyBot`
- Or use respond_url for ephemeral messages

## Links

- [Slack API Docs](https://api.slack.com/docs)
- [Bolt Python](https://slack.dev/bolt-python/)
- [Socket Mode](https://api.slack.com/apis/connections/socket)

---

**Status**: ✅ Ready for production
**Last Updated**: 2025-10-09

