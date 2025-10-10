"""Centralized pricing configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum


class PricingTier(Enum):
    """Pricing tiers."""
    
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


@dataclass
class PricingConfig:
    """Centralized pricing configuration."""
    
    # Free tier
    free_tier_limit: int = 10000
    free_price_per_eval: float = 0.001
    
    # Starter tier
    starter_price_per_eval: float = 0.0008
    starter_monthly_minimum: float = 49.0
    
    # Professional tier
    pro_price_per_eval: float = 0.0005
    pro_monthly_minimum: float = 199.0
    
    # Enterprise tier
    enterprise_price_per_eval: float = 0.0003
    enterprise_monthly_minimum: float = 999.0
    
    def get_tier_config(self, tier: PricingTier) -> dict:
        """Get configuration for specific tier.
        
        Args:
            tier: Pricing tier
            
        Returns:
            Configuration dictionary
        """
        if tier == PricingTier.FREE:
            return {
                "price_per_eval": self.free_price_per_eval,
                "free_tier_limit": self.free_tier_limit,
                "monthly_minimum": 0.0
            }
        elif tier == PricingTier.STARTER:
            return {
                "price_per_eval": self.starter_price_per_eval,
                "free_tier_limit": 0,
                "monthly_minimum": self.starter_monthly_minimum
            }
        elif tier == PricingTier.PROFESSIONAL:
            return {
                "price_per_eval": self.pro_price_per_eval,
                "free_tier_limit": 0,
                "monthly_minimum": self.pro_monthly_minimum
            }
        elif tier == PricingTier.ENTERPRISE:
            return {
                "price_per_eval": self.enterprise_price_per_eval,
                "free_tier_limit": 0,
                "monthly_minimum": self.enterprise_monthly_minimum
            }
        else:
            # Default to free
            return self.get_tier_config(PricingTier.FREE)


# Global config instance
_global_pricing_config: Optional[PricingConfig] = None


def get_pricing_config() -> PricingConfig:
    """Get global pricing configuration.
    
    Returns:
        PricingConfig instance
    """
    global _global_pricing_config
    
    if _global_pricing_config is None:
        # Load from environment with defaults
        _global_pricing_config = PricingConfig(
            free_tier_limit=int(os.getenv("FREE_TIER_LIMIT", "10000")),
            free_price_per_eval=float(os.getenv("FREE_PRICE_PER_EVAL", "0.001")),
            starter_price_per_eval=float(os.getenv("STARTER_PRICE_PER_EVAL", "0.0008")),
            starter_monthly_minimum=float(os.getenv("STARTER_MONTHLY_MINIMUM", "49.0")),
            pro_price_per_eval=float(os.getenv("PRO_PRICE_PER_EVAL", "0.0005")),
            pro_monthly_minimum=float(os.getenv("PRO_MONTHLY_MINIMUM", "199.0")),
            enterprise_price_per_eval=float(os.getenv("ENTERPRISE_PRICE_PER_EVAL", "0.0003")),
            enterprise_monthly_minimum=float(os.getenv("ENTERPRISE_MONTHLY_MINIMUM", "999.0")),
        )
    
    return _global_pricing_config


__all__ = ["PricingConfig", "PricingTier", "get_pricing_config"]

