"""Report builders with streaming support for large exports."""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Dict, Generator

from .redaction import redact_secrets

logger = logging.getLogger(__name__)


class ReportBuilder:
    """Build reports with optional secret redaction.
    
    For small reports (< 1MB), returns complete data.
    For large reports, use StreamingReportBuilder.
    """
    
    SIZE_THRESHOLD = 1024 * 1024  # 1MB
    
    def __init__(self, data: Dict[str, Any], redact: bool = True):
        """Initialize report builder.
        
        Args:
            data: Report data
            redact: Whether to redact secrets
        """
        self.data = data
        self.redact = redact
    
    def build_json(self) -> str:
        """Build JSON report.
        
        Returns:
            JSON string
        """
        # Redact secrets if requested
        data = redact_secrets(self.data) if self.redact else self.data
        
        # Serialize
        json_str = json.dumps(data, indent=2)
        
        return json_str
    
    def build_markdown(self) -> str:
        """Build Markdown report.
        
        Returns:
            Markdown string
        """
        # Redact secrets if requested
        data = redact_secrets(self.data) if self.redact else self.data
        
        # Build markdown
        lines = []
        lines.append("# Safety Evaluation Report")
        lines.append("")
        
        # Add sections
        for key, value in data.items():
            lines.append(f"## {key.replace('_', ' ').title()}")
            lines.append("")
            
            if isinstance(value, dict):
                for k, v in value.items():
                    lines.append(f"- **{k}**: {v}")
            elif isinstance(value, list):
                for item in value:
                    lines.append(f"- {item}")
            else:
                lines.append(str(value))
            
            lines.append("")
        
        return "\n".join(lines)
    
    def estimate_size(self) -> int:
        """Estimate report size in bytes.
        
        Returns:
            Estimated size
        """
        # Rough estimate from JSON serialization
        json_str = self.build_json()
        return len(json_str.encode('utf-8'))
    
    def compute_etag(self) -> str:
        """Compute ETag for report.
        
        Returns:
            ETag hash
        """
        json_str = self.build_json()
        hash_obj = hashlib.sha256(json_str.encode('utf-8'))
        return hash_obj.hexdigest()[:16]


class StreamingReportBuilder:
    """Build reports with streaming for large data.
    
    Yields chunks to keep memory bounded.
    """
    
    CHUNK_SIZE = 8192  # 8KB chunks
    
    def __init__(self, data: Dict[str, Any], redact: bool = True):
        """Initialize streaming builder.
        
        Args:
            data: Report data
            redact: Whether to redact secrets
        """
        self.data = data
        self.redact = redact
    
    def stream_json(self) -> Generator[str, None, None]:
        """Stream JSON report in chunks.
        
        Yields:
            JSON chunks
        """
        # Redact secrets if requested
        data = redact_secrets(self.data) if self.redact else self.data
        
        # Stream JSON
        # For very large data, consider using ijson for true streaming
        # For now, serialize and chunk
        json_str = json.dumps(data, indent=2)
        
        # Yield in chunks
        for i in range(0, len(json_str), self.CHUNK_SIZE):
            chunk = json_str[i:i + self.CHUNK_SIZE]
            yield chunk
    
    def stream_markdown(self) -> Generator[str, None, None]:
        """Stream Markdown report in chunks.
        
        Yields:
            Markdown chunks
        """
        # Redact secrets if requested
        data = redact_secrets(self.data) if self.redact else self.data
        
        # Build markdown in chunks
        yield "# Safety Evaluation Report\n\n"
        
        for key, value in data.items():
            # Section header
            yield f"## {key.replace('_', ' ').title()}\n\n"
            
            # Section content
            if isinstance(value, dict):
                for k, v in value.items():
                    yield f"- **{k}**: {v}\n"
            elif isinstance(value, list):
                for item in value:
                    yield f"- {item}\n"
            else:
                yield f"{value}\n"
            
            yield "\n"


__all__ = ["ReportBuilder", "StreamingReportBuilder"]

