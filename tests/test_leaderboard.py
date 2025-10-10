"""Tests for benchmark leaderboard."""

from __future__ import annotations

import os
import pytest
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from analytics import Leaderboard, BenchmarkResult, LeaderboardEntry, init_benchmark_tables


@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db_path = Path(path)
    
    # Initialize schema
    conn = sqlite3.connect(db_path)
    init_benchmark_tables(conn)
    conn.close()
    
    yield db_path
    
    # Cleanup
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def leaderboard(temp_db):
    """Create leaderboard with temp database."""
    return Leaderboard(db_path=temp_db)


class TestBenchmarkResult:
    """Test BenchmarkResult dataclass."""
    
    def test_result_creation(self):
        """Test creating benchmark result."""
        result = BenchmarkResult(
            dataset_name="test-dataset",
            guard_name="internal",
            guard_version="1.0",
            precision=0.95,
            recall=0.92,
            f1_score=0.935,
            fnr=0.08,
            fpr=0.05,
            tp=92,
            fp=5,
            tn=95,
            fn=8,
        )
        
        assert result.dataset_name == "test-dataset"
        assert result.guard_name == "internal"
        assert result.f1_score == 0.935
    
    def test_result_to_dict(self):
        """Test converting result to dictionary."""
        result = BenchmarkResult(
            dataset_name="test",
            guard_name="openai",
            precision=0.98,
            recall=0.94,
            f1_score=0.96,
        )
        
        data = result.to_dict()
        
        assert data["dataset_name"] == "test"
        assert data["guard_name"] == "openai"
        assert data["precision"] == 0.98


class TestLeaderboard:
    """Test Leaderboard class."""
    
    def test_leaderboard_creation(self, temp_db):
        """Test creating leaderboard."""
        leaderboard = Leaderboard(db_path=temp_db)
        
        assert isinstance(leaderboard, Leaderboard)
        assert leaderboard.db_path == temp_db
    
    def test_add_result(self, leaderboard):
        """Test adding benchmark result."""
        result = BenchmarkResult(
            dataset_name="test-dataset",
            guard_name="internal",
            precision=0.95,
            recall=0.92,
            f1_score=0.935,
            tp=92,
            fp=5,
            tn=95,
            fn=8,
        )
        
        result_id = leaderboard.add_result(result)
        
        assert isinstance(result_id, int)
        assert result_id > 0
    
    def test_get_leaderboard_empty(self, leaderboard):
        """Test getting empty leaderboard."""
        entries = leaderboard.get_leaderboard()
        
        assert len(entries) == 0
    
    def test_get_leaderboard_with_results(self, leaderboard):
        """Test getting leaderboard with results."""
        # Add multiple results
        results = [
            BenchmarkResult(
                dataset_name="test",
                guard_name="internal",
                f1_score=0.90,
                precision=0.95,
                recall=0.85,
                tp=85,
                fp=5,
                tn=90,
                fn=20,
            ),
            BenchmarkResult(
                dataset_name="test",
                guard_name="openai",
                f1_score=0.95,
                precision=0.98,
                recall=0.92,
                tp=92,
                fp=2,
                tn=93,
                fn=13,
            ),
            BenchmarkResult(
                dataset_name="test",
                guard_name="azure",
                f1_score=0.92,
                precision=0.96,
                recall=0.88,
                tp=88,
                fp=4,
                tn=91,
                fn=17,
            ),
        ]
        
        for r in results:
            leaderboard.add_result(r)
        
        # Get leaderboard
        entries = leaderboard.get_leaderboard(dataset_name="test")
        
        assert len(entries) == 3
        
        # Should be sorted by F1 score descending
        assert entries[0].result.guard_name == "openai"  # F1=0.95
        assert entries[1].result.guard_name == "azure"   # F1=0.92
        assert entries[2].result.guard_name == "internal"  # F1=0.90
        
        # Check ranks
        assert entries[0].rank == 1
        assert entries[1].rank == 2
        assert entries[2].rank == 3
    
    def test_leaderboard_ranking_by_different_metrics(self, leaderboard):
        """Test ranking by different metrics."""
        results = [
            BenchmarkResult(
                dataset_name="test",
                guard_name="high-precision",
                precision=0.99,
                recall=0.80,
                f1_score=0.88,
                tp=80,
                fp=1,
                tn=99,
                fn=20,
            ),
            BenchmarkResult(
                dataset_name="test",
                guard_name="high-recall",
                precision=0.85,
                recall=0.99,
                f1_score=0.91,
                tp=99,
                fp=15,
                tn=85,
                fn=1,
            ),
        ]
        
        for r in results:
            leaderboard.add_result(r)
        
        # Rank by F1
        by_f1 = leaderboard.get_leaderboard(dataset_name="test", metric="f1_score")
        assert by_f1[0].result.guard_name == "high-recall"
        
        # Rank by precision
        by_precision = leaderboard.get_leaderboard(dataset_name="test", metric="precision")
        assert by_precision[0].result.guard_name == "high-precision"
        
        # Rank by recall
        by_recall = leaderboard.get_leaderboard(dataset_name="test", metric="recall")
        assert by_recall[0].result.guard_name == "high-recall"
    
    def test_get_datasets(self, leaderboard):
        """Test getting list of datasets."""
        # Add results for different datasets
        leaderboard.add_result(BenchmarkResult(
            dataset_name="dataset-a",
            guard_name="test",
            f1_score=0.9,
            precision=0.9,
            recall=0.9,
            tp=90,
            fp=10,
            tn=90,
            fn=10,
        ))
        
        leaderboard.add_result(BenchmarkResult(
            dataset_name="dataset-b",
            guard_name="test",
            f1_score=0.85,
            precision=0.85,
            recall=0.85,
            tp=85,
            fp=15,
            tn=85,
            fn=15,
        ))
        
        datasets = leaderboard.get_datasets()
        
        assert "dataset-a" in datasets
        assert "dataset-b" in datasets
        assert len(datasets) == 2
    
    def test_register_dataset(self, leaderboard):
        """Test registering a benchmark dataset."""
        leaderboard.register_dataset(
            dataset_name="official-benchmark",
            description="Official safety benchmark",
            size=1000,
            categories=["violence", "hate"],
            languages=["en", "es"],
            source_url="https://example.com/benchmark",
            is_official=True
        )
        
        info = leaderboard.get_dataset_info("official-benchmark")
        
        assert info is not None
        assert info["dataset_name"] == "official-benchmark"
        assert info["description"] == "Official safety benchmark"
        assert info["size"] == 1000
        assert "violence" in info["categories"]
        assert info["is_official"] is True


class TestLeaderboardAPI:
    """Test leaderboard API endpoints."""
    
    def test_get_leaderboard_endpoint(self):
        """Test GET /leaderboard endpoint."""
        from service.api import app
        client = TestClient(app)
        
        response = client.get("/leaderboard")
        
        # Should succeed even if empty
        assert response.status_code == 200
        data = response.json()
        
        assert "entries" in data
        assert "count" in data
        assert isinstance(data["entries"], list)
    
    def test_get_leaderboard_with_filter(self):
        """Test GET /leaderboard with dataset filter."""
        from service.api import app
        client = TestClient(app)
        
        response = client.get("/leaderboard?dataset=test-dataset&metric=precision")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["dataset"] == "test-dataset"
        assert data["metric"] == "precision"
    
    def test_submit_benchmark_result(self):
        """Test POST /leaderboard/submit endpoint."""
        from service.api import app
        client = TestClient(app)
        
        submission = {
            "dataset_name": "test-dataset",
            "guard_name": "my-guard",
            "guard_version": "1.0",
            "precision": 0.95,
            "recall": 0.92,
            "f1_score": 0.935,
            "fnr": 0.08,
            "fpr": 0.05,
            "tp": 92,
            "fp": 5,
            "tn": 95,
            "fn": 8,
            "avg_latency_ms": 150,
            "categories": ["violence", "hate"],
            "languages": ["en"],
            "is_public": True,
        }
        
        response = client.post("/leaderboard/submit", json=submission)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "id" in data
        assert data["guard_name"] == "my-guard"
        assert data["f1_score"] == 0.935
    
    def test_list_datasets_endpoint(self):
        """Test GET /leaderboard/datasets endpoint."""
        from service.api import app
        client = TestClient(app)
        
        response = client.get("/leaderboard/datasets")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "datasets" in data
        assert "count" in data
    
    def test_leaderboard_ui_endpoint(self):
        """Test GET /leaderboard/ui endpoint."""
        from service.api import app
        client = TestClient(app)
        
        response = client.get("/leaderboard/ui")
        
        assert response.status_code == 200
        assert "Benchmark Leaderboard" in response.text
        assert "leaderboardContainer" in response.text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

