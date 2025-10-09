"""Weighted strategy - combines adapter scores with weights."""

from __future__ import annotations

from typing import Any, Dict, List

from .base import EnsembleStrategy, EnsembleResult
from seval.adapters.base import ModerationResult


class WeightedStrategy(EnsembleStrategy):
    """Weighted combination of adapter scores."""
    
    def __init__(self, name: str = "weighted", config: Dict[str, Any] | None = None):
        """Initialize Weighted strategy.
        
        Args:
            name: Strategy name
            config: Configuration with optional weights dict and threshold
        """
        super().__init__(name, config)
        self.weights = config.get("weights", {}) if config else {}
        self.threshold = config.get("threshold", 2.5) if config else 2.5
        self.default_weight = config.get("default_weight", 1.0) if config else 1.0
    
    def combine(
        self,
        results: List[ModerationResult],
        category: str,
        language: str
    ) -> EnsembleResult:
        """Combine results using weighted average.
        
        Args:
            results: List of ModerationResult from adapters
            category: Content category
            language: Language code
            
        Returns:
            EnsembleResult with weighted score
        """
        if not results:
            raise ValueError("Cannot combine empty results list")
        
        # Calculate weighted score
        total_weight = 0.0
        weighted_sum = 0.0
        
        for result in results:
            weight = self.weights.get(result.adapter_name, self.default_weight)
            weighted_sum += result.score * weight
            total_weight += weight
        
        weighted_score = weighted_sum / total_weight if total_weight > 0 else 0.0
        
        # Block if weighted score exceeds threshold
        blocked = weighted_score >= self.threshold
        
        # Sum latencies
        total_latency = sum(r.latency_ms for r in results)
        
        # Get individual adapter decisions
        blocking_adapters = [r.adapter_name for r in results if r.blocked]
        
        return EnsembleResult(
            score=weighted_score,
            blocked=blocked,
            category=category,
            language=language,
            strategy=self.name,
            adapter_results=results,
            total_latency_ms=total_latency,
            metadata={
                "weights_used": {
                    r.adapter_name: self.weights.get(r.adapter_name, self.default_weight)
                    for r in results
                },
                "threshold": self.threshold,
                "blocking_adapters": blocking_adapters,
                "individual_scores": {r.adapter_name: r.score for r in results},
            }
        )

