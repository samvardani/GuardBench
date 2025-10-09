"""Local adapter using built-in candidate guard."""

from __future__ import annotations

import time
from typing import Any, Dict, Optional

from .base import ModerationAdapter, ModerationResult


class LocalAdapter(ModerationAdapter):
    """Local moderation using built-in rules and models."""
    
    def __init__(self, name: str = "local", config: Optional[Dict[str, Any]] = None):
        """Initialize local adapter.
        
        Args:
            name: Adapter name
            config: Optional configuration
        """
        super().__init__(name, config)
        self._guard = None
    
    def _get_guard(self) -> Any:
        """Lazy load the candidate guard."""
        if self._guard is None:
            from guards.candidate import predict as candidate_predict
            self._guard = candidate_predict
        return self._guard
    
    def moderate(
        self,
        text: str,
        category: str,
        language: str,
        **kwargs: Any
    ) -> ModerationResult:
        """Perform local moderation using candidate guard.
        
        Args:
            text: Text to moderate
            category: Content category
            language: Language code
            **kwargs: Additional parameters
            
        Returns:
            ModerationResult with score and decision
        """
        start_time = time.perf_counter()
        
        guard = self._get_guard()
        result = guard(text, category, language)
        
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        self._track_call(latency_ms)
        
        return ModerationResult(
            score=result.get("score", 0.0),
            blocked=result.get("blocked", False),
            category=category,
            language=language,
            adapter_name=self.name,
            latency_ms=latency_ms,
            confidence=result.get("confidence"),
            metadata={"guard_result": result},
        )
    
    def health_check(self) -> bool:
        """Check if local adapter is healthy.
        
        Returns:
            True if guard is available
        """
        try:
            self._get_guard()
            return True
        except Exception:
            return False

