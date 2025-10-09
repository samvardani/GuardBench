"""Base ensemble strategy interface."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List

from seval.adapters.base import ModerationResult

logger = logging.getLogger(__name__)


@dataclass
class EnsembleResult:
    """Result from ensemble of adapters."""
    
    score: float
    blocked: bool
    category: str
    language: str
    strategy: str
    adapter_results: List[ModerationResult]
    total_latency_ms: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "score": self.score,
            "blocked": self.blocked,
            "category": self.category,
            "language": self.language,
            "strategy": self.strategy,
            "adapters": [r.adapter_name for r in self.adapter_results],
            "total_latency_ms": self.total_latency_ms,
            "adapter_details": [r.to_dict() for r in self.adapter_results],
            "metadata": self.metadata,
        }


class EnsembleStrategy(ABC):
    """Abstract base class for ensemble strategies."""
    
    def __init__(self, name: str, config: Dict[str, Any] | None = None):
        """Initialize strategy.
        
        Args:
            name: Strategy name
            config: Optional configuration
        """
        self.name = name
        self.config = config or {}
    
    @abstractmethod
    def combine(
        self,
        results: List[ModerationResult],
        category: str,
        language: str
    ) -> EnsembleResult:
        """Combine results from multiple adapters.
        
        Args:
            results: List of ModerationResult from adapters
            category: Content category
            language: Language code
            
        Returns:
            EnsembleResult with combined decision
        """
        pass
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r})"

