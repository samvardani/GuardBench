"""Slack OAuth installation flow."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional
from urllib.parse import urlencode

logger = logging.getLogger(__name__)


class SlackOAuthConfig:
    """Slack OAuth configuration."""
    
    # Required scopes for the bot
    DEFAULT_SCOPES = [
        "commands",           # Slash commands
        "chat:write",         # Send messages
        "chat:write.public",  # Send to public channels
        "app_mentions:read",  # Read mentions
    ]
    
    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        scopes: Optional[list[str]] = None,
        redirect_uri: Optional[str] = None,
    ):
        """Initialize OAuth config.
        
        Args:
            client_id: Slack app client ID
            client_secret: Slack app client secret
            scopes: OAuth scopes
            redirect_uri: Callback URL
        """
        self.client_id = client_id or os.getenv("SLACK_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("SLACK_CLIENT_SECRET")
        self.scopes = scopes or self.DEFAULT_SCOPES
        self.redirect_uri = redirect_uri or os.getenv(
            "SLACK_REDIRECT_URI",
            "http://localhost:8001/slack/oauth_callback"
        )
        
        if self.is_configured():
            logger.info(f"Slack OAuth configured: client_id={self.client_id[:8]}...")
        else:
            logger.warning("Slack OAuth not configured (missing client_id/secret)")
    
    def is_configured(self) -> bool:
        """Check if OAuth is configured.
        
        Returns:
            True if client_id and secret are set
        """
        return bool(self.client_id and self.client_secret)
    
    def get_install_url(self, state: Optional[str] = None) -> str:
        """Get Slack OAuth install URL.
        
        Args:
            state: Optional state parameter for CSRF protection
            
        Returns:
            OAuth authorization URL
        """
        if not self.is_configured():
            raise ValueError("Slack OAuth not configured")
        
        params = {
            "client_id": self.client_id,
            "scope": ",".join(self.scopes),
            "redirect_uri": self.redirect_uri,
        }
        
        if state:
            params["state"] = state
        
        base_url = "https://slack.com/oauth/v2/authorize"
        return f"{base_url}?{urlencode(params)}"
    
    async def exchange_code(self, code: str) -> Dict[str, Any]:
        """Exchange OAuth code for access token.
        
        Args:
            code: Temporary OAuth code from Slack
            
        Returns:
            OAuth response with access token
            
        Raises:
            ValueError: If exchange fails
        """
        if not self.is_configured():
            raise ValueError("Slack OAuth not configured")
        
        try:
            import httpx
            
            url = "https://slack.com/api/oauth.v2.access"
            data = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code": code,
                "redirect_uri": self.redirect_uri,
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, data=data, timeout=10.0)
                response.raise_for_status()
                
                result = response.json()
                
                if not result.get("ok"):
                    error = result.get("error", "unknown_error")
                    raise ValueError(f"Slack OAuth failed: {error}")
                
                return result
        
        except Exception as e:
            logger.error(f"OAuth code exchange failed: {e}")
            raise ValueError(f"Failed to exchange code: {e}")


class SlackInstallation:
    """Represents a Slack workspace installation."""
    
    def __init__(
        self,
        team_id: str,
        team_name: str,
        access_token: str,
        bot_user_id: str,
        scope: str,
        app_id: str,
    ):
        """Initialize installation.
        
        Args:
            team_id: Slack team/workspace ID
            team_name: Workspace name
            access_token: OAuth access token
            bot_user_id: Bot user ID
            scope: Granted scopes
            app_id: Slack app ID
        """
        self.team_id = team_id
        self.team_name = team_name
        self.access_token = access_token
        self.bot_user_id = bot_user_id
        self.scope = scope
        self.app_id = app_id
    
    @classmethod
    def from_oauth_response(cls, oauth_data: Dict[str, Any]) -> "SlackInstallation":
        """Create installation from OAuth response.
        
        Args:
            oauth_data: OAuth API response
            
        Returns:
            SlackInstallation instance
        """
        team = oauth_data.get("team", {})
        authed_user = oauth_data.get("authed_user", {})
        
        return cls(
            team_id=team.get("id", ""),
            team_name=team.get("name", ""),
            access_token=oauth_data.get("access_token", ""),
            bot_user_id=authed_user.get("id", ""),
            scope=oauth_data.get("scope", ""),
            app_id=oauth_data.get("app_id", ""),
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (for storage).
        
        Returns:
            Dictionary representation (without sensitive data for logs)
        """
        return {
            "team_id": self.team_id,
            "team_name": self.team_name,
            "bot_user_id": self.bot_user_id,
            "scope": self.scope,
            "app_id": self.app_id,
            # Note: access_token not included in to_dict for security
        }


# Global OAuth config
_global_oauth_config: Optional[SlackOAuthConfig] = None


def get_slack_oauth_config() -> SlackOAuthConfig:
    """Get or create global Slack OAuth config.
    
    Returns:
        Global SlackOAuthConfig instance
    """
    global _global_oauth_config
    if _global_oauth_config is None:
        _global_oauth_config = SlackOAuthConfig()
    return _global_oauth_config

