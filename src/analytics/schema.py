"""Database schema for benchmark leaderboard."""

from __future__ import annotations

import logging
import sqlite3

logger = logging.getLogger(__name__)


SQL_CREATE_BENCHMARK_TABLES = """
CREATE TABLE IF NOT EXISTS benchmark_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dataset_name TEXT NOT NULL,
    guard_name TEXT NOT NULL,
    guard_version TEXT,
    guard_config TEXT,  -- JSON config
    run_id TEXT,
    tenant_id TEXT,
    
    -- Metrics
    precision REAL,
    recall REAL,
    f1_score REAL,
    fnr REAL,  -- False Negative Rate
    fpr REAL,  -- False Positive Rate
    
    -- Confusion Matrix
    tp INTEGER,
    fp INTEGER,
    tn INTEGER,
    fn INTEGER,
    
    -- Performance
    avg_latency_ms INTEGER,
    p50_latency_ms INTEGER,
    p90_latency_ms INTEGER,
    p99_latency_ms INTEGER,
    
    -- Metadata
    dataset_size INTEGER,
    categories TEXT,  -- Comma-separated
    languages TEXT,   -- Comma-separated
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Public visibility
    is_public INTEGER DEFAULT 0,
    
    UNIQUE(dataset_name, guard_name, tenant_id, created_at)
);

CREATE INDEX IF NOT EXISTS idx_benchmark_dataset 
ON benchmark_results(dataset_name, is_public);

CREATE INDEX IF NOT EXISTS idx_benchmark_tenant 
ON benchmark_results(tenant_id, dataset_name);

CREATE INDEX IF NOT EXISTS idx_benchmark_f1 
ON benchmark_results(dataset_name, f1_score DESC);

CREATE TABLE IF NOT EXISTS benchmark_datasets (
    dataset_name TEXT PRIMARY KEY,
    description TEXT,
    size INTEGER,
    categories TEXT,  -- Comma-separated
    languages TEXT,   -- Comma-separated
    source_url TEXT,
    is_official INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def init_benchmark_tables(conn: sqlite3.Connection) -> None:
    """Initialize benchmark leaderboard tables.
    
    Args:
        conn: Database connection
    """
    try:
        conn.executescript(SQL_CREATE_BENCHMARK_TABLES)
        conn.commit()
        logger.info("Benchmark leaderboard tables initialized")
    except Exception as e:
        logger.error(f"Failed to initialize benchmark tables: {e}")
        raise

