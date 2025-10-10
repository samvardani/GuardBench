"""Admin endpoints for configuration management."""

from __future__ import annotations

import logging
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

from config import get_config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/config", tags=["admin", "config"])


class ConfigDumpResponse(BaseModel):
    """Configuration dump response."""
    
    config: Dict[str, Any]
    redacted: bool
    frozen: bool


@router.get("/dump", response_model=ConfigDumpResponse)
async def dump_config(
    authorization: str = Header(None),
    redact: bool = True
) -> ConfigDumpResponse:
    """Dump configuration for admin support.
    
    Requires admin authorization header.
    
    Args:
        authorization: Bearer token (must be admin)
        redact: Whether to redact sensitive values (default: True)
        
    Returns:
        ConfigDumpResponse with configuration
        
    Raises:
        HTTPException: 401 if unauthorized
    """
    # Check authorization
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    token = authorization.replace("Bearer ", "")
    
    # Get expected admin token from config
    config = get_config()
    
    # Simple token check (in production, use proper RBAC)
    # For now, we check against an admin token pattern
    import os
    admin_token = os.getenv("ADMIN_TOKEN")
    
    if not admin_token or token != admin_token:
        logger.warning(f"Unauthorized config dump attempt")
        raise HTTPException(status_code=403, detail="Forbidden: admin role required")
    
    # Dump config
    logger.info(f"Config dump requested (redact={redact})")
    
    config_dict = config.dump(redact=redact)
    
    return ConfigDumpResponse(
        config=config_dict,
        redacted=redact,
        frozen=config._frozen
    )


@router.get("/health")
async def config_health() -> Dict[str, str]:
    """Check config health (public endpoint).
    
    Returns:
        Health status
    """
    config = get_config()
    
    return {
        "status": "ok",
        "frozen": str(config._frozen),
        "log_level": config.log_level
    }


__all__ = ["router"]

