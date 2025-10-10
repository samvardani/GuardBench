"""Middleware for route protection."""

from __future__ import annotations

import logging
from typing import Callable

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from .oidc import get_oidc_auth

logger = logging.getLogger(__name__)


class OIDCMiddleware(BaseHTTPMiddleware):
    """Middleware to protect routes with OIDC authentication."""
    
    # Routes that require authentication
    PROTECTED_PREFIXES = [
        "/ui/",  # All UI routes
    ]
    
    # POST routes that require authentication
    PROTECTED_METHODS = {
        "POST": ["/score", "/score-image", "/batch-score"]
    }
    
    # Public routes (always allowed)
    PUBLIC_ROUTES = [
        "/healthz",
        "/metrics",
        "/docs",
        "/openapi.json",
        "/redoc",
    ]
    
    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """Dispatch request with OIDC check.
        
        Args:
            request: FastAPI request
            call_next: Next middleware/route
            
        Returns:
            Response
        """
        oidc = get_oidc_auth()
        
        # Skip if OIDC not configured (backward compatibility)
        if not oidc.is_configured():
            return await call_next(request)
        
        # Check if route is public
        if self._is_public_route(request):
            return await call_next(request)
        
        # Check if route requires auth
        if not self._requires_auth(request):
            return await call_next(request)
        
        # Verify authentication
        auth_header = request.headers.get("authorization")
        
        if not auth_header:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        token = auth_header[7:]
        
        try:
            user_info = await oidc.verify_token(token)
            
            # Add user info to request state
            request.state.user = user_info
            
            logger.debug(f"Authenticated user: {user_info.sub} ({user_info.email})")
            
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(e),
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        response = await call_next(request)
        return response
    
    def _is_public_route(self, request: Request) -> bool:
        """Check if route is public.
        
        Args:
            request: FastAPI request
            
        Returns:
            True if route is public
        """
        path = request.url.path
        
        for public_route in self.PUBLIC_ROUTES:
            if path == public_route or path.startswith(public_route):
                return True
        
        return False
    
    def _requires_auth(self, request: Request) -> bool:
        """Check if route requires authentication.
        
        Args:
            request: FastAPI request
            
        Returns:
            True if auth required
        """
        path = request.url.path
        method = request.method
        
        # Check protected prefixes
        for prefix in self.PROTECTED_PREFIXES:
            if path.startswith(prefix):
                return True
        
        # Check protected methods
        if method in self.PROTECTED_METHODS:
            for protected_path in self.PROTECTED_METHODS[method]:
                if path == protected_path or path.startswith(protected_path):
                    return True
        
        return False

