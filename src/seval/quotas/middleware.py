"""Middleware for usage tracking and quota enforcement."""

from __future__ import annotations

import logging
from typing import Callable, Optional

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from .enforcer import get_quota_enforcer, QuotaExceeded

logger = logging.getLogger(__name__)


class UsageTrackingMiddleware(BaseHTTPMiddleware):
    """Middleware to track and enforce usage quotas."""
    
    # Endpoints that count toward usage
    TRACKED_ENDPOINTS = [
        "/score",
        "/score-image",
        "/batch-score",
    ]
    
    # Endpoints exempt from tracking
    EXEMPT_ENDPOINTS = [
        "/healthz",
        "/metrics",
        "/docs",
        "/openapi.json",
    ]
    
    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """Dispatch with usage tracking.
        
        Args:
            request: FastAPI request
            call_next: Next middleware/route
            
        Returns:
            Response with usage headers
        """
        # Check if endpoint should be tracked
        if not self._should_track(request):
            return await call_next(request)
        
        # Get tenant ID
        tenant_id = self._get_tenant_id(request)
        
        if not tenant_id:
            # No tenant, skip tracking
            return await call_next(request)
        
        # Get enforcer
        enforcer = get_quota_enforcer()
        
        # Track usage
        try:
            usage_info = enforcer.increment_usage(tenant_id, amount=1, check_quota=True)
            
            # Process request
            response = await call_next(request)
            
            # Add usage headers
            response.headers["X-Usage-Count"] = str(usage_info.usage_count)
            response.headers["X-Usage-Period"] = usage_info.period
            
            if usage_info.monthly_quota:
                response.headers["X-Usage-Limit"] = str(usage_info.monthly_quota)
                response.headers["X-Usage-Remaining"] = str(
                    max(0, usage_info.monthly_quota - usage_info.usage_count)
                )
            
            # Add warning header if approaching limit
            if usage_info.quota_warning and not usage_info.quota_exceeded:
                response.headers["X-Usage-Warning"] = (
                    f"Approaching quota limit ({usage_info.usage_count}/{usage_info.monthly_quota})"
                )
            
            # Add exceeded header if over (soft limit)
            if usage_info.quota_exceeded:
                response.headers["X-Usage-Exceeded"] = (
                    f"Quota exceeded ({usage_info.usage_count}/{usage_info.monthly_quota}). "
                    f"Upgrade to continue."
                )
            
            return response
        
        except QuotaExceeded as e:
            # Hard limit - block request
            logger.warning(f"Blocking request: {e}")
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "error": "quota_exceeded",
                    "message": f"Monthly quota of {e.limit} evaluations exceeded",
                    "usage": e.usage,
                    "limit": e.limit,
                    "period": e.period,
                    "action": "Upgrade your plan to continue using the API",
                },
                headers={
                    "X-Usage-Count": str(e.usage),
                    "X-Usage-Limit": str(e.limit),
                    "X-Usage-Period": e.period,
                }
            )
        
        except Exception as e:
            logger.error(f"Usage tracking error: {e}")
            # Don't block on tracking errors
            return await call_next(request)
    
    def _should_track(self, request: Request) -> bool:
        """Check if endpoint should be tracked.
        
        Args:
            request: FastAPI request
            
        Returns:
            True if should track usage
        """
        path = request.url.path
        
        # Skip exempt endpoints
        for exempt in self.EXEMPT_ENDPOINTS:
            if path == exempt or path.startswith(exempt):
                return False
        
        # Only track specific endpoints
        for tracked in self.TRACKED_ENDPOINTS:
            if path == tracked or path.startswith(tracked):
                return True
        
        return False
    
    def _get_tenant_id(self, request: Request) -> Optional[str]:
        """Get tenant ID from request.
        
        Args:
            request: FastAPI request
            
        Returns:
            Tenant ID or None
        """
        # Try to get from request state (set by auth middleware)
        if hasattr(request.state, "user"):
            user = request.state.user
            if hasattr(user, "tenant_id"):
                return user.tenant_id
        
        # Default tenant for public access
        return "default"

