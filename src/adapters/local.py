"""Local policy-based adapter."""

from __future__ import annotations

import time
from typing import Any, Dict, Optional

from .base import BaseGuardAdapter, ScoreResult


class LocalPolicyAdapter(BaseGuardAdapter):
    """Local policy-based guard adapter.
    
    Uses the system's built-in policy rules for content moderation.
    """
    
    def score(self, text: str, context: Optional[Dict[str, Any]] = None) -> ScoreResult:
        """Score content using local policy rules.
        
        Args:
            text: Content to evaluate
            context: Optional context
            
        Returns:
            ScoreResult
        """
        start = time.time()
        
        # Placeholder - would integrate with actual policy engine
        # For now, return a simple safe result
        is_safe = True
        categories = {}
        flagged_categories = []
        
        # Check for obvious unsafe patterns (very basic)
        unsafe_keywords = ["violence", "hate", "self-harm", "illegal"]
        text_lower = text.lower()
        
        for keyword in unsafe_keywords:
            if keyword in text_lower:
                is_safe = False
                categories[keyword] = 0.9
                flagged_categories.append(keyword)
        
        latency_ms = int((time.time() - start) * 1000)
        
        return ScoreResult(
            is_safe=is_safe,
            confidence=0.95 if is_safe else 0.85,
            categories=categories,
            flagged_categories=flagged_categories,
            provider="local",
            latency_ms=latency_ms
        )


__all__ = ["LocalPolicyAdapter"]

