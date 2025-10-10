"""Tests for Azure adapter with mocked API calls."""

from __future__ import annotations

import pytest
from unittest.mock import Mock, MagicMock, patch

from adapters.azure_adapter import AzureContentSafetyAdapter
from adapters.base_guard import ScoreResult


@pytest.fixture
def mock_httpx_client():
    """Mock httpx client."""
    with patch("adapters.azure_adapter.httpx.Client") as mock_client_class:
        mock_client = MagicMock()
        
        # Create mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "Hate": {"severity": 4},
            "SelfHarm": {"severity": 0},
            "Sexual": {"severity": 1},
            "Violence": {"severity": 5},
        }
        mock_response.raise_for_status.return_value = None
        
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        yield mock_client


class TestAzureAdapter:
    """Test Azure Content Safety adapter."""
    
    def test_azure_adapter_requires_api_key(self):
        """Test that Azure adapter requires API key."""
        with patch("adapters.azure_adapter.httpx"):
            with pytest.raises(ValueError) as exc_info:
                AzureContentSafetyAdapter()
            
            assert "API key" in str(exc_info.value)
    
    def test_azure_adapter_requires_endpoint(self):
        """Test that Azure adapter requires endpoint."""
        with patch("adapters.azure_adapter.httpx"):
            with pytest.raises(ValueError) as exc_info:
                AzureContentSafetyAdapter(api_key="test-key")
            
            assert "endpoint" in str(exc_info.value)
    
    def test_azure_adapter_creation(self, mock_httpx_client):
        """Test creating Azure adapter."""
        adapter = AzureContentSafetyAdapter(
            api_key="test-key",
            endpoint="https://test.cognitiveservices.azure.com"
        )
        
        assert adapter.api_key == "test-key"
        assert "test.cognitiveservices.azure.com" in adapter.endpoint
        assert adapter.api_version == "2023-10-01"
    
    def test_azure_adapter_score(self, mock_httpx_client):
        """Test scoring with Azure adapter."""
        adapter = AzureContentSafetyAdapter(
            api_key="test-key",
            endpoint="https://test.cognitiveservices.azure.com"
        )
        
        result = adapter.score("This is violent content")
        
        # Verify API was called
        mock_httpx_client.post.assert_called_once()
        
        # Check call parameters
        call_args = mock_httpx_client.post.call_args
        assert "contentsafety/text:analyze" in call_args[0][0]
        assert call_args[1]["json"]["text"] == "This is violent content"
        
        # Check result
        assert isinstance(result, ScoreResult)
        assert result.provider == "azure"
        assert "hate" in result.categories
        assert "violence" in result.categories
        
        # Severity 5 → 5/6 ≈ 0.83
        assert result.categories["violence"] > 0.8
        
        # Flagged if any severity > 2
        assert result.flagged is True
    
    def test_azure_adapter_error_handling(self, mock_httpx_client):
        """Test error handling in Azure adapter."""
        # Make API call raise exception
        mock_httpx_client.post.side_effect = Exception("API Error")
        
        adapter = AzureContentSafetyAdapter(
            api_key="test-key",
            endpoint="https://test.cognitiveservices.azure.com"
        )
        
        result = adapter.score("test text")
        
        # Should return error result
        assert result.flagged is False
        assert result.score == 0.0
        assert "error" in result.raw_response
    
    def test_azure_adapter_metadata(self, mock_httpx_client):
        """Test Azure adapter metadata."""
        adapter = AzureContentSafetyAdapter(
            api_key="test-key",
            endpoint="https://test.cognitiveservices.azure.com"
        )
        
        metadata = adapter.get_metadata()
        
        assert metadata.name == "azure"
        assert metadata.provider == "Microsoft Azure"
        assert metadata.requires_api_key is True
        assert "hate" in metadata.supported_categories
        assert "violence" in metadata.supported_categories
        assert "en" in metadata.supported_languages


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

