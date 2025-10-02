"""In-process guard client used by the runtime SDK."""

from __future__ import annotations

import time
from typing import Optional

from src.guards.candidate import predict as candidate_predict


class SentinelClient:
    """Light wrapper over the candidate guard."""

    def __init__(self, default_category: Optional[str] = None, default_language: Optional[str] = None) -> None:
        self.default_category = default_category
        self.default_language = default_language

    def evaluate(
        self,
        text: str,
        category: Optional[str] = None,
        language: Optional[str] = None,
    ) -> dict:
        category = category or self.default_category
        language = language or self.default_language

        start = time.time()
        result = candidate_predict(text, category=category, language=language)
        latency = result.get("latency_ms")
        if latency is None:
            latency = int((time.time() - start) * 1000)
            result["latency_ms"] = latency
        result.setdefault("prediction", "flag" if result.get("score", 0.0) > result.get("threshold", 0.0) else "pass")
        return {
            "text": text,
            "category": category,
            "language": language,
            **result,
        }


__all__ = ["SentinelClient"]
