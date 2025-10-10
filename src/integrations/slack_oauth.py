"""Slack OAuth integration with encrypted token storage."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse

from security import get_crypto_box

logger = logging.getLogger(__name__)

try:
    import httpx
except ImportError:
    httpx = None
    logger.warning("httpx not installed - Slack OAuth unavailable")

router = APIRouter(prefix="/slack", tags=["Slack"])


class SlackOAuthClient:
    """Slack OAuth client with encrypted token storage."""
    
    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        redirect_uri: Optional[str] = None
    ):
        """Initialize Slack OAuth client.
        
        Args:
            client_id: Slack OAuth client ID
            client_secret: Slack OAuth client secret
            redirect_uri: OAuth callback URL
        """
        self.client_id = client_id or os.getenv("SLACK_CLIENT_ID", "")
        self.client_secret = client_secret or os.getenv("SLACK_CLIENT_SECRET", "")
        self.redirect_uri = redirect_uri or os.getenv("SLACK_REDIRECT_URI", "http://localhost:8001/slack/oauth_callback")
        
        self.crypto_box = get_crypto_box()
        
        if not self.client_id or not self.client_secret:
            logger.warning("Slack OAuth not configured - set SLACK_CLIENT_ID and SLACK_CLIENT_SECRET")
    
    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """Generate Slack OAuth authorization URL.
        
        Args:
            state: Optional state parameter for CSRF protection
            
        Returns:
            Authorization URL
        """
        params = {
            "client_id": self.client_id,
            "scope": "chat:write,commands",
            "redirect_uri": self.redirect_uri,
        }
        
        if state:
            params["state"] = state
        
        return f"https://slack.com/oauth/v2/authorize?{urlencode(params)}"
    
    async def exchange_code(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access token.
        
        Args:
            code: Authorization code from Slack
            
        Returns:
            OAuth response with access_token
            
        Raises:
            HTTPException: If exchange fails
        """
        if httpx is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="httpx not installed"
            )
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://slack.com/api/oauth.v2.access",
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "redirect_uri": self.redirect_uri
                }
            )
            
            data = response.json()
            
            if not data.get("ok"):
                error = data.get("error", "unknown_error")
                logger.error(f"Slack OAuth exchange failed: {error}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Slack OAuth failed: {error}"
                )
            
            return data
    
    def encrypt_token(self, access_token: str) -> str:
        """Encrypt access token for storage.
        
        Args:
            access_token: Plaintext access token
            
        Returns:
            Encrypted token
        """
        from security.redaction import redact_tokens
        
        # Redact from logs
        logger.info(f"Encrypting Slack token: {redact_tokens(access_token)}")
        
        return self.crypto_box.encrypt(access_token)
    
    def decrypt_token(self, encrypted_token: str) -> str:
        """Decrypt access token from storage.
        
        Args:
            encrypted_token: Encrypted token
            
        Returns:
            Decrypted access token
        """
        return self.crypto_box.decrypt(encrypted_token)


# Global client instance
_global_oauth_client: Optional[SlackOAuthClient] = None


def get_slack_oauth_client() -> SlackOAuthClient:
    """Get global Slack OAuth client.
    
    Returns:
        SlackOAuthClient instance
    """
    global _global_oauth_client
    
    if _global_oauth_client is None:
        _global_oauth_client = SlackOAuthClient()
    
    return _global_oauth_client


@router.get("/install")
async def slack_install() -> RedirectResponse:
    """Redirect to Slack OAuth authorization.
    
    Returns:
        Redirect to Slack authorization URL
    """
    client = get_slack_oauth_client()
    
    if not client.client_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Slack OAuth not configured"
        )
    
    # Generate random state for CSRF protection
    import secrets
    state = secrets.token_urlsafe(32)
    
    # Store state in session (simplified - would use session middleware in production)
    auth_url = client.get_authorization_url(state=state)
    
    logger.info(f"Redirecting to Slack OAuth: {auth_url[:50]}...")
    
    return RedirectResponse(url=auth_url)


@router.get("/oauth_callback")
async def slack_oauth_callback(
    code: Optional[str] = None,
    error: Optional[str] = None,
    state: Optional[str] = None
) -> HTMLResponse:
    """Handle Slack OAuth callback.
    
    Args:
        code: Authorization code
        error: Error message if authorization failed
        state: CSRF state parameter
        
    Returns:
        HTML response
    """
    if error:
        logger.error(f"Slack OAuth error: {error}")
        return HTMLResponse(
            content=f"<html><body><h1>Slack OAuth Failed</h1><p>Error: {error}</p></body></html>",
            status_code=400
        )
    
    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing authorization code"
        )
    
    client = get_slack_oauth_client()
    
    try:
        # Exchange code for token
        oauth_response = await client.exchange_code(code)
        
        # Extract data
        access_token = oauth_response.get("access_token", "")
        team_id = oauth_response.get("team", {}).get("id", "")
        team_name = oauth_response.get("team", {}).get("name", "")
        
        # Encrypt token
        encrypted_token = client.encrypt_token(access_token)
        
        # Store in database
        from db.slack_installations import store_installation
        
        store_installation(
            team_id=team_id,
            team_name=team_name,
            encrypted_access_token=encrypted_token
        )
        
        logger.info(f"Slack workspace installed: team_id={team_id}, team_name={team_name}")
        
        return HTMLResponse(
            content=f"""
            <html>
            <head>
                <style>
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        min-height: 100vh;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    }}
                    .card {{
                        background: white;
                        padding: 60px;
                        border-radius: 20px;
                        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
                        text-align: center;
                    }}
                    h1 {{ color: #333; margin-bottom: 20px; }}
                    p {{ color: #666; font-size: 18px; }}
                    .success {{ color: #28a745; font-size: 72px; }}
                </style>
            </head>
            <body>
                <div class="card">
                    <div class="success">✅</div>
                    <h1>Slack Installation Successful!</h1>
                    <p>Workspace: <strong>{team_name}</strong></p>
                    <p>You can now use the Safety-Eval-Mini bot in your Slack workspace.</p>
                </div>
            </body>
            </html>
            """
        )
    
    except Exception as e:
        logger.exception(f"Slack OAuth callback error: {e}")
        
        return HTMLResponse(
            content=f"""
            <html>
            <body>
                <h1>Slack OAuth Error</h1>
                <p>Failed to complete installation: {str(e)}</p>
                <p>Please try again or contact support.</p>
            </body>
            </html>
            """,
            status_code=500
        )


__all__ = ["router", "SlackOAuthClient", "get_slack_oauth_client"]

