"""OpenAI Moderation API adapter."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

from .base_guard import BaseGuardAdapter, ScoreResult, GuardMetadata

logger = logging.getLogger(__name__)

try:
    import openai
except ImportError:
    openai = None


class OpenAIAdapter(BaseGuardAdapter):
    """Adapter for OpenAI Moderation API.
    
    Uses OpenAI's content moderation endpoint to evaluate text safety.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "text-moderation-latest",
        **kwargs: Any
    ):
        """Initialize OpenAI adapter.
        
        Args:
            api_key: OpenAI API key (required)
            model: Moderation model to use
            **kwargs: Additional configuration
        """
        super().__init__(api_key=api_key, model=model, **kwargs)
        
        if openai is None:
            raise ImportError("openai package not installed. Run: pip install openai")
        
        if not api_key:
            raise ValueError("OpenAI API key is required")
        
        self.api_key = api_key
        self.model = model
        self.client = openai.OpenAI(api_key=api_key)
    
    def score(
        self,
        text: str,
        *,
        category: Optional[str] = None,
        language: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ScoreResult:
        """Evaluate text using OpenAI Moderation API.
        
        Args:
            text: Text to evaluate
            category: Optional category hint (unused by OpenAI)
            language: Optional language code (unused by OpenAI)
            context: Optional context (unused)
            
        Returns:
            ScoreResult
        """
        start_time = time.perf_counter()
        
        try:
            # Call OpenAI Moderation API
            response = self.client.moderations.create(
                input=text,
                model=self.model
            )
            
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            
            # Extract first result
            result = response.results[0]
            
            # Build categories dictionary
            categories = {
                "hate": result.category_scores.hate,
                "hate/threatening": result.category_scores.hate_threatening,
                "harassment": result.category_scores.harassment,
                "harassment/threatening": result.category_scores.harassment_threatening,
                "self-harm": result.category_scores.self_harm,
                "self-harm/intent": result.category_scores.self_harm_intent,
                "self-harm/instructions": result.category_scores.self_harm_instructions,
                "sexual": result.category_scores.sexual,
                "sexual/minors": result.category_scores.sexual_minors,
                "violence": result.category_scores.violence,
                "violence/graphic": result.category_scores.violence_graphic,
            }
            
            # Overall score (max of all categories)
            score = max(categories.values())
            
            # Flagged if any category flagged
            flagged = result.flagged
            
            return ScoreResult(
                flagged=flagged,
                score=score,
                categories=categories,
                latency_ms=latency_ms,
                provider="openai",
                model=self.model,
                raw_response=result.model_dump() if hasattr(result, "model_dump") else None,
            )
        
        except Exception as e:
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            logger.error(f"OpenAI adapter error: {e}")
            
            # Return error result
            return ScoreResult(
                flagged=False,
                score=0.0,
                latency_ms=latency_ms,
                provider="openai",
                raw_response={"error": str(e)},
            )
    
    def get_metadata(self) -> GuardMetadata:
        """Get adapter metadata.
        
        Returns:
            GuardMetadata
        """
        return GuardMetadata(
            name="openai",
            provider="OpenAI",
            version=self.model,
            supported_languages=["en"],  # OpenAI primarily supports English
            supported_categories=[
                "hate",
                "hate/threatening",
                "harassment",
                "harassment/threatening",
                "self-harm",
                "self-harm/intent",
                "self-harm/instructions",
                "sexual",
                "sexual/minors",
                "violence",
                "violence/graphic",
            ],
            requires_api_key=True,
            max_text_length=None,  # OpenAI handles long text
        )
    
    def health_check(self) -> bool:
        """Check if OpenAI API is accessible.
        
        Returns:
            True if healthy
        """
        try:
            # Try a simple moderation call
            response = self.client.moderations.create(
                input="test",
                model=self.model
            )
            return len(response.results) > 0
        except Exception as e:
            logger.error(f"OpenAI health check failed: {e}")
            return False


__all__ = ["OpenAIAdapter"]

