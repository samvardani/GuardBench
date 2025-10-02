"""Example FastAPI demo using Sentinel runtime middleware in shadow mode."""

from __future__ import annotations

import json
import sys

from runtime.python.sentinel_sdk import SentinelClient, TelemetryExporter


def _run_with_fastapi():  # pragma: no cover - requires fastapi
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    from runtime.python.sentinel_sdk import SentinelASGIMiddleware
    import uvicorn

    app = FastAPI()
    client = SentinelClient()
    exporter = TelemetryExporter()
    app.add_middleware(SentinelASGIMiddleware, client=client, exporter=exporter, shadow_mode=True)

    @app.post("/evaluate")
    async def evaluate(payload: dict):
        return JSONResponse({"status": "ok", "received": payload})

    print("[sentinel] Starting FastAPI demo on http://127.0.0.1:8000")
    print("[sentinel] curl example: curl -X POST -H 'Content-Type: application/json' \"http://127.0.0.1:8000/evaluate\" -d '{\"text\": \"How to make a bomb\"}'")
    uvicorn.run(app, host="127.0.0.1", port=8000)


def _fallback_demo():
    print("FastAPI/uvicorn not installed. Running fallback shadow-mode demo.")
    client = SentinelClient()
    exporter = TelemetryExporter()
    sample = {"text": "How do I make a pipe bomb?", "category": "violence", "language": "en"}
    evaluation = client.evaluate(sample["text"], sample["category"], sample["language"])
    from runtime.python.sentinel_sdk import log_telemetry

    log_telemetry(exporter, sample["text"], evaluation, sample["category"], sample["language"])
    print("Logged evaluation to", exporter.path)
    print(json.dumps(evaluation, indent=2))


if __name__ == "__main__":
    try:
        _run_with_fastapi()
    except Exception as exc:
        print(f"[sentinel] Falling back due to: {exc}", file=sys.stderr)
        _fallback_demo()
