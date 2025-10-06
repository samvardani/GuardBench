import pytest
from fastapi.testclient import TestClient

from service import api


def _schema_stub(*_, **__):
    return {
        "prediction": True,
        "score": 0.88,
        "rationale": "looks good",
        "slices": [{"category": "default", "recall": 1.0}],
    }


@pytest.fixture(name="client")
def fixture_client(monkeypatch):
    guard_registry = {
        "baseline": {"name": "Baseline", "predict": _schema_stub, "version": "baseline-test"},
        "candidate": {"name": "Candidate", "predict": _schema_stub, "version": "schema-v1"},
    }
    monkeypatch.setattr(api, "GUARD_REGISTRY", guard_registry)
    monkeypatch.setattr(api, "rate_limiter", api.RateLimiter(100, 60))
    monkeypatch.setattr(api, "circuit_breaker", api.CircuitBreaker(5, 10_000, 5))
    monkeypatch.setattr(api.db, "create_audit_event", lambda *args, **kwargs: None)
    monkeypatch.setattr(api, "POLICY_VERSION", "policy-v1")

    def fake_auth(token: str) -> api.AuthContext:
        return api.AuthContext(
            token=token,
            tenant_id="tenant",
            tenant_slug="slug",
            user_id="user",
            email="user@example.com",
            role="viewer",
        )

    monkeypatch.setattr(api, "_auth_from_token", fake_auth)
    return TestClient(api.app)


def test_score_response_schema_v1(client):
    payload = {"text": "schema test", "category": "testing", "language": "en", "guard": "candidate"}
    headers = {"Authorization": "Bearer schema-token"}

    resp = client.post("/score", json=payload, headers=headers)
    assert resp.status_code == 200

    data = resp.json()
    expected_keys = {"score", "slices", "policy_version", "guard_version", "latency_ms", "request_id"}
    assert expected_keys.issubset(data.keys())
    assert data["score"] == pytest.approx(0.88)
    assert data.get("rationale") == "looks good"
    assert isinstance(data["slices"], list)
    assert data["policy_version"] == "policy-v1"
    assert data["guard_version"] == "schema-v1"
    assert isinstance(data["latency_ms"], int)
    assert data["latency_ms"] >= 0
    assert isinstance(data["request_id"], str) and data["request_id"]
