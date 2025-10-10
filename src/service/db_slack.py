"""Database schema extension for Slack installations."""

from __future__ import annotations

import logging
import sqlite3
from typing import Optional

logger = logging.getLogger(__name__)


SQL_CREATE_SLACK_INSTALLATIONS = """
CREATE TABLE IF NOT EXISTS slack_installations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id TEXT NOT NULL UNIQUE,
    team_name TEXT,
    access_token TEXT NOT NULL,
    bot_user_id TEXT,
    scope TEXT,
    app_id TEXT,
    installed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_slack_team_id ON slack_installations(team_id);
"""


def init_slack_tables(conn: sqlite3.Connection) -> None:
    """Initialize Slack-related database tables.
    
    Args:
        conn: Database connection
    """
    try:
        conn.executescript(SQL_CREATE_SLACK_INSTALLATIONS)
        conn.commit()
        logger.info("Slack installations table initialized")
    except Exception as e:
        logger.error(f"Failed to initialize Slack tables: {e}")


def store_slack_installation(
    conn: sqlite3.Connection,
    team_id: str,
    team_name: str,
    access_token: str,
    bot_user_id: str,
    scope: str,
    app_id: str,
) -> bool:
    """Store Slack installation.
    
    Args:
        conn: Database connection
        team_id: Slack team ID
        team_name: Team name
        access_token: OAuth access token
        bot_user_id: Bot user ID
        scope: Granted scopes
        app_id: App ID
        
    Returns:
        True if stored successfully
    """
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO slack_installations (team_id, team_name, access_token, bot_user_id, scope, app_id)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(team_id) DO UPDATE SET
                team_name = excluded.team_name,
                access_token = excluded.access_token,
                bot_user_id = excluded.bot_user_id,
                scope = excluded.scope,
                app_id = excluded.app_id,
                updated_at = CURRENT_TIMESTAMP
            """,
            (team_id, team_name, access_token, bot_user_id, scope, app_id)
        )
        conn.commit()
        logger.info(f"Stored Slack installation for team: {team_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to store Slack installation: {e}")
        return False


def get_slack_installation(conn: sqlite3.Connection, team_id: str) -> Optional[Dict[str, Any]]:
    """Get Slack installation for team.
    
    Args:
        conn: Database connection
        team_id: Slack team ID
        
    Returns:
        Installation dict if found
    """
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT team_id, team_name, access_token, bot_user_id, scope, app_id FROM slack_installations WHERE team_id = ?",
            (team_id,)
        )
        row = cur.fetchone()
        
        if row:
            return {
                "team_id": row[0],
                "team_name": row[1],
                "access_token": row[2],
                "bot_user_id": row[3],
                "scope": row[4],
                "app_id": row[5],
            }
        return None
    except Exception as e:
        logger.error(f"Failed to get Slack installation: {e}")
        return None


from typing import Any, Dict

