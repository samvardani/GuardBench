"""Integration tests for Safety Copilot API."""

from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


class TestAssistantAPIIntegration:
    """Test assistant API endpoints (integration level)."""
    
    def test_assistant_routes_loaded(self):
        """Test that assistant routes can be loaded."""
        # This test just verifies the module structure is correct
        from assistant import routes
        assert hasattr(routes, "router")
        assert routes.router.prefix == "/assistant"
    
    def test_query_request_model(self):
        """Test QueryRequest Pydantic model."""
        from assistant.routes import QueryRequest
        
        # Valid request
        request = QueryRequest(question="test")
        assert request.question == "test"
        
        # With optional fields
        request = QueryRequest(
            question="test",
            run_id="abc123",
            category="violence"
        )
        assert request.run_id == "abc123"
    
    def test_query_response_model(self):
        """Test QueryResponse Pydantic model."""
        from assistant.routes import QueryResponse
        
        response = QueryResponse(
            answer="test answer",
            query="test question",
            latency_ms=100,
            model="gpt-4",
            tokens_used=50,
        )
        
        assert response.answer == "test answer"
        assert response.latency_ms == 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

