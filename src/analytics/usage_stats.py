"""Tenant usage statistics tracking and aggregation."""

from __future__ import annotations

import datetime as dt
import json
import logging
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class UsageStats:
    """Usage statistics for a time period."""
    
    tenant_id: str
    date: str  # YYYY-MM-DD or YYYY-MM-DD HH:00
    
    total_requests: int = 0
    flagged_requests: int = 0
    safe_requests: int = 0
    
    category_counts: Dict[str, int] = field(default_factory=dict)
    guard_counts: Dict[str, int] = field(default_factory=dict)
    
    avg_latency_ms: int = 0
    p50_latency_ms: int = 0
    p90_latency_ms: int = 0
    p99_latency_ms: int = 0
    
    error_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "tenant_id": self.tenant_id,
            "date": self.date,
            "total_requests": self.total_requests,
            "flagged_requests": self.flagged_requests,
            "safe_requests": self.safe_requests,
            "category_counts": self.category_counts,
            "guard_counts": self.guard_counts,
            "avg_latency_ms": self.avg_latency_ms,
            "p50_latency_ms": self.p50_latency_ms,
            "p90_latency_ms": self.p90_latency_ms,
            "p99_latency_ms": self.p99_latency_ms,
            "error_count": self.error_count,
        }


class UsageTracker:
    """Tracks tenant usage statistics."""
    
    def __init__(self, db_path: Path = Path("history.db")):
        """Initialize usage tracker.
        
        Args:
            db_path: Database path
        """
        self.db_path = db_path
        self._init_tables()
    
    def _init_tables(self) -> None:
        """Initialize database tables."""
        try:
            from .schema import init_analytics_tables
            
            conn = sqlite3.connect(self.db_path)
            init_analytics_tables(conn)
            conn.close()
        except Exception as e:
            logger.warning(f"Failed to initialize analytics tables: {e}")
    
    def _get_current_date(self) -> str:
        """Get current date (YYYY-MM-DD).
        
        Returns:
            Date string
        """
        return dt.datetime.now(dt.UTC).strftime("%Y-%m-%d")
    
    def _get_current_hour(self) -> str:
        """Get current hour (YYYY-MM-DD HH:00).
        
        Returns:
            Hour string
        """
        return dt.datetime.now(dt.UTC).strftime("%Y-%m-%d %H:00")
    
    def track_request(
        self,
        tenant_id: str,
        flagged: bool = False,
        category: Optional[str] = None,
        guard: Optional[str] = None,
        latency_ms: int = 0,
        error: bool = False
    ) -> None:
        """Track a single request.
        
        Args:
            tenant_id: Tenant ID
            flagged: Whether content was flagged
            category: Optional category
            guard: Optional guard name
            latency_ms: Latency in milliseconds
            error: Whether request had an error
        """
        date = self._get_current_date()
        hour = self._get_current_hour()
        
        conn = sqlite3.connect(self.db_path)
        
        try:
            # Update daily stats
            self._update_daily(conn, tenant_id, date, flagged, category, guard, latency_ms, error)
            
            # Update hourly stats
            self._update_hourly(conn, tenant_id, hour, flagged)
            
            conn.commit()
        
        except Exception as e:
            logger.error(f"Error tracking usage: {e}")
            conn.rollback()
        
        finally:
            conn.close()
    
    def _update_daily(
        self,
        conn: sqlite3.Connection,
        tenant_id: str,
        date: str,
        flagged: bool,
        category: Optional[str],
        guard: Optional[str],
        latency_ms: int,
        error: bool
    ) -> None:
        """Update daily usage stats.
        
        Args:
            conn: Database connection
            tenant_id: Tenant ID
            date: Date string
            flagged: Whether flagged
            category: Category
            guard: Guard name
            latency_ms: Latency
            error: Error flag
        """
        cur = conn.cursor()
        
        # Get current row
        cur.execute(
            "SELECT category_counts, guard_counts, total_requests, avg_latency_ms FROM tenant_usage_daily WHERE tenant_id = ? AND date = ?",
            (tenant_id, date)
        )
        row = cur.fetchone()
        
        if row:
            # Update existing
            category_counts = json.loads(row[0]) if row[0] else {}
            guard_counts = json.loads(row[1]) if row[1] else {}
            total = row[2]
            prev_avg_latency = row[3]
        else:
            # New entry
            category_counts = {}
            guard_counts = {}
            total = 0
            prev_avg_latency = 0
        
        # Update category counts
        if category:
            category_counts[category] = category_counts.get(category, 0) + 1
        
        # Update guard counts
        if guard:
            guard_counts[guard] = guard_counts.get(guard, 0) + 1
        
        # Update average latency (incremental)
        new_avg_latency = ((prev_avg_latency * total) + latency_ms) // (total + 1) if total > 0 else latency_ms
        
        # Upsert
        cur.execute("""
            INSERT INTO tenant_usage_daily (
                tenant_id, date, total_requests, flagged_requests, safe_requests,
                category_counts, guard_counts, avg_latency_ms, error_count, updated_at
            )
            VALUES (?, ?, 1, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(tenant_id, date) DO UPDATE SET
                total_requests = total_requests + 1,
                flagged_requests = flagged_requests + ?,
                safe_requests = safe_requests + ?,
                category_counts = ?,
                guard_counts = ?,
                avg_latency_ms = ?,
                error_count = error_count + ?,
                updated_at = CURRENT_TIMESTAMP
        """, (
            tenant_id,
            date,
            1 if flagged else 0,
            0 if flagged else 1,
            json.dumps(category_counts),
            json.dumps(guard_counts),
            new_avg_latency,
            1 if error else 0,
            # UPDATE values
            1 if flagged else 0,
            0 if flagged else 1,
            json.dumps(category_counts),
            json.dumps(guard_counts),
            new_avg_latency,
            1 if error else 0,
        ))
    
    def _update_hourly(
        self,
        conn: sqlite3.Connection,
        tenant_id: str,
        hour: str,
        flagged: bool
    ) -> None:
        """Update hourly usage stats.
        
        Args:
            conn: Database connection
            tenant_id: Tenant ID
            hour: Hour string
            flagged: Whether flagged
        """
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO tenant_usage_hourly (tenant_id, hour, total_requests, flagged_requests, updated_at)
            VALUES (?, ?, 1, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(tenant_id, hour) DO UPDATE SET
                total_requests = total_requests + 1,
                flagged_requests = flagged_requests + ?,
                updated_at = CURRENT_TIMESTAMP
        """, (
            tenant_id,
            hour,
            1 if flagged else 0,
            1 if flagged else 0,
        ))
    
    def get_daily_stats(
        self,
        tenant_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 30
    ) -> List[UsageStats]:
        """Get daily usage statistics.
        
        Args:
            tenant_id: Tenant ID
            start_date: Optional start date (YYYY-MM-DD)
            end_date: Optional end date (YYYY-MM-DD)
            limit: Max days to return
            
        Returns:
            List of UsageStats
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        try:
            query = "SELECT * FROM tenant_usage_daily WHERE tenant_id = ?"
            params = [tenant_id]
            
            if start_date:
                query += " AND date >= ?"
                params.append(start_date)
            
            if end_date:
                query += " AND date <= ?"
                params.append(end_date)
            
            query += " ORDER BY date DESC LIMIT ?"
            params.append(limit)
            
            cur = conn.cursor()
            cur.execute(query, params)
            rows = cur.fetchall()
            
            stats = []
            for row in rows:
                category_counts = json.loads(row["category_counts"]) if row["category_counts"] else {}
                guard_counts = json.loads(row["guard_counts"]) if row["guard_counts"] else {}
                
                stat = UsageStats(
                    tenant_id=row["tenant_id"],
                    date=row["date"],
                    total_requests=row["total_requests"],
                    flagged_requests=row["flagged_requests"],
                    safe_requests=row["safe_requests"],
                    category_counts=category_counts,
                    guard_counts=guard_counts,
                    avg_latency_ms=row["avg_latency_ms"],
                    p50_latency_ms=row["p50_latency_ms"],
                    p90_latency_ms=row["p90_latency_ms"],
                    p99_latency_ms=row["p99_latency_ms"],
                    error_count=row["error_count"],
                )
                
                stats.append(stat)
            
            return stats
        
        finally:
            conn.close()
    
    def get_current_month_total(self, tenant_id: str) -> int:
        """Get total requests for current month.
        
        Args:
            tenant_id: Tenant ID
            
        Returns:
            Total request count
        """
        current_month = dt.datetime.now(dt.UTC).strftime("%Y-%m")
        
        conn = sqlite3.connect(self.db_path)
        
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT SUM(total_requests) as total
                FROM tenant_usage_daily
                WHERE tenant_id = ? AND date LIKE ?
            """, (tenant_id, f"{current_month}%"))
            
            row = cur.fetchone()
            return row[0] if row and row[0] else 0
        
        finally:
            conn.close()
    
    def get_summary(self, tenant_id: str, days: int = 30) -> Dict[str, Any]:
        """Get usage summary for tenant.
        
        Args:
            tenant_id: Tenant ID
            days: Number of days to summarize
            
        Returns:
            Summary dictionary
        """
        # Get daily stats
        stats = self.get_daily_stats(tenant_id, limit=days)
        
        if not stats:
            return {
                "tenant_id": tenant_id,
                "days": days,
                "total_requests": 0,
                "flagged_requests": 0,
                "safe_requests": 0,
                "avg_latency_ms": 0,
                "top_categories": [],
                "top_guards": [],
            }
        
        # Aggregate
        total_requests = sum(s.total_requests for s in stats)
        flagged_requests = sum(s.flagged_requests for s in stats)
        safe_requests = sum(s.safe_requests for s in stats)
        
        # Average latency (weighted by requests)
        total_latency = sum(s.avg_latency_ms * s.total_requests for s in stats)
        avg_latency = total_latency // total_requests if total_requests > 0 else 0
        
        # Aggregate categories
        all_categories: Dict[str, int] = {}
        for s in stats:
            for cat, count in s.category_counts.items():
                all_categories[cat] = all_categories.get(cat, 0) + count
        
        # Aggregate guards
        all_guards: Dict[str, int] = {}
        for s in stats:
            for guard, count in s.guard_counts.items():
                all_guards[guard] = all_guards.get(guard, 0) + count
        
        # Top categories and guards
        top_categories = sorted(all_categories.items(), key=lambda x: x[1], reverse=True)[:5]
        top_guards = sorted(all_guards.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            "tenant_id": tenant_id,
            "days": days,
            "total_requests": total_requests,
            "flagged_requests": flagged_requests,
            "safe_requests": safe_requests,
            "flagged_rate": flagged_requests / total_requests if total_requests > 0 else 0.0,
            "avg_latency_ms": avg_latency,
            "top_categories": [{"name": c, "count": n} for c, n in top_categories],
            "top_guards": [{"name": g, "count": n} for g, n in top_guards],
            "daily_stats": [s.to_dict() for s in reversed(stats)],  # Chronological order
        }


# Global tracker instance
_global_tracker: Optional[UsageTracker] = None


def get_usage_tracker() -> UsageTracker:
    """Get global usage tracker instance.
    
    Returns:
        UsageTracker instance
    """
    global _global_tracker
    
    if _global_tracker is None:
        _global_tracker = UsageTracker()
    
    return _global_tracker


__all__ = ["UsageTracker", "UsageStats", "get_usage_tracker"]

