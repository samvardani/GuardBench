"""Optional image moderation module."""

from __future__ import annotations

import os

__all__ = ["ImageModerator", "ImageModerationResult", "is_enabled", "get_global_moderator"]


def is_enabled() -> bool:
    """Check if image moderation is enabled.
    
    Returns:
        True if ENABLE_IMAGE=1 environment variable is set
    """
    return os.getenv("ENABLE_IMAGE", "0") == "1"


# Always import for testing, but conditionally load model
try:
    from .moderator import ImageModerator, ImageModerationResult, get_global_moderator
except ImportError:
    ImageModerator = None  # type: ignore
    ImageModerationResult = None  # type: ignore
    get_global_moderator = None  # type: ignore

