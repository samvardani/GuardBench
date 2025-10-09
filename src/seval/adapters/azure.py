"""Azure Content Safety adapter."""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, Optional

from .base import ModerationAdapter, ModerationResult

logger = logging.getLogger(__name__)


class AzureAdapter(ModerationAdapter):
    """Azure Content Safety API adapter."""
    
    # Category mapping
    CATEGORY_MAPPING = {
        "violence": "Violence",
        "self_harm": "SelfHarm",
        "hate": "Hate",
        "sexual": "Sexual",
        "crime": "Violence",
        "malware": "Violence",
    }
    
    # Severity thresholds (Azure uses 0-6 scale)
    SEVERITY_THRESHOLD = 2  # Medium severity
    
    def __init__(self, name: str = "azure", config: Optional[Dict[str, Any]] = None):
        """Initialize Azure adapter.
        
        Args:
            name: Adapter name
            config: Optional configuration with endpoint and key
        """
        super().__init__(name, config)
        self.endpoint = config.get("endpoint") if config else None
        self.api_key = config.get("api_key") if config else None
        
        if not self.endpoint:
            self.endpoint = os.getenv("AZURE_CONTENT_SAFETY_ENDPOINT")
        if not self.api_key:
            self.api_key = os.getenv("AZURE_CONTENT_SAFETY_KEY") or os.getenv("AZURE_KEY")
        
        self._client = None
    
    def _get_client(self) -> Any:
        """Lazy load Azure client."""
        if self._client is None:
            try:
                from azure.ai.contentsafety import ContentSafetyClient
                from azure.core.credentials import AzureKeyCredential
                
                if not self.endpoint or not self.api_key:
                    raise ValueError("Azure endpoint and key must be configured")
                
                self._client = ContentSafetyClient(
                    endpoint=self.endpoint,
                    credential=AzureKeyCredential(self.api_key)
                )
            except ImportError:
                logger.error(
                    "azure-ai-contentsafety package not installed. "
                    "Install with: pip install azure-ai-contentsafety"
                )
                raise
            except Exception as e:
                logger.error(f"Failed to initialize Azure client: {e}")
                raise
        return self._client
    
    def moderate(
        self,
        text: str,
        category: str,
        language: str,
        **kwargs: Any
    ) -> ModerationResult:
        """Perform moderation using Azure Content Safety API.
        
        Args:
            text: Text to moderate
            category: Content category
            language: Language code
            **kwargs: Additional parameters
            
        Returns:
            ModerationResult with Azure scores
        """
        if not self.endpoint or not self.api_key:
            raise ValueError("Azure endpoint and key not configured")
        
        start_time = time.perf_counter()
        
        try:
            from azure.ai.contentsafety.models import AnalyzeTextOptions
            
            client = self._get_client()
            
            # Analyze text
            request = AnalyzeTextOptions(text=text)
            response = client.analyze_text(request)
            
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            self._track_call(latency_ms)
            
            # Map our category to Azure category
            azure_category = self.CATEGORY_MAPPING.get(category, "Violence")
            
            # Extract severity for requested category
            severity = 0
            for cat_analysis in response.categories_analysis:
                if cat_analysis.category == azure_category:
                    severity = cat_analysis.severity
                    break
            
            # Azure uses 0-6 scale, normalize to 0-5
            normalized_score = (severity / 6.0) * 5.0
            
            # Block if severity exceeds threshold
            blocked = severity >= self.SEVERITY_THRESHOLD
            
            return ModerationResult(
                score=normalized_score,
                blocked=blocked,
                category=category,
                language=language,
                adapter_name=self.name,
                latency_ms=latency_ms,
                confidence=severity / 6.0,
                metadata={
                    "azure_category": azure_category,
                    "severity": severity,
                    "all_categories": [
                        {
                            "category": cat.category,
                            "severity": cat.severity
                        }
                        for cat in response.categories_analysis
                    ],
                },
            )
        
        except Exception as e:
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            self._track_call(latency_ms)
            logger.error(f"Azure adapter error: {e}")
            
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
        """Check if Azure adapter is healthy.
        
        Returns:
            True if endpoint and key are configured
        """
        if not self.endpoint or not self.api_key:
            return False
        try:
            self._get_client()
            return True
        except Exception:
            return False

