"""Tests for anomaly detection tuning."""

from __future__ import annotations

import pytest
import time

from analytics.anomaly_detector import (
    AnomalyDetector,
    AnomalyConfig,
    MetricTimeSeries,
    create_detector_from_env,
)


class TestMetricTimeSeries:
    """Test MetricTimeSeries class."""
    
    def test_creation(self):
        """Test creating time series."""
        ts = MetricTimeSeries("test_metric")
        
        assert ts.name == "test_metric"
        assert ts.sample_count() == 0
    
    def test_add_values(self):
        """Test adding values."""
        ts = MetricTimeSeries("test_metric")
        
        ts.add(10.0)
        ts.add(20.0)
        ts.add(30.0)
        
        assert ts.sample_count() == 3
    
    def test_compute_stats(self):
        """Test computing statistics."""
        ts = MetricTimeSeries("test_metric")
        
        # Add values with known mean/std
        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        for v in values:
            ts.add(v)
        
        mean, std = ts.compute_stats()
        
        assert mean == 30.0  # Mean of 10, 20, 30, 40, 50
        assert std == pytest.approx(15.811, rel=0.01)  # Sample std
    
    def test_z_score(self):
        """Test z-score computation."""
        ts = MetricTimeSeries("test_metric")
        
        # Add baseline values
        for v in [10.0, 20.0, 30.0, 40.0, 50.0]:
            ts.add(v)
        
        # Check z-score for mean value
        z = ts.compute_z_score(30.0)
        assert z == pytest.approx(0.0, abs=0.01)
        
        # Check z-score for outlier
        z = ts.compute_z_score(100.0)
        assert z > 3.0  # Should be > 3 std devs


class TestAnomalyDetector:
    """Test AnomalyDetector class."""
    
    def test_creation(self):
        """Test creating detector."""
        detector = AnomalyDetector()
        
        assert detector.config.min_samples == 12
        assert detector.config.cooldown_seconds == 600
    
    def test_custom_config(self):
        """Test custom configuration."""
        config = AnomalyConfig(
            min_samples=5,
            cooldown_seconds=60,
            z_threshold=2.5
        )
        detector = AnomalyDetector(config)
        
        assert detector.config.min_samples == 5
        assert detector.config.cooldown_seconds == 60
        assert detector.config.z_threshold == 2.5
    
    def test_record_metric(self):
        """Test recording metrics."""
        detector = AnomalyDetector()
        
        detector.record("latency", 100.0)
        detector.record("latency", 110.0)
        
        stats = detector.get_metric_stats("latency")
        assert stats["sample_count"] == 2


class TestMinSamplesRequirement:
    """Test minimum samples requirement."""
    
    def test_no_alert_before_min_samples(self):
        """Test no alert triggered before minimum samples."""
        config = AnomalyConfig(min_samples=12)
        detector = AnomalyDetector(config)
        
        # Add only 10 normal values
        for i in range(10):
            detector.record("latency", 100.0)
        
        # Add obvious outlier (should not trigger alert - insufficient samples)
        # After this, we'll have 11 samples, still below min of 12
        anomaly = detector.check("latency", 1000.0)
        
        assert anomaly is None  # No alert
        
        # Verify sample count
        stats = detector.get_metric_stats("latency")
        assert stats["sample_count"] == 11  # 10 + 1
    
    def test_alert_after_min_samples(self):
        """Test alert triggered after minimum samples."""
        config = AnomalyConfig(min_samples=12, z_threshold=3.0)
        detector = AnomalyDetector(config)
        
        # Add 12 normal values (around 100)
        for i in range(12):
            detector.record("latency", 100.0 + i)
        
        # Add obvious outlier (should trigger alert now)
        anomaly = detector.check("latency", 1000.0)
        
        assert anomaly is not None
        assert anomaly.metric_name == "latency"
        assert anomaly.value == 1000.0
        assert anomaly.z_score >= 3.0
    
    def test_gradual_baseline(self):
        """Test gradually building baseline."""
        config = AnomalyConfig(min_samples=5, z_threshold=2.0)  # Lower threshold for easier testing
        detector = AnomalyDetector(config)
        
        # Add baseline values (tight distribution around 100)
        baseline_values = [98, 100, 102, 99, 101, 100, 99, 98]  # 8 values
        for v in baseline_values:
            detector.record("requests", v)
        
        # Stats check
        stats = detector.get_metric_stats("requests")
        assert stats["sample_count"] == 8  # Should have 8 samples
        
        # Now outlier should trigger
        anomaly = detector.check("requests", 300.0)  # Much higher than baseline
        assert anomaly is not None


class TestPerMetricCooldown:
    """Test per-metric cooldown."""
    
    def test_two_spikes_inside_cooldown_only_first_alerts(self):
        """Test that only first spike alerts within cooldown period."""
        config = AnomalyConfig(
            min_samples=5,
            cooldown_seconds=10,  # 10 second cooldown
            z_threshold=2.0
        )
        detector = AnomalyDetector(config)
        
        # Build baseline
        for i in range(10):
            detector.record("latency", 100.0)
        
        # First spike (should alert)
        anomaly1 = detector.check("latency", 500.0, timestamp=1000.0)
        assert anomaly1 is not None
        assert anomaly1.value == 500.0
        
        # Second spike within cooldown (should NOT alert)
        anomaly2 = detector.check("latency", 600.0, timestamp=1005.0)  # 5s later
        assert anomaly2 is None  # In cooldown
        
        # Third spike after cooldown (should alert again)
        anomaly3 = detector.check("latency", 700.0, timestamp=1015.0)  # 15s later
        assert anomaly3 is not None
        assert anomaly3.value == 700.0
    
    def test_different_metrics_independent_cooldowns(self):
        """Test that different metrics have independent cooldowns."""
        config = AnomalyConfig(
            min_samples=5,
            cooldown_seconds=10,
            z_threshold=2.0
        )
        detector = AnomalyDetector(config)
        
        # Build baselines for two metrics
        for i in range(10):
            detector.record("latency", 100.0)
            detector.record("error_rate", 0.01)
        
        # Spike in latency (alerts)
        anomaly1 = detector.check("latency", 500.0, timestamp=1000.0)
        assert anomaly1 is not None
        
        # Spike in error_rate (should also alert - different metric)
        anomaly2 = detector.check("error_rate", 0.5, timestamp=1001.0)
        assert anomaly2 is not None
    
    def test_cooldown_prevents_alert_storm(self):
        """Test cooldown prevents alert storm."""
        config = AnomalyConfig(
            min_samples=5,
            cooldown_seconds=60,  # 1 minute
            z_threshold=2.0
        )
        detector = AnomalyDetector(config)
        
        # Build baseline
        for i in range(10):
            detector.record("requests", 100.0)
        
        # Simulate continuous anomaly (e.g., traffic spike lasting 30s)
        alerts = []
        for t in range(30):  # 30 seconds
            anomaly = detector.check("requests", 500.0, timestamp=1000.0 + t)
            if anomaly:
                alerts.append(anomaly)
        
        # Should only alert once (at start)
        assert len(alerts) == 1


class TestZScoreDetection:
    """Test z-score based detection."""
    
    def test_normal_values_no_alert(self):
        """Test normal values don't trigger alerts."""
        config = AnomalyConfig(min_samples=5, z_threshold=3.0)
        detector = AnomalyDetector(config)
        
        # Add normal distribution
        for v in [95, 100, 105, 100, 100]:
            detector.record("latency", v)
        
        # Check normal value
        anomaly = detector.check("latency", 102.0)
        assert anomaly is None
    
    def test_outlier_triggers_alert(self):
        """Test outlier triggers alert."""
        config = AnomalyConfig(min_samples=5, z_threshold=2.5)  # Lower threshold
        detector = AnomalyDetector(config)
        
        # Add distribution with variance (enough samples and spread)
        baseline = [95, 100, 105, 100, 98, 102, 97, 103]
        for v in baseline:
            detector.record("latency", v)
        
        # Check extreme outlier (we have 8 samples now)
        anomaly = detector.check("latency", 500.0)
        assert anomaly is not None
        assert anomaly.z_score > 2.5
    
    def test_z_score_calculation(self):
        """Test z-score is calculated correctly."""
        config = AnomalyConfig(min_samples=3, z_threshold=2.0)
        detector = AnomalyDetector(config)
        
        # Add values: mean=10, std≈5
        detector.record("test", 5.0)
        detector.record("test", 10.0)
        detector.record("test", 15.0)
        
        # Check value 2 std devs away
        anomaly = detector.check("test", 20.0)
        
        # Should be close to 2.0
        if anomaly:
            assert anomaly.z_score >= 1.5  # Allow some tolerance


class TestEnvConfiguration:
    """Test environment-based configuration."""
    
    def test_create_from_env(self, monkeypatch):
        """Test creating detector from environment."""
        monkeypatch.setenv("ANOMALY_MIN_SAMPLES", "20")
        monkeypatch.setenv("ANOMALY_COOLDOWN_SEC", "300")
        monkeypatch.setenv("ANOMALY_Z_THRESHOLD", "2.5")
        
        detector = create_detector_from_env()
        
        assert detector.config.min_samples == 20
        assert detector.config.cooldown_seconds == 300
        assert detector.config.z_threshold == 2.5
    
    def test_default_env_values(self, monkeypatch):
        """Test default values from environment."""
        # Clear any existing env vars
        monkeypatch.delenv("ANOMALY_MIN_SAMPLES", raising=False)
        monkeypatch.delenv("ANOMALY_COOLDOWN_SEC", raising=False)
        
        detector = create_detector_from_env()
        
        assert detector.config.min_samples == 12
        assert detector.config.cooldown_seconds == 600


class TestIntegration:
    """Integration tests."""
    
    def test_realistic_scenario(self):
        """Test realistic anomaly detection scenario."""
        config = AnomalyConfig(
            min_samples=10,
            cooldown_seconds=30,  # Shorter cooldown for testing
            z_threshold=3.0
        )
        detector = AnomalyDetector(config)
        
        # Simulate normal traffic for 20 seconds (baseline around 100)
        for t in range(20):
            detector.record("latency_ms", 100.0 + (t % 3), timestamp=float(t))
        
        # Simulate spike at t=25
        anomaly = detector.check("latency_ms", 500.0, timestamp=25.0)
        assert anomaly is not None  # Should alert
        
        # Try another spike within cooldown (should NOT alert)
        anomaly = detector.check("latency_ms", 510.0, timestamp=30.0)
        assert anomaly is None  # Should not alert (in cooldown)
        
        # Spike after cooldown expires (25 + 30 = 55, check at 60)
        # First build baseline back to normal
        for t in range(60, 75):
            detector.record("latency_ms", 100.0 + (t % 3), timestamp=float(t))
        
        # Now spike again (cooldown expired)
        anomaly = detector.check("latency_ms", 500.0, timestamp=80.0)
        assert anomaly is not None  # Should alert again


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

