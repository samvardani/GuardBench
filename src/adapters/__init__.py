"""Adapter interfaces for external integrations.

This module provides abstract base classes for integrating with third-party services,
eliminating duplicate logic and enabling easy addition of new providers.
"""

from __future__ import annotations

from .base_guard import BaseGuardAdapter, ScoreResult, GuardMetadata
from .base_connector import BaseConnector, ConnectorMetadata
from .registry import AdapterRegistry, get_guard_adapter, register_guard_adapter

__all__ = [
    "BaseGuardAdapter",
    "ScoreResult",
    "GuardMetadata",
    "BaseConnector",
    "ConnectorMetadata",
    "AdapterRegistry",
    "get_guard_adapter",
    "register_guard_adapter",
]

