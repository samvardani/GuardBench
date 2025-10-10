"""Database operations for Slack installations."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

DB_PATH = Path("history.db")


def init_slack_tables(conn: sqlite3.Connection) -> None:
    """Initialize Slack installation tables.
    
    Args:
        conn: Database connection
    """
    conn.execute("""
        CREATE TABLE IF NOT EXISTS slack_installations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id TEXT NOT NULL UNIQUE,
            team_name TEXT NOT NULL,
            encrypted_access_token TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_slack_team 
        ON slack_installations(team_id)
    """)
    
    conn.commit()
    logger.info("Slack installation tables initialized")


def store_installation(
    team_id: str,
    team_name: str,
    encrypted_access_token: str,
    db_path: Path = DB_PATH
) -> None:
    """Store Slack installation.
    
    Args:
        team_id: Slack team ID
        team_name: Slack team name
        encrypted_access_token: Encrypted access token
        db_path: Database path
    """
    conn = sqlite3.connect(db_path)
    
    try:
        # Ensure tables exist
        init_slack_tables(conn)
        
        # Store installation
        conn.execute("""
            INSERT INTO slack_installations (team_id, team_name, encrypted_access_token)
            VALUES (?, ?, ?)
            ON CONFLICT(team_id) DO UPDATE SET
                team_name = ?,
                encrypted_access_token = ?,
                updated_at = CURRENT_TIMESTAMP
        """, (team_id, team_name, encrypted_access_token, team_name, encrypted_access_token))
        
        conn.commit()
        
        logger.info(f"Stored Slack installation for team {team_id}")
    
    except Exception as e:
        logger.error(f"Failed to store Slack installation: {e}")
        conn.rollback()
        raise
    
    finally:
        conn.close()


def get_installation(team_id: str, db_path: Path = DB_PATH) -> Optional[Dict[str, str]]:
    """Get Slack installation by team ID.
    
    Args:
        team_id: Slack team ID
        db_path: Database path
        
    Returns:
        Installation data or None
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT team_id, team_name, encrypted_access_token
            FROM slack_installations
            WHERE team_id = ?
        """, (team_id,))
        
        row = cur.fetchone()
        
        if row:
            return {
                "team_id": row["team_id"],
                "team_name": row["team_name"],
                "encrypted_access_token": row["encrypted_access_token"]
            }
        
        return None
    
    finally:
        conn.close()


def get_decrypted_token(team_id: str, db_path: Path = DB_PATH) -> Optional[str]:
    """Get decrypted access token for team.
    
    Args:
        team_id: Slack team ID
        db_path: Database path
        
    Returns:
        Decrypted access token or None
    """
    installation = get_installation(team_id, db_path)
    
    if not installation:
        return None
    
    from security import get_crypto_box
    
    crypto_box = get_crypto_box()
    
    try:
        return crypto_box.decrypt(installation["encrypted_access_token"])
    except Exception as e:
        logger.error(f"Failed to decrypt Slack token for team {team_id}: {e}")
        return None


__all__ = [
    "init_slack_tables",
    "store_installation",
    "get_installation",
    "get_decrypted_token",
]

