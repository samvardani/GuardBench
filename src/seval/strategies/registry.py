"""Strategy registry for managing ensemble strategies."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Type

from .base import EnsembleStrategy
from .any import AnyStrategy
from .all import AllStrategy
from .weighted import WeightedStrategy

logger = logging.getLogger(__name__)


class StrategyRegistry:
    """Registry for managing ensemble strategies."""
    
    _strategies: Dict[str, Type[EnsembleStrategy]] = {
        "any": AnyStrategy,
        "all": AllStrategy,
        "weighted": WeightedStrategy,
    }
    
    @classmethod
    def register(cls, name: str, strategy_class: Type[EnsembleStrategy]) -> None:
        """Register a new strategy class.
        
        Args:
            name: Strategy name
            strategy_class: Strategy class to register
        """
        cls._strategies[name] = strategy_class
        logger.info(f"Registered strategy: {name}")
    
    @classmethod
    def get_strategy(
        cls,
        name: str,
        config: Optional[Dict[str, Any]] = None
    ) -> EnsembleStrategy:
        """Get a strategy instance.
        
        Args:
            name: Strategy name
            config: Optional configuration
            
        Returns:
            EnsembleStrategy instance
            
        Raises:
            ValueError: If strategy not found
        """
        if name not in cls._strategies:
            raise ValueError(
                f"Strategy '{name}' not found. "
                f"Available strategies: {list(cls._strategies.keys())}"
            )
        
        strategy_class = cls._strategies[name]
        return strategy_class(name=name, config=config)
    
    @classmethod
    def list_strategies(cls) -> list[str]:
        """List available strategy names.
        
        Returns:
            List of strategy names
        """
        return list(cls._strategies.keys())


def get_strategy(name: str, config: Optional[Dict[str, Any]] = None) -> EnsembleStrategy:
    """Convenience function to get a strategy.
    
    Args:
        name: Strategy name
        config: Optional configuration
        
    Returns:
        EnsembleStrategy instance
    """
    return StrategyRegistry.get_strategy(name, config)

