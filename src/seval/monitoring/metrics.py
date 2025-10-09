"""Metrics collection for Prometheus."""

from __future__ import annotations

import logging
import time
from collections import deque
from dataclasses import dataclass
from threading import Lock
from typing import Any, Dict, List, Optional

try:
    from prometheus_client import Counter, Histogram, Gauge
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    # Fallback implementations
    class Counter:
        def __init__(self, *args, **kwargs):
            self._value = 0
        def labels(self, **kwargs):
            return self
        def inc(self, amount=1):
            self._value += amount
    
    class Histogram:
        def __init__(self, *args, **kwargs):
            self._observations = []
        def labels(self, **kwargs):
            return self
        def observe(self, value):
            self._observations.append(value)
    
    class Gauge:
        def __init__(self, *args, **kwargs):
            self._value = 0
        def labels(self, **kwargs):
            return self
        def set(self, value):
            self._value = value

logger = logging.getLogger(__name__)


@dataclass
class MetricSnapshot:
    """Snapshot of metrics at a point in time."""
    timestamp: float
    category: str
    language: str
    blocked: bool
    score: float
    latency_ms: float


class MetricsCollector:
    """Collects and aggregates metrics for monitoring."""
    
    def __init__(self, window_minutes: int = 15):
        """Initialize metrics collector.
        
        Args:
            window_minutes: Rolling window for metrics in minutes
        """
        self.window_seconds = window_minutes * 60
        self._snapshots: deque = deque(maxlen=10000)  # Keep last 10k snapshots
        self._lock = Lock()
        
        # Prometheus metrics
        if PROMETHEUS_AVAILABLE:
            self.request_counter = Counter(
                'safety_eval_requests_total',
                'Total safety evaluation requests',
                ['category', 'language', 'blocked']
            )
            
            self.latency_histogram = Histogram(
                'safety_eval_latency_seconds',
                'Request latency in seconds',
                ['category', 'language'],
                buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)
            )
            
            self.score_histogram = Histogram(
                'safety_eval_score',
                'Safety evaluation score',
                ['category', 'language'],
                buckets=(0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0)
            )
            
            self.blocked_gauge = Gauge(
                'safety_eval_blocked_rate',
                'Rate of blocked requests',
                ['category']
            )
        
        logger.info(f"MetricsCollector initialized (window={window_minutes}m, prometheus={PROMETHEUS_AVAILABLE})")
    
    def record_request(
        self,
        category: str,
        language: str,
        score: float,
        blocked: bool,
        latency_ms: float
    ) -> None:
        """Record a request for metrics.
        
        Args:
            category: Content category
            language: Language code
            score: Safety score
            blocked: Whether request was blocked
            latency_ms: Latency in milliseconds
        """
        timestamp = time.time()
        
        # Record in Prometheus
        if PROMETHEUS_AVAILABLE:
            self.request_counter.labels(
                category=category,
                language=language,
                blocked=str(blocked)
            ).inc()
            
            self.latency_histogram.labels(
                category=category,
                language=language
            ).observe(latency_ms / 1000.0)
            
            self.score_histogram.labels(
                category=category,
                language=language
            ).observe(score)
        
        # Store snapshot for dashboard
        snapshot = MetricSnapshot(
            timestamp=timestamp,
            category=category,
            language=language,
            blocked=blocked,
            score=score,
            latency_ms=latency_ms
        )
        
        with self._lock:
            self._snapshots.append(snapshot)
            self._cleanup_old_snapshots()
    
    def _cleanup_old_snapshots(self) -> None:
        """Remove snapshots outside the rolling window."""
        cutoff = time.time() - self.window_seconds
        while self._snapshots and self._snapshots[0].timestamp < cutoff:
            self._snapshots.popleft()
    
    def get_recent_snapshots(self, seconds: Optional[int] = None) -> List[MetricSnapshot]:
        """Get recent snapshots.
        
        Args:
            seconds: Number of seconds to look back (default: full window)
            
        Returns:
            List of recent snapshots
        """
        if seconds is None:
            seconds = self.window_seconds
        
        cutoff = time.time() - seconds
        
        with self._lock:
            self._cleanup_old_snapshots()
            return [s for s in self._snapshots if s.timestamp >= cutoff]
    
    def get_summary(self, seconds: Optional[int] = None) -> Dict[str, Any]:
        """Get summary statistics.
        
        Args:
            seconds: Number of seconds to look back
            
        Returns:
            Dictionary with summary stats
        """
        snapshots = self.get_recent_snapshots(seconds)
        
        if not snapshots:
            return {
                "total_requests": 0,
                "qps": 0.0,
                "blocked_count": 0,
                "blocked_rate": 0.0,
                "latency_p50": 0.0,
                "latency_p95": 0.0,
                "latency_p99": 0.0,
                "avg_score": 0.0,
                "categories": {},
            }
        
        # Calculate stats
        total = len(snapshots)
        blocked = sum(1 for s in snapshots if s.blocked)
        
        latencies = sorted([s.latency_ms for s in snapshots])
        scores = [s.score for s in snapshots]
        
        time_span = snapshots[-1].timestamp - snapshots[0].timestamp
        qps = total / time_span if time_span > 0 else 0.0
        
        # Percentiles
        def percentile(data: List[float], p: float) -> float:
            if not data:
                return 0.0
            k = (len(data) - 1) * p
            f = int(k)
            c = f + 1
            if c >= len(data):
                return data[-1]
            return data[f] + (k - f) * (data[c] - data[f])
        
        # Category breakdown
        category_stats: Dict[str, Dict[str, Any]] = {}
        for snapshot in snapshots:
            cat = snapshot.category
            if cat not in category_stats:
                category_stats[cat] = {
                    "count": 0,
                    "blocked": 0,
                    "scores": [],
                }
            category_stats[cat]["count"] += 1
            if snapshot.blocked:
                category_stats[cat]["blocked"] += 1
            category_stats[cat]["scores"].append(snapshot.score)
        
        # Calculate per-category stats
        for cat, stats in category_stats.items():
            stats["blocked_rate"] = stats["blocked"] / stats["count"] if stats["count"] > 0 else 0.0
            stats["avg_score"] = sum(stats["scores"]) / len(stats["scores"]) if stats["scores"] else 0.0
            del stats["scores"]  # Don't include raw scores in summary
        
        return {
            "total_requests": total,
            "qps": round(qps, 2),
            "blocked_count": blocked,
            "blocked_rate": round(blocked / total, 3) if total > 0 else 0.0,
            "latency_p50": round(percentile(latencies, 0.50), 2),
            "latency_p95": round(percentile(latencies, 0.95), 2),
            "latency_p99": round(percentile(latencies, 0.99), 2),
            "avg_score": round(sum(scores) / len(scores), 2) if scores else 0.0,
            "categories": category_stats,
        }


# Global metrics collector
_global_collector: Optional[MetricsCollector] = None


def get_global_collector() -> MetricsCollector:
    """Get or create global metrics collector.
    
    Returns:
        Global MetricsCollector instance
    """
    global _global_collector
    if _global_collector is None:
        _global_collector = MetricsCollector()
    return _global_collector

