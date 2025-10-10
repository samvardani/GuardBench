"""Pure cost calculation functions - single source of truth."""

from __future__ import annotations

import datetime as dt
import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .pricing import PricingTier, get_pricing_config

logger = logging.getLogger(__name__)


@dataclass
class CostResult:
    """Cost calculation result."""
    
    total_usage: int
    free_tier_usage: int
    billable_usage: int
    unit_price: float
    subtotal: float
    monthly_minimum: float
    total_cost: float
    pricing_tier: str
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "total_usage": self.total_usage,
            "free_tier_usage": self.free_tier_usage,
            "billable_usage": self.billable_usage,
            "unit_price": self.unit_price,
            "subtotal": self.subtotal,
            "monthly_minimum": self.monthly_minimum,
            "total_cost": self.total_cost,
            "pricing_tier": self.pricing_tier,
            "cost_formatted": f"${self.total_cost:.2f}"
        }


def compute_cost(
    usage: int,
    tier: PricingTier = PricingTier.FREE,
    pricing_config: Optional[object] = None
) -> CostResult:
    """Pure function to compute cost from usage and tier.
    
    This is the single source of truth for cost calculation.
    Used by: API, UI, headers, quotas.
    
    Args:
        usage: Total usage count
        tier: Pricing tier
        pricing_config: Optional pricing config (uses global if None)
        
    Returns:
        CostResult with breakdown
    """
    if pricing_config is None:
        pricing_config = get_pricing_config()
    
    # Get tier configuration
    tier_config = pricing_config.get_tier_config(tier)
    
    price_per_eval = tier_config["price_per_eval"]
    free_tier_limit = tier_config["free_tier_limit"]
    monthly_minimum = tier_config["monthly_minimum"]
    
    # Calculate free tier usage
    free_tier_usage = min(usage, free_tier_limit)
    billable_usage = max(0, usage - free_tier_limit)
    
    # Calculate subtotal
    subtotal = billable_usage * price_per_eval
    
    # Apply monthly minimum (only for paid tiers with usage > 0)
    if tier != PricingTier.FREE and usage > 0:
        total_cost = max(subtotal, monthly_minimum)
    else:
        total_cost = subtotal
    
    return CostResult(
        total_usage=usage,
        free_tier_usage=free_tier_usage,
        billable_usage=billable_usage,
        unit_price=price_per_eval,
        subtotal=subtotal,
        monthly_minimum=monthly_minimum,
        total_cost=total_cost,
        pricing_tier=tier.value
    )


class BillingCalculator:
    """Billing calculator with database-backed usage tracking."""
    
    def __init__(self, db_path: Path = Path("history.db")):
        """Initialize billing calculator.
        
        Args:
            db_path: Database path
        """
        self.db_path = db_path
        self._init_tables()
    
    def _init_tables(self) -> None:
        """Initialize database tables."""
        conn = sqlite3.connect(self.db_path)
        
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tenant_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id TEXT NOT NULL,
                    month TEXT NOT NULL,
                    usage_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(tenant_id, month)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tenant_pricing (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id TEXT NOT NULL UNIQUE,
                    pricing_tier TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
        except Exception as e:
            logger.error(f"Failed to initialize billing tables: {e}")
        finally:
            conn.close()
    
    def track_usage(self, tenant_id: str, count: int = 1) -> None:
        """Track usage for tenant.
        
        Args:
            tenant_id: Tenant ID
            count: Number of evaluations
        """
        # Use UTC for consistency
        current_month = dt.datetime.now(dt.UTC).strftime("%Y-%m")
        
        conn = sqlite3.connect(self.db_path)
        
        try:
            conn.execute("""
                INSERT INTO tenant_usage (tenant_id, month, usage_count)
                VALUES (?, ?, ?)
                ON CONFLICT(tenant_id, month) DO UPDATE SET
                    usage_count = usage_count + ?,
                    updated_at = CURRENT_TIMESTAMP
            """, (tenant_id, current_month, count, count))
            
            conn.commit()
        except Exception as e:
            logger.error(f"Error tracking usage: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def get_usage(self, tenant_id: str, month: Optional[str] = None) -> int:
        """Get usage for tenant.
        
        Args:
            tenant_id: Tenant ID
            month: Month (YYYY-MM), defaults to current month (UTC)
            
        Returns:
            Usage count
        """
        if month is None:
            month = dt.datetime.now(dt.UTC).strftime("%Y-%m")
        
        conn = sqlite3.connect(self.db_path)
        
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT usage_count FROM tenant_usage
                WHERE tenant_id = ? AND month = ?
            """, (tenant_id, month))
            
            row = cur.fetchone()
            return row[0] if row else 0
        finally:
            conn.close()
    
    def get_tier(self, tenant_id: str) -> PricingTier:
        """Get pricing tier for tenant.
        
        Args:
            tenant_id: Tenant ID
            
        Returns:
            PricingTier
        """
        conn = sqlite3.connect(self.db_path)
        
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT pricing_tier FROM tenant_pricing
                WHERE tenant_id = ?
            """, (tenant_id,))
            
            row = cur.fetchone()
            
            if row:
                try:
                    return PricingTier(row[0])
                except ValueError:
                    pass
            
            # Default to free
            return PricingTier.FREE
        finally:
            conn.close()
    
    def set_tier(self, tenant_id: str, tier: PricingTier) -> None:
        """Set pricing tier for tenant.
        
        Args:
            tenant_id: Tenant ID
            tier: Pricing tier
        """
        conn = sqlite3.connect(self.db_path)
        
        try:
            conn.execute("""
                INSERT INTO tenant_pricing (tenant_id, pricing_tier)
                VALUES (?, ?)
                ON CONFLICT(tenant_id) DO UPDATE SET
                    pricing_tier = ?,
                    updated_at = CURRENT_TIMESTAMP
            """, (tenant_id, tier.value, tier.value))
            
            conn.commit()
        finally:
            conn.close()
    
    def calculate_cost(self, tenant_id: str, month: Optional[str] = None) -> CostResult:
        """Calculate cost for tenant.
        
        Uses the pure compute_cost() function - single source of truth.
        
        Args:
            tenant_id: Tenant ID
            month: Month (YYYY-MM), defaults to current month (UTC)
            
        Returns:
            CostResult
        """
        usage = self.get_usage(tenant_id, month)
        tier = self.get_tier(tenant_id)
        
        # Use pure function - single source of truth
        return compute_cost(usage=usage, tier=tier)


# Global calculator instance
_global_calculator: Optional[BillingCalculator] = None


def get_billing_calculator(db_path: Optional[Path] = None) -> BillingCalculator:
    """Get global billing calculator.
    
    Args:
        db_path: Optional database path (for testing)
        
    Returns:
        BillingCalculator instance
    """
    global _global_calculator
    
    if _global_calculator is None or db_path is not None:
        if db_path is not None:
            return BillingCalculator(db_path=db_path)
        _global_calculator = BillingCalculator()
    
    return _global_calculator


__all__ = ["compute_cost", "CostResult", "BillingCalculator", "get_billing_calculator"]

