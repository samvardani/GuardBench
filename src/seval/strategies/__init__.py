"""Ensemble strategies for combining multiple adapters."""

from __future__ import annotations

from .base import EnsembleStrategy, EnsembleResult
from .any import AnyStrategy
from .all import AllStrategy
from .weighted import WeightedStrategy
from .registry import StrategyRegistry, get_strategy

__all__ = [
    "EnsembleStrategy",
    "EnsembleResult",
    "AnyStrategy",
    "AllStrategy",
    "WeightedStrategy",
    "get_strategy",
    "StrategyRegistry",
]

