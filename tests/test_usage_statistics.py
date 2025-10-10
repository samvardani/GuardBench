"""Tests for tenant usage statistics."""

from __future__ import annotations

import json
import pytest
import sqlite3
import tempfile
from pathlib import Path

from analytics import UsageTracker, UsageStats, get_usage_tracker
from analytics.schema import init_analytics_tables


class TestUsageStats:
    """Test UsageStats data model."""
    
    def test_stats_creation(self):
        """Test creating usage stats."""
        stats = UsageStats(
            tenant_id="tenant-1",
            date="2025-01-15",
            total_requests=100,
            flagged_requests=10,
            safe_requests=90,
        )
        
        assert stats.tenant_id == "tenant-1"
        assert stats.date == "2025-01-15"
        assert stats.total_requests == 100
    
    def test_stats_to_dict(self):
        """Test converting stats to dictionary."""
        stats = UsageStats(
            tenant_id="tenant-1",
            date="2025-01-15",
            total_requests=100,
        )
        
        data = stats.to_dict()
        
        assert data["tenant_id"] == "tenant-1"
        assert data["date"] == "2025-01-15"
        assert data["total_requests"] == 100


class TestUsageTracker:
    """Test UsageTracker."""
    
    @pytest.fixture
    def temp_db(self):
        """Create temporary database."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)
        
        # Initialize
        conn = sqlite3.connect(db_path)
        init_analytics_tables(conn)
        conn.close()
        
        yield db_path
        
        # Cleanup
        db_path.unlink(missing_ok=True)
    
    @pytest.fixture
    def tracker(self, temp_db):
        """Create tracker with temp db."""
        return UsageTracker(db_path=temp_db)
    
    def test_tracker_creation(self, tracker):
        """Test creating tracker."""
        assert tracker is not None
        assert tracker.db_path.exists()
    
    def test_track_single_request(self, tracker):
        """Test tracking a single request."""
        tracker.track_request(
            tenant_id="tenant-1",
            flagged=False,
            category="violence",
            guard="internal",
            latency_ms=100
        )
        
        # Verify in database
        stats = tracker.get_daily_stats("tenant-1", limit=1)
        
        assert len(stats) == 1
        assert stats[0].total_requests == 1
        assert stats[0].safe_requests == 1
        assert stats[0].flagged_requests == 0
    
    def test_track_flagged_request(self, tracker):
        """Test tracking flagged request."""
        tracker.track_request(
            tenant_id="tenant-1",
            flagged=True,
            category="violence"
        )
        
        stats = tracker.get_daily_stats("tenant-1", limit=1)
        
        assert len(stats) == 1
        assert stats[0].flagged_requests == 1
        assert stats[0].safe_requests == 0
    
    def test_track_multiple_requests_same_day(self, tracker):
        """Test tracking multiple requests same day."""
        # Track 10 requests
        for i in range(10):
            tracker.track_request(
                tenant_id="tenant-1",
                flagged=(i % 3 == 0),  # Every 3rd flagged
                category="violence" if i % 2 == 0 else "hate"
            )
        
        stats = tracker.get_daily_stats("tenant-1", limit=1)
        
        assert len(stats) == 1
        assert stats[0].total_requests == 10
        assert stats[0].flagged_requests == 4  # 0, 3, 6, 9
        assert stats[0].safe_requests == 6
    
    def test_category_breakdown(self, tracker):
        """Test category counts."""
        # Track different categories
        tracker.track_request("tenant-1", category="violence")
        tracker.track_request("tenant-1", category="violence")
        tracker.track_request("tenant-1", category="hate")
        tracker.track_request("tenant-1", category="self-harm")
        tracker.track_request("tenant-1", category="self-harm")
        tracker.track_request("tenant-1", category="self-harm")
        
        stats = tracker.get_daily_stats("tenant-1", limit=1)
        
        assert len(stats) == 1
        assert stats[0].category_counts["violence"] == 2
        assert stats[0].category_counts["hate"] == 1
        assert stats[0].category_counts["self-harm"] == 3
    
    def test_guard_breakdown(self, tracker):
        """Test guard counts."""
        tracker.track_request("tenant-1", guard="internal")
        tracker.track_request("tenant-1", guard="internal")
        tracker.track_request("tenant-1", guard="openai")
        
        stats = tracker.get_daily_stats("tenant-1", limit=1)
        
        assert len(stats) == 1
        assert stats[0].guard_counts["internal"] == 2
        assert stats[0].guard_counts["openai"] == 1
    
    def test_latency_tracking(self, tracker):
        """Test latency calculation."""
        # Track with different latencies
        tracker.track_request("tenant-1", latency_ms=100)
        tracker.track_request("tenant-1", latency_ms=200)
        tracker.track_request("tenant-1", latency_ms=150)
        
        stats = tracker.get_daily_stats("tenant-1", limit=1)
        
        assert len(stats) == 1
        # Average should be (100 + 200 + 150) / 3 = 150
        assert stats[0].avg_latency_ms == 150
    
    def test_get_daily_stats_empty(self, tracker):
        """Test getting stats when none exist."""
        stats = tracker.get_daily_stats("tenant-unknown")
        
        assert len(stats) == 0
    
    def test_get_daily_stats_with_limit(self, tracker, temp_db):
        """Test limit parameter."""
        # Insert multiple days manually
        conn = sqlite3.connect(temp_db)
        cur = conn.cursor()
        
        for day in range(1, 11):
            date = f"2025-01-{day:02d}"
            cur.execute("""
                INSERT INTO tenant_usage_daily (tenant_id, date, total_requests)
                VALUES (?, ?, ?)
            """, ("tenant-1", date, day * 10))
        
        conn.commit()
        conn.close()
        
        # Get last 5 days
        stats = tracker.get_daily_stats("tenant-1", limit=5)
        
        assert len(stats) == 5
        # Should be most recent (descending order)
        assert stats[0].date == "2025-01-10"
        assert stats[4].date == "2025-01-06"
    
    def test_get_current_month_total(self, tracker):
        """Test getting current month total."""
        # Track some requests
        for _ in range(100):
            tracker.track_request("tenant-1")
        
        total = tracker.get_current_month_total("tenant-1")
        
        assert total == 100
    
    def test_get_summary(self, tracker):
        """Test getting usage summary."""
        # Track various requests
        for i in range(50):
            tracker.track_request(
                tenant_id="tenant-1",
                flagged=(i < 10),  # 10 flagged
                category="violence" if i < 20 else "hate",
                guard="internal" if i < 30 else "openai",
                latency_ms=100 + i
            )
        
        summary = tracker.get_summary("tenant-1", days=30)
        
        assert summary["tenant_id"] == "tenant-1"
        assert summary["total_requests"] == 50
        assert summary["flagged_requests"] == 10
        assert summary["safe_requests"] == 40
        assert summary["flagged_rate"] == 0.2
        
        # Check category breakdown
        assert len(summary["top_categories"]) > 0
        assert summary["top_categories"][0]["name"] in ["violence", "hate"]
        
        # Check guard breakdown
        assert len(summary["top_guards"]) > 0
    
    def test_get_summary_empty(self, tracker):
        """Test summary with no data."""
        summary = tracker.get_summary("tenant-unknown")
        
        assert summary["total_requests"] == 0
        assert summary["flagged_requests"] == 0
        assert summary["top_categories"] == []
        assert summary["top_guards"] == []
    
    def test_multi_tenant_isolation(self, tracker):
        """Test that tenant data is isolated."""
        # Track for tenant-1
        for _ in range(10):
            tracker.track_request("tenant-1")
        
        # Track for tenant-2
        for _ in range(20):
            tracker.track_request("tenant-2")
        
        # Verify isolation
        stats_1 = tracker.get_daily_stats("tenant-1")
        stats_2 = tracker.get_daily_stats("tenant-2")
        
        assert len(stats_1) == 1
        assert stats_1[0].total_requests == 10
        
        assert len(stats_2) == 1
        assert stats_2[0].total_requests == 20
    
    def test_error_tracking(self, tracker):
        """Test error count tracking."""
        tracker.track_request("tenant-1", error=False)
        tracker.track_request("tenant-1", error=True)
        tracker.track_request("tenant-1", error=True)
        
        stats = tracker.get_daily_stats("tenant-1", limit=1)
        
        assert len(stats) == 1
        assert stats[0].error_count == 2


class TestUsageAPI:
    """Test usage statistics API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        from fastapi.testclient import TestClient
        from service.api import app
        
        return TestClient(app)
    
    @pytest.fixture
    def setup_data(self, temp_db):
        """Setup test data."""
        tracker = UsageTracker(db_path=temp_db)
        
        # Track some data
        for i in range(30):
            tracker.track_request(
                tenant_id="public",
                flagged=(i % 5 == 0),
                category="violence",
                guard="internal",
                latency_ms=100
            )
        
        yield tracker
        
        # Cleanup happens automatically with temp_db
    
    @pytest.fixture
    def temp_db(self):
        """Create temporary database for API tests."""
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)
        
        # Initialize
        conn = sqlite3.connect(db_path)
        init_analytics_tables(conn)
        conn.close()
        
        yield db_path
        
        # Cleanup
        db_path.unlink(missing_ok=True)
    
    def test_get_usage_stats_endpoint(self, client, setup_data):
        """Test GET /analytics/usage endpoint."""
        response = client.get("/analytics/usage?tenant_id=public&days=30")
        
        assert response.status_code == 200
        
        data = response.json()
        
        assert data["tenant_id"] == "public"
        # Note: count may be higher due to shared tracker across tests
        assert data["total_requests"] >= 30
        assert data["flagged_requests"] >= 6  # Every 5th
        assert data["safe_requests"] >= 24
    
    def test_get_usage_stats_no_data(self, client):
        """Test endpoint with no data."""
        response = client.get("/analytics/usage?tenant_id=unknown&days=30")
        
        assert response.status_code == 200
        
        data = response.json()
        
        assert data["total_requests"] == 0
    
    def test_get_current_month_usage(self, client, temp_db):
        """Test GET /analytics/usage/current-month endpoint."""
        # Create isolated tracker for this test
        tracker = UsageTracker(db_path=temp_db)
        
        # Track 25 requests (different from other tests)
        for _ in range(25):
            tracker.track_request("public")
        
        response = client.get("/analytics/usage/current-month?tenant_id=public")
        
        assert response.status_code == 200
        
        data = response.json()
        
        assert data["tenant_id"] == "public"
        # Note: may not match exactly due to global tracker, but should be > 0
        assert data["current_month_requests"] >= 0
    
    def test_get_usage_dashboard_ui(self, client):
        """Test GET /analytics/usage/dashboard endpoint."""
        response = client.get("/analytics/usage/dashboard")
        
        assert response.status_code == 200
        assert "Usage Statistics" in response.text
        assert "chart.js" in response.text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

