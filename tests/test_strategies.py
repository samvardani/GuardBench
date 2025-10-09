"""Unit tests for ensemble strategies."""

from __future__ import annotations

import pytest

from seval.adapters.base import ModerationResult
from seval.strategies import AnyStrategy, AllStrategy, WeightedStrategy, EnsembleResult
from seval.strategies.registry import StrategyRegistry


def create_mock_result(adapter_name: str, score: float, blocked: bool) -> ModerationResult:
    """Helper to create mock ModerationResult."""
    return ModerationResult(
        score=score,
        blocked=blocked,
        category="violence",
        language="en",
        adapter_name=adapter_name,
        latency_ms=100,
    )


def test_any_strategy_all_pass():
    """Test ANY strategy when all adapters pass."""
    strategy = AnyStrategy()
    
    results = [
        create_mock_result("adapter1", 1.0, False),
        create_mock_result("adapter2", 1.5, False),
    ]
    
    ensemble = strategy.combine(results, "violence", "en")
    
    assert ensemble.blocked is False
    assert ensemble.strategy == "any"
    assert ensemble.total_latency_ms == 200


def test_any_strategy_one_blocks():
    """Test ANY strategy when one adapter blocks."""
    strategy = AnyStrategy()
    
    results = [
        create_mock_result("adapter1", 1.0, False),
        create_mock_result("adapter2", 4.0, True),
    ]
    
    ensemble = strategy.combine(results, "violence", "en")
    
    assert ensemble.blocked is True
    assert ensemble.score == 4.0  # Max score
    assert "adapter2" in ensemble.metadata["blocking_adapters"]


def test_any_strategy_all_block():
    """Test ANY strategy when all adapters block."""
    strategy = AnyStrategy()
    
    results = [
        create_mock_result("adapter1", 3.5, True),
        create_mock_result("adapter2", 4.0, True),
    ]
    
    ensemble = strategy.combine(results, "violence", "en")
    
    assert ensemble.blocked is True
    assert ensemble.score == 4.0  # Max score
    assert len(ensemble.metadata["blocking_adapters"]) == 2


def test_all_strategy_all_pass():
    """Test ALL strategy when all adapters pass."""
    strategy = AllStrategy()
    
    results = [
        create_mock_result("adapter1", 1.0, False),
        create_mock_result("adapter2", 1.5, False),
    ]
    
    ensemble = strategy.combine(results, "violence", "en")
    
    assert ensemble.blocked is False
    assert ensemble.strategy == "all"


def test_all_strategy_one_blocks():
    """Test ALL strategy when one adapter blocks."""
    strategy = AllStrategy()
    
    results = [
        create_mock_result("adapter1", 1.0, False),
        create_mock_result("adapter2", 4.0, True),
    ]
    
    ensemble = strategy.combine(results, "violence", "en")
    
    assert ensemble.blocked is False  # Not all block
    assert ensemble.score == 2.5  # Average score


def test_all_strategy_all_block():
    """Test ALL strategy when all adapters block."""
    strategy = AllStrategy()
    
    results = [
        create_mock_result("adapter1", 3.5, True),
        create_mock_result("adapter2", 4.0, True),
    ]
    
    ensemble = strategy.combine(results, "violence", "en")
    
    assert ensemble.blocked is True
    assert ensemble.score == 3.75  # Average score
    assert ensemble.metadata["consensus"] is True


def test_weighted_strategy_default_weights():
    """Test WEIGHTED strategy with default weights."""
    strategy = WeightedStrategy(config={"threshold": 2.5})
    
    results = [
        create_mock_result("adapter1", 2.0, False),
        create_mock_result("adapter2", 3.0, False),
    ]
    
    ensemble = strategy.combine(results, "violence", "en")
    
    # Default weight 1.0 for both: (2.0 + 3.0) / 2 = 2.5
    assert ensemble.score == 2.5
    assert ensemble.blocked is True  # Equals threshold


def test_weighted_strategy_custom_weights():
    """Test WEIGHTED strategy with custom weights."""
    strategy = WeightedStrategy(config={
        "threshold": 2.0,
        "weights": {
            "adapter1": 2.0,
            "adapter2": 1.0,
        }
    })
    
    results = [
        create_mock_result("adapter1", 3.0, False),
        create_mock_result("adapter2", 1.0, False),
    ]
    
    ensemble = strategy.combine(results, "violence", "en")
    
    # Weighted: (3.0 * 2.0 + 1.0 * 1.0) / (2.0 + 1.0) = 7.0 / 3.0 = 2.33
    assert abs(ensemble.score - 2.33) < 0.01
    assert ensemble.blocked is True  # > 2.0 threshold


def test_weighted_strategy_below_threshold():
    """Test WEIGHTED strategy below threshold."""
    strategy = WeightedStrategy(config={
        "threshold": 3.0,
        "weights": {
            "adapter1": 1.0,
            "adapter2": 1.0,
        }
    })
    
    results = [
        create_mock_result("adapter1", 2.0, False),
        create_mock_result("adapter2", 2.0, False),
    ]
    
    ensemble = strategy.combine(results, "violence", "en")
    
    assert ensemble.score == 2.0
    assert ensemble.blocked is False  # Below threshold


def test_strategy_empty_results():
    """Test strategies handle empty results gracefully."""
    strategy = AnyStrategy()
    
    with pytest.raises(ValueError, match="Cannot combine empty results"):
        strategy.combine([], "violence", "en")


def test_ensemble_result_to_dict():
    """Test EnsembleResult to_dict conversion."""
    results = [
        create_mock_result("adapter1", 2.0, False),
        create_mock_result("adapter2", 3.0, True),
    ]
    
    strategy = AnyStrategy()
    ensemble = strategy.combine(results, "violence", "en")
    
    d = ensemble.to_dict()
    
    assert d["score"] == 3.0
    assert d["blocked"] is True
    assert d["strategy"] == "any"
    assert "adapter1" in d["adapters"]
    assert "adapter2" in d["adapters"]
    assert len(d["adapter_details"]) == 2


def test_strategy_registry_get_any():
    """Test StrategyRegistry returns ANY strategy."""
    strategy = StrategyRegistry.get_strategy("any")
    
    assert isinstance(strategy, AnyStrategy)


def test_strategy_registry_get_all():
    """Test StrategyRegistry returns ALL strategy."""
    strategy = StrategyRegistry.get_strategy("all")
    
    assert isinstance(strategy, AllStrategy)


def test_strategy_registry_get_weighted():
    """Test StrategyRegistry returns WEIGHTED strategy."""
    strategy = StrategyRegistry.get_strategy("weighted")
    
    assert isinstance(strategy, WeightedStrategy)


def test_strategy_registry_unknown():
    """Test StrategyRegistry raises error for unknown strategy."""
    with pytest.raises(ValueError, match="Strategy 'unknown' not found"):
        StrategyRegistry.get_strategy("unknown")


def test_strategy_registry_list():
    """Test StrategyRegistry lists available strategies."""
    strategies = StrategyRegistry.list_strategies()
    
    assert "any" in strategies
    assert "all" in strategies
    assert "weighted" in strategies


def test_three_adapters_disagree():
    """Test scenario where three adapters disagree."""
    # Adapter 1: pass, Adapter 2: block, Adapter 3: pass
    results = [
        create_mock_result("adapter1", 1.0, False),
        create_mock_result("adapter2", 4.5, True),
        create_mock_result("adapter3", 1.5, False),
    ]
    
    # ANY strategy: should block (one blocks)
    any_strategy = AnyStrategy()
    any_result = any_strategy.combine(results, "violence", "en")
    assert any_result.blocked is True
    
    # ALL strategy: should pass (not all block)
    all_strategy = AllStrategy()
    all_result = all_strategy.combine(results, "violence", "en")
    assert all_result.blocked is False
    
    # WEIGHTED strategy: depends on threshold
    weighted_strategy = WeightedStrategy(config={"threshold": 2.5})
    weighted_result = weighted_strategy.combine(results, "violence", "en")
    # Average: (1.0 + 4.5 + 1.5) / 3 = 2.33 < 2.5
    assert weighted_result.blocked is False


def test_weighted_strategy_metadata():
    """Test WEIGHTED strategy includes weight metadata."""
    strategy = WeightedStrategy(config={
        "threshold": 2.0,
        "weights": {
            "adapter1": 2.0,
            "adapter2": 1.0,
        }
    })
    
    results = [
        create_mock_result("adapter1", 3.0, False),
        create_mock_result("adapter2", 1.0, False),
    ]
    
    ensemble = strategy.combine(results, "violence", "en")
    
    assert "weights_used" in ensemble.metadata
    assert ensemble.metadata["weights_used"]["adapter1"] == 2.0
    assert ensemble.metadata["weights_used"]["adapter2"] == 1.0
    assert "individual_scores" in ensemble.metadata

