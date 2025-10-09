"""Core scoring logic for safety evaluation."""

from __future__ import annotations

from typing import Any, Dict

from . import sdk


def score_once(text: str, category: str, language: str, guard: str = "candidate") -> Dict[str, Any]:
    """
    Score a single text input using the specified guard.
    
    Args:
        text: Input text to evaluate
        category: Safety category (e.g., "violence", "crime")
        language: Language code (e.g., "en", "es")
        guard: Guard model to use (default: "candidate")
    
    Returns:
        Dictionary with scoring results including:
        - score: Float score (0.0-1.0)
        - slices: List of matched policy slices
        - guard_version: Version of the guard used
        - latency_ms: Latency in milliseconds
        - request_id: Unique request identifier
        - policy_version: Policy version used
    """
    result = sdk.predict(text, category, language, guard=guard)
    
    # Normalize to consistent output format
    score_val = float(result.get("score") or (1.0 if result.get("prediction") else 0.0))
    slices = [str(s) for s in (result.get("slices") or [])]
    
    return {
        "score": score_val,
        "slices": slices,
        "guard_version": str(result.get("guard_version") or guard),
        "latency_ms": int(result.get("latency_ms") or 0),
        "request_id": str(result.get("request_id") or ""),
        "policy_version": str(result.get("policy_version") or "n/a"),
    }
