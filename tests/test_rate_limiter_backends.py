import time
from fastapi.testclient import TestClient
from service import api


def _stub_guard(*_, **__):
    return {"prediction": True, "score": 0.9, "threshold": 0.5}


def _make_client_with_auth(monkeypatch):
    guard_registry = {
        "baseline": {"name": "Baseline", "predict": _stub_guard, "version": "baseline-test"},
        "candidate": {"name": "Candidate", "predict": _stub_guard, "version": "candidate-test"},
    }
    monkeypatch.setattr(api, "GUARD_REGISTRY", guard_registry)
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
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


def test_rate_limiter_memory_backend_blocks(monkeypatch):
    client = _make_client_with_auth(monkeypatch)
    # In-memory limiter (no redis)
    api.rate_limiter = api.RateLimiter(limit_per_window=2, window_seconds=60, redis_url=None)

    payload = {"text": "hello", "category": "test", "language": "en", "guard": "candidate"}
    headers = {"Authorization": "Bearer token-mem"}

    for _ in range(2):
        resp = client.post("/score", json=payload, headers=headers)
        assert resp.status_code == 200

    blocked = client.post("/score", json=payload, headers=headers)
    assert blocked.status_code == 429


class _FakePipeline:
    def __init__(self, store, key):
        self._ops = []
        self._store = store
        self._key = key

    def zremrangebyscore(self, key, start, end):
        self._ops.append(("zremrangebyscore", key, start, end))
        return self

    def zcard(self, key):
        self._ops.append(("zcard", key))
        return self

    def zadd(self, key, mapping):
        self._ops.append(("zadd", key, mapping))
        return self

    def expire(self, key, ttl):
        self._ops.append(("expire", key, ttl))
        return self

    def execute(self):
        results = []
        for op in self._ops:
            name = op[0]
            if name == "zremrangebyscore":
                _, key, start, end = op
                bucket = self._store.setdefault(key, {})
                # remove members with score <= end
                for member, score in list(bucket.items()):
                    if score <= end:
                        del bucket[member]
                results.append(None)
            elif name == "zcard":
                _, key = op
                bucket = self._store.get(key, {})
                results.append(len(bucket))
            elif name == "zadd":
                _, key, mapping = op
                bucket = self._store.setdefault(key, {})
                for member, score in mapping.items():
                    bucket[str(member)] = float(score)
                results.append(None)
            elif name == "expire":
                results.append(True)
        self._ops.clear()
        return results


class _FakeRedis:
    def __init__(self):
        self._data = {}

    def ping(self):
        return True

    def pipeline(self):
        return _FakePipeline(self._data, None)

    def zrem(self, key, member):
        bucket = self._data.setdefault(key, {})
        bucket.pop(str(member), None)


def test_rate_limiter_redis_backend_blocks(monkeypatch):
    client = _make_client_with_auth(monkeypatch)

    # Force RateLimiter to use mocked redis backend
    def fake_init_redis(url):
        return _FakeRedis()

    monkeypatch.setattr(api.RateLimiter, "_init_redis", staticmethod(fake_init_redis))
    api.rate_limiter = api.RateLimiter(limit_per_window=2, window_seconds=60, redis_url="redis://local")

    payload = {"text": "hello", "category": "test", "language": "en", "guard": "candidate"}
    headers = {"Authorization": "Bearer token-redis"}

    for _ in range(2):
        resp = client.post("/score", json=payload, headers=headers)
        assert resp.status_code == 200

    blocked = client.post("/score", json=payload, headers=headers)
    assert blocked.status_code == 429

