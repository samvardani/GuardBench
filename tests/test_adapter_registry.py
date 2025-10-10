"""Tests for unified adapter registry."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from adapters import (
    BaseGuardAdapter,
    ScoreResult,
    AdapterRegistry,
    get_adapter_registry,
    LocalPolicyAdapter,
    OpenAIAdapter,
    AzureContentSafetyAdapter
)


class TestScoreResult:
    """Test canonical ScoreResult model."""
    
    def test_score_result_creation(self):
        """Test creating ScoreResult."""
        result = ScoreResult(
            is_safe=True,
            confidence=0.95,
            categories={"violence": 0.1},
            flagged_categories=[],
            provider="test"
        )
        
        assert result.is_safe is True
        assert result.confidence == 0.95
        assert result.provider == "test"
    
    def test_score_result_to_dict(self):
        """Test converting to dictionary."""
        result = ScoreResult(
            is_safe=False,
            confidence=0.85,
            categories={"hate": 0.9},
            flagged_categories=["hate"],
            provider="test",
            latency_ms=150
        )
        
        data = result.to_dict()
        
        assert data["is_safe"] is False
        assert data["confidence"] == 0.85
        assert data["flagged_categories"] == ["hate"]
        assert data["latency_ms"] == 150


class TestAdapterRegistry:
    """Test unified AdapterRegistry."""
    
    @pytest.fixture
    def registry(self):
        """Create fresh registry."""
        reg = AdapterRegistry()
        yield reg
        reg.clear()
    
    def test_registry_creation(self, registry):
        """Test creating registry."""
        assert registry is not None
        assert registry.list_adapters() == []
    
    def test_register_adapter(self, registry):
        """Test registering an adapter."""
        registry.register("local", LocalPolicyAdapter)
        
        assert "local" in registry.list_adapters()
    
    def test_get_adapter(self, registry):
        """Test getting adapter instance."""
        registry.register("local", LocalPolicyAdapter)
        
        adapter = registry.get("local")
        
        assert isinstance(adapter, LocalPolicyAdapter)
        assert adapter.name == "local"
    
    def test_get_unregistered_adapter(self, registry):
        """Test getting unregistered adapter."""
        with pytest.raises(KeyError) as exc_info:
            registry.get("nonexistent")
        
        assert "not registered" in str(exc_info.value)
    
    def test_adapter_caching(self, registry):
        """Test adapter instance caching."""
        registry.register("local", LocalPolicyAdapter)
        
        adapter1 = registry.get("local")
        adapter2 = registry.get("local")
        
        # Should return same instance
        assert adapter1 is adapter2
    
    def test_register_duplicate_warns(self, registry):
        """Test registering duplicate adapter."""
        registry.register("local", LocalPolicyAdapter)
        registry.register("local", LocalPolicyAdapter)  # Duplicate
        
        # Should still work (overwrites)
        assert "local" in registry.list_adapters()


class TestBuiltinAdapters:
    """Test built-in adapter implementations."""
    
    def test_local_adapter(self):
        """Test LocalPolicyAdapter."""
        adapter = LocalPolicyAdapter(name="local")
        
        # Safe content
        result = adapter.score("Hello world")
        assert result.is_safe is True
        assert result.provider == "local"
        
        # Unsafe content
        result = adapter.score("violence and hate")
        assert result.is_safe is False
        assert len(result.flagged_categories) > 0
    
    def test_global_registry_auto_registration(self):
        """Test that global registry auto-registers built-in adapters."""
        registry = get_adapter_registry()
        
        # Should have built-in adapters
        adapters = registry.list_adapters()
        
        assert "local" in adapters
        assert "internal" in adapters  # Alias for local


class TestBackwardCompatibility:
    """Test backward compatibility."""
    
    def test_canonical_score_result(self):
        """Test that only one ScoreResult model exists."""
        from adapters import ScoreResult as SR1
        from adapters.base import ScoreResult as SR2
        
        # Should be same class
        assert SR1 is SR2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

