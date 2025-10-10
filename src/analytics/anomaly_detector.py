"""Anomaly detection with tuning for noise reduction.

Features:
- Minimum sample size requirement before alerting
- Per-metric cooldown to prevent alert storms
- Z-score based statistical anomaly detection
"""

from __future__ import annotations

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AnomalyConfig:
    """Configuration for anomaly detection."""
    
    min_samples: int = 12  # Minimum samples before z-score alerts
    cooldown_seconds: int = 600  # 10 minutes cooldown per metric
    z_threshold: float = 3.0  # Standard deviations for anomaly
    window_size: int = 100  # Rolling window size


@dataclass
class Anomaly:
    """Detected anomaly."""
    
    metric_name: str
    value: float
    mean: float
    std: float
    z_score: float
    timestamp: float
    sample_count: int


class MetricTimeSeries:
    """Time series data for a single metric."""
    
    def __init__(self, name: str, window_size: int = 100):
        self.name = name
        self.window_size = window_size
        self.values: deque = deque(maxlen=window_size)
        self.timestamps: deque = deque(maxlen=window_size)
        self.last_alert_time: Optional[float] = None
    
    def add(self, value: float, timestamp: Optional[float] = None):
        """Add a data point."""
        if timestamp is None:
            timestamp = time.time()
        
        self.values.append(value)
        self.timestamps.append(timestamp)
    
    def compute_stats(self) -> tuple[float, float]:
        """Compute mean and standard deviation.
        
        Returns:
            (mean, std) tuple
        """
        if len(self.values) < 2:
            return 0.0, 0.0
        
        # Use sample std (ddof=1)
        values_list = list(self.values)
        n = len(values_list)
        mean = sum(values_list) / n
        
        variance = sum((x - mean) ** 2 for x in values_list) / (n - 1)
        std = variance ** 0.5
        
        return mean, std
    
    def compute_z_score(self, value: float) -> float:
        """Compute z-score for value.
        
        Args:
            value: Value to score
            
        Returns:
            Z-score (number of standard deviations from mean)
        """
        mean, std = self.compute_stats()
        
        if std == 0:
            return 0.0
        
        return abs((value - mean) / std)
    
    def sample_count(self) -> int:
        """Get current sample count."""
        return len(self.values)
    
    def is_in_cooldown(self, current_time: float, cooldown_seconds: int) -> bool:
        """Check if metric is in cooldown period.
        
        Args:
            current_time: Current timestamp
            cooldown_seconds: Cooldown duration
            
        Returns:
            True if in cooldown
        """
        if self.last_alert_time is None:
            return False
        
        return (current_time - self.last_alert_time) < cooldown_seconds
    
    def mark_alert(self, timestamp: float):
        """Mark that an alert was triggered."""
        self.last_alert_time = timestamp


class AnomalyDetector:
    """Statistical anomaly detector with noise reduction.
    
    Features:
    - Minimum sample requirement (reduces false positives from insufficient data)
    - Per-metric cooldown (prevents alert storms)
    - Z-score based detection (parametric statistical test)
    """
    
    def __init__(self, config: Optional[AnomalyConfig] = None):
        """Initialize detector.
        
        Args:
            config: Anomaly detection configuration
        """
        self.config = config or AnomalyConfig()
        self.metrics: Dict[str, MetricTimeSeries] = {}
        
        logger.info(
            f"AnomalyDetector initialized: "
            f"min_samples={self.config.min_samples}, "
            f"cooldown={self.config.cooldown_seconds}s, "
            f"z_threshold={self.config.z_threshold}"
        )
    
    def record(self, metric_name: str, value: float, timestamp: Optional[float] = None):
        """Record a metric value.
        
        Args:
            metric_name: Name of metric
            value: Metric value
            timestamp: Optional timestamp (default: now)
        """
        if metric_name not in self.metrics:
            self.metrics[metric_name] = MetricTimeSeries(
                metric_name,
                window_size=self.config.window_size
            )
        
        self.metrics[metric_name].add(value, timestamp)
    
    def check(
        self,
        metric_name: str,
        value: float,
        timestamp: Optional[float] = None
    ) -> Optional[Anomaly]:
        """Check if value is anomalous.
        
        Args:
            metric_name: Name of metric
            value: Value to check
            timestamp: Optional timestamp (default: now)
            
        Returns:
            Anomaly if detected, None otherwise
        """
        if timestamp is None:
            timestamp = time.time()
        
        # Record the value first
        self.record(metric_name, value, timestamp)
        
        metric = self.metrics[metric_name]
        
        # Check minimum samples requirement
        if metric.sample_count() < self.config.min_samples:
            logger.debug(
                f"Skipping anomaly check for {metric_name}: "
                f"only {metric.sample_count()}/{self.config.min_samples} samples"
            )
            return None
        
        # Check cooldown
        if metric.is_in_cooldown(timestamp, self.config.cooldown_seconds):
            remaining = int(
                self.config.cooldown_seconds - (timestamp - metric.last_alert_time)
            )
            logger.debug(
                f"Skipping anomaly check for {metric_name}: "
                f"in cooldown ({remaining}s remaining)"
            )
            return None
        
        # Compute z-score
        mean, std = metric.compute_stats()
        z_score = metric.compute_z_score(value)
        
        # Check threshold
        if z_score >= self.config.z_threshold:
            # Anomaly detected!
            anomaly = Anomaly(
                metric_name=metric_name,
                value=value,
                mean=mean,
                std=std,
                z_score=z_score,
                timestamp=timestamp,
                sample_count=metric.sample_count()
            )
            
            # Mark cooldown
            metric.mark_alert(timestamp)
            
            logger.warning(
                f"Anomaly detected: {metric_name}={value:.2f} "
                f"(z={z_score:.2f}, mean={mean:.2f}, std={std:.2f})"
            )
            
            return anomaly
        
        return None
    
    def get_metric_stats(self, metric_name: str) -> Dict[str, float]:
        """Get statistics for a metric.
        
        Args:
            metric_name: Name of metric
            
        Returns:
            Dict with mean, std, sample_count
        """
        if metric_name not in self.metrics:
            return {
                "mean": 0.0,
                "std": 0.0,
                "sample_count": 0
            }
        
        metric = self.metrics[metric_name]
        mean, std = metric.compute_stats()
        
        return {
            "mean": mean,
            "std": std,
            "sample_count": metric.sample_count()
        }


def create_detector_from_env() -> AnomalyDetector:
    """Create anomaly detector from environment variables.
    
    Environment variables:
    - ANOMALY_MIN_SAMPLES: Minimum samples (default: 12)
    - ANOMALY_COOLDOWN_SEC: Cooldown seconds (default: 600)
    - ANOMALY_Z_THRESHOLD: Z-score threshold (default: 3.0)
    - ANOMALY_WINDOW_SIZE: Rolling window size (default: 100)
    
    Returns:
        Configured AnomalyDetector
    """
    import os
    
    config = AnomalyConfig(
        min_samples=int(os.getenv("ANOMALY_MIN_SAMPLES", "12")),
        cooldown_seconds=int(os.getenv("ANOMALY_COOLDOWN_SEC", "600")),
        z_threshold=float(os.getenv("ANOMALY_Z_THRESHOLD", "3.0")),
        window_size=int(os.getenv("ANOMALY_WINDOW_SIZE", "100"))
    )
    
    return AnomalyDetector(config)


__all__ = [
    "AnomalyDetector",
    "AnomalyConfig",
    "Anomaly",
    "MetricTimeSeries",
    "create_detector_from_env",
]

