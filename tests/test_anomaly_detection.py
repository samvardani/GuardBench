"""Tests for anomaly detection system."""

from __future__ import annotations

import asyncio
import pytest
import time
from unittest.mock import Mock, MagicMock

from analytics import (
    AnomalyDetector,
    Anomaly,
    AnomalyType,
    AnomalySeverity,
    MetricWindow,
    AlertSystem
)


class TestMetricWindow:
    """Test MetricWindow."""
    
    def test_window_creation(self):
        """Test creating metric window."""
        window = MetricWindow(name="test", max_size=10)
        
        assert window.name == "test"
        assert window.max_size == 10
        assert len(window.values) == 0
    
    def test_add_values(self):
        """Test adding values to window."""
        window = MetricWindow(name="test", max_size=5)
        
        for i in range(3):
            window.add(float(i))
        
        assert len(window.values) == 3
        assert list(window.values) == [0.0, 1.0, 2.0]
    
    def test_window_overflow(self):
        """Test window overflow (FIFO)."""
        window = MetricWindow(name="test", max_size=3)
        
        for i in range(5):
            window.add(float(i))
        
        # Should keep last 3
        assert len(window.values) == 3
        assert list(window.values) == [2.0, 3.0, 4.0]
    
    def test_mean(self):
        """Test mean calculation."""
        window = MetricWindow(name="test")
        
        window.add(10.0)
        window.add(20.0)
        window.add(30.0)
        
        assert window.mean() == 20.0
    
    def test_std(self):
        """Test standard deviation calculation."""
        window = MetricWindow(name="test")
        
        # Add values: 10, 20, 30
        window.add(10.0)
        window.add(20.0)
        window.add(30.0)
        
        std = window.std()
        
        # Std dev of [10, 20, 30] = 8.165
        assert 8.0 < std < 8.5
    
    def test_is_ready(self):
        """Test ready check."""
        window = MetricWindow(name="test")
        
        assert not window.is_ready(min_samples=5)
        
        for i in range(5):
            window.add(float(i))
        
        assert window.is_ready(min_samples=5)


class TestAnomaly:
    """Test Anomaly dataclass."""
    
    def test_anomaly_creation(self):
        """Test creating anomaly."""
        anomaly = Anomaly(
            type=AnomalyType.VOLUME_SPIKE,
            severity=AnomalySeverity.HIGH,
            metric_name="requests_per_minute",
            current_value=500.0,
            expected_value=100.0,
            deviation=5.0,
            threshold=3.0
        )
        
        assert anomaly.type == AnomalyType.VOLUME_SPIKE
        assert anomaly.severity == AnomalySeverity.HIGH
        assert anomaly.current_value == 500.0
    
    def test_anomaly_to_dict(self):
        """Test converting anomaly to dict."""
        anomaly = Anomaly(
            type=AnomalyType.FLAG_RATE_SPIKE,
            severity=AnomalySeverity.MEDIUM,
            metric_name="flag_rate",
            current_value=0.3,
            expected_value=0.05,
            deviation=0.25,
            threshold=0.15
        )
        
        data = anomaly.to_dict()
        
        assert data["type"] == "flag_rate_spike"
        assert data["severity"] == "medium"
        assert data["current_value"] == 0.3
    
    def test_anomaly_str(self):
        """Test string representation."""
        anomaly = Anomaly(
            type=AnomalyType.VOLUME_SPIKE,
            severity=AnomalySeverity.HIGH,
            metric_name="requests",
            current_value=1000.0,
            expected_value=100.0,
            deviation=5.0,
            threshold=3.0
        )
        
        s = str(anomaly)
        
        assert "HIGH" in s
        assert "volume_spike" in s
        assert "1000.00" in s


class TestAnomalyDetector:
    """Test AnomalyDetector."""
    
    @pytest.fixture
    def detector(self):
        """Create detector for testing."""
        return AnomalyDetector(
            window_size=20,
            min_samples=5,
            z_threshold=3.0,
            check_interval_seconds=1.0,
            cooldown_seconds=5.0
        )
    
    def test_detector_creation(self, detector):
        """Test creating detector."""
        assert detector.window_size == 20
        assert detector.min_samples == 5
        assert detector.z_threshold == 3.0
    
    def test_track_metric(self, detector):
        """Test tracking metrics."""
        detector.track_metric("requests", 100.0)
        detector.track_metric("requests", 110.0)
        
        assert "requests" in detector.windows
        assert len(detector.windows["requests"].values) == 2
    
    def test_track_metric_with_tenant(self, detector):
        """Test tracking with tenant ID."""
        detector.track_metric("requests", 100.0, tenant_id="tenant-1")
        detector.track_metric("requests", 200.0, tenant_id="tenant-2")
        
        assert "tenant-1:requests" in detector.windows
        assert "tenant-2:requests" in detector.windows
    
    def test_volume_spike_detection(self, detector):
        """Test detecting volume spike."""
        # Establish baseline: 100 requests
        for _ in range(10):
            detector.track_metric("requests_volume", 100.0)
        
        # Spike to 600 (6x)
        detector.track_metric("requests_volume", 600.0)
        
        # Check anomalies
        anomalies = detector.check_anomalies()
        
        assert len(anomalies) == 1
        assert anomalies[0].type == AnomalyType.VOLUME_SPIKE
        assert anomalies[0].current_value == 600.0
    
    def test_volume_drop_detection(self, detector):
        """Test detecting volume drop."""
        # Establish baseline: 100 requests
        for _ in range(10):
            detector.track_metric("requests_volume", 100.0)
        
        # Drop to 10 (<20%)
        detector.track_metric("requests_volume", 10.0)
        
        # Check anomalies
        anomalies = detector.check_anomalies()
        
        assert len(anomalies) == 1
        assert anomalies[0].type == AnomalyType.VOLUME_DROP
    
    def test_flag_rate_spike_detection(self, detector):
        """Test detecting flag rate spike."""
        # Establish baseline: 5% flag rate
        for _ in range(10):
            detector.track_metric("flag_rate", 0.05)
        
        # Spike to 35%
        detector.track_metric("flag_rate", 0.35)
        
        # Check anomalies
        anomalies = detector.check_anomalies()
        
        assert len(anomalies) == 1
        assert anomalies[0].type == AnomalyType.FLAG_RATE_SPIKE
        assert anomalies[0].current_value == 0.35
    
    def test_flag_rate_drop_detection(self, detector):
        """Test detecting flag rate drop."""
        # Establish baseline: 30% flag rate
        for _ in range(10):
            detector.track_metric("flag_rate", 0.30)
        
        # Drop to 5% (sudden)
        detector.track_metric("flag_rate", 0.05)
        
        # Check anomalies
        anomalies = detector.check_anomalies()
        
        assert len(anomalies) == 1
        assert anomalies[0].type == AnomalyType.FLAG_RATE_DROP
    
    def test_latency_spike_detection(self, detector):
        """Test detecting latency spike."""
        # Baseline: 100ms
        for _ in range(10):
            detector.track_metric("latency_avg", 100.0)
        
        # Spike to 500ms (5x)
        detector.track_metric("latency_avg", 500.0)
        
        # Check anomalies
        anomalies = detector.check_anomalies()
        
        assert len(anomalies) == 1
        assert anomalies[0].type == AnomalyType.LATENCY_SPIKE
    
    def test_error_rate_spike_detection(self, detector):
        """Test detecting error rate spike."""
        # Baseline: 1% error rate
        for _ in range(10):
            detector.track_metric("error_rate", 0.01)
        
        # Spike to 15%
        detector.track_metric("error_rate", 0.15)
        
        # Check anomalies
        anomalies = detector.check_anomalies()
        
        assert len(anomalies) == 1
        assert anomalies[0].type == AnomalyType.ERROR_SPIKE
    
    def test_no_anomaly_with_normal_variation(self, detector):
        """Test no false positives with normal variation."""
        # Track normal variation: 95-105
        import random
        random.seed(42)
        
        for _ in range(15):
            value = 100.0 + random.uniform(-5, 5)
            detector.track_metric("requests_volume", value)
        
        # Should not detect anomaly
        anomalies = detector.check_anomalies()
        
        assert len(anomalies) == 0
    
    def test_cooldown_period(self, detector):
        """Test cooldown prevents repeated alerts."""
        # Trigger anomaly
        for _ in range(10):
            detector.track_metric("requests_volume", 100.0)
        
        detector.track_metric("requests_volume", 600.0)
        
        # First check
        anomalies1 = detector.check_anomalies()
        assert len(anomalies1) == 1
        
        # Immediate second check (in cooldown)
        detector.track_metric("requests_volume", 650.0)
        anomalies2 = detector.check_anomalies()
        assert len(anomalies2) == 0  # Still in cooldown
    
    def test_min_samples_requirement(self, detector):
        """Test minimum samples requirement."""
        # Only add 3 samples (below min_samples=5)
        for i in range(3):
            detector.track_metric("requests_volume", 100.0)
        
        # Add spike
        detector.track_metric("requests_volume", 600.0)
        
        # Should not detect (not enough samples)
        anomalies = detector.check_anomalies()
        assert len(anomalies) == 0
    
    def test_alert_callback(self, detector):
        """Test alert callbacks are invoked."""
        callback = Mock()
        detector.register_alert_callback(callback)
        
        # Trigger anomaly
        for _ in range(10):
            detector.track_metric("requests_volume", 100.0)
        
        detector.track_metric("requests_volume", 600.0)
        
        # Check (should invoke callback internally)
        anomalies = detector.check_anomalies()
        
        # Manually alert (since check_anomalies doesn't call _alert)
        for anomaly in anomalies:
            detector._alert(anomaly)
        
        # Verify callback was called
        assert callback.called
        assert isinstance(callback.call_args[0][0], Anomaly)
    
    @pytest.mark.asyncio
    async def test_monitoring_loop(self, detector):
        """Test background monitoring loop."""
        # Track metrics
        for _ in range(10):
            detector.track_metric("requests_volume", 100.0)
        
        # Add spike
        detector.track_metric("requests_volume", 600.0)
        
        # Start monitoring
        await detector.start_monitoring()
        
        # Wait for one check cycle
        await asyncio.sleep(1.5)
        
        # Stop monitoring
        await detector.stop_monitoring()
        
        # Verify monitoring ran
        assert detector._running is False


class TestAlertSystem:
    """Test AlertSystem."""
    
    def test_alert_system_creation(self):
        """Test creating alert system."""
        alert_system = AlertSystem(
            slack_webhook_url="https://hooks.slack.com/test",
            email_enabled=True,
            log_enabled=True
        )
        
        assert alert_system.slack_webhook_url is not None
        assert alert_system.email_enabled is True
        assert alert_system.log_enabled is True
    
    def test_log_alert(self):
        """Test log alert."""
        alert_system = AlertSystem(log_enabled=True)
        
        anomaly = Anomaly(
            type=AnomalyType.VOLUME_SPIKE,
            severity=AnomalySeverity.HIGH,
            metric_name="requests",
            current_value=500.0,
            expected_value=100.0,
            deviation=5.0,
            threshold=3.0
        )
        
        # Should not raise
        alert_system.send_alert(anomaly)
    
    def test_alert_color_mapping(self):
        """Test severity to color mapping."""
        alert_system = AlertSystem()
        
        assert alert_system._get_alert_color("low") == "#36a64f"
        assert alert_system._get_alert_color("medium") == "#ff9900"
        assert alert_system._get_alert_color("high") == "#ff0000"
        assert alert_system._get_alert_color("critical") == "#8b0000"


class TestIntegration:
    """Integration tests."""
    
    def test_end_to_end_detection_and_alert(self):
        """Test full detection and alert flow."""
        # Create detector
        detector = AnomalyDetector(
            window_size=20,
            min_samples=5,
            check_interval_seconds=1.0
        )
        
        # Create alert system
        alert_system = AlertSystem(log_enabled=True)
        
        # Register callback
        detector.register_alert_callback(alert_system.send_alert)
        
        # Establish baseline
        for _ in range(10):
            detector.track_metric("requests_volume", 100.0)
        
        # Trigger spike
        detector.track_metric("requests_volume", 600.0)
        
        # Check and alert
        anomalies = detector.check_anomalies()
        
        assert len(anomalies) == 1
        
        # Send alert
        for anomaly in anomalies:
            detector._alert(anomaly)
        
        # Verify (would show in logs)
    
    def test_multiple_metric_types(self):
        """Test monitoring multiple metric types."""
        detector = AnomalyDetector(min_samples=5)
        
        # Track multiple metrics
        for i in range(10):
            detector.track_metric("requests_volume", 100.0)
            detector.track_metric("flag_rate", 0.05)
            detector.track_metric("latency_avg", 150.0)
        
        # Trigger anomalies in different metrics
        detector.track_metric("requests_volume", 600.0)  # Volume spike
        detector.track_metric("flag_rate", 0.35)  # Flag rate spike
        detector.track_metric("latency_avg", 600.0)  # Latency spike
        
        # Check
        anomalies = detector.check_anomalies()
        
        # Should detect all three
        assert len(anomalies) == 3
        
        types = {a.type for a in anomalies}
        assert AnomalyType.VOLUME_SPIKE in types
        assert AnomalyType.FLAG_RATE_SPIKE in types
        assert AnomalyType.LATENCY_SPIKE in types


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

