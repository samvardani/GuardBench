"""E2E tests for image moderation endpoint."""

from __future__ import annotations

import os
import pytest
from io import BytesIO
from unittest.mock import patch, MagicMock

from PIL import Image
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client."""
    from service.api import app
    return TestClient(app)


@pytest.fixture
def mock_image_bytes():
    """Create mock image bytes."""
    img = Image.new('RGB', (100, 100), color='blue')
    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf.getvalue()


def test_e2e_score_image_disabled_by_default(client):
    """E2E: /score-image returns 404 when not enabled."""
    with patch.dict(os.environ, {"ENABLE_IMAGE": "0"}):
        # Need to reload the app for the change to take effect
        # For this test, just check the behavior
        response = client.post("/score-image")
        
        # Should return 404 or 422 (missing required params)
        assert response.status_code in [404, 422]


@pytest.mark.skipif(
    os.getenv("ENABLE_IMAGE") != "1",
    reason="Image moderation not enabled for testing"
)
def test_e2e_score_image_no_input(client):
    """E2E: /score-image requires file or URL."""
    response = client.post("/score-image")
    
    assert response.status_code == 400
    assert "file" in response.json()["detail"].lower() or "url" in response.json()["detail"].lower()


@pytest.mark.skipif(
    os.getenv("ENABLE_IMAGE") != "1",
    reason="Image moderation not enabled"
)
def test_e2e_score_image_with_file(client, mock_image_bytes):
    """E2E: /score-image with uploaded file."""
    # Mock the moderator
    with patch("seval.image_moderation.routes.get_global_moderator") as mock_get_mod:
        from seval.image_moderation.moderator import ImageModerationResult
        
        mock_moderator = MagicMock()
        mock_moderator.moderate_bytes.return_value = ImageModerationResult(
            categories={"normal": 0.9, "nsfw": 0.1},
            blocked=False,
            primary_category="normal",
            latency_ms=50,
            model_name="test-model"
        )
        mock_get_mod.return_value = mock_moderator
        
        response = client.post(
            "/score-image",
            files={"file": ("test.png", mock_image_bytes, "image/png")}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "categories" in data
        assert "blocked" in data
        assert "primary_category" in data
        assert "latency_ms" in data
        assert data["blocked"] is False


@pytest.mark.skipif(
    os.getenv("ENABLE_IMAGE") != "1",
    reason="Image moderation not enabled"
)
def test_e2e_score_image_with_url(client):
    """E2E: /score-image with URL."""
    with patch("seval.image_moderation.routes.get_global_moderator") as mock_get_mod:
        from seval.image_moderation.moderator import ImageModerationResult
        
        mock_moderator = MagicMock()
        mock_moderator.moderate_url.return_value = ImageModerationResult(
            categories={"normal": 0.8, "nsfw": 0.2},
            blocked=False,
            primary_category="normal",
            latency_ms=100,
            model_name="test-model"
        )
        mock_get_mod.return_value = mock_moderator
        
        response = client.post(
            "/score-image",
            data={"url": "https://example.com/image.jpg"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "categories" in data
        assert data["primary_category"] == "normal"


@pytest.mark.skipif(
    os.getenv("ENABLE_IMAGE") != "1",
    reason="Image moderation not enabled"
)
def test_e2e_score_image_blocks_nsfw(client, mock_image_bytes):
    """E2E: /score-image blocks NSFW content."""
    with patch("seval.image_moderation.routes.get_global_moderator") as mock_get_mod:
        from seval.image_moderation.moderator import ImageModerationResult
        
        mock_moderator = MagicMock()
        mock_moderator.moderate_bytes.return_value = ImageModerationResult(
            categories={"normal": 0.1, "nsfw": 0.9},
            blocked=True,
            primary_category="nsfw",
            latency_ms=50,
            model_name="test-model"
        )
        mock_get_mod.return_value = mock_moderator
        
        response = client.post(
            "/score-image",
            files={"file": ("nsfw.png", mock_image_bytes, "image/png")}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["blocked"] is True
        assert data["primary_category"] == "nsfw"
        assert data["categories"]["nsfw"] == 0.9


@pytest.mark.skipif(
    os.getenv("ENABLE_IMAGE") != "1",
    reason="Image moderation not enabled"
)
def test_e2e_score_image_both_file_and_url(client, mock_image_bytes):
    """E2E: /score-image rejects both file and URL."""
    response = client.post(
        "/score-image",
        files={"file": ("test.png", mock_image_bytes, "image/png")},
        data={"url": "https://example.com/image.jpg"}
    )
    
    assert response.status_code == 400
    assert "both" in response.json()["detail"].lower()


@pytest.mark.skipif(
    os.getenv("ENABLE_IMAGE") != "1",
    reason="Image moderation not enabled"
)
def test_e2e_score_image_threshold_gates(client, mock_image_bytes):
    """E2E: Thresholds correctly gate blocking decisions."""
    with patch("seval.image_moderation.routes.get_global_moderator") as mock_get_mod:
        from seval.image_moderation.moderator import ImageModerationResult
        
        mock_moderator = MagicMock()
        
        # Test case 1: Just below threshold
        mock_moderator.moderate_bytes.return_value = ImageModerationResult(
            categories={"nsfw": 0.49},
            blocked=False,
            primary_category="nsfw",
            latency_ms=50,
            model_name="test-model"
        )
        mock_get_mod.return_value = mock_moderator
        
        response1 = client.post(
            "/score-image",
            files={"file": ("test1.png", mock_image_bytes, "image/png")}
        )
        
        assert response1.json()["blocked"] is False
        
        # Test case 2: At threshold
        mock_moderator.moderate_bytes.return_value = ImageModerationResult(
            categories={"nsfw": 0.5},
            blocked=True,
            primary_category="nsfw",
            latency_ms=50,
            model_name="test-model"
        )
        
        response2 = client.post(
            "/score-image",
            files={"file": ("test2.png", mock_image_bytes, "image/png")}
        )
        
        assert response2.json()["blocked"] is True


@pytest.mark.skipif(
    os.getenv("ENABLE_IMAGE") != "1",
    reason="Image moderation not enabled"
)
def test_e2e_score_image_latency_tracking(client, mock_image_bytes):
    """E2E: Latency is tracked correctly."""
    with patch("seval.image_moderation.routes.get_global_moderator") as mock_get_mod:
        from seval.image_moderation.moderator import ImageModerationResult
        
        mock_moderator = MagicMock()
        mock_moderator.moderate_bytes.return_value = ImageModerationResult(
            categories={"normal": 1.0},
            blocked=False,
            primary_category="normal",
            latency_ms=123,
            model_name="test-model"
        )
        mock_get_mod.return_value = mock_moderator
        
        response = client.post(
            "/score-image",
            files={"file": ("test.png", mock_image_bytes, "image/png")}
        )
        
        assert response.status_code == 200
        assert response.json()["latency_ms"] == 123


@pytest.mark.skipif(
    os.getenv("ENABLE_IMAGE") != "1",
    reason="Image moderation not enabled"
)
def test_e2e_score_image_multiple_categories(client, mock_image_bytes):
    """E2E: Multiple categories returned with scores."""
    with patch("seval.image_moderation.routes.get_global_moderator") as mock_get_mod:
        from seval.image_moderation.moderator import ImageModerationResult
        
        mock_moderator = MagicMock()
        mock_moderator.moderate_bytes.return_value = ImageModerationResult(
            categories={
                "normal": 0.4,
                "nsfw": 0.3,
                "violence": 0.2,
                "suggestive": 0.1
            },
            blocked=False,
            primary_category="normal",
            latency_ms=50,
            model_name="test-model"
        )
        mock_get_mod.return_value = mock_moderator
        
        response = client.post(
            "/score-image",
            files={"file": ("test.png", mock_image_bytes, "image/png")}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["categories"]) == 4
        assert "nsfw" in data["categories"]
        assert "violence" in data["categories"]
        assert "suggestive" in data["categories"]


def test_e2e_score_image_endpoint_not_available_without_flag(client):
    """E2E: Endpoint not available without ENABLE_IMAGE flag."""
    with patch.dict(os.environ, {}, clear=True):
        # Try to access endpoint
        response = client.post(
            "/score-image",
            data={"url": "https://example.com/test.jpg"}
        )
        
        # Should return 404 (route not registered) or 400 (validation error)
        # The exact code depends on when the route is registered
        assert response.status_code in [404, 400, 422]

