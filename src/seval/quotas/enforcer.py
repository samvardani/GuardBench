"""Usage quota enforcement."""

from __future__ import annotations

import datetime as dt
import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class QuotaExceeded(Exception):
    """Exception raised when usage quota is exceeded."""
    
    def __init__(self, tenant_id: str, usage: int, limit: int, period: str):
        self.tenant_id = tenant_id
        self.usage = usage
        self.limit = limit
        self.period = period
        super().__init__(
            f"Quota exceeded for tenant {tenant_id}: {usage}/{limit} in period {period}"
        )


@dataclass
class UsageInfo:
    """Usage information for a tenant."""
    
    tenant_id: str
    period: str
    usage_count: int
    plan_type: str
    monthly_quota: Optional[int]
    quota_exceeded: bool
    quota_warning: bool  # True if >= 90% of quota
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            "tenant_id": self.tenant_id,
            "period": self.period,
            "usage_count": self.usage_count,
            "plan_type": self.plan_type,
            "monthly_quota": self.monthly_quota,
            "quota_exceeded": self.quota_exceeded,
            "quota_warning": self.quota_warning,
        }


class QuotaEnforcer:
    """Enforces usage quotas per tenant."""
    
    # Default quotas by plan type
    DEFAULT_QUOTAS = {
        "free": 10_000,      # 10k/month free tier
        "starter": 100_000,  # 100k/month starter
        "pro": 1_000_000,    # 1M/month pro
        "enterprise": None,  # Unlimited
    }
    
    def __init__(
        self,
        db_path: Optional[Path] = None,
        enforce_hard_limit: bool = False,
        quotas: Optional[dict[str, Optional[int]]] = None
    ):
        """Initialize quota enforcer.
        
        Args:
            db_path: Path to database
            enforce_hard_limit: If True, block requests over quota. If False, warn only.
            quotas: Custom quota limits by plan type
        """
        self.db_path = db_path or Path("history.db")
        self.enforce_hard_limit = enforce_hard_limit
        self.quotas = quotas or self.DEFAULT_QUOTAS
        
        # Initialize database
        self._init_tables()
        
        logger.info(
            f"QuotaEnforcer initialized (hard_limit={enforce_hard_limit}, "
            f"free_quota={self.quotas.get('free', 'unlimited')})"
        )
    
    def _init_tables(self) -> None:
        """Initialize database tables."""
        try:
            from seval.quotas.schema import init_usage_tables
            
            conn = sqlite3.connect(self.db_path)
            init_usage_tables(conn)
            conn.close()
        except Exception as e:
            logger.warning(f"Failed to initialize usage tables: {e}")
    
    def _get_current_period(self) -> str:
        """Get current billing period (YYYY-MM).
        
        Returns:
            Period string
        """
        return dt.datetime.now(dt.UTC).strftime("%Y-%m")
    
    def get_tenant_plan(self, conn: sqlite3.Connection, tenant_id: str) -> tuple[str, Optional[int]]:
        """Get tenant plan type and quota.
        
        Args:
            conn: Database connection
            tenant_id: Tenant ID
            
        Returns:
            Tuple of (plan_type, monthly_quota)
        """
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT plan_type, monthly_quota FROM tenant_plans WHERE tenant_id = ?",
                (tenant_id,)
            )
            row = cur.fetchone()
            
            if row:
                plan_type = row[0]
                monthly_quota = row[1]
            else:
                # Default to free tier
                plan_type = "free"
                monthly_quota = self.quotas.get(plan_type, 10_000)
                
                # Insert default plan
                cur.execute(
                    "INSERT OR IGNORE INTO tenant_plans (tenant_id, plan_type, monthly_quota) VALUES (?, ?, ?)",
                    (tenant_id, plan_type, monthly_quota)
                )
                conn.commit()
            
            return plan_type, monthly_quota
        
        except Exception as e:
            logger.error(f"Failed to get tenant plan: {e}")
            return "free", self.quotas.get("free", 10_000)
    
    def get_usage(self, tenant_id: str, period: Optional[str] = None) -> UsageInfo:
        """Get usage information for tenant.
        
        Args:
            tenant_id: Tenant ID
            period: Period string (default: current month)
            
        Returns:
            UsageInfo
        """
        if period is None:
            period = self._get_current_period()
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        try:
            # Get plan
            plan_type, monthly_quota = self.get_tenant_plan(conn, tenant_id)
            
            # Get usage
            cur = conn.cursor()
            cur.execute(
                "SELECT usage_count FROM tenant_usage WHERE tenant_id = ? AND period = ?",
                (tenant_id, period)
            )
            row = cur.fetchone()
            
            usage_count = row[0] if row else 0
            
            # Check quota status
            quota_exceeded = False
            quota_warning = False
            
            if monthly_quota is not None:
                quota_exceeded = usage_count >= monthly_quota
                quota_warning = usage_count >= (monthly_quota * 0.9)
            
            return UsageInfo(
                tenant_id=tenant_id,
                period=period,
                usage_count=usage_count,
                plan_type=plan_type,
                monthly_quota=monthly_quota,
                quota_exceeded=quota_exceeded,
                quota_warning=quota_warning,
            )
        
        finally:
            conn.close()
    
    def increment_usage(
        self,
        tenant_id: str,
        amount: int = 1,
        check_quota: bool = True
    ) -> UsageInfo:
        """Increment usage for tenant (atomic).
        
        Args:
            tenant_id: Tenant ID
            amount: Amount to increment
            check_quota: If True, check quota and raise if exceeded
            
        Returns:
            UsageInfo after increment
            
        Raises:
            QuotaExceeded: If quota exceeded and enforce_hard_limit is True
        """
        period = self._get_current_period()
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        try:
            # Get plan
            plan_type, monthly_quota = self.get_tenant_plan(conn, tenant_id)
            
            # Get current usage (with lock)
            cur = conn.cursor()
            
            # Get current count first
            cur.execute(
                "SELECT usage_count FROM tenant_usage WHERE tenant_id = ? AND period = ?",
                (tenant_id, period)
            )
            row = cur.fetchone()
            current_usage = row[0] if row else 0
            new_usage = current_usage + amount
            
            # Check quota BEFORE incrementing
            quota_exceeded = False
            quota_warning = False
            
            if monthly_quota is not None and check_quota:
                quota_exceeded = new_usage > monthly_quota
                quota_warning = new_usage >= (monthly_quota * 0.9)
                
                # Enforce hard limit if configured - raise BEFORE incrementing
                if quota_exceeded and self.enforce_hard_limit:
                    conn.close()
                    raise QuotaExceeded(tenant_id, new_usage, monthly_quota, period)
            
            # Atomic increment with UPSERT (only if we passed quota check)
            cur.execute(
                """
                INSERT INTO tenant_usage (tenant_id, period, usage_count, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(tenant_id, period) DO UPDATE SET
                    usage_count = usage_count + ?,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (tenant_id, period, amount, amount)
            )
            
            conn.commit()
            
            usage_info = UsageInfo(
                tenant_id=tenant_id,
                period=period,
                usage_count=new_usage,
                plan_type=plan_type,
                monthly_quota=monthly_quota,
                quota_exceeded=quota_exceeded,
                quota_warning=quota_warning,
            )
            
            # Log warning if quota exceeded (soft limit)
            if quota_exceeded and not self.enforce_hard_limit:
                logger.warning(
                    f"Tenant {tenant_id} exceeded quota: {new_usage}/{monthly_quota} "
                    f"(soft limit, allowing request)"
                )
            elif quota_warning:
                logger.info(
                    f"Tenant {tenant_id} approaching quota: {new_usage}/{monthly_quota}"
                )
            
            return usage_info
        
        finally:
            conn.close()
    
    def reset_usage(self, tenant_id: str, period: Optional[str] = None) -> None:
        """Reset usage for tenant in period.
        
        Args:
            tenant_id: Tenant ID
            period: Period to reset (default: current)
        """
        if period is None:
            period = self._get_current_period()
        
        conn = sqlite3.connect(self.db_path)
        
        try:
            conn.execute(
                """
                UPDATE tenant_usage 
                SET usage_count = 0, last_reset_at = CURRENT_TIMESTAMP 
                WHERE tenant_id = ? AND period = ?
                """,
                (tenant_id, period)
            )
            conn.commit()
            logger.info(f"Reset usage for tenant {tenant_id} in period {period}")
        finally:
            conn.close()
    
    def set_tenant_plan(
        self,
        tenant_id: str,
        plan_type: str,
        monthly_quota: Optional[int] = None
    ) -> None:
        """Set tenant plan and quota.
        
        Args:
            tenant_id: Tenant ID
            plan_type: Plan type (free, starter, pro, enterprise)
            monthly_quota: Custom quota (default: from plan type)
        """
        if monthly_quota is None:
            monthly_quota = self.quotas.get(plan_type)
        
        conn = sqlite3.connect(self.db_path)
        
        try:
            conn.execute(
                """
                INSERT INTO tenant_plans (tenant_id, plan_type, monthly_quota, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(tenant_id) DO UPDATE SET
                    plan_type = excluded.plan_type,
                    monthly_quota = excluded.monthly_quota,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (tenant_id, plan_type, monthly_quota)
            )
            conn.commit()
            logger.info(f"Set plan for tenant {tenant_id}: {plan_type} (quota={monthly_quota})")
        finally:
            conn.close()


# Global enforcer instance
_global_enforcer: Optional[QuotaEnforcer] = None


def get_quota_enforcer(
    enforce_hard_limit: Optional[bool] = None
) -> QuotaEnforcer:
    """Get or create global quota enforcer.
    
    Args:
        enforce_hard_limit: Override hard limit setting
        
    Returns:
        Global QuotaEnforcer instance
    """
    global _global_enforcer
    
    if _global_enforcer is None:
        import os
        hard_limit = enforce_hard_limit if enforce_hard_limit is not None else os.getenv("ENFORCE_USAGE_QUOTA", "0") == "1"
        _global_enforcer = QuotaEnforcer(enforce_hard_limit=hard_limit)
    
    return _global_enforcer

