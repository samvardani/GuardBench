"""End-to-end tests for Policy Management UI."""

from __future__ import annotations

import pytest
import time
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create a test client for the service API."""
    from service.api import app
    return TestClient(app)


@pytest.fixture
def test_policy_high_threshold():
    """Policy with high threshold (less restrictive)."""
    return """version: 1
metadata:
  name: lenient-policy
slices:
  - id: violence_en
    category: violence
    language: en
    threshold: 4.5
    rules:
      - id: violence_keywords
        weight: 1.0
        action: block
        match:
          regex:
            - "\\\\bextreme\\\\b"
"""


@pytest.fixture
def test_policy_low_threshold():
    """Policy with low threshold (more restrictive)."""
    return """version: 1
metadata:
  name: strict-policy
slices:
  - id: violence_en
    category: violence
    language: en
    threshold: 0.1
    rules:
      - id: violence_keywords
        weight: 1.0
        action: block
        match:
          regex:
            - "\\\\bkill\\\\b"
            - "\\\\bhurt\\\\b"
"""


def test_e2e_update_policy_and_score(client, test_policy_low_threshold, tmp_path):
    """E2E: Update policy, then score text to verify new thresholds apply."""
    policy_path = tmp_path / "policy.yaml"
    
    with patch("seval.ui.routes.POLICY_PATH", policy_path):
        with patch("seval.ui.routes._git_commit_policy"):
            with patch("seval.ui.routes._reload_policy_cache"):
                # Step 1: Update policy
                update_response = client.post(
                    "/ui/policies",
                    json={"yaml_content": test_policy_low_threshold}
                )
                assert update_response.status_code == 200
                
                # Small delay to ensure update is processed
                time.sleep(0.1)
                
                # Step 2: Score text that should trigger the rule
                test_response = client.post(
                    "/ui/test",
                    json={
                        "text": "I want to hurt someone",
                        "category": "violence",
                        "language": "en"
                    }
                )
                assert test_response.status_code == 200
                data = test_response.json()
                
                # Verify response structure
                assert "score" in data
                assert "blocked" in data
                assert "category" in data
                assert data["category"] == "violence"
                assert data["language"] == "en"


def test_e2e_multiple_policy_updates(client, test_policy_high_threshold, test_policy_low_threshold, tmp_path):
    """E2E: Multiple policy updates in sequence."""
    policy_path = tmp_path / "policy.yaml"
    
    with patch("seval.ui.routes.POLICY_PATH", policy_path):
        with patch("seval.ui.routes._git_commit_policy"):
            with patch("seval.ui.routes._reload_policy_cache"):
                # Update 1: High threshold
                response1 = client.post(
                    "/ui/policies",
                    json={"yaml_content": test_policy_high_threshold}
                )
                assert response1.status_code == 200
                
                # Update 2: Low threshold
                response2 = client.post(
                    "/ui/policies",
                    json={"yaml_content": test_policy_low_threshold}
                )
                assert response2.status_code == 200
                
                # Verify we can still get the policy
                get_response = client.get("/ui/policies")
                assert get_response.status_code == 200


def test_e2e_ui_workflow(client, test_policy_low_threshold, tmp_path):
    """E2E: Complete UI workflow - view, edit, test."""
    policy_path = tmp_path / "policy.yaml"
    # Create initial policy file
    policy_path.write_text(test_policy_low_threshold)
    
    with patch("seval.ui.routes.POLICY_PATH", policy_path):
        with patch("seval.ui.routes._git_commit_policy"):
            with patch("seval.ui.routes._reload_policy_cache"):
                # Step 1: Load UI home page
                ui_response = client.get("/ui/")
                assert ui_response.status_code == 200
                
                # Step 2: Get current policy
                get_response = client.get("/ui/policies")
                assert get_response.status_code == 200
                
                # Step 3: Update policy
                update_response = client.post(
                    "/ui/policies",
                    json={"yaml_content": test_policy_low_threshold}
                )
                assert update_response.status_code == 200
                
                # Step 4: Load test UI
                test_ui_response = client.get("/ui/test")
                assert test_ui_response.status_code == 200
                
                # Step 5: Run test
                test_response = client.post(
                    "/ui/test",
                    json={
                        "text": "hello world",
                        "category": "violence",
                        "language": "en"
                    }
                )
                assert test_response.status_code == 200


def test_e2e_policy_validation_flow(client, test_policy_low_threshold, tmp_path):
    """E2E: Test policy validation catches errors before scoring."""
    policy_path = tmp_path / "policy.yaml"
    # Create initial policy file
    policy_path.write_text(test_policy_low_threshold)
    
    with patch("seval.ui.routes.POLICY_PATH", policy_path):
        # Try to update with invalid policy
        invalid_policy = "invalid: yaml: ["
        response = client.post(
            "/ui/policies",
            json={"yaml_content": invalid_policy}
        )
        assert response.status_code == 400
        assert "Invalid YAML" in response.json()["detail"]
        
        # Scoring should still work with existing policy
        test_response = client.post(
            "/ui/test",
            json={
                "text": "test",
                "category": "violence",
                "language": "en"
            }
        )
        # Should work (using default policy or existing one)
        assert test_response.status_code == 200


def test_e2e_different_categories(client):
    """E2E: Test different categories and languages."""
    categories = ["violence", "self_harm", "crime", "malware"]
    languages = ["en", "es", "fr", "fa"]
    
    for category in categories:
        for language in languages:
            response = client.post(
                "/ui/test",
                json={
                    "text": "test text",
                    "category": category,
                    "language": language
                }
            )
            assert response.status_code == 200
            data = response.json()
            assert data["category"] == category
            assert data["language"] == language


def test_e2e_latency_measurement(client):
    """E2E: Verify latency is measured and returned."""
    response = client.post(
        "/ui/test",
        json={
            "text": "test text",
            "category": "violence",
            "language": "en"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "latency_ms" in data
    assert isinstance(data["latency_ms"], int)
    assert data["latency_ms"] >= 0
    # Latency should be reasonable (< 5 seconds)
    assert data["latency_ms"] < 5000


def test_e2e_policy_version_tracking(client, test_policy_low_threshold, tmp_path):
    """E2E: Verify policy version is tracked in test results."""
    policy_path = tmp_path / "policy.yaml"
    
    with patch("seval.ui.routes.POLICY_PATH", policy_path):
        with patch("seval.ui.routes._git_commit_policy"):
            with patch("seval.ui.routes._reload_policy_cache"):
                # Update policy
                client.post(
                    "/ui/policies",
                    json={"yaml_content": test_policy_low_threshold}
                )
                
                # Run test
                response = client.post(
                    "/ui/test",
                    json={
                        "text": "test",
                        "category": "violence",
                        "language": "en"
                    }
                )
                assert response.status_code == 200
                data = response.json()
                assert "policy_version" in data
                assert isinstance(data["policy_version"], str)


def test_e2e_concurrent_requests(client):
    """E2E: Test handling of concurrent test requests."""
    import concurrent.futures
    
    def run_test():
        return client.post(
            "/ui/test",
            json={
                "text": "test text",
                "category": "violence",
                "language": "en"
            }
        )
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(run_test) for _ in range(10)]
        results = [f.result() for f in futures]
    
    # All requests should succeed
    assert all(r.status_code == 200 for r in results)
    
    # All should have valid responses
    for response in results:
        data = response.json()
        assert "score" in data
        assert "blocked" in data

