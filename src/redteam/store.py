"""Persist red-team swarm discoveries."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List


@dataclass
class StoredCase:
    text: str
    normalized_text: str
    category: str
    language: str
    score: float
    threshold: float
    agent: str
    operations: List[str]
    seed_row_id: str
    iteration: int
    metadata: Dict[str, str]


class CaseStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load_texts(self) -> List[str]:
        if not self.path.exists():
            return []
        texts: List[str] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(payload, dict) and "text" in payload:
                    texts.append(payload["text"])
        return texts

    def append(self, case: StoredCase) -> None:
        payload = {
            "text": case.text,
            "normalized_text": case.normalized_text,
            "category": case.category,
            "language": case.language,
            "score": case.score,
            "threshold": case.threshold,
            "agent": case.agent,
            "operations": case.operations,
            "seed_row_id": case.seed_row_id,
            "iteration": case.iteration,
            **case.metadata,
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


__all__ = ["CaseStore", "StoredCase"]
