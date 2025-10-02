"""Telemetry exporter for runtime evaluations."""

from __future__ import annotations

import json
import hashlib
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional


DEFAULT_PATH = Path("runtime_telemetry.jsonl")


@dataclass
class TelemetryExporter:
    path: Path = DEFAULT_PATH

    def __post_init__(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, record: Dict[str, object]) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def log_telemetry(
    exporter: TelemetryExporter,
    text: str,
    evaluation: Dict[str, object],
    category: Optional[str] = None,
    language: Optional[str] = None,
) -> None:
    text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    record = {
        "ts": int(time.time()),
        "text_hash": text_hash,
        "category_guess": category or evaluation.get("category"),
        "language_guess": language or evaluation.get("language"),
        "prediction": evaluation.get("prediction"),
        "score": evaluation.get("score"),
        "threshold": evaluation.get("threshold"),
        "latency_ms": evaluation.get("latency_ms"),
    }
    exporter.log(record)


__all__ = ["TelemetryExporter", "log_telemetry"]
