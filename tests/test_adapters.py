"""Unit tests for moderation adapters."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from seval.adapters import ModerationAdapter, ModerationResult, LocalAdapter, OpenAIAdapter, AzureAdapter
from seval.adapters.registry import AdapterRegistry


def test_moderation_result_to_dict():
    """Test ModerationResult to_dict conversion."""
    result = ModerationResult(
        score=3.5,
        blocked=True,
        category="violence",
        language="en",
        adapter_name="test",
        latency_ms=100,
        confidence=0.7,
        metadata={"key": "value"}
    )
    
    d = result.to_dict()
    assert d["score"] == 3.5
    assert d["blocked"] is True
    assert d["category"] == "violence"
    assert d["language"] == "en"
    assert d["adapter"] == "test"
    assert d["latency_ms"] == 100
    assert d["confidence"] == 0.7
    assert d["metadata"] == {"key": "value"}


def test_local_adapter_moderate():
    """Test LocalAdapter moderation."""
    adapter = LocalAdapter()
    
    result = adapter.moderate("hello world", "violence", "en")
    
    assert isinstance(result, ModerationResult)
    assert result.adapter_name == "local"
    assert result.category == "violence"
    assert result.language == "en"
    assert result.latency_ms >= 0
    assert isinstance(result.score, (int, float))
    assert isinstance(result.blocked, bool)


def test_local_adapter_violence_keyword():
    """Test LocalAdapter detects violence keywords."""
    adapter = LocalAdapter()
    
    result = adapter.moderate("how to kill someone", "violence", "en")
    
    assert result.score > 0
    assert result.category == "violence"


def test_local_adapter_health_check():
    """Test LocalAdapter health check."""
    adapter = LocalAdapter()
    
    assert adapter.health_check() is True


def test_local_adapter_metrics():
    """Test LocalAdapter metrics tracking."""
    adapter = LocalAdapter()
    
    # Initial metrics
    metrics = adapter.get_metrics()
    assert metrics["call_count"] == 0
    assert metrics["avg_latency_ms"] == 0
    
    # Make some calls
    adapter.moderate("test 1", "violence", "en")
    adapter.moderate("test 2", "violence", "en")
    
    metrics = adapter.get_metrics()
    assert metrics["call_count"] == 2
    assert metrics["avg_latency_ms"] >= 0  # May be 0 for very fast operations
    
    # Reset
    adapter.reset_metrics()
    metrics = adapter.get_metrics()
    assert metrics["call_count"] == 0


def test_openai_adapter_no_api_key():
    """Test OpenAIAdapter fails gracefully without API key."""
    with patch.dict("os.environ", {}, clear=True):
        adapter = OpenAIAdapter()
        
        with pytest.raises(ValueError, match="API key not configured"):
            adapter.moderate("test", "violence", "en")


def test_openai_adapter_with_mock():
    """Test OpenAIAdapter with mocked client."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_result = MagicMock()
    mock_scores = MagicMock()
    
    # Set up mock scores
    mock_scores.violence = 0.8
    mock_result.category_scores = mock_scores
    mock_result.flagged = True
    mock_response.results = [mock_result]
    
    mock_client.moderations.create.return_value = mock_response
    
    adapter = OpenAIAdapter(config={"api_key": "test-key"})
    adapter._client = mock_client
    
    result = adapter.moderate("test text", "violence", "en")
    
    assert isinstance(result, ModerationResult)
    assert result.adapter_name == "openai"
    assert result.blocked is True
    assert result.score > 0
    
    mock_client.moderations.create.assert_called_once_with(input="test text")


def test_openai_adapter_category_mapping():
    """Test OpenAIAdapter category mapping."""
    adapter = OpenAIAdapter(config={"api_key": "test-key"})
    
    assert OpenAIAdapter.CATEGORY_MAPPING["violence"] == "violence"
    assert OpenAIAdapter.CATEGORY_MAPPING["self_harm"] == "self-harm"
    assert OpenAIAdapter.CATEGORY_MAPPING["crime"] == "violence"


def test_azure_adapter_no_credentials():
    """Test AzureAdapter fails gracefully without credentials."""
    with patch.dict("os.environ", {}, clear=True):
        adapter = AzureAdapter()
        
        with pytest.raises(ValueError, match="endpoint and key not configured"):
            adapter.moderate("test", "violence", "en")


def test_azure_adapter_with_mock():
    """Test AzureAdapter error handling without SDK."""
    # Azure SDK not installed - test fallback behavior
    adapter = AzureAdapter(config={
        "endpoint": "https://test.azure.com",
        "api_key": "test-key"
    })
    
    result = adapter.moderate("test text", "violence", "en")
    
    assert isinstance(result, ModerationResult)
    assert result.adapter_name == "azure"
    # Without SDK, should return safe fallback
    assert result.score == 0.0
    assert result.blocked is False
    assert "error" in result.metadata


def test_adapter_registry_get_local():
    """Test AdapterRegistry returns local adapter."""
    adapter = AdapterRegistry.get_adapter("local")
    
    assert isinstance(adapter, LocalAdapter)
    assert adapter.name == "local"


def test_adapter_registry_get_openai():
    """Test AdapterRegistry returns OpenAI adapter."""
    adapter = AdapterRegistry.get_adapter("openai")
    
    assert isinstance(adapter, OpenAIAdapter)
    assert adapter.name == "openai"


def test_adapter_registry_get_azure():
    """Test AdapterRegistry returns Azure adapter."""
    adapter = AdapterRegistry.get_adapter("azure")
    
    assert isinstance(adapter, AzureAdapter)
    assert adapter.name == "azure"


def test_adapter_registry_unknown_adapter():
    """Test AdapterRegistry raises error for unknown adapter."""
    with pytest.raises(ValueError, match="Adapter 'unknown' not found"):
        AdapterRegistry.get_adapter("unknown")


def test_adapter_registry_list_adapters():
    """Test AdapterRegistry lists available adapters."""
    adapters = AdapterRegistry.list_adapters()
    
    assert "local" in adapters
    assert "openai" in adapters
    assert "azure" in adapters


def test_adapter_registry_reuse_instances():
    """Test AdapterRegistry reuses instances."""
    adapter1 = AdapterRegistry.get_adapter("local", reuse=True)
    adapter2 = AdapterRegistry.get_adapter("local", reuse=True)
    
    assert adapter1 is adapter2


def test_adapter_registry_no_reuse():
    """Test AdapterRegistry creates new instances when reuse=False."""
    adapter1 = AdapterRegistry.get_adapter("local", reuse=False)
    adapter2 = AdapterRegistry.get_adapter("local", reuse=False)
    
    assert adapter1 is not adapter2


def test_adapter_registry_clear_instances():
    """Test AdapterRegistry clears instances."""
    AdapterRegistry.get_adapter("local", reuse=True)
    assert "local" in AdapterRegistry._instances
    
    AdapterRegistry.clear_instances()
    assert len(AdapterRegistry._instances) == 0


def test_adapter_error_handling():
    """Test adapter handles errors gracefully."""
    adapter = OpenAIAdapter(config={"api_key": "invalid-key"})
    
    # Mock client to raise exception
    mock_client = MagicMock()
    mock_client.moderations.create.side_effect = Exception("API error")
    adapter._client = mock_client
    
    result = adapter.moderate("test", "violence", "en")
    
    # Should return safe fallback
    assert result.score == 0.0
    assert result.blocked is False
    assert "error" in result.metadata


def test_adapter_timeout_handling():
    """Test adapter handles timeouts gracefully."""
    adapter = LocalAdapter()
    
    # Simulate timeout by mocking guard to take too long
    with patch.object(adapter, "_get_guard") as mock_guard:
        import time
        def slow_guard(*args):
            time.sleep(0.1)
            return {"score": 1.0, "blocked": False}
        
        mock_guard.return_value = slow_guard
        
        result = adapter.moderate("test", "violence", "en")
        
        # Should complete (not timeout in local adapter)
        assert result.latency_ms >= 100

