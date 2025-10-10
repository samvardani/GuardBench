"""Cost calculation for usage-based billing."""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from .pricing import PricingPlan, PricingTier, get_pricing_plan

logger = logging.getLogger(__name__)


@dataclass
class UsageCost:
    """Usage cost breakdown."""
    
    tenant_id: str
    current_month: str
    total_usage: int
    free_tier_usage: int
    billable_usage: int
    unit_cost: float
    total_cost: float
    pricing_tier: str
    free_tier_limit: int
    monthly_minimum: float
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "tenant_id": self.tenant_id,
            "current_month": self.current_month,
            "total_usage": self.total_usage,
            "free_tier_usage": self.free_tier_usage,
            "billable_usage": self.billable_usage,
            "unit_cost": self.unit_cost,
            "total_cost": self.total_cost,
            "pricing_tier": self.pricing_tier,
            "free_tier_limit": self.free_tier_limit,
            "monthly_minimum": self.monthly_minimum,
            "cost_formatted": f"${self.total_cost:.2f}",
        }


class CostCalculator:
    """Calculates costs based on usage and pricing plans."""
    
    def __init__(self, db_path: Path = Path("history.db")):
        """Initialize cost calculator.
        
        Args:
            db_path: Database path
        """
        self.db_path = db_path
        self._init_tables()
    
    def _init_tables(self) -> None:
        """Initialize database tables."""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Table for usage tracking
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
            
            # Table for tenant pricing plans
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tenant_pricing (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id TEXT NOT NULL UNIQUE,
                    pricing_tier TEXT NOT NULL,
                    price_per_eval REAL NOT NULL,
                    free_tier_limit INTEGER NOT NULL,
                    monthly_minimum REAL DEFAULT 0.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            conn.close()
        
        except Exception as e:
            logger.warning(f"Failed to initialize billing tables: {e}")
    
    def track_usage(self, tenant_id: str, count: int = 1) -> None:
        """Track usage for a tenant.
        
        Args:
            tenant_id: Tenant ID
            count: Number of evaluations (default: 1)
        """
        current_month = datetime.now().strftime("%Y-%m")
        
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
        """Get usage for a tenant.
        
        Args:
            tenant_id: Tenant ID
            month: Month (YYYY-MM), defaults to current month
            
        Returns:
            Usage count
        """
        if month is None:
            month = datetime.now().strftime("%Y-%m")
        
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
    
    def get_pricing_plan_for_tenant(self, tenant_id: str) -> PricingPlan:
        """Get pricing plan for tenant.
        
        Args:
            tenant_id: Tenant ID
            
        Returns:
            PricingPlan instance
        """
        conn = sqlite3.connect(self.db_path)
        
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT pricing_tier, price_per_eval, free_tier_limit, monthly_minimum
                FROM tenant_pricing
                WHERE tenant_id = ?
            """, (tenant_id,))
            
            row = cur.fetchone()
            
            if row:
                return PricingPlan(
                    tier=PricingTier(row[0]),
                    price_per_eval=row[1],
                    free_tier_limit=row[2],
                    monthly_minimum=row[3]
                )
            
            # Default to free tier
            return get_pricing_plan()
        
        finally:
            conn.close()
    
    def set_pricing_plan_for_tenant(self, tenant_id: str, plan: PricingPlan) -> None:
        """Set pricing plan for tenant.
        
        Args:
            tenant_id: Tenant ID
            plan: PricingPlan
        """
        conn = sqlite3.connect(self.db_path)
        
        try:
            conn.execute("""
                INSERT INTO tenant_pricing (
                    tenant_id, pricing_tier, price_per_eval,
                    free_tier_limit, monthly_minimum
                )
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(tenant_id) DO UPDATE SET
                    pricing_tier = ?,
                    price_per_eval = ?,
                    free_tier_limit = ?,
                    monthly_minimum = ?,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                tenant_id, plan.tier.value, plan.price_per_eval,
                plan.free_tier_limit, plan.monthly_minimum,
                # UPDATE values
                plan.tier.value, plan.price_per_eval,
                plan.free_tier_limit, plan.monthly_minimum
            ))
            
            conn.commit()
        
        finally:
            conn.close()
    
    def calculate_cost(
        self,
        tenant_id: str,
        month: Optional[str] = None
    ) -> UsageCost:
        """Calculate cost for tenant's usage.
        
        Args:
            tenant_id: Tenant ID
            month: Month (YYYY-MM), defaults to current month
            
        Returns:
            UsageCost breakdown
        """
        if month is None:
            month = datetime.now().strftime("%Y-%m")
        
        # Get usage
        total_usage = self.get_usage(tenant_id, month)
        
        # Get pricing plan
        plan = self.get_pricing_plan_for_tenant(tenant_id)
        
        # Calculate cost
        if total_usage <= plan.free_tier_limit:
            # Within free tier
            free_tier_usage = total_usage
            billable_usage = 0
            cost = 0.0
        else:
            # Exceeded free tier
            free_tier_usage = plan.free_tier_limit
            billable_usage = total_usage - plan.free_tier_limit
            cost = billable_usage * plan.price_per_eval
        
        # Apply monthly minimum
        if cost < plan.monthly_minimum and total_usage > 0:
            cost = plan.monthly_minimum
        
        return UsageCost(
            tenant_id=tenant_id,
            current_month=month,
            total_usage=total_usage,
            free_tier_usage=free_tier_usage,
            billable_usage=billable_usage,
            unit_cost=plan.price_per_eval,
            total_cost=cost,
            pricing_tier=plan.tier.value,
            free_tier_limit=plan.free_tier_limit,
            monthly_minimum=plan.monthly_minimum
        )


# Global calculator instance
_global_calculator: Optional[CostCalculator] = None


def get_cost_calculator() -> CostCalculator:
    """Get global cost calculator instance.
    
    Returns:
        CostCalculator instance
    """
    global _global_calculator
    
    if _global_calculator is None:
        _global_calculator = CostCalculator()
    
    return _global_calculator


__all__ = ["CostCalculator", "UsageCost", "get_cost_calculator"]

