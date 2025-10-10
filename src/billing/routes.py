"""Billing and cost API routes."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import HTMLResponse

from .cost_calculator import get_cost_calculator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["Billing"])


@router.get("/cost")
async def get_current_cost(
    tenant_id: str = "public"  # From auth context in production
) -> Dict[str, Any]:
    """Get current month cost for tenant.
    
    Args:
        tenant_id: Tenant ID
        
    Returns:
        Cost breakdown
    """
    try:
        calculator = get_cost_calculator()
        cost = calculator.calculate_cost(tenant_id)
        
        return cost.to_dict()
    
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
        calculator = get_cost_calculator()
        usage = calculator.get_usage(tenant_id)
        
        plan = calculator.get_pricing_plan_for_tenant(tenant_id)
        
        remaining = max(0, plan.free_tier_limit - usage)
        percentage = (usage / plan.free_tier_limit * 100) if plan.free_tier_limit > 0 else 0
        
        return {
            "tenant_id": tenant_id,
            "current_usage": usage,
            "free_tier_limit": plan.free_tier_limit,
            "remaining": remaining,
            "percentage": min(100.0, percentage),
            "is_over_limit": usage > plan.free_tier_limit
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
        calculator = get_cost_calculator()
        plan = calculator.get_pricing_plan_for_tenant(tenant_id)
        
        return {
            "tenant_id": tenant_id,
            "pricing_tier": plan.tier.value,
            "price_per_eval": plan.price_per_eval,
            "free_tier_limit": plan.free_tier_limit,
            "monthly_minimum": plan.monthly_minimum,
            "price_formatted": f"${plan.price_per_eval:.4f}",
            "monthly_minimum_formatted": f"${plan.monthly_minimum:.2f}"
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

