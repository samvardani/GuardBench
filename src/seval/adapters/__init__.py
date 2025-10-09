"""Pluggable moderation adapters for multi-model support."""

from __future__ import annotations

from .base import ModerationAdapter, ModerationResult
from .local import LocalAdapter
from .openai import OpenAIAdapter
from .azure import AzureAdapter
from .registry import AdapterRegistry, get_adapter

__all__ = [
    "ModerationAdapter",
    "ModerationResult",
    "LocalAdapter",
    "OpenAIAdapter",
    "AzureAdapter",
    "get_adapter",
    "AdapterRegistry",
]

