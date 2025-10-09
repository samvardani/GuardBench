"""Unit tests for monitoring system."""

from __future__ import annotations

import time
import pytest
from unittest.mock import MagicMock, patch

from seval.monitoring.metrics import MetricsCollector, get_global_collector
from seval.monitoring.alerts import SlackAlerter


def test_metrics_collector_initialization():
    """Test MetricsCollector initializes correctly."""
    collector = MetricsCollector(window_minutes=15)
    assert collector.window_seconds == 900
    assert len(collector._snapshots) == 0


def test_metrics_collector_record_request():
    """Test recording a request."""
    collector = MetricsCollector(window_minutes=15)
    
    collector.record_request(
        category="violence",
        language="en",
        score=3.5,
        blocked=True,
        latency_ms=10
    )
    
    snapshots = collector.get_recent_snapshots()
    assert len(snapshots) == 1
    assert snapshots[0].category == "violence"
    assert snapshots[0].score == 3.5
    assert snapshots[0].blocked is True


def test_metrics_collector_summary_empty():
    """Test summary with no snapshots."""
    collector = MetricsCollector(window_minutes=15)
    
    summary = collector.get_summary()
    
    assert summary["total_requests"] == 0
    assert summary["qps"] == 0.0
    assert summary["blocked_count"] == 0


def test_metrics_collector_summary_with_data():
    """Test summary with data."""
    collector = MetricsCollector(window_minutes=15)
    
    # Record some requests
    for i in range(10):
        collector.record_request(
            category="violence",
            language="en",
            score=float(i),
            blocked=i % 2 == 0,
            latency_ms=i * 10
        )
    
    time.sleep(0.1)  # Ensure time span
    
    summary = collector.get_summary()
    
    assert summary["total_requests"] == 10
    assert summary["qps"] > 0
    assert summary["blocked_count"] == 5
    assert summary["blocked_rate"] == 0.5
    assert summary["latency_p50"] > 0
    assert summary["latency_p95"] > 0


def test_metrics_collector_percentiles():
    """Test percentile calculations."""
    collector = MetricsCollector(window_minutes=15)
    
    # Record requests with known latencies
    latencies = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    for lat in latencies:
        collector.record_request(
            category="test",
            language="en",
            score=1.0,
            blocked=False,
            latency_ms=lat
        )
    
    summary = collector.get_summary()
    
    # P50 should be around 50-55
    assert 45 <= summary["latency_p50"] <= 60
    # P95 should be around 95-100
    assert 90 <= summary["latency_p95"] <= 100


def test_metrics_collector_category_breakdown():
    """Test category breakdown in summary."""
    collector = MetricsCollector(window_minutes=15)
    
    # Record requests for different categories
    collector.record_request("violence", "en", 3.0, True, 10)
    collector.record_request("violence", "en", 2.0, False, 15)
    collector.record_request("self_harm", "en", 4.0, True, 20)
    
    summary = collector.get_summary()
    
    assert "violence" in summary["categories"]
    assert "self_harm" in summary["categories"]
    
    violence_stats = summary["categories"]["violence"]
    assert violence_stats["count"] == 2
    assert violence_stats["blocked"] == 1
    assert violence_stats["blocked_rate"] == 0.5


def test_metrics_collector_window_cleanup():
    """Test old snapshots are cleaned up."""
    collector = MetricsCollector(window_minutes=0.01)  # 0.6 seconds
    
    collector.record_request("test", "en", 1.0, False, 10)
    time.sleep(1)  # Wait for snapshot to be outside window
    
    snapshots = collector.get_recent_snapshots()
    assert len(snapshots) == 0


def test_global_collector_singleton():
    """Test global collector is a singleton."""
    collector1 = get_global_collector()
    collector2 = get_global_collector()
    
    assert collector1 is collector2


def test_slack_alerter_no_webhook():
    """Test SlackAlerter without webhook configured."""
    with patch.dict("os.environ", {}, clear=True):
        alerter = SlackAlerter()
        
        result = alerter.send_alert(
            "violence",
            "Test alert",
            {"count": 10}
        )
        
        assert result is False


def test_slack_alerter_with_webhook():
    """Test SlackAlerter with mock webhook."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    
    with patch("seval.monitoring.alerts.httpx.post", return_value=mock_response):
        alerter = SlackAlerter(webhook_url="https://hooks.slack.com/test")
        
        result = alerter.send_alert(
            "violence",
            "Test alert",
            {"count": 10}
        )
        
        assert result is True


def test_slack_alerter_cooldown():
    """Test SlackAlerter cooldown prevents duplicate alerts."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    
    with patch("seval.monitoring.alerts.httpx.post", return_value=mock_response) as mock_post:
        alerter = SlackAlerter(webhook_url="https://hooks.slack.com/test", cooldown_seconds=10)
        
        # First alert should send
        result1 = alerter.send_alert("violence", "Alert 1")
        assert result1 is True
        
        # Second alert within cooldown should not send
        result2 = alerter.send_alert("violence", "Alert 2")
        assert result2 is False
        
        # Only one POST call should be made
        assert mock_post.call_count == 1


def test_slack_alerter_check_thresholds():
    """Test SlackAlerter threshold checking."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    
    summary = {
        "total_requests": 100,
        "blocked_count": 60,
        "blocked_rate": 0.6,
        "qps": 10.0,
        "categories": {
            "violence": {
                "count": 50,
                "blocked": 40,
                "blocked_rate": 0.8,
                "avg_score": 4.0
            }
        }
    }
    
    thresholds = {
        "blocked_rate": 0.5,
        "violence_blocked_rate": 0.7
    }
    
    with patch("seval.monitoring.alerts.httpx.post", return_value=mock_response) as mock_post:
        alerter = SlackAlerter(webhook_url="https://hooks.slack.com/test")
        alerter.check_thresholds(summary, thresholds)
        
        # Should send 2 alerts: overall + violence category
        assert mock_post.call_count == 2


def test_slack_alerter_webhook_failure():
    """Test SlackAlerter handles webhook failures gracefully."""
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    
    with patch("seval.monitoring.alerts.httpx.post", return_value=mock_response):
        alerter = SlackAlerter(webhook_url="https://hooks.slack.com/test")
        
        result = alerter.send_alert("test", "Alert")
        assert result is False


def test_metrics_collector_with_prometheus():
    """Test MetricsCollector works with Prometheus."""
    from seval.monitoring.metrics import PROMETHEUS_AVAILABLE
    
    collector = MetricsCollector()
    
    # Should work regardless of Prometheus availability
    collector.record_request(
        category="test",
        language="en",
        score=2.0,
        blocked=False,
        latency_ms=10
    )
    
    summary = collector.get_summary()
    assert summary["total_requests"] == 1


def test_metrics_collector_concurrent_access():
    """Test MetricsCollector handles concurrent access."""
    import concurrent.futures
    
    collector = MetricsCollector()
    
    def record_metric(i):
        collector.record_request(
            category="test",
            language="en",
            score=float(i),
            blocked=False,
            latency_ms=i
        )
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(record_metric, i) for i in range(100)]
        for future in concurrent.futures.as_completed(futures):
            future.result()
    
    summary = collector.get_summary()
    assert summary["total_requests"] == 100


def test_metrics_collector_large_window():
    """Test MetricsCollector with large window."""
    collector = MetricsCollector(window_minutes=60)
    
    for i in range(100):
        collector.record_request("test", "en", 1.0, False, 10)
    
    summary = collector.get_summary()
    assert summary["total_requests"] == 100


def test_slack_alerter_different_categories():
    """Test SlackAlerter handles different categories independently."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    
    with patch("seval.monitoring.alerts.httpx.post", return_value=mock_response) as mock_post:
        alerter = SlackAlerter(webhook_url="https://hooks.slack.com/test", cooldown_seconds=10)
        
        # Alert for violence
        alerter.send_alert("violence", "Alert 1")
        # Alert for self_harm (should work, different category)
        alerter.send_alert("self_harm", "Alert 2")
        
        # Both should send
        assert mock_post.call_count == 2

