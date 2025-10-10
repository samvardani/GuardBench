"""Analytics API routes for usage statistics."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from .usage_stats import get_usage_tracker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/usage")
async def get_usage_stats(
    tenant_id: str = "public",  # From auth context in production
    days: int = Query(default=30, ge=1, le=365, description="Number of days"),
    start_date: Optional[str] = Query(default=None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(default=None, description="End date (YYYY-MM-DD)")
) -> Dict[str, Any]:
    """Get usage statistics for tenant.
    
    Args:
        tenant_id: Tenant ID
        days: Number of days to retrieve
        start_date: Optional start date
        end_date: Optional end date
        
    Returns:
        Usage statistics
    """
    try:
        tracker = get_usage_tracker()
        
        # Get daily stats
        daily_stats = tracker.get_daily_stats(
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date,
            limit=days
        )
        
        # Get summary
        summary = tracker.get_summary(tenant_id=tenant_id, days=days)
        
        return summary
    
    except Exception as e:
        logger.exception(f"Error fetching usage stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch usage stats: {str(e)}"
        )


@router.get("/usage/current-month")
async def get_current_month_usage(
    tenant_id: str = "public"
) -> Dict[str, Any]:
    """Get current month usage total.
    
    Args:
        tenant_id: Tenant ID
        
    Returns:
        Current month usage
    """
    try:
        tracker = get_usage_tracker()
        total = tracker.get_current_month_total(tenant_id)
        
        return {
            "tenant_id": tenant_id,
            "current_month_requests": total,
        }
    
    except Exception as e:
        logger.exception(f"Error fetching current month usage: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch current month usage: {str(e)}"
        )


@router.get("/usage/dashboard", response_class=HTMLResponse)
async def usage_dashboard() -> HTMLResponse:
    """Serve the usage dashboard UI.
    
    Returns:
        HTML usage dashboard
    """
    template_path = Path(__file__).resolve().parents[2] / "templates" / "analytics" / "usage.html"
    
    if not template_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usage dashboard template not found"
        )
    
    return HTMLResponse(template_path.read_text())


__all__ = ["router"]

