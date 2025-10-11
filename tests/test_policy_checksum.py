import prometheus_client  # type: ignore
from fastapi.testclient import TestClient
from service import api


def test_score_includes_policy_checksum(monkeypatch):
    # Disable rate limiting for this test
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")
    
    for m in (
        getattr(api, "SCORE_LATENCY", None),
        getattr(api, "SCORE_REQUESTS", None),
        getattr(api, "BATCH_LATENCY", None),
        getattr(api, "BATCH_REQUESTS", None),
        getattr(api, "SCORE_RESULT_COUNTER", None),
        getattr(api, "BATCH_RESULT_COUNTER", None),
    ):
        try:
            if m is not None:
                prometheus_client.REGISTRY.unregister(m)
        except Exception:
            pass
    client = TestClient(api.app)
    r = client.post("/score", json={"text": "hello", "category": "violence", "language": "en"})
    assert r.status_code == 200
    body = r.json()
    assert "policy_checksum" in body and isinstance(body["policy_checksum"], str)


def test_batch_includes_policy_checksum(monkeypatch):
    for m in (
        getattr(api, "SCORE_LATENCY", None),
        getattr(api, "SCORE_REQUESTS", None),
        getattr(api, "BATCH_LATENCY", None),
        getattr(api, "BATCH_REQUESTS", None),
        getattr(api, "SCORE_RESULT_COUNTER", None),
        getattr(api, "BATCH_RESULT_COUNTER", None),
    ):
        try:
            if m is not None:
                prometheus_client.REGISTRY.unregister(m)
        except Exception:
            pass
    client = TestClient(api.app)
    token = "token"
    # Override the dependency to bypass auth
    api.app.dependency_overrides[api.require_auth] = lambda: api.AuthContext(
        token=token, tenant_id="t", tenant_slug="t", user_id="u", email="e", role="analyst"
    )
    payload = {
        "rows": [
            {"text": "hello", "category": "violence", "language": "en"}
        ],
        "baseline_guard": "baseline",
        "candidate_guard": "candidate",
    }
    r = client.post("/batch", json=payload, headers={"Authorization": "Bearer "+token})
    assert r.status_code == 200
    body = r.json()
    assert "policy_checksum" in body and isinstance(body["policy_checksum"], str)

