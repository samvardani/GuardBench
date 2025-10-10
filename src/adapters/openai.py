"""OpenAI moderation adapter."""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, Optional

from .base import BaseGuardAdapter, ScoreResult

logger = logging.getLogger(__name__)

try:
    import httpx
except ImportError:
    httpx = None


class OpenAIAdapter(BaseGuardAdapter):
    """OpenAI Moderation API adapter."""
    
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        """Initialize OpenAI adapter.
        
        Args:
            name: Adapter name
            config: Optional configuration
        """
        super().__init__(name, config)
        
        self.api_key = config.get("api_key") if config else None
        if not self.api_key:
            self.api_key = os.getenv("OPENAI_API_KEY")
        
        if not self.api_key:
            logger.warning("OpenAI API key not configured")
    
    def score(self, text: str, context: Optional[Dict[str, Any]] = None) -> ScoreResult:
        """Score content using OpenAI Moderation API.
        
        Args:
            text: Content to evaluate
            context: Optional context
            
        Returns:
            ScoreResult
        """
        if httpx is None:
            raise ImportError("httpx required for OpenAI adapter")
        
        if not self.api_key:
            raise ValueError("OpenAI API key not configured")
        
        start = time.time()
        
        try:
            # Call OpenAI Moderation API
            with httpx.Client(timeout=10.0) as client:
                response = client.post(
                    "https://api.openai.com/v1/moderations",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={"input": text}
                )
                
                response.raise_for_status()
                data = response.json()
            
            # Parse response
            result = data["results"][0]
            categories = result["category_scores"]
            flagged = result["flagged"]
            flagged_categories = [cat for cat, val in result["categories"].items() if val]
            
            latency_ms = int((time.time() - start) * 1000)
            
            return ScoreResult(
                is_safe=not flagged,
                confidence=0.9,
                categories=categories,
                flagged_categories=flagged_categories,
                provider="openai",
                latency_ms=latency_ms
            )
        
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            
            # Return safe on error (fail open)
            latency_ms = int((time.time() - start) * 1000)
            
            return ScoreResult(
                is_safe=True,
                confidence=0.0,
                categories={},
                flagged_categories=[],
                provider="openai",
                latency_ms=latency_ms,
                reason=f"API error: {str(e)}"
            )


__all__ = ["OpenAIAdapter"]

