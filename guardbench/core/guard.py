"""Abstract base class and result type for all guards."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class GuardResult:
    """Result produced by a guard's predict call."""

    prediction: str  # "pass" | "flag"
    score: float  # 0.0 – 1.0
    latency_ms: int
    categories: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class Guard(ABC):
    """Abstract base class that every guard must implement."""

    name: str = "unnamed"
    version: str = "0.0.0"

    @abstractmethod
    def predict(self, text: str, **meta: Any) -> GuardResult:
        """Score a single text and return a GuardResult."""
        ...

    def batch_predict(self, texts: List[str], **meta: Any) -> List[GuardResult]:
        """Score a list of texts; defaults to sequential predict calls."""
        return [self.predict(t, **meta) for t in texts]
