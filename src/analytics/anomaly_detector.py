"""Anomaly detection for safety metrics."""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class AnomalyType(Enum):
    """Types of anomalies."""
    
    VOLUME_SPIKE = "volume_spike"
    VOLUME_DROP = "volume_drop"
    FLAG_RATE_SPIKE = "flag_rate_spike"
    FLAG_RATE_DROP = "flag_rate_drop"
    LATENCY_SPIKE = "latency_spike"
    ERROR_SPIKE = "error_spike"


class AnomalySeverity(Enum):
    """Severity levels for anomalies."""
    
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Anomaly:
    """Detected anomaly."""
    
    type: AnomalyType
    severity: AnomalySeverity
    metric_name: str
    current_value: float
    expected_value: float
    deviation: float
    threshold: float
    timestamp: float = field(default_factory=time.time)
    tenant_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": self.type.value,
            "severity": self.severity.value,
            "metric_name": self.metric_name,
            "current_value": self.current_value,
            "expected_value": self.expected_value,
            "deviation": self.deviation,
            "threshold": self.threshold,
            "timestamp": self.timestamp,
            "tenant_id": self.tenant_id,
        }
    
    def __str__(self) -> str:
        """String representation."""
        pct_change = ((self.current_value - self.expected_value) / self.expected_value * 100) if self.expected_value > 0 else 0
        
        return (
            f"[{self.severity.value.upper()}] {self.type.value}: "
            f"{self.metric_name}={self.current_value:.2f} "
            f"(expected ~{self.expected_value:.2f}, {pct_change:+.1f}% change, "
            f"{self.deviation:.2f}σ deviation)"
        )


@dataclass
class MetricWindow:
    """Sliding window of metric values."""
    
    name: str
    max_size: int = 60  # Default: 1 hour of 1-minute intervals
    values: deque = field(default_factory=deque)
    
    def add(self, value: float) -> None:
        """Add value to window."""
        if len(self.values) >= self.max_size:
            self.values.popleft()
        
        self.values.append(value)
    
    def mean(self) -> float:
        """Calculate mean."""
        if not self.values:
            return 0.0
        
        return sum(self.values) / len(self.values)
    
    def std(self) -> float:
        """Calculate standard deviation."""
        if len(self.values) < 2:
            return 0.0
        
        mean = self.mean()
        variance = sum((x - mean) ** 2 for x in self.values) / len(self.values)
        
        return variance ** 0.5
    
    def is_ready(self, min_samples: int = 10) -> bool:
        """Check if window has enough samples."""
        return len(self.values) >= min_samples


class AnomalyDetector:
    """Detects anomalies in safety metrics."""
    
    def __init__(
        self,
        window_size: int = 60,
        min_samples: int = 10,
        z_threshold: float = 3.0,
        volume_threshold_multiplier: float = 5.0,
        flag_rate_threshold: float = 0.15,  # 15% absolute change
        latency_threshold_multiplier: float = 3.0,
        error_rate_threshold: float = 0.05,  # 5% absolute change
        check_interval_seconds: float = 60.0,
        cooldown_seconds: float = 300.0,  # 5 minutes
    ):
        """Initialize anomaly detector.
        
        Args:
            window_size: Number of samples in sliding window
            min_samples: Minimum samples before detection
            z_threshold: Z-score threshold for anomaly
            volume_threshold_multiplier: Multiplier for volume spikes
            flag_rate_threshold: Absolute change threshold for flag rate
            latency_threshold_multiplier: Multiplier for latency spikes
            error_rate_threshold: Absolute change threshold for error rate
            check_interval_seconds: Interval between checks
            cooldown_seconds: Cooldown after alerting
        """
        self.window_size = window_size
        self.min_samples = min_samples
        self.z_threshold = z_threshold
        self.volume_threshold_multiplier = volume_threshold_multiplier
        self.flag_rate_threshold = flag_rate_threshold
        self.latency_threshold_multiplier = latency_threshold_multiplier
        self.error_rate_threshold = error_rate_threshold
        self.check_interval_seconds = check_interval_seconds
        self.cooldown_seconds = cooldown_seconds
        
        # Metric windows
        self.windows: Dict[str, MetricWindow] = {}
        
        # Alert callbacks
        self.alert_callbacks: List[Callable[[Anomaly], None]] = []
        
        # Cooldown tracking
        self.last_alert_time: Dict[str, float] = {}
        
        # Background task
        self._monitor_task: Optional[asyncio.Task] = None
        self._running = False
        
        logger.info(
            f"AnomalyDetector initialized: window_size={window_size}, "
            f"z_threshold={z_threshold}, check_interval={check_interval_seconds}s"
        )
    
    def register_alert_callback(self, callback: Callable[[Anomaly], None]) -> None:
        """Register alert callback.
        
        Args:
            callback: Function to call when anomaly detected
        """
        self.alert_callbacks.append(callback)
    
    def track_metric(self, name: str, value: float, tenant_id: Optional[str] = None) -> None:
        """Track a metric value.
        
        Args:
            name: Metric name
            value: Metric value
            tenant_id: Optional tenant ID
        """
        key = f"{tenant_id}:{name}" if tenant_id else name
        
        if key not in self.windows:
            self.windows[key] = MetricWindow(name=key, max_size=self.window_size)
        
        self.windows[key].add(value)
    
    def check_anomalies(self) -> List[Anomaly]:
        """Check all metrics for anomalies.
        
        Returns:
            List of detected anomalies
        """
        anomalies = []
        
        for key, window in self.windows.items():
            if not window.is_ready(self.min_samples):
                continue
            
            # Check if in cooldown
            if key in self.last_alert_time:
                elapsed = time.time() - self.last_alert_time[key]
                if elapsed < self.cooldown_seconds:
                    continue
            
            # Get current and historical values
            current = window.values[-1]
            historical = list(window.values)[:-1]
            
            if not historical:
                continue
            
            mean = sum(historical) / len(historical)
            
            # Calculate std dev
            if len(historical) >= 2:
                variance = sum((x - mean) ** 2 for x in historical) / len(historical)
                std = variance ** 0.5
            else:
                std = 0.0
            
            # Extract tenant_id and metric name
            if ":" in key:
                tenant_id, metric_name = key.split(":", 1)
            else:
                tenant_id = None
                metric_name = key
            
            # Detect anomalies
            detected = self._detect_anomaly(
                metric_name=metric_name,
                current=current,
                mean=mean,
                std=std,
                tenant_id=tenant_id
            )
            
            if detected:
                anomalies.append(detected)
                self.last_alert_time[key] = time.time()
        
        return anomalies
    
    def _detect_anomaly(
        self,
        metric_name: str,
        current: float,
        mean: float,
        std: float,
        tenant_id: Optional[str] = None
    ) -> Optional[Anomaly]:
        """Detect anomaly for a metric.
        
        Args:
            metric_name: Metric name
            current: Current value
            mean: Historical mean
            std: Historical standard deviation
            tenant_id: Optional tenant ID
            
        Returns:
            Anomaly if detected, None otherwise
        """
        # Volume metrics (requests_per_minute)
        if "volume" in metric_name or "requests" in metric_name:
            return self._detect_volume_anomaly(metric_name, current, mean, std, tenant_id)
        
        # Flag rate metrics
        elif "flag_rate" in metric_name:
            return self._detect_flag_rate_anomaly(metric_name, current, mean, tenant_id)
        
        # Latency metrics
        elif "latency" in metric_name:
            return self._detect_latency_anomaly(metric_name, current, mean, std, tenant_id)
        
        # Error rate metrics
        elif "error_rate" in metric_name:
            return self._detect_error_rate_anomaly(metric_name, current, mean, tenant_id)
        
        # Generic z-score detection
        else:
            return self._detect_zscore_anomaly(metric_name, current, mean, std, tenant_id)
    
    def _detect_volume_anomaly(
        self,
        metric_name: str,
        current: float,
        mean: float,
        std: float,
        tenant_id: Optional[str]
    ) -> Optional[Anomaly]:
        """Detect volume anomaly."""
        # Spike
        if current > mean * self.volume_threshold_multiplier and mean > 0:
            severity = self._calculate_severity(current, mean, std)
            
            return Anomaly(
                type=AnomalyType.VOLUME_SPIKE,
                severity=severity,
                metric_name=metric_name,
                current_value=current,
                expected_value=mean,
                deviation=(current - mean) / std if std > 0 else 0,
                threshold=self.volume_threshold_multiplier,
                tenant_id=tenant_id
            )
        
        # Drop (to near zero when normally higher)
        elif current < mean * 0.2 and mean > 10:  # Drop to <20% when mean > 10
            severity = AnomalySeverity.MEDIUM
            
            return Anomaly(
                type=AnomalyType.VOLUME_DROP,
                severity=severity,
                metric_name=metric_name,
                current_value=current,
                expected_value=mean,
                deviation=(mean - current) / std if std > 0 else 0,
                threshold=0.2,
                tenant_id=tenant_id
            )
        
        return None
    
    def _detect_flag_rate_anomaly(
        self,
        metric_name: str,
        current: float,
        mean: float,
        tenant_id: Optional[str]
    ) -> Optional[Anomaly]:
        """Detect flag rate anomaly."""
        # Absolute change
        change = abs(current - mean)
        
        if change > self.flag_rate_threshold:
            if current > mean:
                anomaly_type = AnomalyType.FLAG_RATE_SPIKE
            else:
                anomaly_type = AnomalyType.FLAG_RATE_DROP
            
            # Severity based on magnitude
            if change > 0.3:
                severity = AnomalySeverity.CRITICAL
            elif change > 0.2:
                severity = AnomalySeverity.HIGH
            elif change > 0.15:
                severity = AnomalySeverity.MEDIUM
            else:
                severity = AnomalySeverity.LOW
            
            return Anomaly(
                type=anomaly_type,
                severity=severity,
                metric_name=metric_name,
                current_value=current,
                expected_value=mean,
                deviation=change,
                threshold=self.flag_rate_threshold,
                tenant_id=tenant_id
            )
        
        return None
    
    def _detect_latency_anomaly(
        self,
        metric_name: str,
        current: float,
        mean: float,
        std: float,
        tenant_id: Optional[str]
    ) -> Optional[Anomaly]:
        """Detect latency anomaly."""
        if current > mean * self.latency_threshold_multiplier and mean > 0:
            severity = self._calculate_severity(current, mean, std)
            
            return Anomaly(
                type=AnomalyType.LATENCY_SPIKE,
                severity=severity,
                metric_name=metric_name,
                current_value=current,
                expected_value=mean,
                deviation=(current - mean) / std if std > 0 else 0,
                threshold=self.latency_threshold_multiplier,
                tenant_id=tenant_id
            )
        
        return None
    
    def _detect_error_rate_anomaly(
        self,
        metric_name: str,
        current: float,
        mean: float,
        tenant_id: Optional[str]
    ) -> Optional[Anomaly]:
        """Detect error rate anomaly."""
        change = current - mean
        
        if change > self.error_rate_threshold:
            # Severity based on error rate
            if current > 0.2:
                severity = AnomalySeverity.CRITICAL
            elif current > 0.1:
                severity = AnomalySeverity.HIGH
            elif current > 0.05:
                severity = AnomalySeverity.MEDIUM
            else:
                severity = AnomalySeverity.LOW
            
            return Anomaly(
                type=AnomalyType.ERROR_SPIKE,
                severity=severity,
                metric_name=metric_name,
                current_value=current,
                expected_value=mean,
                deviation=change,
                threshold=self.error_rate_threshold,
                tenant_id=tenant_id
            )
        
        return None
    
    def _detect_zscore_anomaly(
        self,
        metric_name: str,
        current: float,
        mean: float,
        std: float,
        tenant_id: Optional[str]
    ) -> Optional[Anomaly]:
        """Detect anomaly using z-score."""
        if std == 0:
            return None
        
        z_score = abs((current - mean) / std)
        
        if z_score > self.z_threshold:
            severity = self._calculate_severity(current, mean, std)
            
            # Determine type
            if current > mean:
                anomaly_type = AnomalyType.VOLUME_SPIKE
            else:
                anomaly_type = AnomalyType.VOLUME_DROP
            
            return Anomaly(
                type=anomaly_type,
                severity=severity,
                metric_name=metric_name,
                current_value=current,
                expected_value=mean,
                deviation=z_score,
                threshold=self.z_threshold,
                tenant_id=tenant_id
            )
        
        return None
    
    def _calculate_severity(self, current: float, mean: float, std: float) -> AnomalySeverity:
        """Calculate severity based on deviation."""
        if std == 0:
            return AnomalySeverity.MEDIUM
        
        z_score = abs((current - mean) / std)
        
        if z_score > 5:
            return AnomalySeverity.CRITICAL
        elif z_score > 4:
            return AnomalySeverity.HIGH
        elif z_score > 3:
            return AnomalySeverity.MEDIUM
        else:
            return AnomalySeverity.LOW
    
    def _alert(self, anomaly: Anomaly) -> None:
        """Send alert for anomaly.
        
        Args:
            anomaly: Detected anomaly
        """
        logger.warning(f"ANOMALY DETECTED: {anomaly}")
        
        # Call registered callbacks
        for callback in self.alert_callbacks:
            try:
                callback(anomaly)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")
    
    async def start_monitoring(self) -> None:
        """Start background monitoring."""
        if self._running:
            logger.warning("Monitoring already running")
            return
        
        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("Anomaly detection monitoring started")
    
    async def stop_monitoring(self) -> None:
        """Stop background monitoring."""
        if not self._running:
            return
        
        self._running = False
        
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None
        
        logger.info("Anomaly detection monitoring stopped")
    
    async def _monitor_loop(self) -> None:
        """Background monitoring loop."""
        while self._running:
            try:
                await asyncio.sleep(self.check_interval_seconds)
                
                # Check for anomalies
                anomalies = self.check_anomalies()
                
                # Alert
                for anomaly in anomalies:
                    self._alert(anomaly)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")


# Global detector instance
_global_detector: Optional[AnomalyDetector] = None


def get_anomaly_detector() -> AnomalyDetector:
    """Get global anomaly detector instance.
    
    Returns:
        AnomalyDetector instance
    """
    global _global_detector
    
    if _global_detector is None:
        import os
        
        # Load configuration from environment
        window_size = int(os.getenv("ANOMALY_WINDOW_SIZE", "60"))
        z_threshold = float(os.getenv("ANOMALY_Z_THRESHOLD", "3.0"))
        check_interval = float(os.getenv("ANOMALY_CHECK_INTERVAL", "60.0"))
        
        _global_detector = AnomalyDetector(
            window_size=window_size,
            z_threshold=z_threshold,
            check_interval_seconds=check_interval
        )
    
    return _global_detector


__all__ = [
    "AnomalyDetector",
    "Anomaly",
    "AnomalyType",
    "AnomalySeverity",
    "MetricWindow",
    "get_anomaly_detector",
]

