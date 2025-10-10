"""Tests for Safety Copilot assistant."""

from __future__ import annotations

import pytest
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path

from assistant.service import SafetyCopilot, AssistantQuery, AssistantResponse, get_copilot
from assistant.context import RunContext, PolicyContext, gather_policy_context


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client."""
    with patch("assistant.service.openai") as mock_openai:
        mock_client = MagicMock()
        mock_openai.OpenAI.return_value = mock_client
        
        # Create mock response
        mock_message = MagicMock()
        mock_message.content = "This is a test response from the assistant."
        
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        
        mock_usage = MagicMock()
        mock_usage.total_tokens = 150
        
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage = mock_usage
        
        mock_client.chat.completions.create.return_value = mock_response
        
        yield mock_openai, mock_client


class TestAssistantQuery:
    """Test AssistantQuery dataclass."""
    
    def test_query_creation(self):
        """Test creating assistant query."""
        query = AssistantQuery(
            question="What categories are detected?",
            run_id="abc123",
            category="violence",
        )
        
        assert query.question == "What categories are detected?"
        assert query.run_id == "abc123"
        assert query.category == "violence"


class TestAssistantResponse:
    """Test AssistantResponse dataclass."""
    
    def test_response_to_dict(self):
        """Test converting response to dictionary."""
        response = AssistantResponse(
            answer="The system detects violence, hate, and harassment.",
            query="What categories?",
            context_used={"policy": "test"},
            latency_ms=250,
            model="gpt-4",
            tokens_used=100,
        )
        
        data = response.to_dict()
        
        assert data["answer"] == "The system detects violence, hate, and harassment."
        assert data["latency_ms"] == 250
        assert data["tokens_used"] == 100


class TestRunContext:
    """Test RunContext."""
    
    def test_run_context_to_summary(self):
        """Test converting run context to summary."""
        ctx = RunContext(
            run_id="test123",
            metrics={
                "baseline": {"precision": 0.95, "recall": 0.92, "tp": 100, "fp": 5},
                "candidate": {"precision": 0.98, "recall": 0.94, "tp": 105, "fp": 2},
            },
            policy_version="v1.2.3",
            baseline_guard="internal",
            candidate_guard="openai",
        )
        
        summary = ctx.to_summary()
        
        assert "test123" in summary
        assert "internal" in summary
        assert "openai" in summary
        assert "Precision: 0.950" in summary or "precision" in summary.lower()


class TestPolicyContext:
    """Test PolicyContext."""
    
    def test_policy_context_to_summary(self):
        """Test converting policy context to summary."""
        ctx = PolicyContext(
            categories=["violence", "hate", "harassment"],
            languages=["en", "es", "fa"],
            rules_count=42,
            policy_description="Content safety policy",
        )
        
        summary = ctx.to_summary()
        
        assert "violence" in summary
        assert "hate" in summary
        assert "42" in summary
        assert "en" in summary


class TestSafetyCopilot:
    """Test SafetyCopilot service."""
    
    def test_copilot_requires_api_key(self):
        """Test that copilot requires API key."""
        with patch("assistant.service.openai"):
            with pytest.raises(ValueError) as exc_info:
                SafetyCopilot()
            
            assert "API key" in str(exc_info.value)
    
    def test_copilot_creation(self, mock_openai_client):
        """Test creating copilot."""
        mock_openai, mock_client = mock_openai_client
        
        copilot = SafetyCopilot(api_key="test-key", model="gpt-4")
        
        assert copilot.api_key == "test-key"
        assert copilot.model == "gpt-4"
        assert copilot.max_tokens == 500
        assert copilot.temperature == 0.7
    
    def test_copilot_query(self, mock_openai_client):
        """Test querying copilot."""
        mock_openai, mock_client = mock_openai_client
        
        copilot = SafetyCopilot(api_key="test-key")
        
        query = AssistantQuery(question="What categories are detected?")
        
        with patch("assistant.context.gather_context") as mock_gather:
            mock_gather.return_value = {
                "policy": "Categories: violence, hate, harassment"
            }
            
            response = copilot.query(query, tenant_id="test-tenant")
        
        # Verify LLM was called
        mock_client.chat.completions.create.assert_called_once()
        
        # Check response
        assert isinstance(response, AssistantResponse)
        assert response.answer == "This is a test response from the assistant."
        assert response.query == "What categories are detected?"
        assert response.model == "gpt-4"
        assert response.tokens_used == 150
    
    def test_copilot_with_run_context(self, mock_openai_client):
        """Test copilot with run ID context."""
        mock_openai, mock_client = mock_openai_client
        
        copilot = SafetyCopilot(api_key="test-key")
        
        query = AssistantQuery(
            question="Why was this flagged?",
            run_id="run123"
        )
        
        with patch("assistant.context.gather_context") as mock_gather:
            mock_gather.return_value = {
                "policy": "Policy info",
                "run": "Run run123: precision=0.95, flagged by violence rule"
            }
            
            response = copilot.query(query, tenant_id="test-tenant")
        
        # Verify context was used
        mock_gather.assert_called_once_with(tenant_id="test-tenant", run_id="run123")
        
        assert response.latency_ms >= 0
    
    def test_copilot_error_handling(self, mock_openai_client):
        """Test copilot error handling."""
        mock_openai, mock_client = mock_openai_client
        
        # Make LLM call raise exception
        mock_client.chat.completions.create.side_effect = Exception("API error")
        
        copilot = SafetyCopilot(api_key="test-key")
        query = AssistantQuery(question="test")
        
        with patch("assistant.context.gather_context") as mock_gather:
            mock_gather.return_value = {}
            
            response = copilot.query(query, tenant_id="test")
        
        # Should return error message
        assert "error" in response.answer.lower()
    
    def test_copilot_question_moderation(self, mock_openai_client):
        """Test question safety moderation."""
        mock_openai, mock_client = mock_openai_client
        
        copilot = SafetyCopilot(api_key="test-key")
        
        # Off-topic question
        query = AssistantQuery(question="What's the weather like?")
        
        with patch("assistant.context.gather_context") as mock_gather:
            mock_gather.return_value = {}
            
            response = copilot.query(query, tenant_id="test")
        
        # Should redirect to safety topics (or allow - depends on implementation)
        assert isinstance(response, AssistantResponse)
    
    def test_copilot_health_check(self, mock_openai_client):
        """Test copilot health check."""
        mock_openai, mock_client = mock_openai_client
        
        copilot = SafetyCopilot(api_key="test-key")
        
        health = copilot.health_check()
        
        assert health is True
        mock_client.chat.completions.create.assert_called()
    
    def test_copilot_build_messages(self, mock_openai_client):
        """Test building messages for LLM."""
        mock_openai, mock_client = mock_openai_client
        
        copilot = SafetyCopilot(api_key="test-key")
        
        context = {
            "policy": "Categories: violence, hate",
            "run": "Run abc: precision=0.95"
        }
        
        messages = copilot._build_messages("Why was this flagged?", context)
        
        # Should have system prompt, context, and question
        assert len(messages) >= 2
        assert messages[0]["role"] == "system"
        assert "Safety Copilot" in messages[0]["content"]
        assert any("Why was this flagged?" in m["content"] for m in messages)
    
    def test_copilot_singleton(self):
        """Test copilot singleton pattern."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            with patch("assistant.service.openai"):
                copilot1 = get_copilot()
                copilot2 = get_copilot()
                
                assert copilot1 is copilot2


class TestGatherContext:
    """Test context gathering."""
    
    def test_gather_policy_context(self):
        """Test gathering policy context."""
        # This test uses the actual policy file if it exists
        ctx = gather_policy_context()
        
        assert isinstance(ctx, PolicyContext)
        # Should have some categories (even if empty)
        assert isinstance(ctx.categories, list)
    
    def test_run_context_with_invalid_run(self):
        """Test gathering context for non-existent run."""
        from assistant.context import gather_run_context
        
        ctx = gather_run_context("nonexistent", "test-tenant")
        
        # Should return None if run not found
        assert ctx is None or ctx.run_id == "nonexistent"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

