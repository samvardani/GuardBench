"""Database schema for analytics and usage statistics."""

from __future__ import annotations

import logging
import sqlite3

logger = logging.getLogger(__name__)


SQL_CREATE_ANALYTICS_TABLES = """
CREATE TABLE IF NOT EXISTS tenant_usage_daily (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id TEXT NOT NULL,
    date TEXT NOT NULL,  -- Format: YYYY-MM-DD
    
    -- Request counts
    total_requests INTEGER DEFAULT 0,
    flagged_requests INTEGER DEFAULT 0,
    safe_requests INTEGER DEFAULT 0,
    
    -- Category breakdown (JSON)
    category_counts TEXT,  -- JSON: {"violence": 10, "hate": 5}
    
    -- Guard breakdown (JSON)
    guard_counts TEXT,  -- JSON: {"internal": 100, "openai": 50}
    
    -- Latency stats
    avg_latency_ms INTEGER DEFAULT 0,
    p50_latency_ms INTEGER DEFAULT 0,
    p90_latency_ms INTEGER DEFAULT 0,
    p99_latency_ms INTEGER DEFAULT 0,
    
    -- Errors
    error_count INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(tenant_id, date)
);

CREATE INDEX IF NOT EXISTS idx_usage_daily_tenant 
ON tenant_usage_daily(tenant_id, date DESC);

CREATE TABLE IF NOT EXISTS tenant_usage_hourly (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id TEXT NOT NULL,
    hour TEXT NOT NULL,  -- Format: YYYY-MM-DD HH:00
    
    total_requests INTEGER DEFAULT 0,
    flagged_requests INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(tenant_id, hour)
);

CREATE INDEX IF NOT EXISTS idx_usage_hourly_tenant 
ON tenant_usage_hourly(tenant_id, hour DESC);
"""


def init_analytics_tables(conn: sqlite3.Connection) -> None:
    """Initialize analytics tables.
    
    Args:
        conn: Database connection
    """
    try:
        conn.executescript(SQL_CREATE_ANALYTICS_TABLES)
        conn.commit()
        logger.info("Analytics tables initialized")
    except Exception as e:
        logger.error(f"Failed to initialize analytics tables: {e}")
        raise

