"""Framework integrations for the Sentinel runtime SDK."""

from __future__ import annotations

import json
from typing import Callable, Optional

from .client import SentinelClient
from .exporter import TelemetryExporter, log_telemetry


class SentinelASGIMiddleware:
    """Minimal ASGI middleware compatible with FastAPI/Starlette."""

    def __init__(self, app, client: SentinelClient, exporter: Optional[TelemetryExporter] = None, shadow_mode: bool = True):
        self.app = app
        self.client = client
        self.exporter = exporter or TelemetryExporter()
        self.shadow_mode = shadow_mode

    async def __call__(self, scope, receive, send):  # pragma: no cover - async simple wrapper
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        body = b""
        saved_messages = []
        while True:
            message = await receive()
            saved_messages.append(message)
            body += message.get("body", b"")
            if not message.get("more_body", False):
                break

        async def receive_wrapper():
            if saved_messages:
                return saved_messages.pop(0)
            return {"type": "http.request", "body": b"", "more_body": False}

        text = ""
        category = None
        language = None
        try:
            data = json.loads(body.decode("utf-8")) if body else {}
            text = data.get("text") or data.get("prompt") or ""
            category = data.get("category")
            language = data.get("language")
        except Exception:
            text = ""

        if text:
            evaluation = self.client.evaluate(text, category=category, language=language)
            log_telemetry(self.exporter, text, evaluation, category, language)

        async def receive_iter():
            while saved_messages:
                yield saved_messages.pop(0)
            while True:
                yield {"type": "http.request", "body": b"", "more_body": False}

        iterator = receive_iter()

        async def receive_adapter():
            return await iterator.__anext__()

        await self.app(scope, receive_adapter, send)


class FlaskSentinelWrapper:
    """Utility to register a before_request hook on a Flask app."""

    def __init__(self, app, client: SentinelClient, exporter: Optional[TelemetryExporter] = None, shadow_mode: bool = True):
        self.app = app
        self.client = client
        self.exporter = exporter or TelemetryExporter()
        self.shadow_mode = shadow_mode

        try:
            from flask import request  # type: ignore
        except Exception:  # pragma: no cover - Flask not installed
            request = None

        if request is not None:
            @app.before_request  # type: ignore[attr-defined]
            def _sentinel_before_request():  # pragma: no cover - requires flask
                try:
                    payload = request.get_json(silent=True) or {}
                except Exception:
                    payload = {}
                text = payload.get("text") or payload.get("prompt") or ""
                if not text:
                    return None
                evaluation = self.client.evaluate(text, category=payload.get("category"), language=payload.get("language"))
                log_telemetry(self.exporter, text, evaluation, payload.get("category"), payload.get("language"))
                return None

    def __call__(self, environ, start_response):
        return self.app(environ, start_response)


__all__ = ["SentinelASGIMiddleware", "FlaskSentinelWrapper"]
