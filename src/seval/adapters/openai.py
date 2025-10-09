"""OpenAI Moderation API adapter."""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, Optional

from .base import ModerationAdapter, ModerationResult

logger = logging.getLogger(__name__)


class OpenAIAdapter(ModerationAdapter):
    """OpenAI Moderation API adapter."""
    
    # Category mapping from our categories to OpenAI's
    CATEGORY_MAPPING = {
        "violence": "violence",
        "self_harm": "self-harm",
        "hate": "hate",
        "sexual": "sexual",
        "harassment": "harassment",
        "crime": "violence",  # Map to closest OpenAI category
        "malware": "violence",
    }
    
    def __init__(self, name: str = "openai", config: Optional[Dict[str, Any]] = None):
        """Initialize OpenAI adapter.
        
        Args:
            name: Adapter name
            config: Optional configuration with api_key
        """
        super().__init__(name, config)
        self.api_key = config.get("api_key") if config else None
        if not self.api_key:
            self.api_key = os.getenv("OPENAI_API_KEY")
        
        self._client = None
    
    def _get_client(self) -> Any:
        """Lazy load OpenAI client."""
        if self._client is None:
            try:
                import openai
                self._client = openai.OpenAI(api_key=self.api_key)
            except ImportError:
                logger.error("openai package not installed. Install with: pip install openai")
                raise
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
                raise
        return self._client
    
    def moderate(
        self,
        text: str,
        category: str,
        language: str,
        **kwargs: Any
    ) -> ModerationResult:
        """Perform moderation using OpenAI API.
        
        Args:
            text: Text to moderate
            category: Content category
            language: Language code
            **kwargs: Additional parameters
            
        Returns:
            ModerationResult with OpenAI scores
        """
        if not self.api_key:
            raise ValueError("OpenAI API key not configured")
        
        start_time = time.perf_counter()
        
        try:
            client = self._get_client()
            response = client.moderations.create(input=text)
            
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            self._track_call(latency_ms)
            
            # Get results from first result object
            result = response.results[0]
            
            # Map our category to OpenAI category
            openai_category = self.CATEGORY_MAPPING.get(category, "violence")
            
            # Get category score
            scores = result.category_scores
            score = getattr(scores, openai_category.replace("-", "_"), 0.0)
            
            # OpenAI provides scores 0-1, we scale to 0-5
            normalized_score = score * 5.0
            
            # Determine if blocked (OpenAI uses 0.5 threshold internally)
            blocked = result.flagged or score > 0.5
            
            return ModerationResult(
                score=normalized_score,
                blocked=blocked,
                category=category,
                language=language,
                adapter_name=self.name,
                latency_ms=latency_ms,
                confidence=score,
                metadata={
                    "openai_category": openai_category,
                    "flagged": result.flagged,
                    "all_scores": {k: getattr(scores, k) for k in dir(scores) if not k.startswith("_")},
                },
            )
        
        except Exception as e:
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            self._track_call(latency_ms)
            logger.error(f"OpenAI adapter error: {e}")
            
            # Return safe fallback
            return ModerationResult(
                score=0.0,
                blocked=False,
                category=category,
                language=language,
                adapter_name=self.name,
                latency_ms=latency_ms,
                metadata={"error": str(e)},
            )
    
    def health_check(self) -> bool:
        """Check if OpenAI adapter is healthy.
        
        Returns:
            True if API key is configured and client can be initialized
        """
        if not self.api_key:
            return False
        try:
            self._get_client()
            return True
        except Exception:
            return False

