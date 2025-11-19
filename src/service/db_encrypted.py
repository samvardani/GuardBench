"""
Database encryption using SQLCipher.

This module provides encrypted database connections using SQLCipher (AES-256).
Can be used as a drop-in replacement for standard sqlite3 connections.

Usage:
    from service.db_encrypted import get_encrypted_key, db_conn_encrypted
    
    # Get encryption key from environment
    key = get_encrypted_key()
    
    # Use encrypted connection
    with db_conn_encrypted(key) as con:
        con.execute("SELECT * FROM users")
"""
import os
import secrets
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

try:
    from pysqlcipher3 import dbapi2 as sqlite_encrypted
    SQLCIPHER_AVAILABLE = True
except ImportError:
    SQLCIPHER_AVAILABLE = False
    sqlite_encrypted = None


def get_encrypted_key() -> Optional[str]:
    """
    Get database encryption key from environment.
    
    Returns:
        Encryption key from DB_ENCRYPTION_KEY environment variable,
        or None if not set.
    """
    return os.getenv("DB_ENCRYPTION_KEY")


def generate_encryption_key() -> str:
    """
    Generate a new random encryption key.
    
    Returns:
        64-character hex string (256-bit key)
        
    Example:
        >>> key = generate_encryption_key()
        >>> print(f"DB_ENCRYPTION_KEY={key}")
        DB_ENCRYPTION_KEY=a3b7c9...
    """
    # Generate 32 bytes (256 bits) of random data
    key_bytes = secrets.token_bytes(32)
    return key_bytes.hex()


@contextmanager
def db_conn_encrypted(db_path: Path, encryption_key: str, commit: bool = True):
    """
    Context manager for encrypted database connections.
    
    Args:
        db_path: Path to database file
        encryption_key: Encryption key (hex string)
        commit: Whether to commit on success (default: True)
        
    Yields:
        SQLite connection with encryption enabled
        
    Example:
        >>> key = get_encrypted_key()
        >>> with db_conn_encrypted(Path("data.db"), key) as con:
        ...     con.execute("SELECT * FROM users")
    """
    if not SQLCIPHER_AVAILABLE:
        raise ImportError("pysqlcipher3 not installed. Run: pip install pysqlcipher3")
    
    con = sqlite_encrypted.connect(str(db_path))
    con.row_factory = sqlite_encrypted.Row
    
    # Set encryption key
    con.execute(f"PRAGMA key = '{encryption_key}';")
    
    # Verify database is accessible
    try:
        con.execute("SELECT count(*) FROM sqlite_master;")
    except sqlite_encrypted.DatabaseError as e:
        con.close()
        raise ValueError(f"Failed to decrypt database. Wrong key? Error: {e}")
    
    try:
        yield con
        if commit:
            con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def encrypt_existing_database(source_db: Path, target_db: Path, encryption_key: str) -> None:
    """
    Encrypt an existing unencrypted database.
    
    Args:
        source_db: Path to existing unencrypted database
        target_db: Path to new encrypted database
        encryption_key: Encryption key to use
        
    Raises:
        FileNotFoundError: If source database doesn't exist
        ValueError: If target database already exists
        
    Example:
        >>> key = generate_encryption_key()
        >>> encrypt_existing_database(
        ...     Path("history.db"),
        ...     Path("history_encrypted.db"),
        ...     key
        ... )
    """
    if not source_db.exists():
        raise FileNotFoundError(f"Source database not found: {source_db}")
    
    if target_db.exists():
        raise ValueError(f"Target database already exists: {target_db}. Remove it first.")
    
    if not SQLCIPHER_AVAILABLE:
        raise ImportError("pysqlcipher3 not installed")
    
    # Open source (unencrypted)
    import sqlite3
    source_con = sqlite3.connect(str(source_db))
    
    # Create target (encrypted)
    target_con = sqlite_encrypted.connect(str(target_db))
    target_con.execute(f"PRAGMA key = '{encryption_key}';")
    
    # Copy schema and data
    for line in source_con.iterdump():
        if line not in ('BEGIN;', 'COMMIT;'):
            target_con.execute(line)
    
    target_con.commit()
    
    # Verify
    source_count = source_con.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table';").fetchone()[0]
    target_count = target_con.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table';").fetchone()[0]
    
    source_con.close()
    target_con.close()
    
    if source_count != target_count:
        raise ValueError(f"Verification failed: {source_count} vs {target_count} tables")
    
    print(f"✅ Encrypted {source_count} tables from {source_db} to {target_db}")


def is_database_encrypted(db_path: Path) -> bool:
    """
    Check if a database file is encrypted.
    
    Args:
        db_path: Path to database file
        
    Returns:
        True if encrypted, False if not
    """
    if not db_path.exists():
        return False
    
    # Try to open without key (unencrypted)
    import sqlite3
    try:
        con = sqlite3.connect(str(db_path))
        con.execute("SELECT COUNT(*) FROM sqlite_master;")
        con.close()
        return False  # Opened successfully = not encrypted
    except sqlite3.DatabaseError:
        return True  # Failed to open = likely encrypted

