"""Tests for OpenAI adapter with mocked API calls."""

from __future__ import annotations

import pytest
from unittest.mock import Mock, MagicMock, patch

from adapters.openai_adapter import OpenAIAdapter
from adapters.base_guard import ScoreResult


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client."""
    with patch("adapters.openai_adapter.openai") as mock_openai:
        # Create mock client
        mock_client = MagicMock()
        mock_openai.OpenAI.return_value = mock_client
        
        # Create mock response
        mock_result = MagicMock()
        mock_result.flagged = True
        mock_result.category_scores = MagicMock(
            hate=0.1,
            hate_threatening=0.05,
            harassment=0.2,
            harassment_threatening=0.1,
            self_harm=0.05,
            self_harm_intent=0.03,
            self_harm_instructions=0.02,
            sexual=0.1,
            sexual_minors=0.01,
            violence=0.9,
            violence_graphic=0.8,
        )
        mock_result.model_dump.return_value = {"flagged": True}
        
        mock_response = MagicMock()
        mock_response.results = [mock_result]
        
        mock_client.moderations.create.return_value = mock_response
        
        yield mock_openai, mock_client


class TestOpenAIAdapter:
    """Test OpenAI adapter."""
    
    def test_openai_adapter_requires_api_key(self):
        """Test that OpenAI adapter requires API key."""
        with patch("adapters.openai_adapter.openai"):
            with pytest.raises(ValueError) as exc_info:
                OpenAIAdapter()
            
            assert "API key" in str(exc_info.value)
    
    def test_openai_adapter_creation(self, mock_openai_client):
        """Test creating OpenAI adapter."""
        mock_openai, mock_client = mock_openai_client
        
        adapter = OpenAIAdapter(api_key="test-key")
        
        assert adapter.api_key == "test-key"
        assert adapter.model == "text-moderation-latest"
        assert adapter.client is mock_client
    
    def test_openai_adapter_score(self, mock_openai_client):
        """Test scoring with OpenAI adapter."""
        mock_openai, mock_client = mock_openai_client
        
        adapter = OpenAIAdapter(api_key="test-key")
        result = adapter.score("This is violent content")
        
        # Verify API was called
        mock_client.moderations.create.assert_called_once()
        
        # Check result
        assert isinstance(result, ScoreResult)
        assert result.flagged is True
        assert result.score > 0.0  # Max of all categories
        assert result.provider == "openai"
        assert "violence" in result.categories
        assert result.categories["violence"] == 0.9
    
    def test_openai_adapter_error_handling(self, mock_openai_client):
        """Test error handling in OpenAI adapter."""
        mock_openai, mock_client = mock_openai_client
        
        # Make API call raise exception
        mock_client.moderations.create.side_effect = Exception("API Error")
        
        adapter = OpenAIAdapter(api_key="test-key")
        result = adapter.score("test text")
        
        # Should return error result
        assert result.flagged is False
        assert result.score == 0.0
        assert "error" in result.raw_response
    
    def test_openai_adapter_metadata(self, mock_openai_client):
        """Test OpenAI adapter metadata."""
        mock_openai, mock_client = mock_openai_client
        
        adapter = OpenAIAdapter(api_key="test-key")
        metadata = adapter.get_metadata()
        
        assert metadata.name == "openai"
        assert metadata.provider == "OpenAI"
        assert metadata.requires_api_key is True
        assert "hate" in metadata.supported_categories
        assert "violence" in metadata.supported_categories
    
    def test_openai_adapter_health_check(self, mock_openai_client):
        """Test OpenAI adapter health check."""
        mock_openai, mock_client = mock_openai_client
        
        adapter = OpenAIAdapter(api_key="test-key")
        
        # Health check should succeed
        health = adapter.health_check()
        assert health is True
        
        # Verify test call was made
        mock_client.moderations.create.assert_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

