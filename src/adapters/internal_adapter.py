"""Internal policy-based guard adapter."""

from __future__ import annotations

import time
from typing import Any, Dict, Optional

from .base_guard import BaseGuardAdapter, ScoreResult, GuardMetadata


class InternalPolicyAdapter(BaseGuardAdapter):
    """Adapter for the built-in policy-based safety guard.
    
    This wraps the internal evaluation logic into the standard adapter interface.
    """
    
    def __init__(self, predict_fn: Optional[callable] = None, **kwargs: Any):
        """Initialize internal adapter.
        
        Args:
            predict_fn: Optional prediction function (uses default if not provided)
            **kwargs: Additional configuration
        """
        super().__init__(**kwargs)
        self.predict_fn = predict_fn or self._default_predict
    
    def _default_predict(self, text: str, category: Optional[str], language: Optional[str]) -> Dict[str, Any]:
        """Default prediction using the internal policy engine.
        
        Args:
            text: Text to evaluate
            category: Category hint
            language: Language code
            
        Returns:
            Prediction result
        """
        # Import here to avoid circular dependency
        from seval.runner import predict
        
        return predict(text, category=category, language=language)
    
    def score(
        self,
        text: str,
        *,
        category: Optional[str] = None,
        language: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ScoreResult:
        """Evaluate text using internal policy.
        
        Args:
            text: Text to evaluate
            category: Optional category hint
            language: Optional language code
            context: Optional context (unused)
            
        Returns:
            ScoreResult
        """
        start_time = time.perf_counter()
        
        try:
            # Call prediction function
            result = self.predict_fn(text, category, language)
            
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            
            # Extract score and flagged status
            score = float(result.get("score", 0.0))
            flagged = result.get("flagged", score > 0.5)
            
            # Extract categories
            categories = result.get("categories", {})
            
            # Build ScoreResult
            return ScoreResult(
                flagged=flagged,
                score=score,
                categories=categories,
                latency_ms=latency_ms,
                provider="internal",
                model="policy-engine",
                raw_response=result,
            )
        
        except Exception as e:
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            logger.error(f"Internal adapter error: {e}")
            
            # Return safe fallback
            return ScoreResult(
                flagged=False,
                score=0.0,
                latency_ms=latency_ms,
                provider="internal",
                raw_response={"error": str(e)},
            )
    
    def get_metadata(self) -> GuardMetadata:
        """Get adapter metadata.
        
        Returns:
            GuardMetadata
        """
        return GuardMetadata(
            name="internal",
            provider="safety-eval-mini",
            version="1.0",
            supported_languages=["en", "es", "fa", "ar", "zh", "de", "fr", "it", "pt", "ru"],
            supported_categories=[
                "violence",
                "hate",
                "self_harm",
                "sexual",
                "harassment",
                "malware",
                "extortion",
            ],
            requires_api_key=False,
            max_text_length=10000,
        )


__all__ = ["InternalPolicyAdapter"]

