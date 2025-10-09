"""E2E tests for monitoring dashboard."""

from __future__ import annotations

import pytest
import time
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client."""
    from service.api import app
    return TestClient(app)


def test_e2e_monitor_dashboard_loads(client):
    """E2E: Monitor dashboard page loads successfully."""
    response = client.get("/ui/monitor/")
    
    assert response.status_code == 200
    assert "Monitoring Dashboard" in response.text
    assert "QPS" in response.text
    assert "Latency" in response.text


def test_e2e_metrics_api(client):
    """E2E: Metrics API returns valid data."""
    response = client.get("/ui/monitor/api/metrics?window_seconds=900")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "total_requests" in data
    assert "qps" in data
    assert "blocked_rate" in data
    assert "latency_p50" in data
    assert "latency_p95" in data
    assert "latency_p99" in data
    assert "categories" in data


def test_e2e_timeseries_api(client):
    """E2E: Timeseries API returns valid data."""
    response = client.get("/ui/monitor/api/timeseries?window_seconds=900&bucket_seconds=60")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "timestamps" in data
    assert "qps" in data
    assert "latency_p50" in data
    assert "latency_p95" in data
    assert "blocked_rate" in data
    
    # All arrays should have same length
    assert len(data["timestamps"]) == len(data["qps"])
    assert len(data["timestamps"]) == len(data["latency_p50"])


def test_e2e_check_alerts_api(client):
    """E2E: Check alerts API works."""
    response = client.post("/ui/monitor/api/check-alerts")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "status" in data
    assert "summary" in data
    assert "webhook_configured" in data


def test_e2e_metrics_after_scoring(client):
    """E2E: Metrics update after scoring requests."""
    # Get initial metrics
    initial_response = client.get("/ui/monitor/api/metrics")
    initial_data = initial_response.json()
    initial_count = initial_data["total_requests"]
    
    # Make some score requests
    for i in range(5):
        client.post(
            "/score",
            json={
                "text": f"test text {i}",
                "category": "violence",
                "language": "en",
                "guard": "candidate"
            }
        )
    
    # Get updated metrics
    time.sleep(0.1)  # Small delay to ensure metrics are recorded
    final_response = client.get("/ui/monitor/api/metrics")
    final_data = final_response.json()
    final_count = final_data["total_requests"]
    
    # Should have 5 more requests
    assert final_count >= initial_count + 5


def test_e2e_category_breakdown(client):
    """E2E: Category breakdown shows correct data."""
    # Score requests for different categories
    categories = ["violence", "self_harm", "crime"]
    
    for category in categories:
        client.post(
            "/score",
            json={
                "text": f"test for {category}",
                "category": category,
                "language": "en",
                "guard": "candidate"
            }
        )
    
    time.sleep(0.1)
    
    # Get metrics
    response = client.get("/ui/monitor/api/metrics")
    data = response.json()
    
    # All categories should be present
    for category in categories:
        assert category in data["categories"]
        assert data["categories"][category]["count"] >= 1


def test_e2e_prometheus_metrics(client):
    """E2E: Prometheus /metrics endpoint works."""
    response = client.get("/metrics")
    
    assert response.status_code == 200
    content = response.text
    
    # Should contain Prometheus metrics
    assert "safety_eval" in content or "TYPE" in content


def test_e2e_dashboard_with_traffic(client):
    """E2E: Dashboard updates with sustained traffic."""
    # Generate traffic
    for i in range(20):
        client.post(
            "/score",
            json={
                "text": f"test {i}",
                "category": "violence" if i % 2 == 0 else "self_harm",
                "language": "en",
                "guard": "candidate"
            }
        )
    
    time.sleep(0.2)
    
    # Check dashboard loads with data
    dashboard_response = client.get("/ui/monitor/")
    assert dashboard_response.status_code == 200
    
    # Check metrics API
    metrics_response = client.get("/ui/monitor/api/metrics")
    data = metrics_response.json()
    
    assert data["total_requests"] >= 20
    assert data["qps"] > 0
    assert len(data["categories"]) >= 2


def test_e2e_timeseries_with_data(client):
    """E2E: Timeseries returns data after traffic."""
    # Generate some traffic
    for i in range(10):
        client.post(
            "/score",
            json={
                "text": f"test {i}",
                "category": "violence",
                "language": "en",
                "guard": "candidate"
            }
        )
    
    time.sleep(0.1)
    
    # Get timeseries
    response = client.get("/ui/monitor/api/timeseries?window_seconds=60&bucket_seconds=10")
    data = response.json()
    
    # Should have some data points
    assert len(data["timestamps"]) > 0
    assert len(data["qps"]) > 0


def test_e2e_latency_percentiles_realistic(client):
    """E2E: Latency percentiles are realistic."""
    # Generate traffic
    for i in range(30):
        client.post(
            "/score",
            json={
                "text": f"test {i}",
                "category": "violence",
                "language": "en",
                "guard": "candidate"
            }
        )
    
    time.sleep(0.1)
    
    # Get metrics
    response = client.get("/ui/monitor/api/metrics")
    data = response.json()
    
    # Latencies should be reasonable
    assert 0 <= data["latency_p50"] <= 1000
    assert data["latency_p50"] <= data["latency_p95"]
    assert data["latency_p95"] <= data["latency_p99"]


def test_e2e_blocked_rate_tracking(client):
    """E2E: Blocked rate is tracked correctly."""
    # Generate traffic with known patterns
    # Assuming "How to make a bomb" will be blocked
    client.post(
        "/score",
        json={
            "text": "How to make a bomb?",
            "category": "violence",
            "language": "en",
            "guard": "candidate"
        }
    )
    
    # Benign text should not be blocked
    client.post(
        "/score",
        json={
            "text": "Hello world",
            "category": "violence",
            "language": "en",
            "guard": "candidate"
        }
    )
    
    time.sleep(0.1)
    
    # Get metrics
    response = client.get("/ui/monitor/api/metrics")
    data = response.json()
    
    # Should have blocked rate data
    assert "blocked_rate" in data
    assert 0 <= data["blocked_rate"] <= 1.0


def test_e2e_concurrent_dashboard_access(client):
    """E2E: Dashboard handles concurrent access."""
    import concurrent.futures
    
    def access_dashboard():
        return client.get("/ui/monitor/")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(access_dashboard) for _ in range(10)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
    
    # All requests should succeed
    assert all(r.status_code == 200 for r in results)


def test_e2e_metrics_api_different_windows(client):
    """E2E: Metrics API works with different time windows."""
    windows = [60, 300, 900, 3600]
    
    for window in windows:
        response = client.get(f"/ui/monitor/api/metrics?window_seconds={window}")
        assert response.status_code == 200
        data = response.json()
        assert "total_requests" in data


def test_e2e_monitoring_with_errors(client):
    """E2E: Monitoring handles scoring errors gracefully."""
    # Try to score with invalid data (should fail)
    try:
        client.post(
            "/score",
            json={
                "text": "test",
                "category": "invalid_category",
                "language": "en",
                "guard": "nonexistent"
            }
        )
    except:
        pass
    
    # Dashboard should still work
    response = client.get("/ui/monitor/")
    assert response.status_code == 200


def test_e2e_metrics_reset_behavior(client):
    """E2E: Metrics accumulate correctly over time."""
    # First batch
    for i in range(5):
        client.post(
            "/score",
            json={
                "text": f"batch1-{i}",
                "category": "violence",
                "language": "en",
                "guard": "candidate"
            }
        )
    
    time.sleep(0.1)
    
    first_response = client.get("/ui/monitor/api/metrics")
    first_count = first_response.json()["total_requests"]
    
    # Second batch
    for i in range(5):
        client.post(
            "/score",
            json={
                "text": f"batch2-{i}",
                "category": "violence",
                "language": "en",
                "guard": "candidate"
            }
        )
    
    time.sleep(0.1)
    
    second_response = client.get("/ui/monitor/api/metrics")
    second_count = second_response.json()["total_requests"]
    
    # Second count should be higher
    assert second_count > first_count

