"""Azure Content Safety API adapter."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

from .base_guard import BaseGuardAdapter, ScoreResult, GuardMetadata

logger = logging.getLogger(__name__)

try:
    import httpx
except ImportError:
    httpx = None


class AzureContentSafetyAdapter(BaseGuardAdapter):
    """Adapter for Azure Content Safety API.
    
    Uses Azure's content moderation service to evaluate text safety.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None,
        api_version: str = "2023-10-01",
        **kwargs: Any
    ):
        """Initialize Azure Content Safety adapter.
        
        Args:
            api_key: Azure Content Safety API key (required)
            endpoint: Azure Content Safety endpoint (required)
            api_version: API version
            **kwargs: Additional configuration
        """
        super().__init__(api_key=api_key, endpoint=endpoint, api_version=api_version, **kwargs)
        
        if httpx is None:
            raise ImportError("httpx package not installed. Run: pip install httpx")
        
        if not api_key:
            raise ValueError("Azure Content Safety API key is required")
        
        if not endpoint:
            raise ValueError("Azure Content Safety endpoint is required")
        
        self.api_key = api_key
        self.endpoint = endpoint.rstrip("/")
        self.api_version = api_version
        self.client = httpx.Client(timeout=30.0)
    
    def score(
        self,
        text: str,
        *,
        category: Optional[str] = None,
        language: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ScoreResult:
        """Evaluate text using Azure Content Safety API.
        
        Args:
            text: Text to evaluate
            category: Optional category hint (unused)
            language: Optional language code
            context: Optional context (unused)
            
        Returns:
            ScoreResult
        """
        start_time = time.perf_counter()
        
        try:
            # Call Azure Content Safety API
            url = f"{self.endpoint}/contentsafety/text:analyze?api-version={self.api_version}"
            
            payload = {"text": text}
            
            headers = {
                "Ocp-Apim-Subscription-Key": self.api_key,
                "Content-Type": "application/json",
            }
            
            response = self.client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            
            data = response.json()
            
            # Azure returns categories with severity levels (0-6)
            # Map to 0.0-1.0 scale (divide by 6)
            categories = {}
            for cat in ["Hate", "SelfHarm", "Sexual", "Violence"]:
                if cat in data:
                    severity = data[cat].get("severity", 0)
                    categories[cat.lower()] = severity / 6.0
            
            # Overall score (max severity)
            score = max(categories.values()) if categories else 0.0
            
            # Flagged if any category severity > 2 (moderate)
            flagged = any(data.get(cat, {}).get("severity", 0) > 2 
                         for cat in ["Hate", "SelfHarm", "Sexual", "Violence"])
            
            return ScoreResult(
                flagged=flagged,
                score=score,
                categories=categories,
                latency_ms=latency_ms,
                provider="azure",
                model="content-safety",
                raw_response=data,
            )
        
        except Exception as e:
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            logger.error(f"Azure Content Safety adapter error: {e}")
            
            return ScoreResult(
                flagged=False,
                score=0.0,
                latency_ms=latency_ms,
                provider="azure",
                raw_response={"error": str(e)},
            )
    
    def get_metadata(self) -> GuardMetadata:
        """Get adapter metadata.
        
        Returns:
            GuardMetadata
        """
        return GuardMetadata(
            name="azure",
            provider="Microsoft Azure",
            version=self.api_version,
            supported_languages=["en", "es", "fr", "de", "it", "pt", "zh", "ja", "ko"],
            supported_categories=[
                "hate",
                "self-harm",
                "sexual",
                "violence",
            ],
            requires_api_key=True,
            max_text_length=10000,
        )
    
    def health_check(self) -> bool:
        """Check if Azure Content Safety API is accessible.
        
        Returns:
            True if healthy
        """
        try:
            # Try a simple analyze call
            result = self.score("test")
            return result.provider == "azure" and "error" not in result.raw_response
        except Exception as e:
            logger.error(f"Azure health check failed: {e}")
            return False


__all__ = ["AzureContentSafetyAdapter"]

