"""Adapter registry and factory."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Type

from .base_guard import BaseGuardAdapter
from .base_connector import BaseConnector

logger = logging.getLogger(__name__)


class AdapterRegistry:
    """Registry for guard and connector adapters."""
    
    def __init__(self):
        """Initialize registry."""
        self._guards: Dict[str, Type[BaseGuardAdapter]] = {}
        self._connectors: Dict[str, Type[BaseConnector]] = {}
    
    def register_guard(self, name: str, adapter_class: Type[BaseGuardAdapter]) -> None:
        """Register a guard adapter.
        
        Args:
            name: Adapter name (e.g., "openai", "azure", "internal")
            adapter_class: Adapter class
        """
        if name in self._guards:
            logger.warning(f"Overwriting existing guard adapter: {name}")
        
        self._guards[name] = adapter_class
        logger.info(f"Registered guard adapter: {name} -> {adapter_class.__name__}")
    
    def register_connector(self, name: str, connector_class: Type[BaseConnector]) -> None:
        """Register a connector adapter.
        
        Args:
            name: Connector name (e.g., "s3", "gcs", "kafka")
            connector_class: Connector class
        """
        if name in self._connectors:
            logger.warning(f"Overwriting existing connector: {name}")
        
        self._connectors[name] = connector_class
        logger.info(f"Registered connector: {name} -> {connector_class.__name__}")
    
    def get_guard(self, name: str, **config: Any) -> BaseGuardAdapter:
        """Get guard adapter instance.
        
        Args:
            name: Adapter name
            **config: Configuration parameters
            
        Returns:
            Adapter instance
            
        Raises:
            ValueError: If adapter not found
        """
        if name not in self._guards:
            available = ", ".join(self._guards.keys())
            raise ValueError(f"Guard adapter '{name}' not found. Available: {available}")
        
        adapter_class = self._guards[name]
        return adapter_class(**config)
    
    def get_connector(self, name: str, **config: Any) -> BaseConnector:
        """Get connector instance.
        
        Args:
            name: Connector name
            **config: Configuration parameters
            
        Returns:
            Connector instance
            
        Raises:
            ValueError: If connector not found
        """
        if name not in self._connectors:
            available = ", ".join(self._connectors.keys())
            raise ValueError(f"Connector '{name}' not found. Available: {available}")
        
        connector_class = self._connectors[name]
        return connector_class(**config)
    
    def list_guards(self) -> List[str]:
        """List registered guard adapters.
        
        Returns:
            List of adapter names
        """
        return list(self._guards.keys())
    
    def list_connectors(self) -> List[str]:
        """List registered connectors.
        
        Returns:
            List of connector names
        """
        return list(self._connectors.keys())


# Global registry
_global_registry: Optional[AdapterRegistry] = None


def get_registry() -> AdapterRegistry:
    """Get global adapter registry.
    
    Returns:
        Global AdapterRegistry instance
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = AdapterRegistry()
        _auto_register_adapters(_global_registry)
    return _global_registry


def _auto_register_adapters(registry: AdapterRegistry) -> None:
    """Auto-register all available adapters.
    
    Args:
        registry: Registry to populate
    """
    # Import and register guard adapters
    try:
        from .internal_adapter import InternalPolicyAdapter
        registry.register_guard("internal", InternalPolicyAdapter)
    except Exception as e:
        logger.debug(f"Could not register internal adapter: {e}")
    
    try:
        from .openai_adapter import OpenAIAdapter
        registry.register_guard("openai", OpenAIAdapter)
    except Exception as e:
        logger.debug(f"Could not register OpenAI adapter: {e}")
    
    try:
        from .azure_adapter import AzureContentSafetyAdapter
        registry.register_guard("azure", AzureContentSafetyAdapter)
    except Exception as e:
        logger.debug(f"Could not register Azure adapter: {e}")
    
    # Import and register connectors
    try:
        from .s3_connector import S3Connector
        registry.register_connector("s3", S3Connector)
    except Exception as e:
        logger.debug(f"Could not register S3 connector: {e}")
    
    try:
        from .kafka_connector import KafkaConnector
        registry.register_connector("kafka", KafkaConnector)
    except Exception as e:
        logger.debug(f"Could not register Kafka connector: {e}")
    
    try:
        from .azure_connector import AzureBlobConnector
        registry.register_connector("azure_blob", AzureBlobConnector)
    except Exception as e:
        logger.debug(f"Could not register Azure Blob connector: {e}")
    
    try:
        from .gcs_connector import GCSConnector
        registry.register_connector("gcs", GCSConnector)
    except Exception as e:
        logger.debug(f"Could not register GCS connector: {e}")


def get_guard_adapter(name: str, **config: Any) -> BaseGuardAdapter:
    """Get guard adapter by name (convenience function).
    
    Args:
        name: Adapter name
        **config: Configuration
        
    Returns:
        Adapter instance
    """
    return get_registry().get_guard(name, **config)


def register_guard_adapter(name: str, adapter_class: Type[BaseGuardAdapter]) -> None:
    """Register guard adapter (convenience function).
    
    Args:
        name: Adapter name
        adapter_class: Adapter class
    """
    get_registry().register_guard(name, adapter_class)


__all__ = [
    "AdapterRegistry",
    "get_registry",
    "get_guard_adapter",
    "register_guard_adapter",
]

