"""Privacy utilities for federated telemetry."""

from __future__ import annotations

import hashlib
import random
from typing import Any, Dict, Optional


def hash_text(text: str, salt: Optional[str] = None) -> str:
    """Hash text for privacy.
    
    Args:
        text: Text to hash
        salt: Optional salt for hashing
        
    Returns:
        SHA-256 hash (hex)
    """
    data = text.encode("utf-8")
    if salt:
        data = salt.encode("utf-8") + data
    
    return hashlib.sha256(data).hexdigest()


def anonymize_tenant_id(tenant_id: str, salt: str = "federated-salt") -> str:
    """Anonymize tenant ID.
    
    Args:
        tenant_id: Tenant ID
        salt: Salt for hashing
        
    Returns:
        Anonymized tenant ID
    """
    return hash_text(tenant_id, salt=salt)[:16]


def add_laplace_noise(value: float, epsilon: float = 1.0) -> float:
    """Add Laplace noise for differential privacy.
    
    Args:
        value: Original value
        epsilon: Privacy parameter (lower = more noise)
        
    Returns:
        Noised value
    """
    # Laplace distribution with scale = sensitivity / epsilon
    # For counts, sensitivity = 1
    scale = 1.0 / epsilon
    noise = random.expovariate(1.0 / scale)
    
    # Symmetric noise
    if random.random() < 0.5:
        noise = -noise
    
    return value + noise


def add_differential_privacy(
    stats: Dict[str, Any],
    epsilon: float = 1.0,
    fields: Optional[list[str]] = None
) -> Dict[str, Any]:
    """Add differential privacy noise to statistics.
    
    Args:
        stats: Statistics dictionary
        epsilon: Privacy parameter
        fields: Fields to noise (default: all numeric fields)
        
    Returns:
        Noised statistics
    """
    noised = stats.copy()
    
    # Default to noising all numeric fields
    if fields is None:
        fields = [k for k, v in stats.items() if isinstance(v, (int, float))]
    
    for field in fields:
        if field in noised and isinstance(noised[field], (int, float)):
            original = float(noised[field])
            noised_value = add_laplace_noise(original, epsilon=epsilon)
            
            # Keep non-negative for counts
            if isinstance(stats[field], int):
                noised[field] = max(0, int(round(noised_value)))
            else:
                noised[field] = max(0.0, noised_value)
    
    return noised


def anonymize_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Anonymize telemetry payload.
    
    Removes any potentially sensitive fields and hashes identifiers.
    
    Args:
        payload: Raw telemetry payload
        
    Returns:
        Anonymized payload
    """
    anonymized = payload.copy()
    
    # Remove sensitive fields
    sensitive_fields = [
        "raw_text",
        "prompt",
        "user_id",
        "email",
        "ip_address",
        "session_id",
    ]
    
    for field in sensitive_fields:
        anonymized.pop(field, None)
    
    # Anonymize tenant ID if present
    if "tenant_id" in anonymized and anonymized["tenant_id"]:
        anonymized["tenant_id"] = anonymize_tenant_id(anonymized["tenant_id"])
    
    # Hash any remaining text fields
    for key, value in list(anonymized.items()):
        if isinstance(value, str) and len(value) > 100:
            # Likely text content - hash it
            anonymized[key] = hash_text(value)
    
    return anonymized


__all__ = [
    "hash_text",
    "anonymize_tenant_id",
    "add_laplace_noise",
    "add_differential_privacy",
    "anonymize_payload",
]

