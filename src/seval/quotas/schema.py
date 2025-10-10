"""Database schema for usage tracking."""

from __future__ import annotations

import logging
import sqlite3

logger = logging.getLogger(__name__)


SQL_CREATE_USAGE_TABLES = """
CREATE TABLE IF NOT EXISTS tenant_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id TEXT NOT NULL,
    period TEXT NOT NULL,  -- Format: YYYY-MM
    usage_count INTEGER DEFAULT 0,
    last_reset_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, period)
);

CREATE INDEX IF NOT EXISTS idx_tenant_usage_lookup 
ON tenant_usage(tenant_id, period);

CREATE TABLE IF NOT EXISTS tenant_plans (
    tenant_id TEXT PRIMARY KEY,
    plan_type TEXT NOT NULL DEFAULT 'free',  -- free, starter, pro, enterprise
    monthly_quota INTEGER,  -- NULL = unlimited
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id)
);
"""


def init_usage_tables(conn: sqlite3.Connection) -> None:
    """Initialize usage tracking tables.
    
    Args:
        conn: Database connection
    """
    try:
        conn.executescript(SQL_CREATE_USAGE_TABLES)
        conn.commit()
        logger.info("Usage tracking tables initialized")
    except Exception as e:
        logger.error(f"Failed to initialize usage tables: {e}")
        raise

