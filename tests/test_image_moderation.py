"""Tests for image moderation with CI-safe stub."""

from __future__ import annotations

import os
import pytest
from pathlib import Path
from tempfile import NamedTemporaryFile
from PIL import Image

from image_moderation import (
    ImageModerationProvider,
    ImageModerationResult,
    StubImageModerator,
    get_image_moderator,
)


class TestStubImageModerator:
    """Test lightweight stub moderator (fast, no model)."""
    
    def test_stub_creation(self):
        """Test stub moderator creation."""
        moderator = StubImageModerator()
        assert moderator is not None
    
    def test_stub_safe_image(self, tmp_path):
        """Test stub returns safe for normal image."""
        moderator = StubImageModerator()
        
        # Create dummy image
        image_path = tmp_path / "safe_image.png"
        self._create_dummy_image(image_path)
        
        # Moderate
        result = moderator.moderate(image_path)
        
        # Assertions
        assert result.is_safe is True
        assert result.provider == "stub"
        assert "normal" in result.categories
        assert result.categories["normal"] > 0.9
        assert len(result.flagged_categories) == 0
        assert result.confidence > 0.9
    
    def test_stub_nsfw_image(self, tmp_path):
        """Test stub returns unsafe for NSFW image."""
        moderator = StubImageModerator()
        
        # Create dummy image with NSFW in filename
        image_path = tmp_path / "nsfw_image.png"
        self._create_dummy_image(image_path)
        
        # Moderate
        result = moderator.moderate(image_path)
        
        # Assertions
        assert result.is_safe is False
        assert result.provider == "stub"
        assert "nsfw" in result.categories
        assert result.categories["nsfw"] > 0.9
        assert "nsfw" in result.flagged_categories
        assert result.confidence > 0.9
    
    def test_stub_violence_image(self, tmp_path):
        """Test stub returns unsafe for violence image."""
        moderator = StubImageModerator()
        
        # Create dummy image with violence in filename
        image_path = tmp_path / "violence_image.png"
        self._create_dummy_image(image_path)
        
        # Moderate
        result = moderator.moderate(image_path)
        
        # Assertions
        assert result.is_safe is False
        assert result.provider == "stub"
        assert "violence" in result.categories
        assert result.categories["violence"] >= 0.9
        assert "violence" in result.flagged_categories
        assert result.confidence >= 0.9
    
    def test_stub_deterministic(self, tmp_path):
        """Test stub returns deterministic results."""
        moderator = StubImageModerator()
        
        # Create dummy image
        image_path = tmp_path / "test_image.png"
        self._create_dummy_image(image_path)
        
        # Run multiple times
        results = [moderator.moderate(image_path) for _ in range(5)]
        
        # All results should be identical
        for result in results[1:]:
            assert result.is_safe == results[0].is_safe
            assert result.categories == results[0].categories
            assert result.flagged_categories == results[0].flagged_categories
            assert result.confidence == results[0].confidence
    
    @staticmethod
    def _create_dummy_image(path: Path):
        """Create a dummy image for testing."""
        img = Image.new("RGB", (100, 100), color="red")
        img.save(path)


class TestImageModerationFactory:
    """Test image moderator factory."""
    
    def test_get_moderator_test_mode(self, monkeypatch):
        """Test factory returns stub in TEST_MODE."""
        monkeypatch.setenv("TEST_MODE", "1")
        monkeypatch.setenv("ENABLE_IMAGE", "1")
        
        moderator = get_image_moderator()
        
        assert isinstance(moderator, StubImageModerator)
    
    def test_get_moderator_disabled(self, monkeypatch):
        """Test factory returns stub when ENABLE_IMAGE=0."""
        monkeypatch.setenv("TEST_MODE", "0")
        monkeypatch.setenv("ENABLE_IMAGE", "0")
        
        moderator = get_image_moderator()
        
        assert isinstance(moderator, StubImageModerator)
    
    @pytest.mark.slow
    @pytest.mark.image
    def test_get_moderator_production(self, monkeypatch):
        """Test factory returns HF model in production (slow)."""
        monkeypatch.setenv("TEST_MODE", "0")
        monkeypatch.setenv("ENABLE_IMAGE", "1")
        
        try:
            from image_moderation.provider import HuggingFaceImageModerator
            moderator = get_image_moderator()
            assert isinstance(moderator, HuggingFaceImageModerator)
        except ImportError:
            pytest.skip("transformers not installed")


class TestImageModerationThresholds:
    """Test threshold-based gating (deterministic)."""
    
    def test_threshold_gate_safe(self, tmp_path):
        """Test threshold gate passes safe images."""
        moderator = StubImageModerator()
        
        image_path = tmp_path / "safe.png"
        TestStubImageModerator._create_dummy_image(image_path)
        
        result = moderator.moderate(image_path)
        
        # Threshold: 0.5
        threshold = 0.5
        
        # Should pass (all scores < 0.5 except "normal")
        flagged = [
            cat for cat, score in result.categories.items()
            if cat != "normal" and score > threshold
        ]
        
        assert len(flagged) == 0
    
    def test_threshold_gate_unsafe(self, tmp_path):
        """Test threshold gate blocks unsafe images."""
        moderator = StubImageModerator()
        
        image_path = tmp_path / "nsfw_content.png"
        TestStubImageModerator._create_dummy_image(image_path)
        
        result = moderator.moderate(image_path)
        
        # Threshold: 0.5
        threshold = 0.5
        
        # Should block (nsfw score > 0.5)
        flagged = [
            cat for cat, score in result.categories.items()
            if cat != "normal" and score > threshold
        ]
        
        assert len(flagged) > 0
        assert "nsfw" in flagged


class TestImageModerationResult:
    """Test ImageModerationResult dataclass."""
    
    def test_result_creation(self):
        """Test creating result."""
        result = ImageModerationResult(
            is_safe=True,
            categories={"normal": 0.98, "nsfw": 0.02},
            flagged_categories=[],
            confidence=0.98,
            provider="stub"
        )
        
        assert result.is_safe is True
        assert result.provider == "stub"
        assert result.confidence == 0.98


@pytest.mark.slow
@pytest.mark.image
class TestHuggingFaceImageModerator:
    """Test HuggingFace model (slow, downloads model)."""
    
    def test_hf_moderator_creation(self):
        """Test creating HF moderator (requires model download)."""
        try:
            from image_moderation.provider import HuggingFaceImageModerator
            moderator = HuggingFaceImageModerator()
            assert moderator is not None
        except ImportError:
            pytest.skip("transformers not installed")
    
    def test_hf_moderate_image(self, tmp_path):
        """Test HF moderation (requires model)."""
        try:
            from image_moderation.provider import HuggingFaceImageModerator
            
            moderator = HuggingFaceImageModerator()
            
            # Create test image
            image_path = tmp_path / "test.png"
            TestStubImageModerator._create_dummy_image(image_path)
            
            # Moderate
            result = moderator.moderate(image_path)
            
            # Assertions
            assert isinstance(result, ImageModerationResult)
            assert result.provider == "huggingface"
            assert "categories" in result.__dict__
        
        except ImportError:
            pytest.skip("transformers not installed")


if __name__ == "__main__":
    # Run fast tests only (skip slow)
    pytest.main([__file__, "-v", "-m", "not slow"])

