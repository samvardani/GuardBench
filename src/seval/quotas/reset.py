"""Monthly usage reset logic."""

from __future__ import annotations

import datetime as dt
import logging
import sqlite3
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class UsageResetter:
    """Handles monthly usage resets."""
    
    def __init__(self, db_path: Optional[Path] = None):
        """Initialize usage resetter.
        
        Args:
            db_path: Path to database
        """
        self.db_path = db_path or Path("history.db")
    
    def _get_current_period(self) -> str:
        """Get current billing period (YYYY-MM).
        
        Returns:
            Period string
        """
        return dt.datetime.now(dt.UTC).strftime("%Y-%m")
    
    def reset_if_new_period(self) -> int:
        """Reset usage if we're in a new billing period.
        
        Returns:
            Number of tenants reset
        """
        current_period = self._get_current_period()
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        try:
            # Find tenants with old periods
            cur = conn.cursor()
            cur.execute(
                "SELECT DISTINCT tenant_id, period FROM tenant_usage WHERE period < ?",
                (current_period,)
            )
            old_records = cur.fetchall()
            
            if not old_records:
                return 0
            
            # Reset each tenant's count to 0 and update period
            reset_count = 0
            for row in old_records:
                tenant_id = row["tenant_id"]
                old_period = row["period"]
                
                # Insert new period record or update existing
                cur.execute(
                    """
                    INSERT INTO tenant_usage (tenant_id, period, usage_count, last_reset_at, updated_at)
                    VALUES (?, ?, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    ON CONFLICT(tenant_id, period) DO UPDATE SET
                        usage_count = 0,
                        last_reset_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (tenant_id, current_period)
                )
                
                reset_count += 1
                logger.info(
                    f"Reset usage for tenant {tenant_id}: {old_period} -> {current_period}"
                )
            
            conn.commit()
            return reset_count
        
        finally:
            conn.close()
    
    def check_and_reset_all(self) -> dict[str, int]:
        """Check all tenants and reset if needed.
        
        Returns:
            Dict with reset statistics
        """
        current_period = self._get_current_period()
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        try:
            cur = conn.cursor()
            
            # Get all tenants with their current period
            cur.execute("SELECT tenant_id, period, usage_count FROM tenant_usage")
            records = cur.fetchall()
            
            reset_count = 0
            kept_count = 0
            
            for row in records:
                tenant_id = row["tenant_id"]
                period = row["period"]
                
                if period < current_period:
                    # Reset this tenant
                    cur.execute(
                        """
                        INSERT INTO tenant_usage (tenant_id, period, usage_count, last_reset_at, updated_at)
                        VALUES (?, ?, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                        ON CONFLICT(tenant_id, period) DO UPDATE SET
                            usage_count = 0,
                            last_reset_at = CURRENT_TIMESTAMP,
                            updated_at = CURRENT_TIMESTAMP
                        """,
                        (tenant_id, current_period)
                    )
                    reset_count += 1
                    logger.info(f"Reset tenant {tenant_id}: {period} -> {current_period}")
                else:
                    kept_count += 1
            
            conn.commit()
            
            return {
                "current_period": current_period,
                "reset_count": reset_count,
                "kept_count": kept_count,
            }
        
        finally:
            conn.close()


def reset_usage_for_new_month() -> int:
    """Check and reset usage for all tenants if in new month.
    
    This function can be called from a cron job or scheduler.
    
    Returns:
        Number of tenants reset
    """
    resetter = UsageResetter()
    return resetter.reset_if_new_period()

