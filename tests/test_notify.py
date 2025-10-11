import json

from utils.notify import NotificationManager


def test_notification_manager_writes_log(tmp_path):
    log_file = tmp_path / "alerts.log"
    manager = NotificationManager({"enabled": True, "log_path": log_file})
    manager.notify("Subject", "Message", {"foo": "bar"})
    assert log_file.exists()
    content = log_file.read_text(encoding="utf-8").strip()
    assert "Subject" in content
    assert "foo" in content
    assert "bar" in content


def test_notification_manager_posts_webhook(monkeypatch, tmp_path):
    captured = {}

    def fake_urlopen(req, timeout=0):
        captured["url"] = req.full_url
        captured["timeout"] = timeout
        captured["headers"] = dict(req.header_items())
        captured["payload"] = json.loads(req.data.decode("utf-8"))

        class _Resp:
            status = 204

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return b""

        return _Resp()

    monkeypatch.setattr("src.utils.notify.request.urlopen", fake_urlopen)

    log_file = tmp_path / "alerts.log"
    manager = NotificationManager(
        {
            "enabled": True,
            "log_path": log_file,
            "channels": [
                {
                    "type": "webhook",
                    "url": "http://localhost:8799/notify",
                    "timeout": 1.5,
                    "headers": {"X-Test": "yes"},
                }
            ],
        }
    )

    manager.notify("Subject", "Message", {"run_id": "abc123", "fnr": 0.42})

    assert captured["url"] == "http://localhost:8799/notify"
    assert captured["timeout"] == 1.5
    lowered_headers = {k.lower(): v for k, v in captured["headers"].items()}
    assert lowered_headers["content-type"] == "application/json"
    assert lowered_headers["x-test"] == "yes"
    assert captured["payload"]["metadata"]["run_id"] == "abc123"
    assert captured["payload"]["metadata"]["fnr"] == 0.42
