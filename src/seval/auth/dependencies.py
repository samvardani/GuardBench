"""FastAPI dependencies for OIDC authentication."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import Depends, HTTPException, Header, status
from .oidc import get_oidc_auth, UserInfo

logger = logging.getLogger(__name__)


async def get_current_user(
    authorization: Optional[str] = Header(None)
) -> Optional[UserInfo]:
    """Get current user from OIDC token (optional).
    
    Args:
        authorization: Authorization header with Bearer token
        
    Returns:
        UserInfo if token valid, None if no token or OIDC not configured
        
    Raises:
        HTTPException: 401 if token invalid
    """
    oidc = get_oidc_auth()
    
    # If OIDC not configured, return None (public access)
    if not oidc.is_configured():
        return None
    
    # If no authorization header, return None
    if not authorization:
        return None
    
    # Extract token
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = authorization[7:]  # Remove "Bearer " prefix
    
    # Verify token
    try:
        user_info = await oidc.verify_token(token)
        return user_info
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


async def require_auth(
    authorization: Optional[str] = Header(None)
) -> UserInfo:
    """Require authentication (mandatory).
    
    Args:
        authorization: Authorization header with Bearer token
        
    Returns:
        UserInfo
        
    Raises:
        HTTPException: 401 if not authenticated
    """
    oidc = get_oidc_auth()
    
    # If OIDC not configured, allow access for backward compatibility
    if not oidc.is_configured():
        # Return a default public user
        return UserInfo(
            sub="public",
            email=None,
            name="Public User",
            groups=[],
            roles=["viewer"]
        )
    
    # Get current user
    user = await get_current_user(authorization)
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


def require_role(required_role: str):
    """Dependency factory to require specific role.
    
    Args:
        required_role: Required role name
        
    Returns:
        Dependency function
    """
    async def role_checker(user: UserInfo = Depends(require_auth)) -> UserInfo:
        """Check if user has required role.
        
        Args:
            user: Authenticated user
            
        Returns:
            UserInfo
            
        Raises:
            HTTPException: 403 if user doesn't have required role
        """
        # Role hierarchy
        role_hierarchy = {
            "admin": 4,
            "developer": 3,
            "analyst": 2,
            "viewer": 1,
        }
        
        user_level = max(
            [role_hierarchy.get(role, 0) for role in user.roles],
            default=0
        )
        required_level = role_hierarchy.get(required_role, 0)
        
        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {required_role}"
            )
        
        return user
    
    return role_checker

