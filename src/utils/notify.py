"""Notification helpers for safety evaluation alerts."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional
from urllib import error, request


class NotificationManager:
    """Simple notification abstraction writing to a log for alerting hooks."""

    def __init__(self, settings: Optional[Mapping[str, Any]] = None) -> None:
        settings = settings or {}
        self.enabled = bool(settings.get("enabled"))
        log_path = settings.get("log_path", "notifications.log")
        self.log_path = Path(log_path)
        self.channels = settings.get("channels", [])
        self.thresholds = settings.get("thresholds", {})

    def notify(self, subject: str, message: str, metadata: Optional[Mapping[str, Any]] = None) -> None:
        if not self.enabled:
            return
        payload: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "subject": subject,
            "message": message,
            "metadata": metadata or {},
            "channels": self.channels,
        }
        deliveries = self._deliver_channels(payload)
        if deliveries:
            payload["deliveries"] = deliveries
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def threshold(self, key: str, default: float) -> float:
        value = self.thresholds.get(key, default)
        try:
            return float(value)
        except (TypeError, ValueError):  # pragma: no cover - defensive
            return default

    def _deliver_channels(self, payload: Mapping[str, Any]) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for channel in self.channels:
            if not isinstance(channel, Mapping):
                results.append({"status": "skipped", "reason": "invalid channel"})
                continue
            channel_type = str(channel.get("type", "")).lower()
            if channel_type == "webhook":
                results.append(self._deliver_webhook(channel, payload))
            else:
                results.append(
                    {
                        "status": "skipped",
                        "type": channel_type or "unknown",
                        "reason": "unsupported channel type",
                    }
                )
        return [result for result in results if result]

    def _deliver_webhook(self, channel: Mapping[str, Any], payload: Mapping[str, Any]) -> Dict[str, Any]:
        url = channel.get("url")
        if not url:
            return {"status": "skipped", "type": "webhook", "reason": "missing url"}
        headers = {"Content-Type": "application/json"}
        extra_headers = channel.get("headers")
        if isinstance(extra_headers, Mapping):
            for key, value in extra_headers.items():
                headers[str(key)] = str(value)
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = request.Request(str(url), data=data, headers=headers, method="POST")
        timeout = channel.get("timeout", 5)
        try:
            timeout_value = float(timeout)
        except (TypeError, ValueError):
            timeout_value = 5.0
        try:
            with request.urlopen(req, timeout=timeout_value) as resp:
                status = getattr(resp, "status", getattr(resp, "code", None))
                return {
                    "status": "ok",
                    "type": "webhook",
                    "target": str(url),
                    "code": status,
                }
        except error.URLError as exc:
            reason = getattr(exc, "reason", str(exc))
            if not isinstance(reason, str):
                reason = str(reason)
            return {
                "status": "error",
                "type": "webhook",
                "target": str(url),
                "error": reason,
            }
        except Exception as exc:  # pragma: no cover - defensive
            return {
                "status": "error",
                "type": "webhook",
                "target": str(url),
                "error": str(exc),
            }


__all__ = ["NotificationManager"]
