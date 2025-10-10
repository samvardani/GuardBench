"""Stub image moderator for CI-safe testing."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Union

from .provider import ImageModerationProvider, ImageModerationResult

logger = logging.getLogger(__name__)


class StubImageModerator(ImageModerationProvider):
    """Lightweight stub moderator for testing.
    
    Returns deterministic results based on filename patterns.
    No model loading, no network access, fast execution.
    """
    
    def __init__(self):
        """Initialize stub moderator."""
        logger.info("StubImageModerator initialized (lightweight, no model)")
    
    def moderate(self, image_path: Union[str, Path]) -> ImageModerationResult:
        """Moderate image with deterministic stub logic.
        
        Args:
            image_path: Path to image (filename pattern determines result)
            
        Returns:
            ImageModerationResult with fixed logits
        """
        image_path = Path(image_path)
        filename = image_path.name.lower()
        
        # Deterministic logic based on filename
        if "nsfw" in filename or "unsafe" in filename:
            # Unsafe image
            categories = {
                "nsfw": 0.95,
                "normal": 0.05
            }
            flagged_categories = ["nsfw"]
            is_safe = False
            confidence = 0.95
        
        elif "violence" in filename:
            # Violence
            categories = {
                "violence": 0.90,
                "normal": 0.10
            }
            flagged_categories = ["violence"]
            is_safe = False
            confidence = 0.90
        
        else:
            # Safe image (default)
            categories = {
                "normal": 0.98,
                "nsfw": 0.02
            }
            flagged_categories = []
            is_safe = True
            confidence = 0.98
        
        return ImageModerationResult(
            is_safe=is_safe,
            categories=categories,
            flagged_categories=flagged_categories,
            confidence=confidence,
            provider="stub"
        )


__all__ = ["StubImageModerator"]

