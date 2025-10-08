from fastapi.testclient import TestClient
from service import api


def test_cors_preflight_allows_origin(monkeypatch):
    client = TestClient(api.app)
    resp = client.options(
        "/healthz",
        headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.status_code in (200, 204)
    assert resp.headers.get("access-control-allow-origin") in ("*", "https://example.com")


def test_oversized_json_returns_413(monkeypatch):
    client = TestClient(api.app)
    big = {"x": "a" * (api.get_settings().max_json_body_bytes + 10)}
    # Provide a rough content-length header to trigger early reject
    headers = {"Content-Type": "application/json", "Content-Length": str(len(big["x"]) + 20)}
    resp = client.post("/score", json=big, headers=headers)
    assert resp.status_code == 413


