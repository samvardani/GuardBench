import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from service import api


@pytest.fixture
def client(monkeypatch):
    def fake_auth(token: str) -> api.AuthContext:
        return api.AuthContext(
            token=token,
            tenant_id="tenant",
            tenant_slug="tenant",
            user_id="user",
            email="user@example.com",
            role="owner",
        )

    monkeypatch.setattr(api, "_auth_from_token", fake_auth)
    monkeypatch.setattr(api.rate_limiter, "allow", lambda *args, **kwargs: True)
    monkeypatch.setattr(api.db, "create_audit_event", lambda *args, **kwargs: None)
    monkeypatch.setattr(api.db, "record_run", lambda *args, **kwargs: None)
    monkeypatch.setattr(api.db, "upsert_metrics", lambda *args, **kwargs: None)
    monkeypatch.setattr(api.db, "store_report_record", lambda *args, **kwargs: None)
    monkeypatch.setattr(api.db, "record_alert", lambda *args, **kwargs: None)
    monkeypatch.setattr(api.db, "create_audit_event", lambda *args, **kwargs: None)

    guard_response = {"prediction": "flag", "score": 0.9, "threshold": 0.5}
    monkeypatch.setitem(api.GUARD_REGISTRY, "candidate", {"name": "Candidate", "predict": lambda *args, **kwargs: guard_response, "version": "test"})
    monkeypatch.setitem(api.GUARD_REGISTRY, "baseline", {"name": "Baseline", "predict": lambda *args, **kwargs: guard_response, "version": "test"})

    return TestClient(api.app)


def test_metrics_endpoint_exposes_counters(client):
    headers = {"Authorization": "Bearer token"}
    payload = {"text": "hello", "guard": "candidate"}
    resp = client.post("/score", json=payload, headers=headers)
    assert resp.status_code == 200

    batch_payload = {"rows": [{"text": "item", "category": "self_harm", "language": "en", "label": "unsafe"}]}
    resp = client.post("/batch", json=batch_payload, headers=headers)
    assert resp.status_code == 200

    metrics_resp = client.get("/metrics")
    assert metrics_resp.status_code == 200
    body = metrics_resp.text
    if not body.strip():
        pytest.skip("Prometheus client not available")
    assert "safety_score_requests_total" in body
    assert "safety_score_results_total" in body
    assert "safety_batch_requests_total" in body
    assert "safety_batch_results_total" in body
