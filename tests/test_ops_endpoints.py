from fastapi.testclient import TestClient
from service import api


def test_healthz_ok():
    client = TestClient(api.app)
    resp = client.get("/healthz")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("status") == "ok"
    assert "version" in data and "policy_version" in data


def test_metrics_exposes_prom():
    client = TestClient(api.app)
    resp = client.get("/metrics")
    assert resp.status_code == 200
    body = resp.text
    # Expect at least one of our counters to appear
    assert "safety_score_requests_total" in body or "safety_batch_requests_total" in body


