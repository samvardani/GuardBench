"""Simple Kafka producer with retry/backoff."""

from __future__ import annotations

import json
import os
import random
import time
from pathlib import Path
from typing import Iterable, Optional

try:  # pragma: no cover - optional dependency
    from kafka import KafkaProducer  # type: ignore
except Exception:  # pragma: no cover
    KafkaProducer = None  # type: ignore

try:  # pragma: no cover
    import httpx  # type: ignore
except Exception:  # pragma: no cover
    httpx = None  # type: ignore


class Producer:
    """Kafka producer wrapper with fallbacks to HTTP or filesystem."""

    def __init__(
        self,
        brokers: Optional[str] = None,
        retries: int = 3,
        backoff_seconds: float = 0.5,
        rest_endpoint: Optional[str] = None,
    ) -> None:
        self._brokers = brokers or os.getenv("KAFKA_BROKERS", "localhost:9092")
        self._retries = max(1, retries)
        self._backoff = max(0.1, backoff_seconds)
        self._rest_endpoint = rest_endpoint or os.getenv("KAFKA_REST_PROXY")
        self._fallback_dir = Path(os.getenv("KAFKA_FALLBACK_DIR", ".cache/kafka"))
        self._producer = self._build_producer()

    def _build_producer(self):  # pragma: no cover - exercised when kafka available
        if KafkaProducer is None:
            return None
        try:
            return KafkaProducer(
                bootstrap_servers=self._brokers.split(","),
                value_serializer=lambda payload: json.dumps(payload).encode("utf-8"),
            )
        except Exception:
            return None

    def _send_via_producer(self, topic: str, payload: dict) -> bool:  # pragma: no cover
        if self._producer is None:
            return False
        future = self._producer.send(topic, value=payload)
        future.get(timeout=10)
        return True

    def _send_via_http(self, topic: str, payload: dict) -> bool:
        if not self._rest_endpoint or httpx is None:
            return False
        resp = httpx.post(
            self._rest_endpoint.rstrip("/") + f"/topics/{topic}",
            json={"records": [{"value": payload}]},
            timeout=5.0,
        )
        resp.raise_for_status()
        return True

    def _send_via_filesystem(self, topic: str, payload: dict) -> bool:
        ts = int(time.time() * 1000)
        suffix = random.randint(0, 1_000_000)
        path = self._fallback_dir / topic / f"{ts}-{suffix}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return True

    def send_json(self, topic: str, payload: dict) -> None:
        for attempt in range(1, self._retries + 1):
            try:
                if self._producer and self._send_via_producer(topic, payload):
                    return
                if self._send_via_http(topic, payload):
                    return
                if self._send_via_filesystem(topic, payload):
                    return
            except Exception:
                if attempt == self._retries:
                    raise
                time.sleep(self._backoff * attempt)


__all__ = ["Producer"]

