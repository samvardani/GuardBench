"""Token redaction utilities for logging and responses."""

from __future__ import annotations

import logging
import re
from typing import Any, Dict

logger = logging.getLogger(__name__)


class TokenRedactor:
    """Redacts sensitive tokens from logs and responses."""
    
    # Patterns for common token formats
    PATTERNS = [
        # Slack tokens
        (r'xox[baprs]-[0-9a-zA-Z\-]+', 'xoxb-****'),
        # OAuth tokens
        (r'Bearer\s+[A-Za-z0-9\-._~+/]+=*', 'Bearer ****'),
        # Generic tokens (long alphanumeric strings)
        (r'["\']token["\']\s*:\s*["\']([^"\']{20,})["\']', '"token": "****"'),
        (r'["\']access_token["\']\s*:\s*["\']([^"\']{20,})["\']', '"access_token": "****"'),
        # Authorization headers
        (r'Authorization:\s*Bearer\s+[^\s]+', 'Authorization: Bearer ****'),
    ]
    
    @classmethod
    def redact(cls, text: str) -> str:
        """Redact tokens from text.
        
        Args:
            text: Text potentially containing tokens
            
        Returns:
            Text with tokens redacted
        """
        if not text:
            return text
        
        result = text
        
        for pattern, replacement in cls.PATTERNS:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        
        return result
    
    @classmethod
    def redact_dict(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Redact tokens from dictionary.
        
        Args:
            data: Dictionary potentially containing tokens
            
        Returns:
            Dictionary with tokens redacted
        """
        if not data:
            return data
        
        result = data.copy()
        
        # Redact known token fields
        sensitive_fields = [
            'token',
            'access_token',
            'refresh_token',
            'api_key',
            'secret',
            'password',
            'authorization'
        ]
        
        for key in result:
            if any(field in key.lower() for field in sensitive_fields):
                if isinstance(result[key], str) and len(result[key]) > 8:
                    # Keep first 4 and last 4 characters
                    result[key] = result[key][:4] + '****' + result[key][-4:]
        
        return result


def redact_tokens(text: str) -> str:
    """Convenience function to redact tokens from text.
    
    Args:
        text: Text potentially containing tokens
        
    Returns:
        Text with tokens redacted
    """
    return TokenRedactor.redact(text)


# Custom logging filter to redact tokens
class TokenRedactionFilter(logging.Filter):
    """Logging filter that redacts tokens from log messages."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Filter log record to redact tokens.
        
        Args:
            record: Log record
            
        Returns:
            True (always allow record, but modify it)
        """
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            record.msg = TokenRedactor.redact(record.msg)
        
        if hasattr(record, 'args') and record.args:
            # Redact arguments
            redacted_args = []
            for arg in record.args:
                if isinstance(arg, str):
                    redacted_args.append(TokenRedactor.redact(arg))
                else:
                    redacted_args.append(arg)
            record.args = tuple(redacted_args)
        
        return True


def install_redaction_filter():
    """Install token redaction filter on root logger."""
    root_logger = logging.getLogger()
    
    # Check if filter already installed
    for f in root_logger.filters:
        if isinstance(f, TokenRedactionFilter):
            return
    
    root_logger.addFilter(TokenRedactionFilter())
    logger.info("Token redaction filter installed")


__all__ = [
    "TokenRedactor",
    "redact_tokens",
    "TokenRedactionFilter",
    "install_redaction_filter",
]

