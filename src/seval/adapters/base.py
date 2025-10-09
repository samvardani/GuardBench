"""Base adapter interface for moderation systems."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class ModerationResult:
    """Standardized moderation result across adapters."""
    
    score: float
    blocked: bool
    category: str
    language: str
    adapter_name: str
    latency_ms: int
    confidence: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "score": self.score,
            "blocked": self.blocked,
            "category": self.category,
            "language": self.language,
            "adapter": self.adapter_name,
            "latency_ms": self.latency_ms,
        }
        if self.confidence is not None:
            result["confidence"] = self.confidence
        if self.metadata:
            result["metadata"] = self.metadata
        return result


class ModerationAdapter(ABC):
    """Abstract base class for moderation adapters."""
    
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        """Initialize adapter with name and optional config.
        
        Args:
            name: Adapter name
            config: Optional configuration dictionary
        """
        self.name = name
        self.config = config or {}
        self._call_count = 0
        self._total_latency_ms = 0
    
    @abstractmethod
    def moderate(
        self,
        text: str,
        category: str,
        language: str,
        **kwargs: Any
    ) -> ModerationResult:
        """Perform moderation check.
        
        Args:
            text: Text to moderate
            category: Content category (violence, self_harm, etc.)
            language: Language code (en, es, etc.)
            **kwargs: Additional adapter-specific parameters
            
        Returns:
            ModerationResult with score, blocking decision, and metadata
        """
        pass
    
    def _track_call(self, latency_ms: int) -> None:
        """Track adapter call for metrics."""
        self._call_count += 1
        self._total_latency_ms += latency_ms
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get adapter metrics.
        
        Returns:
            Dictionary with call count, average latency, etc.
        """
        avg_latency = (
            self._total_latency_ms / self._call_count
            if self._call_count > 0
            else 0
        )
        return {
            "adapter": self.name,
            "call_count": self._call_count,
            "total_latency_ms": self._total_latency_ms,
            "avg_latency_ms": round(avg_latency, 2),
        }
    
    def reset_metrics(self) -> None:
        """Reset adapter metrics."""
        self._call_count = 0
        self._total_latency_ms = 0
    
    @abstractmethod
    def health_check(self) -> bool:
        """Check if adapter is healthy and ready.
        
        Returns:
            True if adapter is healthy, False otherwise
        """
        pass
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r})"

