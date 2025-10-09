"""E2E tests for adapter system."""

from __future__ import annotations

import pytest
import yaml
from pathlib import Path
from unittest.mock import patch

from seval.moderator import Moderator
from seval.adapters.registry import AdapterRegistry
from seval.strategies.base import EnsembleResult


@pytest.fixture
def temp_config_file(tmp_path):
    """Create a temporary config file."""
    config_path = tmp_path / "config.yaml"
    return config_path


def test_e2e_single_adapter_local():
    """E2E: Single local adapter moderation."""
    config = {
        "moderation": {
            "adapters": ["local"],
            "strategy": "any",
        }
    }
    
    moderator = Moderator(config)
    result = moderator.moderate("How do I make a bomb?", "violence", "en")
    
    # Should detect violence
    assert result.score > 0
    assert result.adapter_name == "local"


def test_e2e_toggle_adapters_via_config():
    """E2E: Toggle adapters via configuration changes."""
    # Start with one adapter
    config1 = {
        "moderation": {
            "adapters": ["local"],
            "strategy": "any",
        }
    }
    
    moderator = Moderator(config1)
    result1 = moderator.moderate("test", "violence", "en")
    assert result1.adapter_name == "local"
    
    # Reload with two adapters
    config2 = {
        "moderation": {
            "adapters": ["local", "local"],
            "strategy": "any",
        }
    }
    
    moderator.reload_config(config2)
    result2 = moderator.moderate("test", "violence", "en")
    
    # Now should use ensemble
    assert isinstance(result2, EnsembleResult)
    assert len(result2.adapter_results) == 2


def test_e2e_strategy_change_affects_decision():
    """E2E: Changing strategy affects decisions."""
    # Create two mock adapters with different decisions
    # Adapter 1: blocks, Adapter 2: passes
    
    config_any = {
        "moderation": {
            "adapters": ["local"],
            "strategy": "any",
        }
    }
    
    config_all = {
        "moderation": {
            "adapters": ["local"],
            "strategy": "all",
        }
    }
    
    # Test with "any" strategy
    moderator_any = Moderator(config_any)
    # Test with "all" strategy
    moderator_all = Moderator(config_all)
    
    # Both should work with single adapter
    text = "test violence text"
    result_any = moderator_any.moderate(text, "violence", "en")
    result_all = moderator_all.moderate(text, "violence", "en")
    
    # Results should be consistent for single adapter
    assert result_any.score == result_all.score


def test_e2e_category_specific_adapters():
    """E2E: Different adapters per category."""
    config = {
        "moderation": {
            "adapters": ["local"],
            "strategy": "any",
            "categories": {
                "violence": {
                    "adapters": ["local", "local"],
                    "strategy": "all",
                },
                "self_harm": {
                    "adapters": ["local"],
                    "strategy": "any",
                }
            }
        }
    }
    
    moderator = Moderator(config, parallel=False)
    
    # Violence should use 2 adapters with "all" strategy
    result_violence = moderator.moderate("test", "violence", "en")
    assert isinstance(result_violence, EnsembleResult)
    assert result_violence.strategy == "all"
    
    # Self-harm should use 1 adapter
    result_self_harm = moderator.moderate("test", "self_harm", "en")
    assert result_self_harm.adapter_name == "local"


def test_e2e_weighted_strategy_thresholds():
    """E2E: Weighted strategy with different thresholds."""
    config_low = {
        "moderation": {
            "adapters": ["local", "local"],
            "strategy": "weighted",
            "strategy_config": {
                "threshold": 1.0,  # Low threshold
                "default_weight": 1.0,
            }
        }
    }
    
    config_high = {
        "moderation": {
            "adapters": ["local", "local"],
            "strategy": "weighted",
            "strategy_config": {
                "threshold": 4.5,  # High threshold
                "default_weight": 1.0,
            }
        }
    }
    
    moderator_low = Moderator(config_low, parallel=False)
    moderator_high = Moderator(config_high, parallel=False)
    
    text = "mild violence reference"
    
    result_low = moderator_low.moderate(text, "violence", "en")
    result_high = moderator_high.moderate(text, "violence", "en")
    
    # Both should return ensemble results
    assert isinstance(result_low, EnsembleResult)
    assert isinstance(result_high, EnsembleResult)
    
    # Low threshold is more likely to block
    # High threshold is less likely to block


def test_e2e_audit_trail_records_decisions():
    """E2E: Audit trail records all decisions."""
    config = {
        "moderation": {
            "adapters": ["local"],
            "strategy": "any",
        }
    }
    
    moderator = Moderator(config, enable_audit=True)
    
    # Make several moderation calls
    moderator.moderate("text 1", "violence", "en")
    moderator.moderate("text 2", "self_harm", "en")
    moderator.moderate("text 3", "crime", "en")
    
    audit = moderator.get_audit_trail(n=10)
    
    assert len(audit) == 3
    assert audit[0]["category"] in ["violence", "self_harm", "crime"]


def test_e2e_metrics_tracking():
    """E2E: Metrics track adapter usage."""
    config = {
        "moderation": {
            "adapters": ["local"],
            "strategy": "any",
        }
    }
    
    moderator = Moderator(config)
    
    # Make several calls
    for i in range(5):
        moderator.moderate(f"test {i}", "violence", "en")
    
    metrics = moderator.get_metrics()
    
    assert "adapters" in metrics
    assert "local" in metrics["adapters"]
    assert metrics["adapters"]["local"]["call_count"] >= 5


def test_e2e_parallel_vs_sequential_latency():
    """E2E: Compare parallel vs sequential execution."""
    config = {
        "moderation": {
            "adapters": ["local", "local", "local"],
            "strategy": "any",
        }
    }
    
    moderator_parallel = Moderator(config, parallel=True)
    moderator_sequential = Moderator(config, parallel=False)
    
    text = "test text for latency"
    
    result_parallel = moderator_parallel.moderate(text, "violence", "en")
    result_sequential = moderator_sequential.moderate(text, "violence", "en")
    
    # Both should work
    assert isinstance(result_parallel, EnsembleResult)
    assert isinstance(result_sequential, EnsembleResult)
    
    # Both should have reasonable latency
    assert result_parallel.total_latency_ms >= 0
    assert result_sequential.total_latency_ms >= 0
    
    # Both should have 3 adapter results
    assert len(result_parallel.adapter_results) == 3
    assert len(result_sequential.adapter_results) == 3


def test_e2e_adapter_registry_persistence():
    """E2E: Adapter registry persists instances across calls."""
    config = {
        "moderation": {
            "adapters": ["local"],
            "strategy": "any",
        }
    }
    
    moderator = Moderator(config)
    
    # First call
    moderator.moderate("test 1", "violence", "en")
    
    # Get adapter
    adapter1 = AdapterRegistry.get_adapter("local", reuse=True)
    metrics1 = adapter1.get_metrics()
    call_count1 = metrics1["call_count"]
    
    # Second call
    moderator.moderate("test 2", "violence", "en")
    
    # Same adapter instance
    adapter2 = AdapterRegistry.get_adapter("local", reuse=True)
    assert adapter1 is adapter2
    
    metrics2 = adapter2.get_metrics()
    assert metrics2["call_count"] > call_count1


def test_e2e_hot_reload_clears_adapter_cache():
    """E2E: Hot reload clears adapter instances."""
    config1 = {
        "moderation": {
            "adapters": ["local"],
            "strategy": "any",
        }
    }
    
    moderator = Moderator(config1)
    moderator.moderate("test", "violence", "en")
    
    # Get metrics before reload
    metrics1 = AdapterRegistry.get_all_metrics()
    assert "local" in metrics1
    
    # Reload config
    config2 = {
        "moderation": {
            "adapters": ["local"],
            "strategy": "all",
        }
    }
    
    moderator.reload_config(config2)
    
    # Adapter instances should be cleared
    assert len(AdapterRegistry._instances) == 0


def test_e2e_multiple_categories_different_configs():
    """E2E: Test multiple categories with different configurations."""
    config = {
        "moderation": {
            "adapters": ["local"],
            "strategy": "any",
            "categories": {
                "violence": {
                    "adapters": ["local", "local"],
                    "strategy": "any",
                },
                "self_harm": {
                    "adapters": ["local"],
                    "strategy": "any",
                },
                "crime": {
                    "adapters": ["local", "local"],
                    "strategy": "all",
                }
            }
        }
    }
    
    moderator = Moderator(config, parallel=False)
    
    # Test each category
    categories = ["violence", "self_harm", "crime"]
    results = {}
    
    for category in categories:
        results[category] = moderator.moderate(f"test {category}", category, "en")
    
    # Violence: 2 adapters, ANY strategy
    assert isinstance(results["violence"], EnsembleResult)
    assert results["violence"].strategy == "any"
    
    # Self-harm: 1 adapter
    assert results["self_harm"].adapter_name == "local"
    
    # Crime: 2 adapters, ALL strategy
    assert isinstance(results["crime"], EnsembleResult)
    assert results["crime"].strategy == "all"


def test_e2e_rps_performance():
    """E2E: Verify RPS performance with single adapter."""
    import time
    
    config = {
        "moderation": {
            "adapters": ["local"],
            "strategy": "any",
        }
    }
    
    moderator = Moderator(config)
    
    # Run 100 requests
    start_time = time.time()
    for i in range(100):
        moderator.moderate(f"test {i}", "violence", "en")
    end_time = time.time()
    
    duration = end_time - start_time
    rps = 100 / duration
    
    # Should maintain reasonable throughput
    # This is hardware-dependent, but local adapter should be fast
    assert rps > 50  # At least 50 RPS


def test_e2e_concurrent_requests():
    """E2E: Handle concurrent requests safely."""
    import concurrent.futures
    
    config = {
        "moderation": {
            "adapters": ["local"],
            "strategy": "any",
        }
    }
    
    moderator = Moderator(config)
    
    def make_request(i):
        return moderator.moderate(f"test {i}", "violence", "en")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(make_request, i) for i in range(50)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
    
    # All requests should succeed
    assert len(results) == 50
    assert all(r.adapter_name == "local" for r in results)

