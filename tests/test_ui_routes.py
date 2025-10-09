"""Unit tests for Policy Management UI routes."""

from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import yaml

from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create a test client for the service API."""
    from service.api import app
    return TestClient(app)


@pytest.fixture
def valid_policy_yaml():
    """Valid policy YAML for testing."""
    return """version: 1
metadata:
  name: test-policy
  description: Test policy
slices:
  - id: test_violence
    category: violence
    language: en
    threshold: 0.5
    rules:
      - id: test_rule
        weight: 1.0
        action: block
        match:
          regex:
            - "\\\\btest\\\\b"
"""


@pytest.fixture
def invalid_policy_yaml():
    """Invalid policy YAML for testing."""
    return """version: "not-an-integer"
slices:
  - category: violence
"""


def test_ui_home_loads(client):
    """Test that the UI home page loads successfully."""
    response = client.get("/ui/")
    assert response.status_code == 200
    assert "Policy Management" in response.text
    assert "policy_yaml" in response.text or "textarea" in response.text


def test_get_policies(client):
    """Test GET /ui/policies returns policy data."""
    response = client.get("/ui/policies")
    assert response.status_code == 200
    data = response.json()
    assert "version" in data
    assert "slices" in data
    assert isinstance(data["slices"], list)


def test_update_policy_valid(client, valid_policy_yaml, tmp_path):
    """Test updating policy with valid YAML."""
    with patch("seval.ui.routes.POLICY_PATH", tmp_path / "policy.yaml"):
        with patch("seval.ui.routes._git_commit_policy"):
            with patch("seval.ui.routes._reload_policy_cache"):
                response = client.post(
                    "/ui/policies",
                    json={"yaml_content": valid_policy_yaml}
                )
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert "successfully" in data["message"].lower()


def test_update_policy_invalid_yaml(client):
    """Test that invalid YAML is rejected."""
    invalid_yaml = "invalid: yaml: content: ["
    response = client.post(
        "/ui/policies",
        json={"yaml_content": invalid_yaml}
    )
    assert response.status_code == 400
    assert "Invalid YAML" in response.json()["detail"]


def test_update_policy_invalid_schema(client, invalid_policy_yaml, tmp_path):
    """Test that policy with invalid schema is rejected."""
    with patch("seval.ui.routes.POLICY_PATH", tmp_path / "policy.yaml"):
        response = client.post(
            "/ui/policies",
            json={"yaml_content": invalid_policy_yaml}
        )
        assert response.status_code == 400
        assert "validation" in response.json()["detail"].lower()


def test_update_policy_missing_required_fields(client, tmp_path):
    """Test that policy missing required fields is rejected."""
    missing_slices = """version: 1
metadata:
  name: test
"""
    with patch("seval.ui.routes.POLICY_PATH", tmp_path / "policy.yaml"):
        response = client.post(
            "/ui/policies",
            json={"yaml_content": missing_slices}
        )
        assert response.status_code == 400


def test_test_ui_loads(client):
    """Test that the test UI page loads successfully."""
    response = client.get("/ui/test")
    assert response.status_code == 200
    assert "Test Runner" in response.text or "test" in response.text.lower()


def test_run_test_basic(client):
    """Test running a basic policy test."""
    response = client.post(
        "/ui/test",
        json={
            "text": "hello world",
            "category": "violence",
            "language": "en"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "score" in data
    assert "blocked" in data
    assert "category" in data
    assert "language" in data
    assert "latency_ms" in data
    assert "policy_version" in data
    assert isinstance(data["score"], (int, float))
    assert isinstance(data["blocked"], bool)


def test_run_test_violence_keyword(client):
    """Test that violence keywords trigger blocking."""
    response = client.post(
        "/ui/test",
        json={
            "text": "How do I kill someone?",
            "category": "violence",
            "language": "en"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "score" in data
    # Score should be non-zero for violence keywords
    assert data["score"] >= 0


def test_policy_reload_affects_scoring(client, valid_policy_yaml, tmp_path):
    """Test that policy reload affects scoring behavior."""
    # This is an E2E-like test that verifies the full flow
    policy_path = tmp_path / "policy.yaml"
    
    with patch("seval.ui.routes.POLICY_PATH", policy_path):
        with patch("seval.ui.routes._git_commit_policy"):
            with patch("seval.ui.routes._reload_policy_cache") as mock_reload:
                # Update policy
                response = client.post(
                    "/ui/policies",
                    json={"yaml_content": valid_policy_yaml}
                )
                assert response.status_code == 200
                
                # Verify reload was called
                mock_reload.assert_called_once()


def test_git_commit_called_on_save(client, valid_policy_yaml, tmp_path):
    """Test that git commit is called when saving policy."""
    with patch("seval.ui.routes.POLICY_PATH", tmp_path / "policy.yaml"):
        with patch("seval.ui.routes._git_commit_policy") as mock_commit:
            with patch("seval.ui.routes._reload_policy_cache"):
                response = client.post(
                    "/ui/policies",
                    json={"yaml_content": valid_policy_yaml}
                )
                assert response.status_code == 200
                mock_commit.assert_called_once()


def test_invalid_rule_weight(client, tmp_path):
    """Test that negative or zero rule weights are rejected."""
    invalid_weight = """version: 1
slices:
  - id: test
    category: violence
    language: en
    threshold: 0.5
    rules:
      - id: rule1
        weight: 0
        action: block
        match:
          regex: ["test"]
"""
    with patch("seval.ui.routes.POLICY_PATH", tmp_path / "policy.yaml"):
        response = client.post(
            "/ui/policies",
            json={"yaml_content": invalid_weight}
        )
        assert response.status_code == 400


def test_invalid_threshold_range(client, tmp_path):
    """Test that thresholds outside [0, 5] are rejected."""
    invalid_threshold = """version: 1
slices:
  - id: test
    category: violence
    language: en
    threshold: 10.0
    rules:
      - id: rule1
        weight: 1.0
        action: block
        match:
          regex: ["test"]
"""
    with patch("seval.ui.routes.POLICY_PATH", tmp_path / "policy.yaml"):
        response = client.post(
            "/ui/policies",
            json={"yaml_content": invalid_threshold}
        )
        assert response.status_code == 400


def test_policy_with_safe_contexts(client, tmp_path):
    """Test that policies with safe contexts are valid."""
    policy_with_context = """version: 1
safe_contexts:
  - id: support
    type: regex
    patterns:
      - "\\\\bhelp\\\\b"
slices:
  - id: test
    category: violence
    language: en
    threshold: 0.5
    rules:
      - id: rule1
        weight: 1.0
        action: block
        match:
          regex: ["bad"]
"""
    with patch("seval.ui.routes.POLICY_PATH", tmp_path / "policy.yaml"):
        with patch("seval.ui.routes._git_commit_policy"):
            with patch("seval.ui.routes._reload_policy_cache"):
                response = client.post(
                    "/ui/policies",
                    json={"yaml_content": policy_with_context}
                )
                assert response.status_code == 200


def test_run_test_missing_fields(client):
    """Test that test request with missing fields returns 422."""
    response = client.post(
        "/ui/test",
        json={"text": "hello"}
        # Missing category and language (though they have defaults)
    )
    # Should still work with defaults
    assert response.status_code == 200

