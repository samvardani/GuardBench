import pathlib
import sqlite3
from typing import Iterable

DB_PATH = pathlib.Path(__file__).resolve().parents[2] / "history.db"


def _ensure_column(cursor: sqlite3.Cursor, table: str, column: str, definition: str) -> None:
    """Add a column to a table when it is missing."""
    info = cursor.execute(f"PRAGMA table_info({table})").fetchall()
    columns = {row[1] for row in info}
    if column not in columns:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {definition}")


def _ensure_index(cursor: sqlite3.Cursor, name: str, ddl: str) -> None:
    """Create an index when it does not exist."""
    existing = cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name=?", (name,)
    ).fetchone()
    if not existing:
        cursor.execute(ddl)


def main():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("PRAGMA journal_mode=WAL;")
    cur.executescript(
        """
    CREATE TABLE IF NOT EXISTS runs (
      run_id TEXT PRIMARY KEY,
      created_at TEXT,
      dataset_path TEXT,
      dataset_sha TEXT,
      git_commit TEXT,
      policy_version TEXT,
      engine_baseline TEXT,
      engine_candidate TEXT,
      tenant_id TEXT,
      run_status TEXT DEFAULT 'completed'
    );
    CREATE TABLE IF NOT EXISTS metrics (
      run_id TEXT,
      model TEXT,
      tp INTEGER, fp INTEGER, tn INTEGER, fn INTEGER,
      precision REAL, recall REAL, fnr REAL, fpr REAL,
      p50_ms INTEGER, p90_ms INTEGER, p99_ms INTEGER,
      tenant_id TEXT,
      PRIMARY KEY (run_id, model)
    );
    CREATE TABLE IF NOT EXISTS results (
      run_id TEXT,
      sample_id TEXT,
      model TEXT,
      gt_label TEXT,
      gt_category TEXT,
      gt_language TEXT,
      attack_type TEXT,
      prediction TEXT,
      score REAL,
      latency_ms INTEGER,
      tenant_id TEXT
    );
    CREATE TABLE IF NOT EXISTS tenants (
      tenant_id TEXT PRIMARY KEY,
      name TEXT NOT NULL,
      slug TEXT NOT NULL UNIQUE,
      created_at TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'active',
      metadata TEXT
    );
    CREATE TABLE IF NOT EXISTS users (
      user_id TEXT PRIMARY KEY,
      tenant_id TEXT NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
      email TEXT NOT NULL,
      email_normalized TEXT NOT NULL,
      password_hash TEXT NOT NULL,
      role TEXT NOT NULL DEFAULT 'viewer',
      status TEXT NOT NULL DEFAULT 'active',
      created_at TEXT NOT NULL,
      last_login_at TEXT,
      UNIQUE(tenant_id, email_normalized)
    );
    CREATE TABLE IF NOT EXISTS api_tokens (
      token_id TEXT PRIMARY KEY,
      tenant_id TEXT NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
      user_id TEXT REFERENCES users(user_id) ON DELETE SET NULL,
      token_hash TEXT NOT NULL,
      label TEXT,
      scopes TEXT,
      created_at TEXT NOT NULL,
      expires_at TEXT,
      last_used_at TEXT,
      UNIQUE(token_hash)
    );
    CREATE TABLE IF NOT EXISTS audit_events (
      event_id TEXT PRIMARY KEY,
      tenant_id TEXT NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
      user_id TEXT,
      actor_type TEXT NOT NULL,
      action TEXT NOT NULL,
      resource TEXT,
      context TEXT,
      created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS integrations (
      integration_id TEXT PRIMARY KEY,
      tenant_id TEXT NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
      kind TEXT NOT NULL,
      name TEXT,
      config TEXT,
      enabled INTEGER NOT NULL DEFAULT 0,
      created_at TEXT NOT NULL,
      last_synced_at TEXT
    );
    CREATE TABLE IF NOT EXISTS alerts (
      alert_id TEXT PRIMARY KEY,
      tenant_id TEXT NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
      severity TEXT NOT NULL,
      title TEXT NOT NULL,
      message TEXT,
      run_id TEXT,
      created_at TEXT NOT NULL,
      acknowledged_at TEXT,
      metadata TEXT
    );
    CREATE TABLE IF NOT EXISTS reports (
      report_id TEXT PRIMARY KEY,
      tenant_id TEXT NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
      run_id TEXT,
      title TEXT,
      summary TEXT,
      created_at TEXT NOT NULL,
      path TEXT
    );
    """
    )

    # Backfill columns when older schema versions are detected.
    _ensure_column(cur, "runs", "tenant_id", "tenant_id TEXT")
    _ensure_column(cur, "runs", "run_status", "run_status TEXT DEFAULT 'completed'")
    _ensure_column(cur, "metrics", "tenant_id", "tenant_id TEXT")
    _ensure_column(cur, "results", "tenant_id", "tenant_id TEXT")

    indexes: Iterable[tuple[str, str]] = (
        (
            "idx_users_email",
            "CREATE UNIQUE INDEX idx_users_email ON users(tenant_id, email_normalized)",
        ),
        (
            "idx_tokens_token_hash",
            "CREATE UNIQUE INDEX idx_tokens_token_hash ON api_tokens(token_hash)",
        ),
        (
            "idx_audit_tenant_created",
            "CREATE INDEX idx_audit_tenant_created ON audit_events(tenant_id, created_at DESC)",
        ),
        ("idx_alerts_tenant_created", "CREATE INDEX idx_alerts_tenant_created ON alerts(tenant_id, created_at DESC)"),
        ("idx_integrations_tenant_kind", "CREATE INDEX idx_integrations_tenant_kind ON integrations(tenant_id, kind)"),
        ("idx_runs_tenant_created", "CREATE INDEX idx_runs_tenant_created ON runs(tenant_id, created_at DESC)"),
    )
    for name, ddl in indexes:
        _ensure_index(cur, name, ddl)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_results_run_model ON results(run_id, model)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_results_sample ON results(sample_id)")
    con.commit()
    print(f"DB ready at {DB_PATH}")
    con.close()

if __name__ == "__main__":
    main()
