"""Moderator orchestrator for multi-model moderation."""

from __future__ import annotations

import concurrent.futures
import logging
import time
from typing import Any, Dict, List, Optional

from seval.adapters.base import ModerationAdapter, ModerationResult
from seval.adapters.registry import AdapterRegistry
from seval.strategies.base import EnsembleStrategy, EnsembleResult
from seval.strategies.registry import StrategyRegistry

logger = logging.getLogger(__name__)


class ModerationAudit:
    """Audit trail for moderation decisions."""
    
    def __init__(self, max_entries: int = 1000):
        """Initialize audit trail.
        
        Args:
            max_entries: Maximum number of entries to keep
        """
        self.max_entries = max_entries
        self._entries: List[Dict[str, Any]] = []
    
    def log_decision(
        self,
        text_hash: str,
        category: str,
        language: str,
        result: EnsembleResult | ModerationResult,
        timestamp: Optional[float] = None
    ) -> None:
        """Log a moderation decision.
        
        Args:
            text_hash: Hash of the text (for privacy)
            category: Content category
            language: Language code
            result: Moderation result
            timestamp: Optional timestamp
        """
        entry = {
            "timestamp": timestamp or time.time(),
            "text_hash": text_hash,
            "category": category,
            "language": language,
            "score": result.score,
            "blocked": result.blocked,
        }
        
        if isinstance(result, EnsembleResult):
            entry["strategy"] = result.strategy
            entry["adapters"] = [r.adapter_name for r in result.adapter_results]
            entry["adapter_scores"] = {
                r.adapter_name: r.score for r in result.adapter_results
            }
        else:
            entry["adapter"] = result.adapter_name
        
        self._entries.append(entry)
        
        # Keep only recent entries
        if len(self._entries) > self.max_entries:
            self._entries = self._entries[-self.max_entries:]
    
    def get_recent(self, n: int = 10) -> List[Dict[str, Any]]:
        """Get recent audit entries.
        
        Args:
            n: Number of recent entries
            
        Returns:
            List of recent entries
        """
        return self._entries[-n:]
    
    def get_all(self) -> List[Dict[str, Any]]:
        """Get all audit entries.
        
        Returns:
            List of all entries
        """
        return self._entries.copy()
    
    def clear(self) -> None:
        """Clear audit trail."""
        self._entries.clear()


class Moderator:
    """Orchestrator for multi-model moderation."""
    
    def __init__(
        self,
        config: Dict[str, Any],
        enable_audit: bool = True,
        parallel: bool = True
    ):
        """Initialize moderator.
        
        Args:
            config: Configuration dictionary
            enable_audit: Enable audit trail
            parallel: Run adapters in parallel
        """
        self.config = config
        self.enable_audit = enable_audit
        self.parallel = parallel
        self.audit = ModerationAudit() if enable_audit else None
        
        # Parse configuration
        self._load_config(config)
    
    def _load_config(self, config: Dict[str, Any]) -> None:
        """Load configuration.
        
        Args:
            config: Configuration dictionary
        """
        moderation_config = config.get("moderation", {})
        
        # Global defaults
        self.default_adapters = moderation_config.get("adapters", ["local"])
        self.default_strategy = moderation_config.get("strategy", "any")
        self.default_strategy_config = moderation_config.get("strategy_config", {})
        
        # Per-category overrides
        self.category_config = moderation_config.get("categories", {})
        
        # Adapter configurations
        self.adapter_configs = moderation_config.get("adapter_configs", {})
        
        logger.info(
            f"Moderator configured: adapters={self.default_adapters}, "
            f"strategy={self.default_strategy}"
        )
    
    def reload_config(self, config: Dict[str, Any]) -> None:
        """Hot-reload configuration.
        
        Args:
            config: New configuration dictionary
        """
        logger.info("Reloading moderator configuration")
        self._load_config(config)
        # Clear adapter instances to pick up new config
        AdapterRegistry.clear_instances()
    
    def _get_config_for_category(
        self,
        category: str
    ) -> tuple[List[str], str, Dict[str, Any]]:
        """Get configuration for a specific category.
        
        Args:
            category: Content category
            
        Returns:
            Tuple of (adapters, strategy, strategy_config)
        """
        if category in self.category_config:
            cat_config = self.category_config[category]
            adapters = cat_config.get("adapters", self.default_adapters)
            strategy = cat_config.get("strategy", self.default_strategy)
            strategy_config = cat_config.get("strategy_config", self.default_strategy_config)
        else:
            adapters = self.default_adapters
            strategy = self.default_strategy
            strategy_config = self.default_strategy_config
        
        return adapters, strategy, strategy_config
    
    def moderate(
        self,
        text: str,
        category: str,
        language: str,
        **kwargs: Any
    ) -> EnsembleResult | ModerationResult:
        """Perform moderation using configured adapters and strategy.
        
        Args:
            text: Text to moderate
            category: Content category
            language: Language code
            **kwargs: Additional parameters
            
        Returns:
            EnsembleResult or ModerationResult
        """
        # Get category-specific config
        adapter_names, strategy_name, strategy_config = self._get_config_for_category(category)
        
        # Single adapter case - no ensemble needed
        if len(adapter_names) == 1:
            return self._moderate_single(
                text, category, language, adapter_names[0], **kwargs
            )
        
        # Multiple adapters - use ensemble
        return self._moderate_ensemble(
            text, category, language,
            adapter_names, strategy_name, strategy_config,
            **kwargs
        )
    
    def _moderate_single(
        self,
        text: str,
        category: str,
        language: str,
        adapter_name: str,
        **kwargs: Any
    ) -> ModerationResult:
        """Moderate using a single adapter.
        
        Args:
            text: Text to moderate
            category: Content category
            language: Language code
            adapter_name: Adapter to use
            **kwargs: Additional parameters
            
        Returns:
            ModerationResult
        """
        adapter_config = self.adapter_configs.get(adapter_name, {})
        adapter = AdapterRegistry.get_adapter(adapter_name, adapter_config)
        
        result = adapter.moderate(text, category, language, **kwargs)
        
        # Log to audit trail
        if self.audit:
            import hashlib
            text_hash = hashlib.sha256(text.encode()).hexdigest()[:12]
            self.audit.log_decision(text_hash, category, language, result)
        
        return result
    
    def _moderate_ensemble(
        self,
        text: str,
        category: str,
        language: str,
        adapter_names: List[str],
        strategy_name: str,
        strategy_config: Dict[str, Any],
        **kwargs: Any
    ) -> EnsembleResult:
        """Moderate using multiple adapters with ensemble strategy.
        
        Args:
            text: Text to moderate
            category: Content category
            language: Language code
            adapter_names: List of adapters to use
            strategy_name: Strategy name
            strategy_config: Strategy configuration
            **kwargs: Additional parameters
            
        Returns:
            EnsembleResult
        """
        # Get adapters
        adapters = []
        for name in adapter_names:
            adapter_config = self.adapter_configs.get(name, {})
            try:
                adapter = AdapterRegistry.get_adapter(name, adapter_config)
                adapters.append(adapter)
            except Exception as e:
                logger.error(f"Failed to load adapter '{name}': {e}")
        
        if not adapters:
            raise RuntimeError("No adapters available")
        
        # Run adapters (parallel or sequential)
        if self.parallel and len(adapters) > 1:
            results = self._run_adapters_parallel(
                adapters, text, category, language, **kwargs
            )
        else:
            results = self._run_adapters_sequential(
                adapters, text, category, language, **kwargs
            )
        
        # Apply strategy
        strategy = StrategyRegistry.get_strategy(strategy_name, strategy_config)
        ensemble_result = strategy.combine(results, category, language)
        
        # Log to audit trail
        if self.audit:
            import hashlib
            text_hash = hashlib.sha256(text.encode()).hexdigest()[:12]
            self.audit.log_decision(text_hash, category, language, ensemble_result)
        
        return ensemble_result
    
    def _run_adapters_parallel(
        self,
        adapters: List[ModerationAdapter],
        text: str,
        category: str,
        language: str,
        **kwargs: Any
    ) -> List[ModerationResult]:
        """Run adapters in parallel.
        
        Args:
            adapters: List of adapters
            text: Text to moderate
            category: Content category
            language: Language code
            **kwargs: Additional parameters
            
        Returns:
            List of ModerationResult
        """
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(adapters)) as executor:
            futures = {
                executor.submit(adapter.moderate, text, category, language, **kwargs): adapter
                for adapter in adapters
            }
            
            for future in concurrent.futures.as_completed(futures):
                adapter = futures[future]
                try:
                    result = future.result(timeout=5.0)
                    results.append(result)
                except concurrent.futures.TimeoutError:
                    logger.warning(f"Adapter {adapter.name} timed out")
                    # Return safe fallback
                    results.append(ModerationResult(
                        score=0.0,
                        blocked=False,
                        category=category,
                        language=language,
                        adapter_name=adapter.name,
                        latency_ms=5000,
                        metadata={"error": "timeout"},
                    ))
                except Exception as e:
                    logger.error(f"Adapter {adapter.name} failed: {e}")
                    results.append(ModerationResult(
                        score=0.0,
                        blocked=False,
                        category=category,
                        language=language,
                        adapter_name=adapter.name,
                        latency_ms=0,
                        metadata={"error": str(e)},
                    ))
        
        return results
    
    def _run_adapters_sequential(
        self,
        adapters: List[ModerationAdapter],
        text: str,
        category: str,
        language: str,
        **kwargs: Any
    ) -> List[ModerationResult]:
        """Run adapters sequentially.
        
        Args:
            adapters: List of adapters
            text: Text to moderate
            category: Content category
            language: Language code
            **kwargs: Additional parameters
            
        Returns:
            List of ModerationResult
        """
        results = []
        for adapter in adapters:
            try:
                result = adapter.moderate(text, category, language, **kwargs)
                results.append(result)
            except Exception as e:
                logger.error(f"Adapter {adapter.name} failed: {e}")
                results.append(ModerationResult(
                    score=0.0,
                    blocked=False,
                    category=category,
                    language=language,
                    adapter_name=adapter.name,
                    latency_ms=0,
                    metadata={"error": str(e)},
                ))
        
        return results
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get metrics from all adapters.
        
        Returns:
            Dictionary with adapter metrics
        """
        return {
            "adapters": AdapterRegistry.get_all_metrics(),
            "audit_size": len(self.audit._entries) if self.audit else 0,
        }
    
    def get_audit_trail(self, n: int = 10) -> List[Dict[str, Any]]:
        """Get recent audit entries.
        
        Args:
            n: Number of recent entries
            
        Returns:
            List of audit entries
        """
        if not self.audit:
            return []
        return self.audit.get_recent(n)

