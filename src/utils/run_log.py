"""Append evaluation lineage records to runs.jsonl."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Mapping

RUN_LOG_PATH = Path("runs.jsonl")


def append_run_record(record: Mapping[str, object]) -> None:
    enriched = dict(record)
    enriched.setdefault("logged_at", datetime.utcnow().isoformat() + "Z")
    with RUN_LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(enriched, ensure_ascii=False) + "\n")


__all__ = ["append_run_record", "RUN_LOG_PATH"]
