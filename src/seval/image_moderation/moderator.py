"""Image moderation using lightweight models."""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional
from io import BytesIO

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


@dataclass
class ImageModerationResult:
    """Result from image moderation."""
    
    categories: Dict[str, float]
    blocked: bool
    primary_category: str
    latency_ms: int
    model_name: str
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "categories": self.categories,
            "blocked": self.blocked,
            "primary_category": self.primary_category,
            "latency_ms": self.latency_ms,
            "model_name": self.model_name,
            "metadata": self.metadata or {},
        }


class ImageModerator:
    """Image moderation using CLIP-based NSFW detection."""
    
    def __init__(
        self,
        model_name: str = "Falconsai/nsfw_image_detection",
        cache_dir: Optional[str] = None,
        thresholds: Optional[Dict[str, float]] = None
    ):
        """Initialize image moderator.
        
        Args:
            model_name: HuggingFace model name
            cache_dir: Directory for model cache
            thresholds: Category thresholds for blocking
        """
        self.model_name = model_name
        self.cache_dir = cache_dir or os.path.expanduser("~/.cache/seval-image-models")
        self.thresholds = thresholds or {
            "nsfw": 0.5,
            "violence": 0.7,
            "suggestive": 0.6,
        }
        
        self._model = None
        self._processor = None
        
        logger.info(f"ImageModerator initialized (model={model_name}, lazy_load=True)")
    
    def _load_model(self) -> None:
        """Lazy load the model and processor."""
        if self._model is not None:
            return
        
        try:
            from transformers import pipeline
            
            logger.info(f"Loading image moderation model: {self.model_name}")
            start = time.time()
            
            # Use HuggingFace pipeline for image classification
            self._model = pipeline(
                "image-classification",
                model=self.model_name,
                cache_dir=self.cache_dir
            )
            
            elapsed = time.time() - start
            logger.info(f"Model loaded in {elapsed:.2f}s")
        
        except ImportError as e:
            logger.error("transformers or torch not installed. Install with: pip install transformers torch pillow")
            raise RuntimeError(
                "Image moderation requires: pip install transformers torch pillow"
            ) from e
        except Exception as e:
            logger.error(f"Failed to load model {self.model_name}: {e}")
            raise
    
    def moderate_image(
        self,
        image: Image.Image,
        **kwargs: Any
    ) -> ImageModerationResult:
        """Moderate an image.
        
        Args:
            image: PIL Image object
            **kwargs: Additional parameters
            
        Returns:
            ImageModerationResult with scores and decision
        """
        self._load_model()
        
        start_time = time.perf_counter()
        
        try:
            # Run inference
            results = self._model(image)
            
            # Convert to our format
            categories = {}
            for item in results:
                label = item["label"].lower()
                score = float(item["score"])
                categories[label] = score
            
            # Determine primary category (highest score)
            primary_category = max(categories, key=categories.get) if categories else "unknown"
            primary_score = categories.get(primary_category, 0.0)
            
            # Check if blocked
            blocked = False
            for category, score in categories.items():
                threshold = self.thresholds.get(category, 0.5)
                if score >= threshold:
                    blocked = True
                    break
            
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            
            return ImageModerationResult(
                categories=categories,
                blocked=blocked,
                primary_category=primary_category,
                latency_ms=latency_ms,
                model_name=self.model_name,
                metadata={
                    "primary_score": primary_score,
                    "thresholds": self.thresholds,
                }
            )
        
        except Exception as e:
            logger.error(f"Image moderation failed: {e}")
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            
            # Return safe fallback
            return ImageModerationResult(
                categories={"error": 1.0},
                blocked=False,
                primary_category="error",
                latency_ms=latency_ms,
                model_name=self.model_name,
                metadata={"error": str(e)}
            )
    
    def moderate_bytes(self, image_bytes: bytes, **kwargs: Any) -> ImageModerationResult:
        """Moderate image from bytes.
        
        Args:
            image_bytes: Image bytes
            **kwargs: Additional parameters
            
        Returns:
            ImageModerationResult
        """
        try:
            image = Image.open(BytesIO(image_bytes))
            # Convert to RGB if needed
            if image.mode != "RGB":
                image = image.convert("RGB")
            return self.moderate_image(image, **kwargs)
        except Exception as e:
            logger.error(f"Failed to load image from bytes: {e}")
            return ImageModerationResult(
                categories={"error": 1.0},
                blocked=False,
                primary_category="error",
                latency_ms=0,
                model_name=self.model_name,
                metadata={"error": str(e)}
            )
    
    def moderate_url(self, url: str, **kwargs: Any) -> ImageModerationResult:
        """Moderate image from URL.
        
        Args:
            url: Image URL
            **kwargs: Additional parameters
            
        Returns:
            ImageModerationResult
        """
        try:
            import httpx
            
            response = httpx.get(url, timeout=10.0)
            response.raise_for_status()
            
            return self.moderate_bytes(response.content, **kwargs)
        
        except Exception as e:
            logger.error(f"Failed to load image from URL {url}: {e}")
            return ImageModerationResult(
                categories={"error": 1.0},
                blocked=False,
                primary_category="error",
                latency_ms=0,
                model_name=self.model_name,
                metadata={"error": str(e)}
            )
    
    def health_check(self) -> bool:
        """Check if moderator is healthy.
        
        Returns:
            True if model can be loaded
        """
        try:
            self._load_model()
            return self._model is not None
        except Exception:
            return False


# Global moderator instance
_global_moderator: Optional[ImageModerator] = None


def get_global_moderator(
    thresholds: Optional[Dict[str, float]] = None
) -> ImageModerator:
    """Get or create global image moderator.
    
    Args:
        thresholds: Optional thresholds to set
        
    Returns:
        Global ImageModerator instance
    """
    global _global_moderator
    if _global_moderator is None:
        _global_moderator = ImageModerator(thresholds=thresholds)
    elif thresholds:
        # Update thresholds if provided
        _global_moderator.thresholds = thresholds
    return _global_moderator

