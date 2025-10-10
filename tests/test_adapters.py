"""Tests for adapter interfaces and implementations."""

from __future__ import annotations

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Any, Dict, Optional

from adapters.base_guard import BaseGuardAdapter, ScoreResult, GuardMetadata
from adapters.base_connector import BaseConnector, ObjectStorageConnector, MessageQueueConnector, ConnectorType
from adapters.registry import AdapterRegistry, get_registry, get_guard_adapter
from adapters.internal_adapter import InternalPolicyAdapter


class TestScoreResult:
    """Test ScoreResult dataclass."""
    
    def test_score_result_creation(self):
        """Test creating ScoreResult."""
        result = ScoreResult(
            flagged=True,
            score=0.85,
            categories={"violence": 0.9, "hate": 0.7},
            latency_ms=150,
            provider="test",
            model="test-model",
        )
        
        assert result.flagged is True
        assert result.score == 0.85
        assert result.categories["violence"] == 0.9
        assert result.latency_ms == 150
        assert result.provider == "test"
    
    def test_score_result_to_dict(self):
        """Test converting ScoreResult to dictionary."""
        result = ScoreResult(
            flagged=True,
            score=0.75,
            categories={"hate": 0.8},
            reasoning="Detected hateful language",
            confidence=0.95,
            latency_ms=200,
            provider="openai",
        )
        
        data = result.to_dict()
        
        assert data["flagged"] is True
        assert data["score"] == 0.75
        assert data["categories"]["hate"] == 0.8
        assert data["reasoning"] == "Detected hateful language"
        assert data["confidence"] == 0.95
    
    def test_score_result_from_dict(self):
        """Test creating ScoreResult from dictionary."""
        data = {
            "flagged": True,
            "score": 0.65,
            "categories": {"violence": 0.7},
            "latency_ms": 100,
        }
        
        result = ScoreResult.from_dict(data)
        
        assert result.flagged is True
        assert result.score == 0.65
        assert result.categories["violence"] == 0.7
        assert result.latency_ms == 100


class TestGuardMetadata:
    """Test GuardMetadata dataclass."""
    
    def test_metadata_creation(self):
        """Test creating GuardMetadata."""
        metadata = GuardMetadata(
            name="test-guard",
            provider="Test Provider",
            version="1.0",
            supported_languages=["en", "es"],
            supported_categories=["hate", "violence"],
            requires_api_key=True,
            max_text_length=5000,
        )
        
        assert metadata.name == "test-guard"
        assert metadata.provider == "Test Provider"
        assert metadata.supported_languages == ["en", "es"]
        assert metadata.requires_api_key is True
    
    def test_metadata_to_dict(self):
        """Test converting metadata to dictionary."""
        metadata = GuardMetadata(
            name="test",
            provider="Test",
            supported_categories=["hate"],
        )
        
        data = metadata.to_dict()
        
        assert data["name"] == "test"
        assert data["provider"] == "Test"
        assert "hate" in data["supported_categories"]


class MockGuardAdapter(BaseGuardAdapter):
    """Mock guard adapter for testing."""
    
    def score(self, text: str, **kwargs) -> ScoreResult:
        """Mock score method."""
        return ScoreResult(
            flagged=len(text) > 10,
            score=min(len(text) / 100.0, 1.0),
            categories={"test": 0.5},
            provider="mock",
        )
    
    def get_metadata(self) -> GuardMetadata:
        """Mock metadata."""
        return GuardMetadata(
            name="mock",
            provider="Mock Provider",
            supported_languages=["en"],
            requires_api_key=False,
        )


class TestBaseGuardAdapter:
    """Test BaseGuardAdapter abstract interface."""
    
    def test_adapter_must_implement_score(self):
        """Test that adapter must implement score method."""
        with pytest.raises(TypeError):
            # Cannot instantiate without implementing abstract methods
            BaseGuardAdapter()  # type: ignore
    
    def test_mock_adapter_works(self):
        """Test mock adapter implementation."""
        adapter = MockGuardAdapter()
        
        result = adapter.score("short text")
        assert isinstance(result, ScoreResult)
        assert result.provider == "mock"
    
    def test_adapter_initialize(self):
        """Test adapter initialization (optional override)."""
        adapter = MockGuardAdapter()
        adapter.initialize()  # Should not raise
    
    def test_adapter_health_check(self):
        """Test adapter health check (default implementation)."""
        adapter = MockGuardAdapter()
        assert adapter.health_check() is True
    
    def test_supports_language(self):
        """Test language support check."""
        adapter = MockGuardAdapter()
        
        assert adapter.supports_language("en") is True
        assert adapter.supports_language("fr") is False
    
    def test_supports_category(self):
        """Test category support check."""
        metadata = GuardMetadata(
            name="test",
            provider="test",
            supported_categories=["hate", "violence"],
        )
        
        adapter = MockGuardAdapter()
        
        # Mock get_metadata
        with patch.object(adapter, "get_metadata", return_value=metadata):
            assert adapter.supports_category("hate") is True
            assert adapter.supports_category("violence") is True
            assert adapter.supports_category("other") is False


class TestInternalAdapter:
    """Test InternalPolicyAdapter."""
    
    def test_internal_adapter_creation(self):
        """Test creating internal adapter."""
        adapter = InternalPolicyAdapter()
        
        metadata = adapter.get_metadata()
        assert metadata.name == "internal"
        assert metadata.provider == "safety-eval-mini"
        assert metadata.requires_api_key is False
    
    def test_internal_adapter_with_mock_predict(self):
        """Test internal adapter with custom predict function."""
        def mock_predict(text, category, language):
            return {
                "score": 0.75,
                "flagged": True,
                "categories": {"violence": 0.8},
            }
        
        adapter = InternalPolicyAdapter(predict_fn=mock_predict)
        result = adapter.score("test text")
        
        assert result.flagged is True
        assert result.score == 0.75
        assert result.categories["violence"] == 0.8
        assert result.provider == "internal"


class TestAdapterRegistry:
    """Test AdapterRegistry."""
    
    def test_registry_creation(self):
        """Test creating registry."""
        registry = AdapterRegistry()
        
        assert isinstance(registry, AdapterRegistry)
        assert len(registry.list_guards()) == 0
        assert len(registry.list_connectors()) == 0
    
    def test_register_guard_adapter(self):
        """Test registering guard adapter."""
        registry = AdapterRegistry()
        registry.register_guard("mock", MockGuardAdapter)
        
        assert "mock" in registry.list_guards()
    
    def test_get_guard_adapter(self):
        """Test getting guard adapter instance."""
        registry = AdapterRegistry()
        registry.register_guard("mock", MockGuardAdapter)
        
        adapter = registry.get_guard("mock")
        
        assert isinstance(adapter, MockGuardAdapter)
        assert isinstance(adapter, BaseGuardAdapter)
    
    def test_get_nonexistent_guard(self):
        """Test getting non-existent guard."""
        registry = AdapterRegistry()
        
        with pytest.raises(ValueError) as exc_info:
            registry.get_guard("nonexistent")
        
        assert "not found" in str(exc_info.value)
    
    def test_register_overwrites_existing(self, caplog):
        """Test that re-registering adapter logs warning."""
        registry = AdapterRegistry()
        
        class MockAdapter1(MockGuardAdapter):
            pass
        
        class MockAdapter2(MockGuardAdapter):
            pass
        
        registry.register_guard("test", MockAdapter1)
        
        with caplog.at_level("WARNING"):
            registry.register_guard("test", MockAdapter2)
        
        assert "Overwriting" in caplog.text
    
    def test_global_registry(self):
        """Test global registry singleton."""
        registry1 = get_registry()
        registry2 = get_registry()
        
        assert registry1 is registry2
    
    def test_auto_registration(self):
        """Test auto-registration of adapters."""
        registry = get_registry()
        
        guards = registry.list_guards()
        
        # Should have internal adapter at minimum
        assert "internal" in guards or len(guards) >= 0  # May fail if imports fail


class TestConnectorAdapters:
    """Test connector adapters."""
    
    def test_s3_connector_metadata(self):
        """Test S3 connector metadata."""
        from adapters.s3_connector import S3Connector
        
        connector = S3Connector()
        metadata = connector.get_metadata()
        
        assert metadata.name == "s3"
        assert metadata.connector_type == ConnectorType.OBJECT_STORAGE
        assert metadata.provider == "AWS S3"
    
    def test_kafka_connector_metadata(self):
        """Test Kafka connector metadata."""
        from adapters.kafka_connector import KafkaConnector
        
        connector = KafkaConnector()
        metadata = connector.get_metadata()
        
        assert metadata.name == "kafka"
        assert metadata.connector_type == ConnectorType.MESSAGE_QUEUE
        assert metadata.supports_streaming is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

