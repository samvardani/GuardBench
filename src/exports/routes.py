"""Export routes with streaming and security headers."""

from __future__ import annotations

import logging
from typing import Dict, Any

from fastapi import APIRouter, Response
from fastapi.responses import StreamingResponse

from .report_builder import ReportBuilder, StreamingReportBuilder

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/exports", tags=["exports"])


def add_security_headers(response: Response, etag: str = None):
    """Add security headers to response.
    
    Args:
        response: Response object
        etag: Optional ETag value
    """
    # Cache control - no caching for sensitive data
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    
    # Prevent opening in browser (download only)
    response.headers["X-Download-Options"] = "noopen"
    response.headers["X-Content-Type-Options"] = "nosniff"
    
    # ETag for caching validation if provided
    if etag:
        response.headers["ETag"] = f'"{etag}"'


@router.get("/report.json")
async def export_json(
    sample_data: bool = False,
    redact: bool = True
) -> Response:
    """Export report as JSON.
    
    Args:
        sample_data: Use sample data for testing
        redact: Whether to redact secrets
        
    Returns:
        JSON response with security headers
    """
    # Get report data (in real app, fetch from database)
    data = _get_sample_data() if sample_data else _get_report_data()
    
    # Build report
    builder = ReportBuilder(data, redact=redact)
    
    # Check if streaming needed
    estimated_size = builder.estimate_size()
    
    if estimated_size > ReportBuilder.SIZE_THRESHOLD:
        # Stream large reports
        logger.info(f"Streaming large report ({estimated_size} bytes)")
        
        streaming_builder = StreamingReportBuilder(data, redact=redact)
        
        response = StreamingResponse(
            streaming_builder.stream_json(),
            media_type="application/json",
            headers={
                "Content-Disposition": "attachment; filename=report.json"
            }
        )
        
        add_security_headers(response)
        return response
    
    else:
        # Return complete report
        json_str = builder.build_json()
        etag = builder.compute_etag()
        
        response = Response(
            content=json_str,
            media_type="application/json",
            headers={
                "Content-Disposition": "attachment; filename=report.json"
            }
        )
        
        add_security_headers(response, etag=etag)
        return response


@router.get("/report.md")
async def export_markdown(
    sample_data: bool = False,
    redact: bool = True
) -> Response:
    """Export report as Markdown.
    
    Args:
        sample_data: Use sample data for testing
        redact: Whether to redact secrets
        
    Returns:
        Markdown response with security headers
    """
    # Get report data
    data = _get_sample_data() if sample_data else _get_report_data()
    
    # Build report
    builder = ReportBuilder(data, redact=redact)
    
    # Check if streaming needed
    estimated_size = builder.estimate_size()
    
    if estimated_size > ReportBuilder.SIZE_THRESHOLD:
        # Stream large reports
        logger.info(f"Streaming large markdown report ({estimated_size} bytes)")
        
        streaming_builder = StreamingReportBuilder(data, redact=redact)
        
        response = StreamingResponse(
            streaming_builder.stream_markdown(),
            media_type="text/markdown",
            headers={
                "Content-Disposition": "attachment; filename=report.md"
            }
        )
        
        add_security_headers(response)
        return response
    
    else:
        # Return complete report
        md_str = builder.build_markdown()
        etag = builder.compute_etag()
        
        response = Response(
            content=md_str,
            media_type="text/markdown",
            headers={
                "Content-Disposition": "attachment; filename=report.md"
            }
        )
        
        add_security_headers(response, etag=etag)
        return response


def _get_sample_data() -> Dict[str, Any]:
    """Get sample report data for testing.
    
    Returns:
        Sample data with nested secrets
    """
    return {
        "metadata": {
            "version": "1.0",
            "timestamp": "2025-01-01T00:00:00Z",
            "api_key": "secret_key_123",  # Should be redacted
        },
        "config": {
            "database_url": "postgresql://localhost/db",
            "slack_client_secret": "xoxb-secret-token",  # Should be redacted
            "slack_signing_secret": "signing_secret_456",  # Should be redacted
        },
        "results": [
            {
                "test": "test1",
                "score": 0.95,
                "auth_token": "Bearer abc123",  # Should be redacted
            },
            {
                "test": "test2",
                "score": 0.87,
                "password": "mypassword",  # Should be redacted
            }
        ],
        "summary": {
            "total_tests": 2,
            "passed": 2,
            "safe": True
        }
    }


def _get_report_data() -> Dict[str, Any]:
    """Get actual report data.
    
    In production, this would fetch from database.
    
    Returns:
        Report data
    """
    # Placeholder - in real app, fetch from database
    return _get_sample_data()


__all__ = ["router", "add_security_headers"]

