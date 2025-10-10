"""Base adapter interface for content moderation providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ScoreResult:
    """Canonical score result model - single source of truth.
    
    All adapters must return this format for consistency.
    """
    
    # Safety decision
    is_safe: bool
    confidence: float  # 0.0 - 1.0
    
    # Category scores
    categories: Dict[str, float] = field(default_factory=dict)
    
    # Flagged categories (above threshold)
    flagged_categories: List[str] = field(default_factory=list)
    
    # Metadata
    provider: str = "unknown"
    latency_ms: int = 0
    
    # Optional details
    reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "is_safe": self.is_safe,
            "confidence": self.confidence,
            "categories": self.categories,
            "flagged_categories": self.flagged_categories,
            "provider": self.provider,
            "latency_ms": self.latency_ms,
            "reason": self.reason,
            "metadata": self.metadata,
        }


class BaseGuardAdapter(ABC):
    """Base class for content moderation adapters.
    
    All adapters (OpenAI, Azure, local policy, etc.) must implement this interface.
    """
    
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        """Initialize adapter.
        
        Args:
            name: Adapter name
            config: Optional configuration
        """
        self.name = name
        self.config = config or {}
    
    @abstractmethod
    def score(self, text: str, context: Optional[Dict[str, Any]] = None) -> ScoreResult:
        """Score content for safety.
        
        Args:
            text: Content to evaluate
            context: Optional context (language, category, etc.)
            
        Returns:
            ScoreResult with safety decision and category scores
        """
        pass
    
    def health_check(self) -> bool:
        """Health check for adapter.
        
        Returns:
            True if adapter is healthy
        """
        return True


__all__ = ["BaseGuardAdapter", "ScoreResult"]

