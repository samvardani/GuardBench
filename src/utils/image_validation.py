"""Image validation utilities following OWASP guidelines."""

import imghdr
import os
from pathlib import Path
from typing import Optional, Tuple

# Allowed MIME types
ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
}

# Allowed file extensions
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}

# Maximum file size (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024


def validate_image_file(file_content: bytes, filename: str) -> Tuple[bool, Optional[str]]:
    """
    Validate an image file according to OWASP guidelines.
    
    Returns:
        (is_valid, error_message)
    """
    # Check file size
    if len(file_content) > MAX_FILE_SIZE:
        return False, f"File size exceeds maximum allowed size of {MAX_FILE_SIZE / (1024*1024):.1f}MB"
    
    if len(file_content) == 0:
        return False, "File is empty"
    
    # Check file extension
    file_ext = Path(filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        return False, f"File extension not allowed. Allowed extensions: {', '.join(ALLOWED_EXTENSIONS)}"
    
    # Validate file header (magic bytes) to prevent spoofing
    detected_type = imghdr.what(None, h=file_content)
    if not detected_type:
        return False, "File does not appear to be a valid image"
    
    # Map imghdr types to MIME types
    imghdr_to_mime = {
        "jpeg": "image/jpeg",
        "jpg": "image/jpeg",
        "png": "image/png",
    }
    
    mime_type = imghdr_to_mime.get(detected_type)
    if not mime_type or mime_type not in ALLOWED_MIME_TYPES:
        return False, f"Image type not allowed. Detected: {detected_type}"
    
    # Verify extension matches detected type
    if detected_type == "jpeg" and file_ext not in {".jpg", ".jpeg"}:
        return False, "File extension does not match image type"
    if detected_type == "png" and file_ext != ".png":
        return False, "File extension does not match image type"
    
    return True, None


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent directory traversal and other attacks.
    
    Removes path components and dangerous characters.
    """
    # Remove path components
    filename = os.path.basename(filename)
    
    # Remove dangerous characters
    dangerous_chars = ['/', '\\', '..', '<', '>', ':', '"', '|', '?', '*']
    for char in dangerous_chars:
        filename = filename.replace(char, '_')
    
    # Limit length
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:255 - len(ext)] + ext
    
    return filename


def get_mime_type(file_content: bytes) -> Optional[str]:
    """Get MIME type from file content."""
    detected_type = imghdr.what(None, h=file_content)
    if not detected_type:
        return None
    
    imghdr_to_mime = {
        "jpeg": "image/jpeg",
        "jpg": "image/jpeg",
        "png": "image/png",
    }
    
    return imghdr_to_mime.get(detected_type)

