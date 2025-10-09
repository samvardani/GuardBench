"""Any strategy - blocks if any adapter blocks."""

from __future__ import annotations

from typing import Any, Dict, List

from .base import EnsembleStrategy, EnsembleResult
from seval.adapters.base import ModerationResult


class AnyStrategy(EnsembleStrategy):
    """Block if ANY adapter blocks (most restrictive)."""
    
    def __init__(self, name: str = "any", config: Dict[str, Any] | None = None):
        """Initialize Any strategy."""
        super().__init__(name, config)
    
    def combine(
        self,
        results: List[ModerationResult],
        category: str,
        language: str
    ) -> EnsembleResult:
        """Combine results - block if any adapter blocks.
        
        Args:
            results: List of ModerationResult from adapters
            category: Content category
            language: Language code
            
        Returns:
            EnsembleResult with ANY logic applied
        """
        if not results:
            raise ValueError("Cannot combine empty results list")
        
        # Block if ANY adapter blocks
        blocked = any(r.blocked for r in results)
        
        # Use maximum score
        max_score = max(r.score for r in results)
        
        # Sum latencies
        total_latency = sum(r.latency_ms for r in results)
        
        # Find which adapters blocked
        blocking_adapters = [r.adapter_name for r in results if r.blocked]
        
        return EnsembleResult(
            score=max_score,
            blocked=blocked,
            category=category,
            language=language,
            strategy=self.name,
            adapter_results=results,
            total_latency_ms=total_latency,
            metadata={
                "blocking_adapters": blocking_adapters,
                "num_blocked": len(blocking_adapters),
                "num_total": len(results),
            }
        )

