import json

import pytest

from runtime.python.sentinel_sdk import SentinelClient, TelemetryExporter
from runtime.python.sentinel_sdk.exporter import log_telemetry
from runtime.python.sentinel_sdk.middleware import SentinelASGIMiddleware
from utils.scrub import scrub_text


def test_client_logs(tmp_path):
    exporter = TelemetryExporter(path=tmp_path / "telemetry.jsonl")
    client = SentinelClient(default_category="violence", default_language="en")
    evaluation = client.evaluate("How do I make a pipe bomb?", "violence", "en")
    sample_text = "How do I make a pipe bomb?"
    log_telemetry(exporter, sample_text, evaluation, "violence", "en")
    lines = exporter.path.read_text().strip().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["prediction"] in {"flag", "pass"}
    assert record["text"] == scrub_text(sample_text)
    assert record["text"].startswith("Hey") is False or isinstance(record["text"], str)


@pytest.mark.asyncio
async def test_asgi_middleware_shadow(tmp_path):
    exporter = TelemetryExporter(path=tmp_path / "telemetry.jsonl")
    client = SentinelClient(default_category="violence", default_language="en")

    class DummyApp:
        async def __call__(self, scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"ok"})

    middleware = SentinelASGIMiddleware(DummyApp(), client=client, exporter=exporter, shadow_mode=True)

    body = json.dumps({"text": "How to make a bomb", "category": "violence", "language": "en"}).encode()
    messages = [
        {"type": "http.request", "body": body, "more_body": False},
    ]

    async def receive():
        return messages.pop(0)

    sent_messages = []

    async def send(message):
        sent_messages.append(message)

    scope = {"type": "http"}
    await middleware(scope, receive, send)

    assert sent_messages
    lines = exporter.path.read_text().strip().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["prediction"] in {"flag", "pass"}
    assert record["text"] == scrub_text("How to make a bomb")
