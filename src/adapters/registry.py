"""Unified adapter registry - single source of truth for providers."""

from __future__ import annotations

import logging
from typing import Dict, Optional, Type

from .base import BaseGuardAdapter

logger = logging.getLogger(__name__)


class AdapterRegistry:
    """Centralized registry for all guard adapters.
    
    Single source of truth for provider routing.
    """
    
    def __init__(self):
        """Initialize adapter registry."""
        self._adapters: Dict[str, Type[BaseGuardAdapter]] = {}
        self._instances: Dict[str, BaseGuardAdapter] = {}
        
        logger.info("AdapterRegistry initialized")
    
    def register(self, name: str, adapter_class: Type[BaseGuardAdapter]) -> None:
        """Register an adapter class.
        
        Args:
            name: Adapter name (e.g., "openai", "azure", "local")
            adapter_class: Adapter class (must extend BaseGuardAdapter)
        """
        if not issubclass(adapter_class, BaseGuardAdapter):
            raise ValueError(f"{adapter_class} must extend BaseGuardAdapter")
        
        if name in self._adapters:
            logger.warning(f"Adapter '{name}' already registered, overwriting")
        
        self._adapters[name] = adapter_class
        logger.info(f"Registered adapter: {name} → {adapter_class.__name__}")
    
    def get(self, name: str, config: Optional[dict] = None) -> BaseGuardAdapter:
        """Get adapter instance.
        
        Args:
            name: Adapter name
            config: Optional configuration
            
        Returns:
            Adapter instance
            
        Raises:
            KeyError: If adapter not registered
        """
        # Check cache
        cache_key = f"{name}:{id(config) if config else 'default'}"
        
        if cache_key in self._instances:
            return self._instances[cache_key]
        
        # Get class
        if name not in self._adapters:
            raise KeyError(f"Adapter '{name}' not registered. Available: {list(self._adapters.keys())}")
        
        adapter_class = self._adapters[name]
        
        # Instantiate
        instance = adapter_class(name=name, config=config)
        
        # Cache
        self._instances[cache_key] = instance
        
        logger.info(f"Created adapter instance: {name}")
        
        return instance
    
    def list_adapters(self) -> list[str]:
        """List registered adapter names.
        
        Returns:
            List of adapter names
        """
        return list(self._adapters.keys())
    
    def clear(self) -> None:
        """Clear all registrations (for testing)."""
        self._adapters.clear()
        self._instances.clear()


# Global registry instance
_global_registry: Optional[AdapterRegistry] = None


def get_adapter_registry() -> AdapterRegistry:
    """Get global adapter registry.
    
    Returns:
        AdapterRegistry instance
    """
    global _global_registry
    
    if _global_registry is None:
        _global_registry = AdapterRegistry()
        
        # Auto-register built-in adapters
        _register_builtin_adapters(_global_registry)
    
    return _global_registry


def _register_builtin_adapters(registry: AdapterRegistry) -> None:
    """Register built-in adapters.
    
    Args:
        registry: AdapterRegistry instance
    """
    try:
        from .local import LocalPolicyAdapter
        registry.register("local", LocalPolicyAdapter)
        registry.register("internal", LocalPolicyAdapter)  # Alias
    except ImportError:
        logger.warning("LocalPolicyAdapter not available")
    
    try:
        from .openai import OpenAIAdapter
        registry.register("openai", OpenAIAdapter)
    except ImportError:
        logger.debug("OpenAIAdapter not available")
    
    try:
        from .azure import AzureContentSafetyAdapter
        registry.register("azure", AzureContentSafetyAdapter)
    except ImportError:
        logger.debug("AzureContentSafetyAdapter not available")


__all__ = ["AdapterRegistry", "get_adapter_registry"]

