"""All strategy - blocks only if all adapters block."""

from __future__ import annotations

from typing import Any, Dict, List

from .base import EnsembleStrategy, EnsembleResult
from seval.adapters.base import ModerationResult


class AllStrategy(EnsembleStrategy):
    """Block only if ALL adapters block (most permissive)."""
    
    def __init__(self, name: str = "all", config: Dict[str, Any] | None = None):
        """Initialize All strategy."""
        super().__init__(name, config)
    
    def combine(
        self,
        results: List[ModerationResult],
        category: str,
        language: str
    ) -> EnsembleResult:
        """Combine results - block only if all adapters block.
        
        Args:
            results: List of ModerationResult from adapters
            category: Content category
            language: Language code
            
        Returns:
            EnsembleResult with ALL logic applied
        """
        if not results:
            raise ValueError("Cannot combine empty results list")
        
        # Block only if ALL adapters block
        blocked = all(r.blocked for r in results)
        
        # Use average score
        avg_score = sum(r.score for r in results) / len(results)
        
        # Sum latencies
        total_latency = sum(r.latency_ms for r in results)
        
        # Find which adapters blocked
        blocking_adapters = [r.adapter_name for r in results if r.blocked]
        
        return EnsembleResult(
            score=avg_score,
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
                "consensus": len(blocking_adapters) == len(results),
            }
        )

