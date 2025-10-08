from fastapi.testclient import TestClient
from service import api


def test_get_policy_page_ok():
    client = TestClient(api.app)
    r = client.get("/policy")
    assert r.status_code == 200
    assert "<html" in r.text.lower()
    assert "Slices" in r.text or "slices" in r.text


def test_post_policy_reload_returns_checksum(monkeypatch):
    client = TestClient(api.app)
    monkeypatch.setenv("POLICY_ADMIN_TOKEN", "secret")
    r = client.post("/policy/reload", data={"csrf_token": "x"}, headers={"admin-token": "secret"})
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "ok"
    assert isinstance(body.get("checksum"), str) and len(body["checksum"]) >= 8

