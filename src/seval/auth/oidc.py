"""OIDC authentication provider."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class UserInfo:
    """User information from OIDC token."""
    
    sub: str  # Subject (user ID)
    email: Optional[str] = None
    name: Optional[str] = None
    groups: List[str] = None  # type: ignore
    roles: List[str] = None  # type: ignore
    
    def __post_init__(self):
        if self.groups is None:
            self.groups = []
        if self.roles is None:
            self.roles = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "sub": self.sub,
            "email": self.email,
            "name": self.name,
            "groups": self.groups,
            "roles": self.roles,
        }


class OIDCAuth:
    """OIDC authentication handler."""
    
    # Default role mapping from OIDC groups to RBAC roles
    DEFAULT_ROLE_MAPPING = {
        "admin": "admin",
        "admins": "admin",
        "safety-admin": "admin",
        "developer": "developer",
        "developers": "developer",
        "viewer": "viewer",
        "viewers": "viewer",
        "analyst": "analyst",
        "analysts": "analyst",
    }
    
    def __init__(
        self,
        issuer: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        audience: Optional[str] = None,
        role_mapping: Optional[Dict[str, str]] = None,
    ):
        """Initialize OIDC auth.
        
        Args:
            issuer: OIDC issuer URL
            client_id: OIDC client ID
            client_secret: OIDC client secret
            audience: OIDC audience
            role_mapping: Custom group -> role mapping
        """
        self.issuer = issuer or os.getenv("OIDC_ISSUER")
        self.client_id = client_id or os.getenv("OIDC_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("OIDC_CLIENT_SECRET")
        self.audience = audience or os.getenv("OIDC_AUDIENCE")
        self.role_mapping = role_mapping or self.DEFAULT_ROLE_MAPPING
        
        self._jwks_client = None
        self._signing_key = None
        
        if self.is_configured():
            logger.info(f"OIDC configured: issuer={self.issuer}")
        else:
            logger.warning("OIDC not configured (missing env vars)")
    
    def is_configured(self) -> bool:
        """Check if OIDC is properly configured.
        
        Returns:
            True if all required config is present
        """
        return bool(
            self.issuer and
            self.client_id and
            self.client_secret
        )
    
    def _get_jwks_client(self) -> Any:
        """Get or create JWKS client.
        
        Returns:
            JWKS client for token verification
        """
        if self._jwks_client is None:
            try:
                from authlib.integrations.httpx_client import AsyncOAuth2Client
                from authlib.jose import JsonWebKey
                
                # Create JWKS client
                jwks_uri = f"{self.issuer}/.well-known/jwks.json"
                self._jwks_client = jwks_uri
                logger.info(f"JWKS client initialized: {jwks_uri}")
            except ImportError:
                logger.error("authlib not installed. Install with: pip install authlib")
                raise
        
        return self._jwks_client
    
    async def verify_token(self, token: str) -> UserInfo:
        """Verify OIDC token and extract user info.
        
        Args:
            token: JWT token from Authorization header
            
        Returns:
            UserInfo with user details
            
        Raises:
            ValueError: If token is invalid
        """
        if not self.is_configured():
            raise ValueError("OIDC not configured")
        
        try:
            from authlib.jose import jwt
            from authlib.jose.errors import JoseError
            import httpx
            
            # Get JWKS
            jwks_uri = f"{self.issuer}/.well-known/jwks.json"
            async with httpx.AsyncClient() as client:
                response = await client.get(jwks_uri, timeout=5.0)
                response.raise_for_status()
                jwks = response.json()
            
            # Verify token
            claims = jwt.decode(
                token,
                jwks,
                claims_options={
                    "iss": {"essential": True, "value": self.issuer},
                    "aud": {"essential": True, "value": self.audience or self.client_id},
                }
            )
            
            # Extract user info
            sub = claims.get("sub")
            if not sub:
                raise ValueError("Token missing 'sub' claim")
            
            email = claims.get("email")
            name = claims.get("name") or claims.get("preferred_username")
            groups = claims.get("groups", [])
            
            # Map groups to roles
            roles = self._map_groups_to_roles(groups)
            
            return UserInfo(
                sub=sub,
                email=email,
                name=name,
                groups=groups,
                roles=roles,
            )
        
        except JoseError as e:
            logger.warning(f"Token verification failed: {e}")
            raise ValueError(f"Invalid token: {e}")
        except Exception as e:
            logger.error(f"OIDC verification error: {e}")
            raise ValueError(f"Token verification failed: {e}")
    
    def _map_groups_to_roles(self, groups: List[str]) -> List[str]:
        """Map OIDC groups to RBAC roles.
        
        Args:
            groups: List of group names from OIDC token
            
        Returns:
            List of mapped roles
        """
        roles = []
        
        for group in groups:
            # Normalize group name
            group_lower = group.lower().strip()
            
            # Check mapping
            if group_lower in self.role_mapping:
                role = self.role_mapping[group_lower]
                if role not in roles:
                    roles.append(role)
        
        # Default role if no mapping found
        if not roles:
            roles.append("viewer")
        
        return roles
    
    def get_primary_role(self, roles: List[str]) -> str:
        """Get primary role (highest privilege).
        
        Args:
            roles: List of roles
            
        Returns:
            Primary role
        """
        # Role hierarchy (highest to lowest)
        hierarchy = ["admin", "developer", "analyst", "viewer"]
        
        for role in hierarchy:
            if role in roles:
                return role
        
        return "viewer"


# Global OIDC auth instance
_global_oidc_auth: Optional[OIDCAuth] = None


def get_oidc_auth() -> OIDCAuth:
    """Get or create global OIDC auth instance.
    
    Returns:
        Global OIDCAuth instance
    """
    global _global_oidc_auth
    if _global_oidc_auth is None:
        _global_oidc_auth = OIDCAuth()
    return _global_oidc_auth

