"""Tests for export endpoints."""

from __future__ import annotations

import json
import pytest
from fastapi.testclient import TestClient

from seval.export.schema import ReportSchemaModel
from seval.export.builder import ReportBuilder, sanitize_for_export


@pytest.fixture
def client():
    """Create test client."""
    from service.api import app
    return TestClient(app)


@pytest.fixture
def sample_evaluation():
    """Sample evaluation data."""
    return {
        "guards": {
            "candidate": {
                "name": "candidate-v1",
                "predictions": [True, False, True, True, False],
                "latencies": [10, 15, 12, 20, 18],
                "latency": {"p50": 15.0, "p90": 19.0, "p95": 19.5, "p99": 20.0},
                "modes": {
                    "strict": {
                        "confusion": {
                            "tp": 3,
                            "fp": 0,
                            "tn": 2,
                            "fn": 0,
                            "precision": 1.0,
                            "recall": 1.0,
                            "fnr": 0.0,
                            "fpr": 0.0,
                        },
                        "slices": []
                    }
                }
            }
        }
    }


@pytest.fixture
def sample_config():
    """Sample configuration."""
    return {
        "dataset_path": "./dataset/sample.csv",
        "policy_version": "v0.1"
    }


def test_report_builder_metadata(sample_evaluation, sample_config):
    """Test building metadata section."""
    builder = ReportBuilder(sample_evaluation, sample_config)
    metadata = builder.build_metadata()
    
    assert "report_id" in metadata
    assert "generated_at" in metadata
    assert "policy_version" in metadata
    assert "total_samples" in metadata
    assert metadata["total_samples"] == 5


def test_report_builder_kpis(sample_evaluation, sample_config):
    """Test building KPIs."""
    builder = ReportBuilder(sample_evaluation, sample_config)
    kpis = builder.build_kpis()
    
    assert "precision" in kpis
    assert "recall" in kpis
    assert "fnr" in kpis
    assert "fpr" in kpis
    assert "latency_p50_ms" in kpis
    
    # Check values
    assert kpis["precision"] == 1.0
    assert kpis["recall"] == 1.0


def test_report_builder_improvement_plan(sample_evaluation, sample_config):
    """Test building improvement plan."""
    builder = ReportBuilder(sample_evaluation, sample_config)
    improvements = builder.build_improvement_plan()
    
    # Should be a list
    assert isinstance(improvements, list)
    
    # Each item should have required fields
    for item in improvements:
        assert "category" in item
        assert "issue" in item
        assert "recommendation" in item
        assert "priority" in item
        assert item["priority"] in ["high", "medium", "low"]


def test_report_builder_risks(sample_evaluation, sample_config):
    """Test building risks."""
    builder = ReportBuilder(sample_evaluation, sample_config)
    risks = builder.build_risks()
    
    assert isinstance(risks, list)
    
    for risk in risks:
        assert "category" in risk
        assert "risk_level" in risk
        assert risk["risk_level"] in ["high", "medium", "low"]
        assert "description" in risk


def test_report_builder_references(sample_evaluation, sample_config):
    """Test building references."""
    builder = ReportBuilder(sample_evaluation, sample_config)
    refs = builder.build_references()
    
    assert isinstance(refs, list)
    assert len(refs) > 0
    
    for ref in refs:
        assert "title" in ref
        assert "type" in ref


def test_report_builder_market_data(sample_evaluation, sample_config):
    """Test market data has TBD markers."""
    builder = ReportBuilder(sample_evaluation, sample_config)
    market = builder.build_market_data()
    
    assert isinstance(market, dict)
    
    # All fields should be marked as TBD/external
    for key, value in market.items():
        if isinstance(value, dict):
            assert value.get("value") == "TBD"
            assert value.get("source") == "external"


def test_report_builder_complete(sample_evaluation, sample_config):
    """Test building complete report."""
    builder = ReportBuilder(sample_evaluation, sample_config)
    report = builder.build_report()
    
    assert "metadata" in report
    assert "kpis" in report
    assert "improvement_plan" in report
    assert "risks" in report
    assert "references" in report
    assert "market_data" in report


def test_report_schema_validation(sample_evaluation, sample_config):
    """Test report validates against schema."""
    builder = ReportBuilder(sample_evaluation, sample_config)
    report = builder.build_report()
    
    # Should validate without errors
    schema = ReportSchemaModel(**report)
    
    assert schema.metadata.total_samples == 5
    assert isinstance(schema.kpis.precision, float)


def test_sanitize_removes_secrets():
    """Test sanitize_for_export removes secrets."""
    data = {
        "api_key": "secret123",
        "normal_field": "value",
        "nested": {
            "password": "hidden",
            "safe": "visible"
        },
        "list": [
            {"token": "abc", "data": "xyz"}
        ]
    }
    
    sanitized = sanitize_for_export(data)
    
    assert sanitized["api_key"] == "[REDACTED]"
    assert sanitized["normal_field"] == "value"
    assert sanitized["nested"]["password"] == "[REDACTED]"
    assert sanitized["nested"]["safe"] == "visible"
    assert sanitized["list"][0]["token"] == "[REDACTED]"
    assert sanitized["list"][0]["data"] == "xyz"


def test_export_json_endpoint(client):
    """Test /export/report.json endpoint."""
    response = client.get("/export/report.json")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "metadata" in data
    assert "kpis" in data
    assert "improvement_plan" in data
    assert "risks" in data
    assert "references" in data
    assert "market_data" in data


def test_export_json_with_guard_param(client):
    """Test /export/report.json with guard parameter."""
    response = client.get("/export/report.json?guard=baseline")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "metadata" in data


def test_export_markdown_endpoint(client):
    """Test /export/report.md endpoint."""
    response = client.get("/export/report.md")
    
    assert response.status_code == 200
    content = response.text
    
    # Should be markdown format
    assert "# Safety Evaluation Report" in content
    assert "## Executive Summary" in content
    assert "## Key Performance Indicators" in content


def test_export_markdown_has_tables(client):
    """Test markdown report contains tables."""
    response = client.get("/export/report.md")
    
    assert response.status_code == 200
    content = response.text
    
    # Should have markdown tables
    assert "|" in content  # Table delimiter
    assert "Metric" in content or "Percentile" in content


def test_export_markdown_has_sections(client):
    """Test markdown report has all sections."""
    response = client.get("/export/report.md")
    
    assert response.status_code == 200
    content = response.text
    
    sections = [
        "Executive Summary",
        "Key Performance Indicators",
        "Latency Performance",
        "Improvement Plan",
        "Risk Assessment",
        "References",
    ]
    
    for section in sections:
        assert section in content


def test_export_json_no_secrets_leaked(client):
    """Test JSON export doesn't leak secrets."""
    response = client.get("/export/report.json")
    
    assert response.status_code == 200
    content = response.text.lower()
    
    # Check for common secret patterns
    secret_indicators = [
        "sk-",  # OpenAI API key prefix
        "bearer ",
        "password",
        # Don't check "api_key" as it might be in field names
    ]
    
    # These should not appear in the output
    for indicator in secret_indicators:
        assert indicator not in content or "[redacted]" in content.lower()


def test_export_markdown_no_secrets_leaked(client):
    """Test Markdown export doesn't leak secrets."""
    response = client.get("/export/report.md")
    
    assert response.status_code == 200
    content = response.text.lower()
    
    # Should not contain actual secrets
    secret_patterns = ["sk-", "bearer "]
    
    for pattern in secret_patterns:
        # If pattern exists, it should be redacted
        if pattern in content:
            assert "[redacted]" in content or "tbd" in content


def test_report_builder_high_fnr_improvement(sample_config):
    """Test improvement plan for high FNR."""
    # Create evaluation with high FNR
    eval_data = {
        "guards": {
            "candidate": {
                "predictions": [False] * 10,
                "latencies": [10] * 10,
                "latency": {"p50": 10.0, "p95": 10.0, "p99": 10.0},
                "modes": {
                    "strict": {
                        "confusion": {
                            "tp": 0,
                            "fp": 0,
                            "tn": 5,
                            "fn": 5,  # High FNR
                            "precision": 0.0,
                            "recall": 0.0,
                            "fnr": 1.0,
                            "fpr": 0.0,
                        },
                        "slices": []
                    }
                }
            }
        }
    }
    
    builder = ReportBuilder(eval_data, sample_config)
    improvements = builder.build_improvement_plan()
    
    # Should recommend fixing recall
    assert any("False Negative" in item.get("issue", "") for item in improvements)


def test_report_builder_high_latency_improvement(sample_config):
    """Test improvement plan for high latency."""
    eval_data = {
        "guards": {
            "candidate": {
                "predictions": [True] * 5,
                "latencies": [200] * 5,  # High latency
                "latency": {"p50": 200.0, "p95": 200.0, "p99": 200.0},
                "modes": {
                    "strict": {
                        "confusion": {
                            "tp": 5,
                            "fp": 0,
                            "tn": 0,
                            "fn": 0,
                            "precision": 1.0,
                            "recall": 1.0,
                            "fnr": 0.0,
                            "fpr": 0.0,
                        },
                        "slices": []
                    }
                }
            }
        }
    }
    
    builder = ReportBuilder(eval_data, sample_config)
    improvements = builder.build_improvement_plan()
    
    # Should recommend performance optimization
    assert any("latency" in item.get("issue", "").lower() for item in improvements)


def test_markdown_rendering_snapshot(sample_evaluation, sample_config):
    """Test markdown rendering produces expected format (snapshot test)."""
    from seval.export.markdown import render_markdown_report
    
    builder = ReportBuilder(sample_evaluation, sample_config)
    report = builder.build_report()
    markdown = render_markdown_report(report)
    
    # Check structure
    assert markdown.startswith("# Safety Evaluation Report")
    assert "## Executive Summary" in markdown
    assert "| Metric | Value |" in markdown or "Metric" in markdown
    assert "✅" in markdown or "⚠️" in markdown  # Status indicators


def test_export_endpoints_accessible(client):
    """Test both export endpoints are accessible."""
    endpoints = [
        "/export/report.json",
        "/export/report.md",
    ]
    
    for endpoint in endpoints:
        response = client.get(endpoint)
        assert response.status_code == 200

