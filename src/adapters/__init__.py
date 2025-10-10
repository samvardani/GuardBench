"""Unified adapter registry for content moderation providers."""

from __future__ import annotations

from .base import BaseGuardAdapter, ScoreResult
from .registry import AdapterRegistry, get_adapter_registry
from .local import LocalPolicyAdapter
from .openai import OpenAIAdapter
from .azure import AzureContentSafetyAdapter

__all__ = [
    "BaseGuardAdapter",
    "ScoreResult",
    "AdapterRegistry",
    "get_adapter_registry",
    "LocalPolicyAdapter",
    "OpenAIAdapter",
    "AzureContentSafetyAdapter",
]

