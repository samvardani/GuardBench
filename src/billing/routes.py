"""Billing API routes - uses unified pricing."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, status, Response
from fastapi.responses import HTMLResponse

from .calculator import get_billing_calculator
from .pricing import get_pricing_config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["Billing"])


@router.get("/cost")
async def get_current_cost(
    response: Response,
    tenant_id: str = "public"  # From auth context in production
) -> Dict[str, Any]:
    """Get current month cost for tenant.
    
    Uses unified compute_cost() - single source of truth.
    
    Args:
        response: FastAPI response (for headers)
        tenant_id: Tenant ID
        
    Returns:
        Cost breakdown
    """
    try:
        calculator = get_billing_calculator()
        pricing_config = get_pricing_config()
        
        # Calculate cost using unified function
        cost_result = calculator.calculate_cost(tenant_id)
        
        # Add billing headers for consistency
        tier = calculator.get_tier(tenant_id)
        tier_config = pricing_config.get_tier_config(tier)
        
        response.headers["X-Billing-Plan"] = tier.value
        response.headers["X-Billable-Usage"] = str(cost_result.billable_usage)
        response.headers["X-Total-Cost"] = f"${cost_result.total_cost:.2f}"
        response.headers["X-Free-Tier-Limit"] = str(tier_config["free_tier_limit"])
        
        # Return full breakdown
        result = cost_result.to_dict()
        result["tenant_id"] = tenant_id
        result["current_month"] = calculator.get_usage(tenant_id, month=None)  # Dummy for compatibility
        result["free_tier_limit"] = tier_config["free_tier_limit"]
        
        return result
    
    except Exception as e:
        logger.exception(f"Error calculating cost: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate cost: {str(e)}"
        )


@router.get("/usage")
async def get_current_usage(
    tenant_id: str = "public"
) -> Dict[str, Any]:
    """Get current month usage for tenant.
    
    Args:
        tenant_id: Tenant ID
        
    Returns:
        Usage information
    """
    try:
        calculator = get_billing_calculator()
        pricing_config = get_pricing_config()
        
        tier = calculator.get_tier(tenant_id)
        tier_config = pricing_config.get_tier_config(tier)
        
        usage = calculator.get_usage(tenant_id)
        free_tier_limit = tier_config["free_tier_limit"]
        
        remaining = max(0, free_tier_limit - usage)
        percentage = (usage / free_tier_limit * 100) if free_tier_limit > 0 else 0
        
        return {
            "tenant_id": tenant_id,
            "current_usage": usage,
            "free_tier_limit": free_tier_limit,
            "remaining": remaining,
            "percentage": min(100.0, percentage),
            "is_over_limit": usage > free_tier_limit
        }
    
    except Exception as e:
        logger.exception(f"Error getting usage: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get usage: {str(e)}"
        )


@router.get("/pricing")
async def get_pricing_info(
    tenant_id: str = "public"
) -> Dict[str, Any]:
    """Get pricing information for tenant.
    
    Args:
        tenant_id: Tenant ID
        
    Returns:
        Pricing information
    """
    try:
        calculator = get_billing_calculator()
        pricing_config = get_pricing_config()
        
        tier = calculator.get_tier(tenant_id)
        tier_config = pricing_config.get_tier_config(tier)
        
        return {
            "tenant_id": tenant_id,
            "pricing_tier": tier.value,
            "price_per_eval": tier_config["price_per_eval"],
            "free_tier_limit": tier_config["free_tier_limit"],
            "monthly_minimum": tier_config["monthly_minimum"],
            "price_formatted": f"${tier_config['price_per_eval']:.4f}",
            "monthly_minimum_formatted": f"${tier_config['monthly_minimum']:.2f}"
        }
    
    except Exception as e:
        logger.exception(f"Error getting pricing: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get pricing: {str(e)}"
        )


@router.get("/dashboard", response_class=HTMLResponse)
async def cost_dashboard() -> HTMLResponse:
    """Serve the cost visibility dashboard UI.
    
    Returns:
        HTML cost dashboard
    """
    template_path = Path(__file__).resolve().parents[2] / "templates" / "billing" / "cost_dashboard.html"
    
    if not template_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cost dashboard template not found"
        )
    
    return HTMLResponse(template_path.read_text())


__all__ = ["router"]

