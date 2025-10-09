"""Adapter registry for managing available adapters."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Type

from .base import ModerationAdapter
from .local import LocalAdapter
from .openai import OpenAIAdapter
from .azure import AzureAdapter

logger = logging.getLogger(__name__)


class AdapterRegistry:
    """Registry for managing moderation adapters."""
    
    _adapters: Dict[str, Type[ModerationAdapter]] = {
        "local": LocalAdapter,
        "openai": OpenAIAdapter,
        "azure": AzureAdapter,
    }
    
    _instances: Dict[str, ModerationAdapter] = {}
    
    @classmethod
    def register(cls, name: str, adapter_class: Type[ModerationAdapter]) -> None:
        """Register a new adapter class.
        
        Args:
            name: Adapter name
            adapter_class: Adapter class to register
        """
        cls._adapters[name] = adapter_class
        logger.info(f"Registered adapter: {name}")
    
    @classmethod
    def get_adapter(
        cls,
        name: str,
        config: Optional[Dict[str, Any]] = None,
        reuse: bool = True
    ) -> ModerationAdapter:
        """Get an adapter instance.
        
        Args:
            name: Adapter name
            config: Optional configuration
            reuse: If True, reuse existing instance
            
        Returns:
            ModerationAdapter instance
            
        Raises:
            ValueError: If adapter not found
        """
        if reuse and name in cls._instances:
            return cls._instances[name]
        
        if name not in cls._adapters:
            raise ValueError(
                f"Adapter '{name}' not found. "
                f"Available adapters: {list(cls._adapters.keys())}"
            )
        
        adapter_class = cls._adapters[name]
        instance = adapter_class(name=name, config=config)
        
        if reuse:
            cls._instances[name] = instance
        
        logger.info(f"Created adapter instance: {name}")
        return instance
    
    @classmethod
    def list_adapters(cls) -> List[str]:
        """List available adapter names.
        
        Returns:
            List of adapter names
        """
        return list(cls._adapters.keys())
    
    @classmethod
    def clear_instances(cls) -> None:
        """Clear all adapter instances."""
        cls._instances.clear()
        logger.info("Cleared all adapter instances")
    
    @classmethod
    def get_all_metrics(cls) -> Dict[str, Dict[str, Any]]:
        """Get metrics from all active adapters.
        
        Returns:
            Dictionary mapping adapter name to metrics
        """
        return {
            name: adapter.get_metrics()
            for name, adapter in cls._instances.items()
        }


def get_adapter(name: str, config: Optional[Dict[str, Any]] = None) -> ModerationAdapter:
    """Convenience function to get an adapter.
    
    Args:
        name: Adapter name
        config: Optional configuration
        
    Returns:
        ModerationAdapter instance
    """
    return AdapterRegistry.get_adapter(name, config)

