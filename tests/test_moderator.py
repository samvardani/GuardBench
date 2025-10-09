"""Unit tests for Moderator orchestrator."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from seval.moderator import Moderator, ModerationAudit
from seval.adapters.base import ModerationResult
from seval.strategies.base import EnsembleResult


def test_moderation_audit_log_decision():
    """Test ModerationAudit logs decisions."""
    audit = ModerationAudit(max_entries=10)
    
    result = ModerationResult(
        score=3.5,
        blocked=True,
        category="violence",
        language="en",
        adapter_name="test",
        latency_ms=100,
    )
    
    audit.log_decision("hash123", "violence", "en", result, timestamp=1234567890.0)
    
    entries = audit.get_all()
    assert len(entries) == 1
    assert entries[0]["text_hash"] == "hash123"
    assert entries[0]["score"] == 3.5
    assert entries[0]["blocked"] is True
    assert entries[0]["adapter"] == "test"


def test_moderation_audit_max_entries():
    """Test ModerationAudit respects max entries."""
    audit = ModerationAudit(max_entries=5)
    
    result = ModerationResult(
        score=1.0,
        blocked=False,
        category="violence",
        language="en",
        adapter_name="test",
        latency_ms=100,
    )
    
    # Add 10 entries
    for i in range(10):
        audit.log_decision(f"hash{i}", "violence", "en", result)
    
    entries = audit.get_all()
    assert len(entries) == 5  # Only keeps last 5


def test_moderation_audit_get_recent():
    """Test ModerationAudit get_recent."""
    audit = ModerationAudit()
    
    result = ModerationResult(
        score=1.0,
        blocked=False,
        category="violence",
        language="en",
        adapter_name="test",
        latency_ms=100,
    )
    
    for i in range(10):
        audit.log_decision(f"hash{i}", "violence", "en", result)
    
    recent = audit.get_recent(n=3)
    assert len(recent) == 3


def test_moderator_single_adapter():
    """Test Moderator with single adapter."""
    config = {
        "moderation": {
            "adapters": ["local"],
            "strategy": "any",
        }
    }
    
    moderator = Moderator(config)
    result = moderator.moderate("hello", "violence", "en")
    
    assert isinstance(result, ModerationResult)
    assert result.adapter_name == "local"


def test_moderator_multiple_adapters():
    """Test Moderator with multiple adapters."""
    config = {
        "moderation": {
            "adapters": ["local", "local"],  # Use local twice for testing
            "strategy": "any",
        }
    }
    
    moderator = Moderator(config, parallel=False)
    result = moderator.moderate("hello", "violence", "en")
    
    assert isinstance(result, EnsembleResult)
    assert result.strategy == "any"
    assert len(result.adapter_results) == 2


def test_moderator_category_override():
    """Test Moderator uses category-specific configuration."""
    config = {
        "moderation": {
            "adapters": ["local"],
            "strategy": "any",
            "categories": {
                "violence": {
                    "adapters": ["local", "local"],
                    "strategy": "all",
                }
            }
        }
    }
    
    moderator = Moderator(config, parallel=False)
    
    # Violence category should use override
    result = moderator.moderate("test", "violence", "en")
    assert isinstance(result, EnsembleResult)
    assert result.strategy == "all"
    
    # Other categories should use defaults
    result2 = moderator.moderate("test", "self_harm", "en")
    assert isinstance(result2, ModerationResult)


def test_moderator_audit_logging():
    """Test Moderator logs to audit trail."""
    config = {
        "moderation": {
            "adapters": ["local"],
            "strategy": "any",
        }
    }
    
    moderator = Moderator(config, enable_audit=True)
    moderator.moderate("hello", "violence", "en")
    
    audit_trail = moderator.get_audit_trail(n=10)
    assert len(audit_trail) >= 1
    assert audit_trail[0]["category"] == "violence"


def test_moderator_no_audit():
    """Test Moderator without audit trail."""
    config = {
        "moderation": {
            "adapters": ["local"],
            "strategy": "any",
        }
    }
    
    moderator = Moderator(config, enable_audit=False)
    moderator.moderate("hello", "violence", "en")
    
    audit_trail = moderator.get_audit_trail(n=10)
    assert len(audit_trail) == 0


def test_moderator_reload_config():
    """Test Moderator hot-reloads configuration."""
    initial_config = {
        "moderation": {
            "adapters": ["local"],
            "strategy": "any",
        }
    }
    
    moderator = Moderator(initial_config)
    assert moderator.default_strategy == "any"
    
    # Reload with new config
    new_config = {
        "moderation": {
            "adapters": ["local"],
            "strategy": "all",
        }
    }
    
    moderator.reload_config(new_config)
    assert moderator.default_strategy == "all"


def test_moderator_adapter_timeout():
    """Test Moderator handles adapter timeouts gracefully."""
    config = {
        "moderation": {
            "adapters": ["local", "local"],
            "strategy": "any",
        }
    }
    
    moderator = Moderator(config, parallel=True)
    
    # Mock one adapter to timeout
    with patch("seval.adapters.local.LocalAdapter.moderate") as mock_moderate:
        import concurrent.futures
        
        def slow_moderate(*args, **kwargs):
            import time
            time.sleep(10)  # Simulate timeout
            return ModerationResult(
                score=0.0,
                blocked=False,
                category="violence",
                language="en",
                adapter_name="local",
                latency_ms=10000,
            )
        
        mock_moderate.side_effect = slow_moderate
        
        # Should timeout but continue
        result = moderator.moderate("test", "violence", "en")
        
        # Should return result (with timeout fallbacks)
        assert isinstance(result, EnsembleResult)


def test_moderator_get_metrics():
    """Test Moderator returns metrics."""
    config = {
        "moderation": {
            "adapters": ["local"],
            "strategy": "any",
        }
    }
    
    moderator = Moderator(config, enable_audit=True)
    moderator.moderate("hello", "violence", "en")
    
    metrics = moderator.get_metrics()
    
    assert "adapters" in metrics
    assert "audit_size" in metrics
    assert metrics["audit_size"] >= 1


def test_moderator_parallel_execution():
    """Test Moderator runs adapters in parallel."""
    config = {
        "moderation": {
            "adapters": ["local", "local"],
            "strategy": "any",
        }
    }
    
    moderator = Moderator(config, parallel=True)
    result = moderator.moderate("test", "violence", "en")
    
    assert isinstance(result, EnsembleResult)
    # Parallel execution should be faster than sequential
    assert result.total_latency_ms < 1000  # Reasonable for parallel


def test_moderator_sequential_execution():
    """Test Moderator runs adapters sequentially."""
    config = {
        "moderation": {
            "adapters": ["local", "local"],
            "strategy": "any",
        }
    }
    
    moderator = Moderator(config, parallel=False)
    result = moderator.moderate("test", "violence", "en")
    
    assert isinstance(result, EnsembleResult)
    assert len(result.adapter_results) == 2


def test_moderator_adapter_failure_fallback():
    """Test Moderator handles adapter failures gracefully."""
    config = {
        "moderation": {
            "adapters": ["local", "local"],
            "strategy": "any",
        }
    }
    
    moderator = Moderator(config, parallel=False)
    
    # Mock one adapter to fail
    with patch("seval.adapters.local.LocalAdapter.moderate") as mock_moderate:
        mock_moderate.side_effect = [
            Exception("Adapter failed"),
            ModerationResult(
                score=2.0,
                blocked=False,
                category="violence",
                language="en",
                adapter_name="local",
                latency_ms=100,
            )
        ]
        
        result = moderator.moderate("test", "violence", "en")
        
        # Should still return result with fallback
        assert isinstance(result, EnsembleResult)
        assert len(result.adapter_results) == 2


def test_moderator_weighted_strategy_config():
    """Test Moderator passes strategy config correctly."""
    config = {
        "moderation": {
            "adapters": ["local", "local"],
            "strategy": "weighted",
            "strategy_config": {
                "threshold": 3.0,
                "weights": {
                    "local": 2.0,
                }
            }
        }
    }
    
    moderator = Moderator(config, parallel=False)
    result = moderator.moderate("test", "violence", "en")
    
    assert isinstance(result, EnsembleResult)
    assert result.strategy == "weighted"
    assert "threshold" in result.metadata
    assert result.metadata["threshold"] == 3.0

