"""Unit tests for image moderation."""

from __future__ import annotations

import os
import pytest
from unittest.mock import MagicMock, patch
from io import BytesIO

from PIL import Image


@pytest.fixture
def mock_image():
    """Create a mock image."""
    img = Image.new('RGB', (100, 100), color='red')
    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf.getvalue()


@pytest.fixture
def enable_image():
    """Enable image moderation for tests."""
    with patch.dict(os.environ, {"ENABLE_IMAGE": "1"}):
        yield


def test_is_enabled_default():
    """Test image moderation is disabled by default."""
    with patch.dict(os.environ, {}, clear=True):
        from seval.image_moderation import is_enabled
        assert is_enabled() is False


def test_is_enabled_when_set():
    """Test image moderation is enabled when flag set."""
    with patch.dict(os.environ, {"ENABLE_IMAGE": "1"}):
        from seval.image_moderation import is_enabled
        assert is_enabled() is True


@pytest.mark.skipif(
    os.getenv("ENABLE_IMAGE") != "1",
    reason="Image moderation not enabled"
)
def test_image_moderator_initialization(enable_image):
    """Test ImageModerator initializes correctly."""
    from seval.image_moderation.moderator import ImageModerator
    
    moderator = ImageModerator()
    assert moderator.model_name == "Falconsai/nsfw_image_detection"
    assert moderator.thresholds["nsfw"] == 0.5


@pytest.mark.skipif(
    os.getenv("ENABLE_IMAGE") != "1",
    reason="Image moderation not enabled"
)
def test_image_moderator_custom_thresholds(enable_image):
    """Test ImageModerator with custom thresholds."""
    from seval.image_moderation.moderator import ImageModerator
    
    custom_thresholds = {
        "nsfw": 0.3,
        "violence": 0.8,
    }
    
    moderator = ImageModerator(thresholds=custom_thresholds)
    assert moderator.thresholds["nsfw"] == 0.3
    assert moderator.thresholds["violence"] == 0.8


@pytest.mark.skipif(
    os.getenv("ENABLE_IMAGE") != "1",
    reason="Image moderation not enabled"
)
def test_image_moderator_moderate_bytes_mock(enable_image, mock_image):
    """Test moderating image bytes with mocked model."""
    from seval.image_moderation.moderator import ImageModerator, ImageModerationResult
    
    moderator = ImageModerator()
    
    # Mock the model pipeline
    mock_pipeline = MagicMock()
    mock_pipeline.return_value = [
        {"label": "normal", "score": 0.8},
        {"label": "nsfw", "score": 0.2},
    ]
    moderator._model = mock_pipeline
    
    result = moderator.moderate_bytes(mock_image)
    
    assert isinstance(result, ImageModerationResult)
    assert "normal" in result.categories
    assert "nsfw" in result.categories
    assert result.primary_category == "normal"
    assert result.blocked is False  # 0.2 < 0.5 threshold


@pytest.mark.skipif(
    os.getenv("ENABLE_IMAGE") != "1",
    reason="Image moderation not enabled"
)
def test_image_moderator_blocks_nsfw(enable_image, mock_image):
    """Test moderator blocks NSFW content."""
    from seval.image_moderation.moderator import ImageModerator
    
    moderator = ImageModerator()
    
    # Mock the model to return high NSFW score
    mock_pipeline = MagicMock()
    mock_pipeline.return_value = [
        {"label": "normal", "score": 0.1},
        {"label": "nsfw", "score": 0.9},
    ]
    moderator._model = mock_pipeline
    
    result = moderator.moderate_bytes(mock_image)
    
    assert result.blocked is True  # 0.9 >= 0.5 threshold
    assert result.primary_category == "nsfw"
    assert result.categories["nsfw"] == 0.9


@pytest.mark.skipif(
    os.getenv("ENABLE_IMAGE") != "1",
    reason="Image moderation not enabled"
)
def test_image_moderator_violence_threshold(enable_image, mock_image):
    """Test moderator uses different threshold for violence."""
    from seval.image_moderation.moderator import ImageModerator
    
    moderator = ImageModerator(thresholds={
        "nsfw": 0.5,
        "violence": 0.7,
    })
    
    # Mock the model to return medium violence score
    mock_pipeline = MagicMock()
    mock_pipeline.return_value = [
        {"label": "violence", "score": 0.6},
        {"label": "normal", "score": 0.4},
    ]
    moderator._model = mock_pipeline
    
    result = moderator.moderate_bytes(mock_image)
    
    # 0.6 < 0.7, should not block
    assert result.blocked is False


@pytest.mark.skipif(
    os.getenv("ENABLE_IMAGE") != "1",
    reason="Image moderation not enabled"
)
def test_image_moderator_url_with_mock(enable_image):
    """Test moderating image from URL with mock."""
    from seval.image_moderation.moderator import ImageModerator
    
    moderator = ImageModerator()
    
    # Mock httpx and model
    mock_response = MagicMock()
    mock_response.content = b"fake_image_data"
    
    mock_pipeline = MagicMock()
    mock_pipeline.return_value = [
        {"label": "normal", "score": 0.9},
        {"label": "nsfw", "score": 0.1},
    ]
    moderator._model = mock_pipeline
    
    with patch("seval.image_moderation.moderator.httpx.get", return_value=mock_response):
        with patch("seval.image_moderation.moderator.Image.open"):
            with patch.object(moderator, "moderate_bytes") as mock_moderate:
                mock_moderate.return_value = ImageModerationResult(
                    categories={"normal": 0.9, "nsfw": 0.1},
                    blocked=False,
                    primary_category="normal",
                    latency_ms=50,
                    model_name=moderator.model_name
                )
                
                result = moderator.moderate_url("https://example.com/image.jpg")
                
                assert result.blocked is False
                mock_moderate.assert_called_once()


@pytest.mark.skipif(
    os.getenv("ENABLE_IMAGE") != "1",
    reason="Image moderation not enabled"
)
def test_image_moderator_error_handling(enable_image):
    """Test moderator handles errors gracefully."""
    from seval.image_moderation.moderator import ImageModerator
    
    moderator = ImageModerator()
    
    # Pass invalid image data
    result = moderator.moderate_bytes(b"not an image")
    
    assert result.primary_category == "error"
    assert result.blocked is False
    assert "error" in result.metadata


@pytest.mark.skipif(
    os.getenv("ENABLE_IMAGE") != "1",
    reason="Image moderation not enabled"
)
def test_global_moderator_singleton(enable_image):
    """Test global moderator is singleton."""
    from seval.image_moderation.moderator import get_global_moderator
    
    mod1 = get_global_moderator()
    mod2 = get_global_moderator()
    
    assert mod1 is mod2


@pytest.mark.skipif(
    os.getenv("ENABLE_IMAGE") != "1",
    reason="Image moderation not enabled"
)
def test_global_moderator_threshold_update(enable_image):
    """Test global moderator updates thresholds."""
    from seval.image_moderation.moderator import get_global_moderator
    
    mod = get_global_moderator(thresholds={"nsfw": 0.3})
    assert mod.thresholds["nsfw"] == 0.3


def test_image_result_to_dict():
    """Test ImageModerationResult to_dict conversion."""
    from seval.image_moderation.moderator import ImageModerationResult
    
    result = ImageModerationResult(
        categories={"nsfw": 0.8, "normal": 0.2},
        blocked=True,
        primary_category="nsfw",
        latency_ms=100,
        model_name="test-model",
        metadata={"key": "value"}
    )
    
    d = result.to_dict()
    
    assert d["categories"]["nsfw"] == 0.8
    assert d["blocked"] is True
    assert d["primary_category"] == "nsfw"
    assert d["latency_ms"] == 100
    assert d["model_name"] == "test-model"
    assert d["metadata"]["key"] == "value"


@pytest.mark.skipif(
    os.getenv("ENABLE_IMAGE") != "1",
    reason="Image moderation not enabled"
)
def test_image_moderator_lazy_loading(enable_image):
    """Test model is loaded lazily."""
    from seval.image_moderation.moderator import ImageModerator
    
    moderator = ImageModerator()
    
    # Model should not be loaded yet
    assert moderator._model is None
    
    # Mock the pipeline to avoid actual loading
    with patch("seval.image_moderation.moderator.pipeline") as mock_pipeline:
        mock_model = MagicMock()
        mock_pipeline.return_value = mock_model
        
        moderator._load_model()
        
        # Model should now be loaded
        assert moderator._model is not None
        mock_pipeline.assert_called_once()

