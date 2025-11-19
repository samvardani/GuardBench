"""Secure image upload handler for staging platform."""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from service.api import AuthContext, require_auth, require_any_role
from service.staging_db import create_job_image, get_job, list_job_images
from service.staging_models import ImageUploadResponse
from utils.image_validation import get_mime_type, sanitize_filename, validate_image_file

router = APIRouter(prefix="/api/staging", tags=["staging"])

# Storage configuration
STORAGE_ROOT = Path(os.getenv("STORAGE_ROOT", "uploads/staging"))
STORAGE_ROOT.mkdir(parents=True, exist_ok=True)

# Base URL for serving images (can be configured)
BASE_URL = os.getenv("STORAGE_BASE_URL", "/uploads/staging")


def _generate_unique_filename(original_filename: str) -> str:
    """Generate a unique filename to prevent collisions."""
    ext = Path(original_filename).suffix.lower()
    unique_id = uuid.uuid4().hex[:16]
    return f"{unique_id}{ext}"


def _save_file(file_content: bytes, filename: str, job_id: str) -> tuple[str, str]:
    """
    Save file to storage and return (file_path, url).
    
    For now, saves to local filesystem. Can be extended to use S3, Supabase Storage, etc.
    """
    # Create job-specific directory
    job_dir = STORAGE_ROOT / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    
    # Save original file
    file_path = job_dir / filename
    file_path.write_bytes(file_content)
    
    # Generate URL (relative path for now)
    url = f"{BASE_URL}/{job_id}/{filename}"
    
    return str(file_path), url


@router.post("/jobs/{job_id}/upload", response_model=ImageUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_job_image(
    job_id: str,
    file: UploadFile = File(...),
    image_type: str = "original",
    ctx: AuthContext = Depends(require_auth),
) -> Dict[str, Any]:
    """
    Upload an image for a staging job.
    
    - Clients can upload original images
    - Staff can upload staged images
    - OWASP-compliant validation
    """
    # Validate image_type
    if image_type not in ["original", "staged"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="image_type must be 'original' or 'staged'")
    
    # Verify job exists and user has access
    job = get_job(job_id, ctx.tenant_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    
    # Role-based access control
    if ctx.role == "client":
        if job.get("client_id") != ctx.user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        if image_type != "original":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Clients can only upload original images")
    elif ctx.role == "staff":
        if job.get("assigned_staff_id") != ctx.user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        if image_type != "staged":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Staff can only upload staged images")
    
    # Read file content
    try:
        file_content = await file.read()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to read file: {str(e)}")
    
    # Validate file
    is_valid, error_msg = validate_image_file(file_content, file.filename or "unknown")
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg or "Invalid image file")
    
    # Sanitize filename
    sanitized_filename = sanitize_filename(file.filename or "image.jpg")
    unique_filename = _generate_unique_filename(sanitized_filename)
    
    # Get MIME type
    mime_type = get_mime_type(file_content)
    
    # Save file
    try:
        file_path, image_url = _save_file(file_content, unique_filename, job_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to save file: {str(e)}")
    
    # Create database record
    image_record = create_job_image(
        tenant_id=ctx.tenant_id,
        job_id=job_id,
        image_url=image_url,
        filename=unique_filename,
        image_type=image_type,
        file_size_bytes=len(file_content),
        mime_type=mime_type,
        uploaded_by=ctx.user_id,
    )
    
    return image_record


@router.post("/jobs/{job_id}/upload/batch", response_model=List[ImageUploadResponse], status_code=status.HTTP_201_CREATED)
async def upload_job_images_batch(
    job_id: str,
    files: List[UploadFile] = File(...),
    image_type: str = "original",
    ctx: AuthContext = Depends(require_auth),
) -> List[Dict[str, Any]]:
    """
    Upload multiple images for a staging job.
    
    Maximum 10 files per request.
    """
    if len(files) > 10:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Maximum 10 files per upload")
    
    # Verify job exists and user has access
    job = get_job(job_id, ctx.tenant_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    
    # Role-based access control
    if ctx.role == "client":
        if job.get("client_id") != ctx.user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        if image_type != "original":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Clients can only upload original images")
    elif ctx.role == "staff":
        if job.get("assigned_staff_id") != ctx.user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        if image_type != "staged":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Staff can only upload staged images")
    
    uploaded_images = []
    errors = []
    
    for file in files:
        try:
            # Read file content
            file_content = await file.read()
            
            # Validate file
            is_valid, error_msg = validate_image_file(file_content, file.filename or "unknown")
            if not is_valid:
                errors.append(f"{file.filename}: {error_msg}")
                continue
            
            # Sanitize filename
            sanitized_filename = sanitize_filename(file.filename or "image.jpg")
            unique_filename = _generate_unique_filename(sanitized_filename)
            
            # Get MIME type
            mime_type = get_mime_type(file_content)
            
            # Save file
            file_path, image_url = _save_file(file_content, unique_filename, job_id)
            
            # Create database record
            image_record = create_job_image(
                tenant_id=ctx.tenant_id,
                job_id=job_id,
                image_url=image_url,
                filename=unique_filename,
                image_type=image_type,
                file_size_bytes=len(file_content),
                mime_type=mime_type,
                uploaded_by=ctx.user_id,
            )
            uploaded_images.append(image_record)
        except Exception as e:
            errors.append(f"{file.filename}: {str(e)}")
    
    if errors and not uploaded_images:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"All uploads failed: {', '.join(errors)}")
    
    return uploaded_images


@router.get("/jobs/{job_id}/images", response_model=List[ImageUploadResponse])
def list_job_images_endpoint(
    job_id: str,
    image_type: Optional[str] = None,
    ctx: AuthContext = Depends(require_auth),
) -> List[Dict[str, Any]]:
    """List all images for a job."""
    # Verify job exists and user has access
    job = get_job(job_id, ctx.tenant_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    
    # Role-based access control
    if ctx.role == "client" and job.get("client_id") != ctx.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    if ctx.role == "staff" and job.get("assigned_staff_id") != ctx.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    images = list_job_images(job_id, ctx.tenant_id, image_type=image_type)
    return images

