"""Secure metrics endpoint with authentication."""

from __future__ import annotations

import logging
from fastapi import APIRouter, Depends, Request
from fastapi.responses import PlainTextResponse

from .auth import verify_metrics_access, get_metrics_config

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Monitoring"])


async def check_metrics_access(request: Request) -> None:
    """Dependency to verify metrics access.
    
    Args:
        request: FastAPI request
        
    Raises:
        HTTPException: If access denied
    """
    verify_metrics_access(request)


@router.get("/metrics", response_class=PlainTextResponse)
async def get_metrics(
    request: Request,
    _auth: None = Depends(check_metrics_access)
) -> str:
    """Get Prometheus metrics (secured).
    
    Authentication modes:
    - public: No authentication required
    - token: Requires Authorization: Bearer <METRICS_TOKEN>
    - ip_allowlist: Requires IP in METRICS_IP_ALLOWLIST
    
    Args:
        request: FastAPI request
        _auth: Authentication dependency
        
    Returns:
        Prometheus metrics in text format
    """
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    
    config = get_metrics_config()
    logger.info(f"Metrics accessed (mode={config.auth_mode.value})")
    
    # Generate Prometheus metrics
    metrics = generate_latest()
    
    return PlainTextResponse(
        content=metrics.decode("utf-8"),
        media_type=CONTENT_TYPE_LATEST
    )


__all__ = ["router"]

