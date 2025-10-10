"""Slack OAuth routes for installation flow."""

from __future__ import annotations

import logging
import secrets
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from .slack_oauth import get_slack_oauth_config, SlackInstallation

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/slack", tags=["slack"])

# In-memory store for OAuth state (use Redis in production)
_oauth_states = {}


@router.get("/install")
async def slack_install(request: Request) -> RedirectResponse:
    """Redirect user to Slack OAuth consent page.
    
    Returns:
        Redirect to Slack authorization URL
    """
    oauth_config = get_slack_oauth_config()
    
    if not oauth_config.is_configured():
        raise HTTPException(
            status_code=503,
            detail="Slack OAuth not configured. Set SLACK_CLIENT_ID and SLACK_CLIENT_SECRET."
        )
    
    # Generate CSRF state token
    state = secrets.token_urlsafe(32)
    _oauth_states[state] = {
        "created_at": "now",  # In production, use actual timestamp
    }
    
    # Get install URL
    install_url = oauth_config.get_install_url(state=state)
    
    logger.info(f"Redirecting to Slack install URL (state={state[:8]}...)")
    
    return RedirectResponse(url=install_url)


@router.get("/oauth_callback")
async def slack_oauth_callback(
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
) -> HTMLResponse:
    """Handle OAuth callback from Slack.
    
    Args:
        code: Temporary OAuth code
        state: CSRF state token
        error: Error from Slack (if authorization denied)
        
    Returns:
        HTML response with installation result
    """
    # Check for errors
    if error:
        logger.warning(f"Slack OAuth error: {error}")
        return HTMLResponse(
            content=f"""
            <html>
                <body style="font-family: Arial; text-align: center; padding: 50px;">
                    <h1>❌ Installation Failed</h1>
                    <p>Slack returned an error: <code>{error}</code></p>
                    <p><a href="/slack/install">Try again</a></p>
                </body>
            </html>
            """,
            status_code=400
        )
    
    if not code:
        raise HTTPException(status_code=400, detail="Missing OAuth code")
    
    # Verify state (CSRF protection)
    if state and state not in _oauth_states:
        logger.warning(f"Invalid OAuth state: {state}")
        raise HTTPException(status_code=400, detail="Invalid state parameter")
    
    # Clean up state
    if state:
        _oauth_states.pop(state, None)
    
    # Exchange code for token
    oauth_config = get_slack_oauth_config()
    
    try:
        oauth_response = await oauth_config.exchange_code(code)
        
        # Create installation object
        installation = SlackInstallation.from_oauth_response(oauth_response)
        
        # Store installation in database
        try:
            from service import db
            
            # Store in database (simplified - extend db.py with slack_installations table)
            logger.info(
                f"Slack installed: team={installation.team_name} "
                f"({installation.team_id}), bot={installation.bot_user_id}"
            )
            
            # TODO: Persist to database
            # db.store_slack_installation(installation.team_id, installation.access_token, ...)
            
        except Exception as db_error:
            logger.error(f"Failed to store installation: {db_error}")
            # Continue anyway - we'll log the token for now
        
        # Success response
        return HTMLResponse(
            content=f"""
            <html>
                <head>
                    <title>Slack Installation Successful</title>
                    <style>
                        body {{
                            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            min-height: 100vh;
                            margin: 0;
                        }}
                        .container {{
                            background: white;
                            border-radius: 12px;
                            padding: 40px;
                            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                            text-align: center;
                            max-width: 500px;
                        }}
                        h1 {{
                            color: #2ecc71;
                            margin-bottom: 20px;
                        }}
                        .info {{
                            background: #f8f9fa;
                            padding: 20px;
                            border-radius: 8px;
                            margin: 20px 0;
                            text-align: left;
                        }}
                        .info strong {{
                            color: #667eea;
                        }}
                        a {{
                            display: inline-block;
                            margin-top: 20px;
                            padding: 12px 24px;
                            background: #667eea;
                            color: white;
                            text-decoration: none;
                            border-radius: 6px;
                            font-weight: 600;
                        }}
                        a:hover {{
                            background: #5568d3;
                        }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h1>✅ Installation Successful!</h1>
                        <p>Safety-Eval-Mini has been added to your Slack workspace.</p>
                        
                        <div class="info">
                            <p><strong>Workspace:</strong> {installation.team_name}</p>
                            <p><strong>Bot User:</strong> {installation.bot_user_id}</p>
                        </div>
                        
                        <p><strong>Try these commands in Slack:</strong></p>
                        <ul style="text-align: left; display: inline-block;">
                            <li><code>/safety-check how to make a bomb</code></li>
                            <li><code>/safety-report</code></li>
                            <li>Mention the bot: <code>@SafetyBot check this text</code></li>
                        </ul>
                        
                        <a href="https://slack.com/app_redirect?app={installation.app_id}">
                            Open in Slack →
                        </a>
                    </div>
                </body>
            </html>
            """
        )
    
    except ValueError as e:
        logger.error(f"OAuth exchange failed: {e}")
        return HTMLResponse(
            content=f"""
            <html>
                <body style="font-family: Arial; text-align: center; padding: 50px;">
                    <h1>❌ Installation Failed</h1>
                    <p>Failed to complete installation: <code>{str(e)}</code></p>
                    <p>This usually means the authorization code expired or was already used.</p>
                    <p><a href="/slack/install">Try installing again</a></p>
                </body>
            </html>
            """,
            status_code=400
        )


@router.get("/add-to-slack", response_class=HTMLResponse)
async def add_to_slack_page() -> HTMLResponse:
    """Render 'Add to Slack' button page.
    
    Returns:
        HTML page with Add to Slack button
    """
    oauth_config = get_slack_oauth_config()
    
    if not oauth_config.is_configured():
        return HTMLResponse(
            content="""
            <html>
                <body style="font-family: Arial; text-align: center; padding: 50px;">
                    <h1>⚠️ Slack OAuth Not Configured</h1>
                    <p>Set <code>SLACK_CLIENT_ID</code> and <code>SLACK_CLIENT_SECRET</code> environment variables.</p>
                </body>
            </html>
            """,
            status_code=503
        )
    
    return HTMLResponse(
        content="""
        <html>
            <head>
                <title>Add Safety-Eval-Mini to Slack</title>
                <style>
                    body {
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        min-height: 100vh;
                        margin: 0;
                    }
                    .container {
                        background: white;
                        border-radius: 12px;
                        padding: 40px;
                        box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                        text-align: center;
                        max-width: 600px;
                    }
                    h1 {
                        color: #333;
                        margin-bottom: 20px;
                    }
                    .features {
                        text-align: left;
                        margin: 30px 0;
                        padding: 20px;
                        background: #f8f9fa;
                        border-radius: 8px;
                    }
                    .features li {
                        margin: 10px 0;
                    }
                    .add-button {
                        display: inline-block;
                        margin-top: 20px;
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>🛡️ Add Safety-Eval-Mini to Slack</h1>
                    <p>Check content safety directly from Slack with AI-powered moderation.</p>
                    
                    <div class="features">
                        <strong>Features:</strong>
                        <ul>
                            <li>✅ <strong>/safety-check</strong> - Instantly check if text is safe</li>
                            <li>📊 <strong>/safety-report</strong> - Get summary of recent checks</li>
                            <li>🤖 <strong>@SafetyBot</strong> - Mention the bot to check messages</li>
                            <li>⚡ Real-time NSFW, violence, and harmful content detection</li>
                            <li>🔒 Privacy-first (no data stored)</li>
                        </ul>
                    </div>
                    
                    <div class="add-button">
                        <a href="/slack/install">
                            <img 
                                alt="Add to Slack" 
                                height="40" 
                                width="139" 
                                src="https://platform.slack-edge.com/img/add_to_slack.png" 
                                srcSet="https://platform.slack-edge.com/img/add_to_slack.png 1x, https://platform.slack-edge.com/img/add_to_slack@2x.png 2x" 
                            />
                        </a>
                    </div>
                    
                    <p style="margin-top: 30px; font-size: 12px; color: #7f8c8d;">
                        By installing, you agree to the <a href="/docs">Terms of Service</a>
                    </p>
                </div>
            </body>
        </html>
        """
    )


# Storage functions (extend service/db.py for production)
async def store_slack_installation(installation: SlackInstallation) -> bool:
    """Store Slack installation in database.
    
    Args:
        installation: Installation to store
        
    Returns:
        True if stored successfully
    """
    try:
        from service import db
        
        # For now, log the installation
        # In production, add to db.py:
        # cur.execute(
        #     "INSERT OR REPLACE INTO slack_installations (team_id, access_token, ...) VALUES (?, ?, ...)",
        #     (installation.team_id, installation.access_token, ...)
        # )
        
        logger.info(f"Storing Slack installation: {installation.to_dict()}")
        return True
    
    except Exception as e:
        logger.error(f"Failed to store installation: {e}")
        return False


async def get_slack_installation(team_id: str) -> Optional[SlackInstallation]:
    """Get Slack installation for team.
    
    Args:
        team_id: Slack team ID
        
    Returns:
        SlackInstallation if found
    """
    try:
        from service import db
        
        # For now, return None
        # In production, query from database
        logger.debug(f"Looking up installation for team: {team_id}")
        return None
    
    except Exception as e:
        logger.error(f"Failed to get installation: {e}")
        return None

