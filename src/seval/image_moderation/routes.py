"""FastAPI routes for image moderation."""

from __future__ import annotations

import logging
import hashlib
from typing import Any, Dict, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from . import is_enabled
from .moderator import get_global_moderator, ImageModerationResult

logger = logging.getLogger(__name__)

# Only create router if image moderation is enabled
router = APIRouter(prefix="", tags=["image_moderation"])


class ImageURLRequest(BaseModel):
    """Request model for image URL moderation."""
    url: str
    thresholds: Optional[Dict[str, float]] = None


def _load_thresholds_from_config() -> Dict[str, float]:
    """Load image thresholds from config.
    
    Returns:
        Dictionary of category thresholds
    """
    try:
        from utils.io_utils import load_config
        config = load_config()
        image_config = config.get("image_moderation", {})
        return image_config.get("thresholds", {
            "nsfw": 0.5,
            "violence": 0.7,
            "suggestive": 0.6,
        })
    except Exception as e:
        logger.warning(f"Failed to load image thresholds from config: {e}")
        return {
            "nsfw": 0.5,
            "violence": 0.7,
            "suggestive": 0.6,
        }


@router.post("/score-image")
async def score_image_endpoint(
    file: Optional[UploadFile] = File(None),
    url: Optional[str] = Form(None),
) -> JSONResponse:
    """Score an image for NSFW/violence content.
    
    Args:
        file: Uploaded image file (multipart)
        url: Image URL (alternative to file upload)
        
    Returns:
        JSON response with category scores and blocking decision
    """
    if not is_enabled():
        raise HTTPException(
            status_code=404,
            detail="Image moderation not enabled. Set ENABLE_IMAGE=1 to enable."
        )
    
    if not file and not url:
        raise HTTPException(
            status_code=400,
            detail="Either 'file' or 'url' must be provided"
        )
    
    if file and url:
        raise HTTPException(
            status_code=400,
            detail="Provide either 'file' or 'url', not both"
        )
    
    try:
        # Load thresholds from config
        thresholds = _load_thresholds_from_config()
        moderator = get_global_moderator(thresholds=thresholds)
        
        # Moderate image
        if file:
            image_bytes = await file.read()
            image_hash = hashlib.sha256(image_bytes).hexdigest()[:12]
            result = moderator.moderate_bytes(image_bytes)
        else:
            # url is not None here (checked above)
            image_hash = hashlib.sha256(url.encode()).hexdigest()[:12]  # type: ignore
            result = moderator.moderate_url(url)  # type: ignore
        
        # Log to audit (reuse existing pattern)
        try:
            from service import db
            db.create_audit_event(
                tenant_id="public",
                action="image.score",
                resource="image_moderator",
                user_id=None,
                context={
                    "image_hash": image_hash,
                    "primary_category": result.primary_category,
                    "blocked": result.blocked,
                    "source": "file" if file else "url"
                }
            )
        except Exception as audit_exc:
            logger.debug(f"Failed to create audit event: {audit_exc}")
        
        return JSONResponse(content=result.to_dict())
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Image moderation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Image moderation failed: {str(e)}"
        )

