#!/usr/bin/env python3
"""
SeaRei Python SDK
Official Python client for SeaRei AI Safety API

Installation:
    pip install searei

Usage:
    from searei import SeaReiClient
    
    client = SeaReiClient(api_key="your_api_key")
    result = client.score("I will kill you")
    
    if result.is_unsafe:
        print(f"Flagged: {result.category} ({result.score:.2f})")
"""

import os
import time
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field

try:
    import requests
except ImportError:
    raise ImportError("requests library required. Install with: pip install requests")


__version__ = "0.1.0"
__author__ = "SeaRei Team"


@dataclass
class ScoreResult:
    """Result from a content safety score request"""
    prediction: str
    score: float
    category: Optional[str] = None
    rationale: Optional[str] = None
    method: Optional[str] = None
    latency_ms: Optional[int] = None
    policy_version: Optional[str] = None
    policy_checksum: Optional[str] = None
    
    @property
    def is_safe(self) -> bool:
        """Returns True if content is safe (prediction == 'pass')"""
        return self.prediction == "pass"
    
    @property
    def is_unsafe(self) -> bool:
        """Returns True if content is unsafe (prediction == 'flag')"""
        return self.prediction == "flag"
    
    def __repr__(self) -> str:
        return f"ScoreResult(prediction='{self.prediction}', score={self.score:.3f}, category='{self.category}')"


@dataclass
class BatchResult:
    """Result from a batch score request"""
    results: List[ScoreResult]
    total: int
    flagged: int
    safe: int
    latency_ms: int
    
    def __repr__(self) -> str:
        return f"BatchResult(total={self.total}, flagged={self.flagged}, safe={self.safe})"


class SeaReiError(Exception):
    """Base exception for SeaRei SDK errors"""
    pass


class AuthenticationError(SeaReiError):
    """Raised when API key is invalid or missing"""
    pass


class RateLimitError(SeaReiError):
    """Raised when rate limit is exceeded"""
    pass


class ValidationError(SeaReiError):
    """Raised when request validation fails"""
    pass


class SeaReiClient:
    """
    SeaRei AI Safety API Client
    
    Args:
        api_key: API key for authentication (optional for self-hosted)
        base_url: Base URL for API (default: http://localhost:8001)
        timeout: Request timeout in seconds (default: 30)
        max_retries: Maximum number of retries on failure (default: 3)
    
    Example:
        >>> client = SeaReiClient(api_key="sk_test_...")
        >>> result = client.score("I will kill you")
        >>> print(result.prediction)
        flag
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "http://localhost:8001",
        timeout: int = 30,
        max_retries: int = 3
    ):
        self.api_key = api_key or os.environ.get("SEAREI_API_KEY")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self._session = requests.Session()
        
        # Set default headers
        self._session.headers.update({
            "User-Agent": f"searei-python/{__version__}",
            "Content-Type": "application/json"
        })
        
        if self.api_key:
            self._session.headers["Authorization"] = f"Bearer {self.api_key}"
    
    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make an HTTP request with retry logic"""
        url = f"{self.base_url}{endpoint}"
        kwargs.setdefault("timeout", self.timeout)
        
        last_error = None
        for attempt in range(self.max_retries):
            try:
                response = self._session.request(method, url, **kwargs)
                
                # Handle errors
                if response.status_code == 401:
                    raise AuthenticationError("Invalid or missing API key")
                elif response.status_code == 429:
                    raise RateLimitError("Rate limit exceeded")
                elif response.status_code == 422:
                    raise ValidationError(f"Validation error: {response.text}")
                elif response.status_code >= 400:
                    raise SeaReiError(f"API error ({response.status_code}): {response.text}")
                
                return response.json()
                
            except requests.exceptions.RequestException as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                continue
        
        raise SeaReiError(f"Request failed after {self.max_retries} retries: {last_error}")
    
    def score(
        self,
        text: str,
        category: Optional[str] = None,
        language: Optional[str] = None
    ) -> ScoreResult:
        """
        Score a single text for safety violations
        
        Args:
            text: Text content to score
            category: Optional category filter (violence, self_harm, harassment, etc.)
            language: Optional language code (en, es, ar, etc.)
        
        Returns:
            ScoreResult with prediction, score, and metadata
        
        Example:
            >>> result = client.score("I will kill you")
            >>> if result.is_unsafe:
            ...     print(f"Flagged: {result.category}")
        """
        payload = {"text": text}
        if category:
            payload["category"] = category
        if language:
            payload["language"] = language
        
        data = self._request("POST", "/score", json=payload)
        
        return ScoreResult(
            prediction=data["prediction"],
            score=data["score"],
            category=data.get("category"),
            rationale=data.get("rationale"),
            method=data.get("method"),
            latency_ms=data.get("latency_ms"),
            policy_version=data.get("policy_version"),
            policy_checksum=data.get("policy_checksum")
        )
    
    def batch_score(
        self,
        texts: List[str],
        category: Optional[str] = None,
        language: Optional[str] = None
    ) -> BatchResult:
        """
        Score multiple texts in a single request
        
        Args:
            texts: List of text contents to score
            category: Optional category filter
            language: Optional language code
        
        Returns:
            BatchResult with results for all texts
        
        Example:
            >>> texts = ["Hello world", "I will kill you", "Nice weather"]
            >>> result = client.batch_score(texts)
            >>> print(f"Flagged {result.flagged}/{result.total}")
        """
        rows = [{"text": text} for text in texts]
        payload = {"rows": rows}
        if category:
            payload["category"] = category
        if language:
            payload["language"] = language
        
        data = self._request("POST", "/score-batch", json=payload)
        
        results = [
            ScoreResult(
                prediction=r["prediction"],
                score=r["score"],
                category=r.get("category"),
                rationale=r.get("rationale"),
                method=r.get("method")
            )
            for r in data["results"]
        ]
        
        return BatchResult(
            results=results,
            total=len(results),
            flagged=sum(1 for r in results if r.is_unsafe),
            safe=sum(1 for r in results if r.is_safe),
            latency_ms=data.get("latency_ms", 0)
        )
    
    def health(self) -> Dict[str, Any]:
        """
        Check API health status
        
        Returns:
            Dict with health status and metadata
        
        Example:
            >>> health = client.health()
            >>> print(health["status"])
            healthy
        """
        return self._request("GET", "/healthz")
    
    def __enter__(self):
        """Context manager support"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close session on context exit"""
        self._session.close()


# Convenience function
def score(text: str, api_key: Optional[str] = None, **kwargs) -> ScoreResult:
    """
    Quick score function without creating a client
    
    Example:
        >>> from searei import score
        >>> result = score("I will kill you")
        >>> print(result.prediction)
        flag
    """
    with SeaReiClient(api_key=api_key) as client:
        return client.score(text, **kwargs)


if __name__ == "__main__":
    # Simple CLI for testing
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python searei.py 'text to score'")
        sys.exit(1)
    
    text = " ".join(sys.argv[1:])
    
    try:
        result = score(text)
        print(f"\nResult: {result.prediction}")
        print(f"Score: {result.score:.3f}")
        if result.category:
            print(f"Category: {result.category}")
        if result.rationale:
            print(f"Rationale: {result.rationale}")
        print(f"Method: {result.method}")
        print(f"Latency: {result.latency_ms}ms")
    except SeaReiError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)












