"""Base adapter interface for content safety guards."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ScoreResult:
    """Standardized result from safety guard evaluation.
    
    This is the unified format returned by all guard adapters.
    """
    
    # Primary result
    flagged: bool
    score: float  # 0.0 to 1.0, where higher = more unsafe
    
    # Categories
    categories: Dict[str, float] = field(default_factory=dict)
    
    # Optional details
    reasoning: Optional[str] = None
    confidence: Optional[float] = None  # 0.0 to 1.0
    
    # Metadata
    latency_ms: int = 0
    provider: Optional[str] = None
    model: Optional[str] = None
    
    # Raw response (for debugging/logging)
    raw_response: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "flagged": self.flagged,
            "score": self.score,
            "categories": self.categories,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "latency_ms": self.latency_ms,
            "provider": self.provider,
            "model": self.model,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ScoreResult:
        """Create from dictionary."""
        return cls(
            flagged=data.get("flagged", False),
            score=data.get("score", 0.0),
            categories=data.get("categories", {}),
            reasoning=data.get("reasoning"),
            confidence=data.get("confidence"),
            latency_ms=data.get("latency_ms", 0),
            provider=data.get("provider"),
            model=data.get("model"),
        )


@dataclass
class GuardMetadata:
    """Metadata about a guard adapter."""
    
    name: str
    provider: str
    version: Optional[str] = None
    supported_languages: List[str] = field(default_factory=lambda: ["en"])
    supported_categories: List[str] = field(default_factory=list)
    requires_api_key: bool = True
    max_text_length: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "provider": self.provider,
            "version": self.version,
            "supported_languages": self.supported_languages,
            "supported_categories": self.supported_categories,
            "requires_api_key": self.requires_api_key,
            "max_text_length": self.max_text_length,
        }


class BaseGuardAdapter(ABC):
    """Abstract base class for content safety guard adapters.
    
    All third-party content moderation services should implement this interface.
    This provides a uniform way to evaluate text across different providers
    (OpenAI, Azure, Google Perspective, etc.).
    """
    
    def __init__(self, **kwargs: Any):
        """Initialize adapter.
        
        Args:
            **kwargs: Configuration parameters (API keys, endpoints, etc.)
        """
        self.config = kwargs
    
    @abstractmethod
    def score(
        self,
        text: str,
        *,
        category: Optional[str] = None,
        language: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ScoreResult:
        """Evaluate text and return safety score.
        
        Args:
            text: Text to evaluate
            category: Optional category hint (e.g., "violence", "hate")
            language: Optional language code (e.g., "en", "es")
            context: Optional additional context
            
        Returns:
            ScoreResult with flagged status, score, and categories
            
        Raises:
            Exception: If evaluation fails
        """
        pass
    
    @abstractmethod
    def get_metadata(self) -> GuardMetadata:
        """Get adapter metadata.
        
        Returns:
            GuardMetadata describing this adapter
        """
        pass
    
    def initialize(self) -> None:
        """Optional initialization/health check.
        
        Override this method to perform any setup needed before scoring.
        """
        pass
    
    def health_check(self) -> bool:
        """Check if adapter is healthy and can serve requests.
        
        Returns:
            True if healthy, False otherwise
        """
        return True
    
    def supports_language(self, language: str) -> bool:
        """Check if adapter supports given language.
        
        Args:
            language: Language code
            
        Returns:
            True if supported
        """
        metadata = self.get_metadata()
        return language in metadata.supported_languages
    
    def supports_category(self, category: str) -> bool:
        """Check if adapter supports given category.
        
        Args:
            category: Category name
            
        Returns:
            True if supported
        """
        metadata = self.get_metadata()
        if not metadata.supported_categories:
            return True  # Supports all
        return category in metadata.supported_categories


__all__ = ["BaseGuardAdapter", "ScoreResult", "GuardMetadata"]

