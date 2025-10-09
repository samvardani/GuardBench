import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from service import db
from store import init_db


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    test_db = tmp_path / "history.db"
    monkeypatch.setattr(init_db, "DB_PATH", test_db)
    monkeypatch.setattr(db, "DB_PATH", test_db)
    monkeypatch.setattr(db, "_SCHEMA_READY", False)
    db.ensure_schema()
    yield
    if test_db.exists():
        test_db.unlink()


def test_tenant_user_token_flow(isolated_db):
    tenant = db.create_tenant("Test Tenant", slug="test")
    user = db.create_user(tenant["tenant_id"], "user@example.com", "StrongPass123", role="admin")

    auth = db.authenticate_user("user@example.com", "StrongPass123", tenant_slug="test")
    assert auth is not None
    assert auth["user_id"] == user["user_id"]
    assert auth["tenant_id"] == tenant["tenant_id"]

    token = db.issue_token(user["user_id"], tenant["tenant_id"], label="test")
    assert "token" in token

    resolved = db.resolve_token(token["token"])
    assert resolved is not None
    assert resolved["tenant_id"] == tenant["tenant_id"]
    assert resolved["email"] == "user@example.com"

    users = db.list_users(tenant["tenant_id"])
    assert len(users) == 1
    assert users[0]["email"] == "user@example.com"


def test_run_metrics_alerts(isolated_db):
    tenant = db.create_tenant("ACME", slug="acme")
    user = db.create_user(tenant["tenant_id"], "owner@acme.com", "Passw0rd-!", role="owner")

    run_id = "run12345"
    db.record_run(
        tenant["tenant_id"],
        run_id,
        dataset_path="service/upload",
        engine_baseline="rules",
        engine_candidate="candidate",
    )

    metrics_payload = {
        "baseline": {"tp": 10, "fp": 1, "tn": 80, "fn": 2, "precision": 0.91, "recall": 0.83, "fnr": 0.17, "fpr": 0.012, "p50_ms": 50, "p90_ms": 70, "p99_ms": 90},
        "candidate": {"tp": 12, "fp": 2, "tn": 78, "fn": 1, "precision": 0.857, "recall": 0.923, "fnr": 0.077, "fpr": 0.025, "p50_ms": 60, "p90_ms": 85, "p99_ms": 110},
    }
    db.upsert_metrics(run_id, tenant["tenant_id"], metrics_payload)

    metrics = db.latest_metrics(run_id)
    assert metrics["candidate"]["recall"] == pytest.approx(0.923)

    alert = db.record_alert(
        tenant["tenant_id"],
        severity="high",
        title="Recall drop",
        message="Candidate recall below target",
        run_id=run_id,
        metadata={"recall": 0.7},
    )
    assert alert["alert_id"]

    alerts = db.list_alerts(tenant["tenant_id"])
    assert len(alerts) == 1
    assert alerts[0]["metadata"] == {"recall": 0.7}

    db.acknowledge_alert(alert["alert_id"])
    alerts = db.list_alerts(tenant["tenant_id"])
    assert alerts[0]["acknowledged_at"] is not None

    db.create_audit_event(tenant["tenant_id"], action="test.event", user_id=user["user_id"], context={"run": run_id})
    events = db.list_audit_events(tenant["tenant_id"])
    assert events
