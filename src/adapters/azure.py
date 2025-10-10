"""Azure Content Safety adapter."""

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


class AzureContentSafetyAdapter(BaseGuardAdapter):
    """Azure Content Safety API adapter."""
    
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        """Initialize Azure adapter.
        
        Args:
            name: Adapter name
            config: Optional configuration
        """
        super().__init__(name, config)
        
        self.api_key = config.get("api_key") if config else None
        self.endpoint = config.get("endpoint") if config else None
        
        if not self.api_key:
            self.api_key = os.getenv("AZURE_CONTENT_SAFETY_KEY")
        
        if not self.endpoint:
            self.endpoint = os.getenv("AZURE_CONTENT_SAFETY_ENDPOINT")
        
        if not self.api_key or not self.endpoint:
            logger.warning("Azure Content Safety not fully configured")
    
    def score(self, text: str, context: Optional[Dict[str, Any]] = None) -> ScoreResult:
        """Score content using Azure Content Safety API.
        
        Args:
            text: Content to evaluate
            context: Optional context
            
        Returns:
            ScoreResult
        """
        if httpx is None:
            raise ImportError("httpx required for Azure adapter")
        
        if not self.api_key or not self.endpoint:
            raise ValueError("Azure Content Safety not configured")
        
        start = time.time()
        
        try:
            # Call Azure Content Safety API
            with httpx.Client(timeout=10.0) as client:
                response = client.post(
                    f"{self.endpoint}/contentsafety/text:analyze?api-version=2023-10-01",
                    headers={
                        "Ocp-Apim-Subscription-Key": self.api_key,
                        "Content-Type": "application/json"
                    },
                    json={"text": text}
                )
                
                response.raise_for_status()
                data = response.json()
            
            # Parse response
            categories = {}
            flagged_categories = []
            
            for cat_result in data.get("categoriesAnalysis", []):
                cat_name = cat_result["category"].lower()
                severity = cat_result["severity"]
                
                # Convert severity (0-6) to probability
                score = severity / 6.0
                categories[cat_name] = score
                
                if severity >= 2:  # Threshold
                    flagged_categories.append(cat_name)
            
            is_safe = len(flagged_categories) == 0
            
            latency_ms = int((time.time() - start) * 1000)
            
            return ScoreResult(
                is_safe=is_safe,
                confidence=0.9,
                categories=categories,
                flagged_categories=flagged_categories,
                provider="azure",
                latency_ms=latency_ms
            )
        
        except Exception as e:
            logger.error(f"Azure API error: {e}")
            
            # Fail open
            latency_ms = int((time.time() - start) * 1000)
            
            return ScoreResult(
                is_safe=True,
                confidence=0.0,
                categories={},
                flagged_categories=[],
                provider="azure",
                latency_ms=latency_ms,
                reason=f"API error: {str(e)}"
            )


__all__ = ["AzureContentSafetyAdapter"]

