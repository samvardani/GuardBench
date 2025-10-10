"""Image moderation provider interface."""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Union

logger = logging.getLogger(__name__)


@dataclass
class ImageModerationResult:
    """Result from image moderation."""
    
    is_safe: bool
    categories: Dict[str, float]  # Category scores (0.0-1.0)
    flagged_categories: list[str]
    confidence: float
    provider: str = "unknown"


class ImageModerationProvider(ABC):
    """Abstract interface for image moderation providers."""
    
    @abstractmethod
    def moderate(self, image_path: Union[str, Path]) -> ImageModerationResult:
        """Moderate an image.
        
        Args:
            image_path: Path to image file
            
        Returns:
            ImageModerationResult
        """
        pass


class HuggingFaceImageModerator(ImageModerationProvider):
    """HuggingFace model-based image moderator.
    
    Only loaded when ENABLE_IMAGE=1 and not in test mode.
    """
    
    def __init__(self, model_name: str = "Falconsai/nsfw_image_detection"):
        """Initialize HuggingFace moderator.
        
        Args:
            model_name: HuggingFace model name
        """
        try:
            from transformers import pipeline
            from PIL import Image
        except ImportError:
            raise ImportError(
                "transformers and Pillow required for image moderation. "
                "Install with: pip install transformers pillow torch"
            )
        
        self.model_name = model_name
        self.pipeline = pipeline("image-classification", model=model_name)
        
        logger.info(f"HuggingFace image moderator loaded: {model_name}")
    
    def moderate(self, image_path: Union[str, Path]) -> ImageModerationResult:
        """Moderate image using HuggingFace model.
        
        Args:
            image_path: Path to image
            
        Returns:
            ImageModerationResult
        """
        from PIL import Image
        
        # Load image
        image = Image.open(image_path)
        
        # Run model
        results = self.pipeline(image)
        
        # Parse results
        categories = {}
        flagged_categories = []
        
        for result in results:
            label = result["label"]
            score = result["score"]
            
            categories[label] = score
            
            # Threshold: 0.5
            if score > 0.5:
                flagged_categories.append(label)
        
        is_safe = len(flagged_categories) == 0
        confidence = max(categories.values()) if categories else 0.0
        
        return ImageModerationResult(
            is_safe=is_safe,
            categories=categories,
            flagged_categories=flagged_categories,
            confidence=confidence,
            provider="huggingface"
        )


def get_image_moderator() -> ImageModerationProvider:
    """Get image moderator based on configuration.
    
    Returns:
        ImageModerationProvider instance
    """
    # Check if image moderation enabled
    enable_image = os.getenv("ENABLE_IMAGE", "0") == "1"
    test_mode = os.getenv("TEST_MODE", "0") == "1"
    
    # Use stub in test mode
    if test_mode or not enable_image:
        from .stub import StubImageModerator
        logger.info("Using StubImageModerator (TEST_MODE or ENABLE_IMAGE=0)")
        return StubImageModerator()
    
    # Use HuggingFace model in production
    logger.info("Using HuggingFaceImageModerator")
    return HuggingFaceImageModerator()


__all__ = [
    "ImageModerationProvider",
    "ImageModerationResult",
    "HuggingFaceImageModerator",
    "get_image_moderator",
]

