"""Database engine with SQLite WAL and Postgres support."""

from __future__ import annotations

import logging
import os
import random
import sqlite3
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def configure_sqlite_for_concurrency(conn: sqlite3.Connection) -> None:
    """Configure SQLite for high concurrency.
    
    Enables WAL mode and optimizes for concurrent access.
    
    Args:
        conn: SQLite connection
    """
    # Enable WAL mode for better concurrency
    conn.execute("PRAGMA journal_mode=WAL")
    
    # Set synchronous mode to NORMAL (good balance)
    conn.execute("PRAGMA synchronous=NORMAL")
    
    # Set busy timeout (5 seconds)
    conn.execute("PRAGMA busy_timeout=5000")
    
    # Set journal size limit (32MB)
    conn.execute("PRAGMA journal_size_limit=33554432")
    
    # Enable foreign keys
    conn.execute("PRAGMA foreign_keys=ON")
    
    logger.info("SQLite configured for high concurrency (WAL mode, 5s timeout)")


def get_sqlite_connection(db_path: Path) -> sqlite3.Connection:
    """Get SQLite connection with concurrency optimizations.
    
    Args:
        db_path: Database file path
        
    Returns:
        Configured SQLite connection
    """
    conn = sqlite3.connect(db_path, check_same_thread=False)
    configure_sqlite_for_concurrency(conn)
    return conn


def retry_on_locked(func, max_retries: int = 5, base_delay: float = 0.1):
    """Retry function on database locked errors with exponential backoff and jitter.
    
    Args:
        func: Function to retry
        max_retries: Maximum retry attempts
        base_delay: Base delay in seconds
        
    Returns:
        Function result
        
    Raises:
        sqlite3.OperationalError: If all retries exhausted
    """
    last_error = None
    
    for attempt in range(max_retries):
        try:
            return func()
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e) or "locked" in str(e).lower():
                last_error = e
                
                # Exponential backoff with jitter
                delay = base_delay * (2 ** attempt)
                jitter = random.uniform(0, delay * 0.1)
                total_delay = delay + jitter
                
                logger.warning(
                    f"Database locked, retry {attempt + 1}/{max_retries} "
                    f"after {total_delay:.3f}s"
                )
                
                time.sleep(total_delay)
            else:
                # Not a lock error, re-raise immediately
                raise
    
    # All retries exhausted
    logger.error(f"Database locked after {max_retries} retries")
    raise last_error


class CounterStore(ABC):
    """Abstract counter store for usage tracking."""
    
    @abstractmethod
    def increment(self, period_key: str, tenant_id: str, count: int = 1) -> int:
        """Increment counter for period.
        
        Args:
            period_key: Period key (e.g., "2025-01")
            tenant_id: Tenant ID
            count: Amount to increment
            
        Returns:
            New counter value
        """
        pass
    
    @abstractmethod
    def get(self, period_key: str, tenant_id: str) -> int:
        """Get counter value.
        
        Args:
            period_key: Period key
            tenant_id: Tenant ID
            
        Returns:
            Counter value
        """
        pass
    
    @abstractmethod
    def close(self) -> None:
        """Close connection."""
        pass


class SQLiteCounterStore(CounterStore):
    """SQLite-based counter store with WAL mode and retries."""
    
    def __init__(self, db_path: Path = Path("history.db")):
        """Initialize SQLite counter store.
        
        Args:
            db_path: Database path
        """
        self.db_path = db_path
        self._init_tables()
        
        logger.info(f"SQLiteCounterStore initialized: {db_path}")
    
    def _init_tables(self) -> None:
        """Initialize tables."""
        def _create():
            conn = get_sqlite_connection(self.db_path)
            
            try:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS usage_counters (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tenant_id TEXT NOT NULL,
                        period_key TEXT NOT NULL,
                        count INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(tenant_id, period_key)
                    )
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_counters_tenant_period
                    ON usage_counters(tenant_id, period_key)
                """)
                
                conn.commit()
            finally:
                conn.close()
        
        retry_on_locked(_create)
    
    def increment(self, period_key: str, tenant_id: str, count: int = 1) -> int:
        """Increment counter with retry logic.
        
        Args:
            period_key: Period key
            tenant_id: Tenant ID
            count: Amount to increment
            
        Returns:
            New counter value
        """
        def _increment():
            conn = get_sqlite_connection(self.db_path)
            
            try:
                # Upsert with increment
                conn.execute("""
                    INSERT INTO usage_counters (tenant_id, period_key, count)
                    VALUES (?, ?, ?)
                    ON CONFLICT(tenant_id, period_key) DO UPDATE SET
                        count = count + ?,
                        updated_at = CURRENT_TIMESTAMP
                """, (tenant_id, period_key, count, count))
                
                # Get new value
                cur = conn.cursor()
                cur.execute("""
                    SELECT count FROM usage_counters
                    WHERE tenant_id = ? AND period_key = ?
                """, (tenant_id, period_key))
                
                row = cur.fetchone()
                new_value = row[0] if row else 0
                
                conn.commit()
                
                return new_value
            
            finally:
                conn.close()
        
        return retry_on_locked(_increment)
    
    def get(self, period_key: str, tenant_id: str) -> int:
        """Get counter value.
        
        Args:
            period_key: Period key
            tenant_id: Tenant ID
            
        Returns:
            Counter value
        """
        def _get():
            conn = get_sqlite_connection(self.db_path)
            
            try:
                cur = conn.cursor()
                cur.execute("""
                    SELECT count FROM usage_counters
                    WHERE tenant_id = ? AND period_key = ?
                """, (tenant_id, period_key))
                
                row = cur.fetchone()
                return row[0] if row else 0
            
            finally:
                conn.close()
        
        return retry_on_locked(_get)
    
    def close(self) -> None:
        """Close connection (no-op for SQLite)."""
        pass


class PostgresCounterStore(CounterStore):
    """Postgres-based counter store."""
    
    def __init__(self, database_url: str):
        """Initialize Postgres counter store.
        
        Args:
            database_url: Postgres connection URL
        """
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
        except ImportError:
            raise ImportError("psycopg2 required for Postgres support")
        
        self.database_url = database_url
        self.conn = psycopg2.connect(database_url)
        self.conn.autocommit = True
        
        self._init_tables()
        
        logger.info(f"PostgresCounterStore initialized")
    
    def _init_tables(self) -> None:
        """Initialize tables."""
        with self.conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS usage_counters (
                    id SERIAL PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    period_key TEXT NOT NULL,
                    count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(tenant_id, period_key)
                )
            """)
            
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_counters_tenant_period
                ON usage_counters(tenant_id, period_key)
            """)
    
    def increment(self, period_key: str, tenant_id: str, count: int = 1) -> int:
        """Increment counter.
        
        Args:
            period_key: Period key
            tenant_id: Tenant ID
            count: Amount to increment
            
        Returns:
            New counter value
        """
        with self.conn.cursor() as cur:
            # Upsert with RETURNING
            cur.execute("""
                INSERT INTO usage_counters (tenant_id, period_key, count)
                VALUES (%s, %s, %s)
                ON CONFLICT(tenant_id, period_key) DO UPDATE SET
                    count = usage_counters.count + %s,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING count
            """, (tenant_id, period_key, count, count))
            
            row = cur.fetchone()
            return row[0] if row else 0
    
    def get(self, period_key: str, tenant_id: str) -> int:
        """Get counter value.
        
        Args:
            period_key: Period key
            tenant_id: Tenant ID
            
        Returns:
            Counter value
        """
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT count FROM usage_counters
                WHERE tenant_id = %s AND period_key = %s
            """, (tenant_id, period_key))
            
            row = cur.fetchone()
            return row[0] if row else 0
    
    def close(self) -> None:
        """Close connection."""
        if self.conn:
            self.conn.close()


def get_counter_store(database_url: Optional[str] = None) -> CounterStore:
    """Get counter store based on configuration.
    
    Args:
        database_url: Optional database URL (uses DATABASE_URL env if None)
        
    Returns:
        CounterStore instance (SQLite or Postgres)
    """
    if database_url is None:
        database_url = os.getenv("DATABASE_URL", "")
    
    # Check if Postgres
    if database_url.startswith("postgres://") or database_url.startswith("postgresql://"):
        logger.info("Using PostgresCounterStore")
        return PostgresCounterStore(database_url)
    
    # Default to SQLite
    db_path = Path(database_url) if database_url else Path("history.db")
    logger.info(f"Using SQLiteCounterStore: {db_path}")
    return SQLiteCounterStore(db_path)


__all__ = [
    "CounterStore",
    "SQLiteCounterStore",
    "PostgresCounterStore",
    "get_counter_store",
    "configure_sqlite_for_concurrency",
    "retry_on_locked",
]

