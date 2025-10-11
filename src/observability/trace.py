"""Unified trace ID management for HTTP and gRPC using contextvars.

This module provides a single source of truth for trace IDs across the entire
application, ensuring consistent propagation through HTTP and gRPC layers.
"""

from __future__ import annotations

import contextvars
import uuid
from typing import Mapping, Optional

# Context variable to store trace ID for the current async task
# This ensures proper isolation between concurrent requests
_TRACE_ID: contextvars.ContextVar[str] = contextvars.ContextVar("trace_id", default="")


def get_or_create_trace_id(
    request_headers: Optional[Mapping[str, str]] = None
) -> str:
    """Get existing trace ID or create a new one.
    
    Priority order:
    1. Check if trace ID already set in contextvar (reuse within same request)
    2. Extract from x-trace-id header
    3. Extract from x-request-id header  
    4. Parse from traceparent header (OpenTelemetry W3C format)
    5. Generate new UUID4 and convert to 32-char hex format
    
    Args:
        request_headers: Optional mapping of request headers (case-insensitive keys)
        
    Returns:
        32-character hex string trace ID (no dashes, OpenTelemetry format)
        
    Examples:
        >>> trace_id = get_or_create_trace_id({"x-trace-id": "abc123"})
        >>> trace_id = get_or_create_trace_id()  # Generates new UUID
    """
    # Check if already set in contextvar (within same request)
    existing = _TRACE_ID.get("")
    if existing:
        return existing
    
    # Try to extract from headers
    if request_headers:
        # Convert headers to lowercase for case-insensitive lookup
        headers_lower = {k.lower(): v for k, v in request_headers.items()}
        
        # Priority 1: x-trace-id (most explicit)
        if "x-trace-id" in headers_lower:
            trace_id = headers_lower["x-trace-id"]
            # If already 32 hex chars, use as-is
            if len(trace_id) == 32 and all(c in "0123456789abcdefABCDEF" for c in trace_id):
                trace_id = trace_id.lower()
            else:
                # Try to normalize (remove dashes, take first 32 hex chars)
                normalized = trace_id.replace("-", "").replace("_", "")
                if len(normalized) >= 32 and all(c in "0123456789abcdefABCDEF" for c in normalized[:32]):
                    trace_id = normalized[:32].lower()
                else:
                    # Invalid format, generate new
                    trace_id = _generate_trace_id()
            _TRACE_ID.set(trace_id)
            return trace_id
        
        # Priority 2: x-request-id
        if "x-request-id" in headers_lower:
            request_id = headers_lower["x-request-id"]
            # Convert UUID format to 32 hex chars
            trace_id = _normalize_to_hex32(request_id)
            _TRACE_ID.set(trace_id)
            return trace_id
        
        # Priority 3: traceparent (OpenTelemetry W3C Trace Context)
        # Format: "00-{trace_id}-{span_id}-{flags}"
        if "traceparent" in headers_lower:
            traceparent = headers_lower["traceparent"]
            parts = traceparent.split("-")
            if len(parts) >= 2 and len(parts[1]) == 32:
                trace_id = parts[1].lower()
                _TRACE_ID.set(trace_id)
                return trace_id
    
    # No valid header found, generate new trace ID
    trace_id = _generate_trace_id()
    _TRACE_ID.set(trace_id)
    return trace_id


def current_trace_id() -> Optional[str]:
    """Get the current trace ID from contextvar.
    
    Returns:
        Current trace ID if set, None otherwise
        
    Examples:
        >>> trace_id = current_trace_id()
        >>> if trace_id:
        ...     logger.info("Processing", extra={"trace_id": trace_id})
    """
    trace_id = _TRACE_ID.get("")
    return trace_id if trace_id else None


def set_trace_id(trace_id: str) -> None:
    """Explicitly set the trace ID for the current context.
    
    Args:
        trace_id: Trace ID to set (should be 32 hex chars)
        
    Examples:
        >>> set_trace_id("abc123def456...")
    """
    # Normalize to 32 hex chars
    normalized = _normalize_to_hex32(trace_id)
    _TRACE_ID.set(normalized)


def clear_trace_id() -> None:
    """Clear the current trace ID (useful for testing).
    
    Examples:
        >>> clear_trace_id()
        >>> assert current_trace_id() is None
    """
    _TRACE_ID.set("")


def _generate_trace_id() -> str:
    """Generate a new trace ID in OpenTelemetry format (32 hex chars).
    
    Returns:
        32-character lowercase hex string (no dashes)
        
    Examples:
        >>> trace_id = _generate_trace_id()
        >>> len(trace_id)
        32
        >>> all(c in '0123456789abcdef' for c in trace_id)
        True
    """
    # Generate UUID4 and convert to 32 hex chars (remove dashes)
    return uuid.uuid4().hex


def _normalize_to_hex32(value: str) -> str:
    """Normalize various trace ID formats to 32 hex chars.
    
    Handles:
    - UUID format with dashes: "550e8400-e29b-41d4-a716-446655440000"
    - Hex string with dashes: "550e8400-e29b-41d4-a716-446655440000"
    - Already normalized: "550e8400e29b41d4a716446655440000"
    - Partial/invalid: generates new ID
    
    Args:
        value: Input trace ID in various formats
        
    Returns:
        32-character lowercase hex string
        
    Examples:
        >>> _normalize_to_hex32("550e8400-e29b-41d4-a716-446655440000")
        '550e8400e29b41d4a716446655440000'
    """
    # Remove common separators
    cleaned = value.replace("-", "").replace("_", "").replace(" ", "").lower()
    
    # If exactly 32 hex chars, use as-is
    if len(cleaned) == 32 and all(c in "0123456789abcdef" for c in cleaned):
        return cleaned
    
    # If longer, take first 32 hex chars
    if len(cleaned) > 32:
        prefix = cleaned[:32]
        if all(c in "0123456789abcdef" for c in prefix):
            return prefix
    
    # Invalid format, generate new
    return _generate_trace_id()


__all__ = [
    "get_or_create_trace_id",
    "current_trace_id",
    "set_trace_id",
    "clear_trace_id",
]

