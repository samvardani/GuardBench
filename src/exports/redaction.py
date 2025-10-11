"""Deep secret redaction for export data.

Recursively walks data structures and redacts sensitive keys matching patterns.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Pattern, Set

logger = logging.getLogger(__name__)


class SecretRedactor:
    """Recursive secret redaction for nested data structures.
    
    Features:
    - Pattern-based key matching (case-insensitive)
    - Recursive walk through dicts, lists, tuples
    - Preserves data structure
    - Tracks redacted keys for logging
    """
    
    # Default patterns for sensitive keys (case-insensitive)
    DEFAULT_PATTERNS = [
        r"key",
        r"token",
        r"secret",
        r"pwd",
        r"password",
        r"client_secret",
        r"api_key",
        r"auth",
        r"bearer",
        r"credential",
    ]
    
    def __init__(self, patterns: Optional[List[str]] = None, redacted_text: str = "***REDACTED***"):
        """Initialize redactor.
        
        Args:
            patterns: List of regex patterns to match (case-insensitive)
            redacted_text: Text to replace secrets with
        """
        self.patterns = patterns or self.DEFAULT_PATTERNS
        self.redacted_text = redacted_text
        
        # Compile patterns (case-insensitive)
        self.compiled_patterns: List[Pattern[str]] = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.patterns
        ]
        
        self.redacted_keys: Set[str] = set()
    
    def is_sensitive_key(self, key: str) -> bool:
        """Check if key matches sensitive patterns.
        
        Args:
            key: Key to check
            
        Returns:
            True if sensitive
        """
        for pattern in self.compiled_patterns:
            if pattern.search(key):
                return True
        return False
    
    def redact(self, data: Any) -> Any:
        """Recursively redact secrets from data.
        
        Args:
            data: Data to redact (dict, list, or primitive)
            
        Returns:
            Redacted copy of data
        """
        if isinstance(data, dict):
            return self._redact_dict(data)
        elif isinstance(data, list):
            return self._redact_list(data)
        elif isinstance(data, tuple):
            return tuple(self._redact_list(list(data)))
        else:
            # Primitives pass through
            return data
    
    def _redact_dict(self, d: Dict[str, Any]) -> Dict[str, Any]:
        """Redact secrets from dictionary.
        
        Args:
            d: Dictionary to redact
            
        Returns:
            Redacted dictionary
        """
        result = {}
        
        for key, value in d.items():
            if self.is_sensitive_key(key):
                # Redact the value
                result[key] = self.redacted_text
                self.redacted_keys.add(key)
            else:
                # Recursively process value
                result[key] = self.redact(value)
        
        return result
    
    def _redact_list(self, lst: List[Any]) -> List[Any]:
        """Redact secrets from list.
        
        Args:
            lst: List to redact
            
        Returns:
            Redacted list
        """
        return [self.redact(item) for item in lst]
    
    def get_redacted_keys(self) -> Set[str]:
        """Get set of keys that were redacted.
        
        Returns:
            Set of redacted key names
        """
        return self.redacted_keys.copy()


def redact_secrets(data: Any, patterns: Optional[List[str]] = None) -> Any:
    """Convenience function to redact secrets from data.
    
    Args:
        data: Data to redact
        patterns: Optional custom patterns
        
    Returns:
        Redacted copy of data
    """
    redactor = SecretRedactor(patterns=patterns)
    redacted = redactor.redact(data)
    
    if redactor.redacted_keys:
        logger.info(f"Redacted {len(redactor.redacted_keys)} secret keys: {sorted(redactor.redacted_keys)}")
    
    return redacted


__all__ = ["SecretRedactor", "redact_secrets"]

