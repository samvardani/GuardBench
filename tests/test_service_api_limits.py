import pytest
from fastapi.testclient import TestClient

from service import api


def _latency_stub(*_, **__):
    return {"prediction": True, "score": 0.9}


@pytest.fixture(name="client")
def fixture_client(monkeypatch):
    guard_registry = {
        "baseline": {"name": "Baseline", "predict": _latency_stub, "version": "baseline-test"},
        "candidate": {"name": "Candidate", "predict": _latency_stub, "version": "candidate-test"},
    }
    monkeypatch.setattr(api, "GUARD_REGISTRY", guard_registry)
    # Ensure rate limiting enabled and low threshold for test
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    rl = api.RateLimiter(2, 60)
    monkeypatch.setattr(api, "rate_limiter", rl)
    monkeypatch.setattr(api, "circuit_breaker", api.CircuitBreaker(5, 10_000, 5))
    monkeypatch.setattr(api.db, "create_audit_event", lambda *args, **kwargs: None)

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


def test_token_rate_limit_blocks_after_threshold(client):
    payload = {"text": "hello", "category": "test", "language": "en", "guard": "candidate"}
    headers = {"Authorization": "Bearer token-123"}

    for _ in range(2):
        resp = client.post("/score", json=payload, headers=headers)
        assert resp.status_code == 200

    blocked = client.post("/score", json=payload, headers=headers)
    assert blocked.status_code == 429
