import json
import logging
from fastapi.testclient import TestClient
from service import api


def test_request_id_passthrough_and_json_log(caplog):
    client = TestClient(api.app)
    headers = {"X-Request-ID": "test-req-123"}
    caplog.set_level(logging.INFO)
    resp = client.get("/healthz", headers=headers)
    assert resp.status_code == 200
    assert resp.headers.get("X-Request-ID") == "test-req-123"

    # Inspect captured log records
    found = False
    for rec in caplog.records:
        msg = rec.getMessage()
        try:
            obj = json.loads(msg)
        except Exception:
            continue
        if obj.get("request_id") == "test-req-123" and obj.get("path") == "/healthz":
            for key in ("ts", "level", "path", "status", "latency_ms", "request_id"):
                assert key in obj
            found = True
            break
    assert found, "JSON access log with request_id not found"

