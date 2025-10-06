from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import Optional

from src.federation.signatures import Matcher, Signature


class FeedService:
    """Background refresher for federation feed.

    Pulls a local/remote JSONL feed hourly and updates in-memory matcher.
    """

    def __init__(self, feed_path: str) -> None:
        self._path = feed_path
        self._matcher = Matcher()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    @property
    def matcher(self) -> Matcher:
        return self._matcher

    def _load_once(self) -> None:
        path = Path(self._path)
        if not path.exists():
            return
        data = path.read_text(encoding="utf-8").splitlines()
        fresh = Matcher()
        for line in data:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                sig = Signature(
                    tenant=obj["tenant"],
                    algo=obj["algo"],
                    perms=list(obj["perms"]),
                    bloom=list(obj["bloom"]),
                    meta=dict(obj.get("meta", {})),
                )
                fresh.add(sig)
            except Exception:
                continue
        self._matcher = fresh

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    def _run(self) -> None:
        interval = float(os.getenv("FEED_REFRESH_SECONDS", "3600"))
        while not self._stop.is_set():
            try:
                self._load_once()
            except Exception:
                pass
            self._stop.wait(interval)


__all__ = ["FeedService"]


