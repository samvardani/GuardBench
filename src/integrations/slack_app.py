"""
Slack Bot Integration for Safety-Eval

Commands:
  /safety-check <text> - Check safety of a message
  /safety-report - Get summary of recent checks

Setup:
  1. Create Slack app at api.slack.com/apps
  2. Add slash commands: /safety-check, /safety-report
  3. Enable Socket Mode or set Request URL to your server/slack/events
  4. Set env vars: SLACK_BOT_TOKEN, SLACK_SIGNING_SECRET
  5. Install app to workspace

Usage:
  # Run standalone
  SLACK_BOT_TOKEN=xoxb-... SLACK_SIGNING_SECRET=... python -m integrations.slack_app
  
  # Or integrate with FastAPI (see service/api.py)
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

try:
    from slack_bolt import App
    from slack_bolt.adapter.fastapi import SlackRequestHandler
    SLACK_AVAILABLE = True
except ImportError:
    SLACK_AVAILABLE = False
    App = None  # type: ignore
    SlackRequestHandler = None  # type: ignore

from seval import sdk

# In-memory store for recent checks (use Redis/DB in production)
recent_checks: List[Dict] = []
MAX_RECENT = 100

logger = logging.getLogger(__name__)


def create_slack_app() -> Optional[App]:
    """Create and configure Slack app."""
    if not SLACK_AVAILABLE:
        logger.warning("slack-bolt not installed. Run: pip install slack-bolt")
        return None
    
    bot_token = os.getenv("SLACK_BOT_TOKEN")
    signing_secret = os.getenv("SLACK_SIGNING_SECRET")
    
    if not bot_token or not signing_secret:
        logger.warning("SLACK_BOT_TOKEN or SLACK_SIGNING_SECRET not set. Slack bot disabled.")
        return None
    
    app = App(
        token=bot_token,
        signing_secret=signing_secret,
    )
    
    @app.command("/safety-check")
    def handle_safety_check(ack, command, respond):
        """Handle /safety-check <text> command."""
        ack()  # Acknowledge immediately
        
        text = command.get("text", "").strip()
        if not text:
            respond("Usage: `/safety-check <text to check>`")
            return
        
        # Default category and language
        category = "violence"  # Could parse or make configurable
        language = "en"
        
        try:
            result = sdk.predict(text, category, language, guard="candidate")
            
            # Store for /safety-report
            recent_checks.append({
                "text": text[:100],  # Truncate for privacy
                "score": result.score,
                "category": category,
                "timestamp": datetime.utcnow().isoformat(),
                "user": command.get("user_name", "unknown"),
            })
            if len(recent_checks) > MAX_RECENT:
                recent_checks.pop(0)
            
            # Format response
            if result.score >= 0.99:
                emoji = "🚨"
                verdict = "UNSAFE"
            elif result.score >= 0.7:
                emoji = "⚠️"
                verdict = "CAUTION"
            else:
                emoji = "✅"
                verdict = "SAFE"
            
            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"{emoji} *Safety Check Result*"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Verdict:*\n{verdict}"},
                        {"type": "mrkdwn", "text": f"*Score:*\n{result.score:.2f}"},
                        {"type": "mrkdwn", "text": f"*Category:*\n{category}"},
                        {"type": "mrkdwn", "text": f"*Latency:*\n{result.latency_ms}ms"},
                    ]
                },
            ]
            
            if result.slices:
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Matched Rules:*\n{', '.join(result.slices)}"
                    }
                })
            
            respond(blocks=blocks, response_type="in_channel")
            
        except Exception as e:
            logger.error(f"Safety check failed: {e}")
            respond(f"❌ Error: {str(e)}")
    
    @app.command("/safety-report")
    def handle_safety_report(ack, command, respond):
        """Handle /safety-report command - show summary."""
        ack()
        
        if not recent_checks:
            respond("No recent safety checks found.")
            return
        
        # Calculate stats
        total = len(recent_checks)
        unsafe_count = sum(1 for c in recent_checks if c["score"] >= 0.99)
        caution_count = sum(1 for c in recent_checks if 0.7 <= c["score"] < 0.99)
        safe_count = total - unsafe_count - caution_count
        
        # Last 24h
        day_ago = datetime.utcnow() - timedelta(days=1)
        recent_24h = [
            c for c in recent_checks
            if datetime.fromisoformat(c["timestamp"]) > day_ago
        ]
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "📊 Safety Check Summary"
                }
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Total Checks:*\n{total}"},
                    {"type": "mrkdwn", "text": f"*Last 24h:*\n{len(recent_24h)}"},
                    {"type": "mrkdwn", "text": f"*🚨 Unsafe:*\n{unsafe_count}"},
                    {"type": "mrkdwn", "text": f"*⚠️ Caution:*\n{caution_count}"},
                    {"type": "mrkdwn", "text": f"*✅ Safe:*\n{safe_count}"},
                ]
            },
        ]
        
        # Recent flagged items
        flagged = [c for c in reversed(recent_checks[-10:]) if c["score"] >= 0.7]
        if flagged:
            items_text = "\n".join([
                f"• {c['text'][:50]}... (score: {c['score']:.2f})"
                for c in flagged[:5]
            ])
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Recent Flagged Items:*\n{items_text}"
                }
            })
        
        respond(blocks=blocks)
    
    @app.event("app_mention")
    def handle_mention(event, say):
        """Handle @SafetyBot mentions."""
        text = event.get("text", "")
        # Remove bot mention
        clean_text = " ".join([w for w in text.split() if not w.startswith("<@")])
        
        if clean_text.strip():
            result = sdk.predict(clean_text, "violence", "en", guard="candidate")
            emoji = "🚨" if result.score >= 0.99 else "⚠️" if result.score >= 0.7 else "✅"
            say(f"{emoji} Score: {result.score:.2f} | Latency: {result.latency_ms}ms")
        else:
            say("👋 Hi! Use `/safety-check <text>` to check content safety.")
    
    logger.info("Slack app configured successfully")
    return app


def get_slack_handler(app: Optional[App] = None) -> Optional[SlackRequestHandler]:
    """Get FastAPI request handler for Slack events."""
    if not SLACK_AVAILABLE:
        return None
    
    if app is None:
        app = create_slack_app()
    
    if app is None:
        return None
    
    return SlackRequestHandler(app)


def run_slack_app():
    """Run Slack app in Socket Mode (for development)."""
    app = create_slack_app()
    if not app:
        print("❌ Slack app not configured. Set SLACK_BOT_TOKEN and SLACK_SIGNING_SECRET.")
        return
    
    from slack_bolt.adapter.socket_mode import SocketModeHandler
    
    app_token = os.getenv("SLACK_APP_TOKEN")
    if not app_token:
        print("❌ SLACK_APP_TOKEN not set. Required for Socket Mode.")
        print("   Get it from: https://api.slack.com/apps → Basic Information → App-Level Tokens")
        return
    
    handler = SocketModeHandler(app, app_token)
    print("⚡️ Slack bot is running in Socket Mode!")
    handler.start()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_slack_app()

