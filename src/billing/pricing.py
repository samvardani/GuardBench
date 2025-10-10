"""Pricing plan configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class PricingTier(Enum):
    """Pricing tiers."""
    
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


@dataclass
class PricingPlan:
    """Pricing plan configuration."""
    
    tier: PricingTier
    price_per_eval: float
    free_tier_limit: int
    monthly_minimum: float = 0.0
    
    def __post_init__(self):
        """Validate pricing plan."""
        if self.price_per_eval < 0:
            raise ValueError("price_per_eval must be non-negative")
        
        if self.free_tier_limit < 0:
            raise ValueError("free_tier_limit must be non-negative")


# Default pricing plans
DEFAULT_PRICING_PLANS = {
    PricingTier.FREE: PricingPlan(
        tier=PricingTier.FREE,
        price_per_eval=0.001,
        free_tier_limit=10000,
        monthly_minimum=0.0
    ),
    PricingTier.STARTER: PricingPlan(
        tier=PricingTier.STARTER,
        price_per_eval=0.0008,
        free_tier_limit=0,
        monthly_minimum=49.0
    ),
    PricingTier.PROFESSIONAL: PricingPlan(
        tier=PricingTier.PROFESSIONAL,
        price_per_eval=0.0005,
        free_tier_limit=0,
        monthly_minimum=199.0
    ),
    PricingTier.ENTERPRISE: PricingPlan(
        tier=PricingTier.ENTERPRISE,
        price_per_eval=0.0003,
        free_tier_limit=0,
        monthly_minimum=999.0
    ),
}


def get_pricing_plan(tier: Optional[str] = None) -> PricingPlan:
    """Get pricing plan from configuration.
    
    Args:
        tier: Pricing tier name (defaults to FREE)
        
    Returns:
        PricingPlan instance
    """
    # Get tier from argument or environment
    tier_name = tier or os.getenv("PRICING_TIER", "free")
    
    try:
        pricing_tier = PricingTier(tier_name.lower())
    except ValueError:
        pricing_tier = PricingTier.FREE
    
    # Get default plan for tier
    plan = DEFAULT_PRICING_PLANS.get(pricing_tier)
    
    if plan is None:
        return DEFAULT_PRICING_PLANS[PricingTier.FREE]
    
    # Allow environment overrides
    price_per_eval = float(os.getenv("PRICE_PER_EVAL", plan.price_per_eval))
    free_tier_limit = int(os.getenv("FREE_TIER_LIMIT", plan.free_tier_limit))
    monthly_minimum = float(os.getenv("MONTHLY_MINIMUM", plan.monthly_minimum))
    
    return PricingPlan(
        tier=pricing_tier,
        price_per_eval=price_per_eval,
        free_tier_limit=free_tier_limit,
        monthly_minimum=monthly_minimum
    )


__all__ = ["PricingPlan", "PricingTier", "get_pricing_plan", "DEFAULT_PRICING_PLANS"]

