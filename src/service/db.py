"""Database helpers for multi-tenant user management and audit logging."""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import secrets
import sqlite3
import string
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Optional

from store import init_db

DB_PATH = Path(__file__).resolve().parents[2] / "history.db"
_PBKDF2_ROUNDS = 160_000
_TOKEN_BYTES = 32
_SCHEMA_READY = False


def ensure_schema() -> None:
    """Ensure the SQLite schema contains the latest tables and indexes."""
    global _SCHEMA_READY
    if _SCHEMA_READY and DB_PATH.exists():
        return
    init_db.main()
    _SCHEMA_READY = True


def _connect() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


@contextmanager
def db_conn(commit: bool = True):
    con = _connect()
    try:
        yield con
        if commit:
            con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


def _slugify(name: str) -> str:
    allowed = string.ascii_lowercase + string.digits + "-"
    cleaned = name.strip().lower().replace(" ", "-")
    slug = "".join(ch for ch in cleaned if ch in allowed)
    slug = slug.strip("-")
    return slug or secrets.token_hex(4)


def _hash_password(password: str, *, salt: Optional[bytes] = None) -> str:
    if salt is None:
        salt = secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ROUNDS)
    return f"pbkdf2_sha256${_PBKDF2_ROUNDS}${salt.hex()}${derived.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, rounds, salt_hex, hash_hex = stored.split("$")
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    try:
        rounds_int = int(rounds)
        salt = bytes.fromhex(salt_hex)
    except (ValueError, TypeError):
        return False
    compare = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, rounds_int)
    return secrets.compare_digest(compare.hex(), hash_hex)


def _token_pair() -> tuple[str, str]:
    token = secrets.token_urlsafe(_TOKEN_BYTES)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return token, token_hash


def create_tenant(name: str, *, slug: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    ensure_schema()
    tenant_id = uuid.uuid4().hex
    slug_value = slug or _slugify(name)
    created = _now()
    serialized = json.dumps(metadata or {})
    with db_conn() as con:
        cur = con.cursor()
        try:
            cur.execute(
                "INSERT INTO tenants (tenant_id, name, slug, created_at, status, metadata) VALUES (?, ?, ?, ?, 'active', ?)",
                (tenant_id, name, slug_value, created, serialized),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError("Tenant slug already exists") from exc
    return {
        "tenant_id": tenant_id,
        "name": name,
        "slug": slug_value,
        "metadata": metadata or {},
        "created_at": created,
    }


def get_user_by_email(tenant_id: str, email: str) -> Optional[Dict[str, Any]]:
    """Get user by email.
    
    Args:
        tenant_id: Tenant ID
        email: User email (case-insensitive)
        
    Returns:
        User dictionary or None
    """
    ensure_schema()
    email_lower = email.lower().strip()
    with db_conn(commit=False) as con:
        row = con.execute(
            "SELECT * FROM users WHERE tenant_id = ? AND LOWER(email) = ? AND status = 'active'",
            (tenant_id, email_lower)
        ).fetchone()
    if not row:
        return None
    return dict(row)


def create_token(tenant_id: str, user_id: str, *, role: str = "viewer", label: Optional[str] = None, ttl_minutes: Optional[int] = None) -> Dict[str, Any]:
    """Create API token for user.
    
    Args:
        tenant_id: Tenant ID
        user_id: User ID
        role: User role
        label: Optional token label
        ttl_minutes: Optional TTL in minutes
        
    Returns:
        Token dictionary with 'token' key
    """
    return issue_token(user_id, tenant_id, label=label, ttl_minutes=ttl_minutes)


def create_user(
    tenant_id: str,
    email: str,
    password: str,
    *,
    role: str = "viewer",
    status: str = "active",
) -> Dict[str, Any]:
    ensure_schema()
    user_id = uuid.uuid4().hex
    created = _now()
    normalized = _normalize_email(email)
    password_hash = _hash_password(password)
    with db_conn() as con:
        cur = con.cursor()
        try:
            cur.execute(
                """
                INSERT INTO users (user_id, tenant_id, email, email_normalized, password_hash, role, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, tenant_id, email, normalized, password_hash, role, status, created),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError("User already exists for tenant") from exc
    return {
        "user_id": user_id,
        "tenant_id": tenant_id,
        "email": email,
        "role": role,
        "status": status,
        "created_at": created,
    }


def authenticate_user(email: str, password: str, *, tenant_slug: Optional[str] = None) -> Optional[Dict[str, Any]]:
    ensure_schema()
    normalized = _normalize_email(email)
    query = (
        "SELECT u.*, t.slug, t.name FROM users u JOIN tenants t ON u.tenant_id = t.tenant_id "
        "WHERE u.email_normalized = ?"
    )
    params: list[Any] = [normalized]
    if tenant_slug:
        query += " AND t.slug = ?"
        params.append(tenant_slug.lower())
    with db_conn(commit=False) as con:
        row = con.execute(query, params).fetchone()
    if not row:
        return None
    if row["status"] != "active":
        return None
    if not _verify_password(password, row["password_hash"]):
        return None
    with db_conn() as con:
        con.execute(
            "UPDATE users SET last_login_at = ? WHERE user_id = ?",
            (_now(), row["user_id"]),
        )
    payload = dict(row)
    payload.pop("password_hash", None)
    return payload


def issue_token(user_id: str, tenant_id: str, *, label: Optional[str] = None, ttl_minutes: Optional[int] = None) -> Dict[str, Any]:
    ensure_schema()
    raw_token, token_hash = _token_pair()
    created = _now()
    expires_at: Optional[str] = None
    if ttl_minutes:
        expires_at = (_dt.datetime.now(_dt.timezone.utc) + _dt.timedelta(minutes=ttl_minutes)).isoformat()
    token_id = uuid.uuid4().hex
    with db_conn() as con:
        con.execute(
            """
            INSERT INTO api_tokens (token_id, tenant_id, user_id, token_hash, label, scopes, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (token_id, tenant_id, user_id, token_hash, label, json.dumps(["api"]), created, expires_at),
        )
    return {
        "token": raw_token,
        "token_id": token_id,
        "tenant_id": tenant_id,
        "user_id": user_id,
        "created_at": created,
        "expires_at": expires_at,
    }


def resolve_token(bearer_token: str) -> Optional[Dict[str, Any]]:
    ensure_schema()
    token_hash = hashlib.sha256(bearer_token.encode("utf-8")).hexdigest()
    query = (
        "SELECT t.token_id, t.tenant_id, t.user_id, t.scopes, t.expires_at, u.email, u.role, u.status, te.slug "
        "FROM api_tokens t "
        "LEFT JOIN users u ON t.user_id = u.user_id "
        "JOIN tenants te ON t.tenant_id = te.tenant_id "
        "WHERE t.token_hash = ?"
    )
    with db_conn(commit=False) as con:
        row = con.execute(query, (token_hash,)).fetchone()
    if not row:
        return None
    if row["expires_at"]:
        expires = _dt.datetime.fromisoformat(row["expires_at"])
        if expires < _dt.datetime.utcnow().replace(tzinfo=_dt.timezone.utc):
            return None
    with db_conn() as con:
        con.execute(
            "UPDATE api_tokens SET last_used_at = ? WHERE token_id = ?",
            (_now(), row["token_id"]),
        )
    payload = dict(row)
    if payload.get("scopes"):
        try:
            payload["scopes"] = json.loads(payload["scopes"])
        except json.JSONDecodeError:
            payload["scopes"] = []
    return payload


def create_audit_event(
    tenant_id: str,
    *,
    action: str,
    resource: Optional[str] = None,
    actor_type: str = "user",
    user_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
) -> None:
    ensure_schema()
    event_id = uuid.uuid4().hex
    serialized = json.dumps(context or {})
    with db_conn() as con:
        con.execute(
            """
            INSERT INTO audit_events (event_id, tenant_id, user_id, actor_type, action, resource, context, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (event_id, tenant_id, user_id, actor_type, action, resource, serialized, _now()),
        )


def list_audit_events(tenant_id: str, *, limit: int = 50) -> list[Dict[str, Any]]:
    ensure_schema()
    with db_conn(commit=False) as con:
        rows = con.execute(
            "SELECT * FROM audit_events WHERE tenant_id = ? ORDER BY created_at DESC LIMIT ?",
            (tenant_id, limit),
        ).fetchall()
    entries: list[Dict[str, Any]] = []
    for row in rows:
        payload = dict(row)
        if payload.get("context"):
            try:
                payload["context"] = json.loads(payload["context"])
            except json.JSONDecodeError:
                payload["context"] = {}
        entries.append(payload)
    return entries


def record_alert(
    tenant_id: str,
    *,
    severity: str,
    title: str,
    message: Optional[str] = None,
    run_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    ensure_schema()
    alert_id = uuid.uuid4().hex
    payload = json.dumps(metadata or {})
    created = _now()
    with db_conn() as con:
        con.execute(
            """
            INSERT INTO alerts (alert_id, tenant_id, severity, title, message, run_id, created_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (alert_id, tenant_id, severity, title, message, run_id, created, payload),
        )
    return {
        "alert_id": alert_id,
        "tenant_id": tenant_id,
        "severity": severity,
        "title": title,
        "message": message,
        "run_id": run_id,
        "created_at": created,
        "metadata": metadata or {},
    }


def list_alerts(tenant_id: str, *, limit: int = 20) -> list[Dict[str, Any]]:
    ensure_schema()
    with db_conn(commit=False) as con:
        rows = con.execute(
            "SELECT * FROM alerts WHERE tenant_id = ? ORDER BY created_at DESC LIMIT ?",
            (tenant_id, limit),
        ).fetchall()
    alerts: list[Dict[str, Any]] = []
    for row in rows:
        payload = dict(row)
        if payload.get("metadata"):
            try:
                payload["metadata"] = json.loads(payload["metadata"])
            except json.JSONDecodeError:
                payload["metadata"] = {}
        alerts.append(payload)
    return alerts


def acknowledge_alert(alert_id: str) -> None:
    ensure_schema()
    with db_conn() as con:
        con.execute(
            "UPDATE alerts SET acknowledged_at = ? WHERE alert_id = ?",
            (_now(), alert_id),
        )


def upsert_integration(
    tenant_id: str,
    *,
    kind: str,
    name: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
    enabled: bool = True,
) -> Dict[str, Any]:
    ensure_schema()
    config_json = json.dumps(config or {})
    integration_id = uuid.uuid4().hex
    created = _now()
    with db_conn() as con:
        con.execute(
            """
            INSERT INTO integrations (integration_id, tenant_id, kind, name, config, enabled, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (integration_id, tenant_id, kind, name, config_json, int(enabled), created),
        )
    return {
        "integration_id": integration_id,
        "tenant_id": tenant_id,
        "kind": kind,
        "name": name,
        "config": config or {},
        "enabled": enabled,
        "created_at": created,
    }


def list_integrations(tenant_id: str) -> list[Dict[str, Any]]:
    ensure_schema()
    with db_conn(commit=False) as con:
        rows = con.execute(
            "SELECT * FROM integrations WHERE tenant_id = ? ORDER BY created_at DESC",
            (tenant_id,),
        ).fetchall()
    records: list[Dict[str, Any]] = []
    for row in rows:
        payload = dict(row)
        if payload.get("config"):
            try:
                payload["config"] = json.loads(payload["config"])
            except json.JSONDecodeError:
                payload["config"] = {}
        payload["enabled"] = bool(payload.get("enabled"))
        records.append(payload)
    return records


def record_run(
    tenant_id: str,
    run_id: str,
    *,
    dataset_path: Optional[str] = None,
    dataset_sha: Optional[str] = None,
    git_commit: Optional[str] = None,
    policy_version: Optional[str] = None,
    engine_baseline: Optional[str] = None,
    engine_candidate: Optional[str] = None,
    status: str = "completed",
) -> None:
    ensure_schema()
    created = _now()
    with db_conn() as con:
        # Discover available columns to support older schemas
        cols = {row[1] for row in con.execute("PRAGMA table_info(runs)").fetchall()}  # type: ignore[index]
        base_cols = ["run_id", "created_at", "tenant_id", "run_status"]
        optional_map = {
            "dataset_path": dataset_path,
            "dataset_sha": dataset_sha,
            "git_commit": git_commit,
            "policy_version": policy_version,
            "engine_baseline": engine_baseline,
            "engine_candidate": engine_candidate,
        }
        insert_cols = [c for c in base_cols if c in cols]
        values = [run_id, created, tenant_id, status]
        # Align values with insert_cols ordering
        col_to_value = {
            "run_id": run_id,
            "created_at": created,
            "tenant_id": tenant_id,
            "run_status": status,
        }
        for name, val in optional_map.items():
            if name in cols:
                insert_cols.append(name)
                col_to_value[name] = val
        values = [col_to_value[c] for c in insert_cols]

        placeholders = ", ".join(["?"] * len(insert_cols))
        update_assignments = ", ".join(
            [f"{c} = excluded.{c}" for c in insert_cols if c != "run_id"]
        )
        sql = (
            f"INSERT INTO runs ({', '.join(insert_cols)}) VALUES ({placeholders}) "
            f"ON CONFLICT(run_id) DO UPDATE SET {update_assignments}"
        )
        con.execute(sql, values)


def list_runs(tenant_id: str, *, limit: int = 20) -> list[Dict[str, Any]]:
    ensure_schema()
    with db_conn(commit=False) as con:
        rows = con.execute(
            "SELECT * FROM runs WHERE tenant_id = ? ORDER BY created_at DESC LIMIT ?",
            (tenant_id, limit),
        ).fetchall()
    return [dict(row) for row in rows]


def latest_metrics(run_id: str) -> Dict[str, Any]:
    ensure_schema()
    with db_conn(commit=False) as con:
        rows = con.execute(
            "SELECT model, tp, fp, tn, fn, precision, recall, fnr, fpr, p50_ms, p90_ms, p99_ms FROM metrics WHERE run_id = ?",
            (run_id,),
        ).fetchall()
    return {row["model"]: dict(row) for row in rows}


def upsert_metrics(run_id: str, tenant_id: str, metrics_map: Dict[str, Dict[str, Any]]) -> None:
    ensure_schema()
    with db_conn() as con:
        for model, payload in metrics_map.items():
            con.execute(
                """
                INSERT INTO metrics (run_id, model, tp, fp, tn, fn, precision, recall, fnr, fpr, p50_ms, p90_ms, p99_ms, tenant_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(run_id, model) DO UPDATE SET
                  tp = excluded.tp,
                  fp = excluded.fp,
                  tn = excluded.tn,
                  fn = excluded.fn,
                  precision = excluded.precision,
                  recall = excluded.recall,
                  fnr = excluded.fnr,
                  fpr = excluded.fpr,
                  p50_ms = excluded.p50_ms,
                  p90_ms = excluded.p90_ms,
                  p99_ms = excluded.p99_ms,
                  tenant_id = excluded.tenant_id
                """,
                (
                    run_id,
                    model,
                    payload.get("tp", 0),
                    payload.get("fp", 0),
                    payload.get("tn", 0),
                    payload.get("fn", 0),
                    payload.get("precision", 0.0),
                    payload.get("recall", 0.0),
                    payload.get("fnr", 0.0),
                    payload.get("fpr", 0.0),
                    payload.get("p50_ms", 0),
                    payload.get("p90_ms", 0),
                    payload.get("p99_ms", 0),
                    tenant_id,
                ),
            )


def store_report_record(
    tenant_id: str,
    run_id: str,
    *,
    title: Optional[str] = None,
    summary: Optional[str] = None,
    path: Optional[str] = None,
) -> None:
    ensure_schema()
    report_id = uuid.uuid4().hex
    with db_conn() as con:
        con.execute(
            """
            INSERT INTO reports (report_id, tenant_id, run_id, title, summary, created_at, path)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (report_id, tenant_id, run_id, title, summary, _now(), path),
        )


def list_users(tenant_id: str) -> list[Dict[str, Any]]:
    ensure_schema()
    with db_conn(commit=False) as con:
        rows = con.execute(
            "SELECT user_id, email, role, status, created_at, last_login_at FROM users WHERE tenant_id = ? ORDER BY created_at",
            (tenant_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def update_user_status(user_id: str, status: str) -> None:
    ensure_schema()
    with db_conn() as con:
        con.execute(
            "UPDATE users SET status = ? WHERE user_id = ?",
            (status, user_id),
        )


def update_user_role(user_id: str, role: str) -> None:
    ensure_schema()
    with db_conn() as con:
        con.execute(
            "UPDATE users SET role = ? WHERE user_id = ?",
            (role, user_id),
        )


def get_tenant_metadata(tenant_id: str) -> Dict[str, Any]:
    ensure_schema()
    with db_conn(commit=False) as con:
        row = con.execute("SELECT metadata FROM tenants WHERE tenant_id = ?", (tenant_id,)).fetchone()
    metadata: Dict[str, Any] = {}
    if row and row["metadata"]:
        try:
            metadata = json.loads(row["metadata"])
        except json.JSONDecodeError:
            metadata = {}
    return metadata


def set_tenant_metadata(tenant_id: str, metadata: Dict[str, Any]) -> None:
    ensure_schema()
    serialized = json.dumps(metadata)
    with db_conn() as con:
        con.execute("UPDATE tenants SET metadata = ? WHERE tenant_id = ?", (serialized, tenant_id))


def get_autopatch_canary_flag(tenant_id: str) -> Optional[bool]:
    metadata = get_tenant_metadata(tenant_id)
    if not isinstance(metadata, dict):
        return None
    if "autopatch_canary" in metadata:
        return bool(metadata["autopatch_canary"])
    autopatch_info = metadata.get("autopatch")
    if isinstance(autopatch_info, dict) and "canary" in autopatch_info:
        return bool(autopatch_info["canary"])
    return None


def set_autopatch_canary_flag(tenant_id: str, enabled: bool) -> None:
    metadata = get_tenant_metadata(tenant_id)
    if not isinstance(metadata, dict):
        metadata = {}
    metadata["autopatch_canary"] = bool(enabled)
    set_tenant_metadata(tenant_id, metadata)


__all__ = [
    "acknowledge_alert",
    "authenticate_user",
    "create_audit_event",
    "list_audit_events",
    "create_tenant",
    "create_user",
    "ensure_schema",
    "issue_token",
    "latest_metrics",
    "list_alerts",
    "list_integrations",
    "list_runs",
    "record_alert",
    "record_run",
    "list_users",
    "resolve_token",
    "get_autopatch_canary_flag",
    "set_autopatch_canary_flag",
    "get_tenant_metadata",
    "set_tenant_metadata",
    "upsert_integration",
    "upsert_metrics",
    "store_report_record",
    "update_user_status",
    "update_user_role",
]
