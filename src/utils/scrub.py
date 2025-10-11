"""Utilities for scrubbing sensitive data before persistence."""

from __future__ import annotations

import hashlib
import re
import math
from typing import Dict, Iterable, Optional

from utils.io_utils import load_config

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE_RE = re.compile(r"\b(?:\+?\d[\d\-\s]{7,}\d)\b")
_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_ENTROPY_RE = re.compile(r"[A-Za-z0-9+/=]{16,}")


def _privacy_config() -> Dict[str, object]:
    cfg = load_config() or {}
    privacy = cfg.get("privacy")
    if isinstance(privacy, dict):
        return privacy  # type: ignore[return-value]
    return {}


def privacy_mode_for(endpoint: Optional[str] = None) -> str:
    privacy = _privacy_config()
    default_mode = str(privacy.get("default_mode", "off")).lower()
    # legacy fallback
    cfg = load_config() or {}
    legacy = str(cfg.get("privacy_mode", default_mode or "off")).lower()
    mode = default_mode or legacy or "off"
    endpoints = privacy.get("endpoints") if isinstance(privacy.get("endpoints"), dict) else {}
    if endpoint and isinstance(endpoints, dict):
        override = endpoints.get(endpoint)
        if override:
            mode = str(override).lower()
    return "strict" if mode == "strict" else "off"


def _apply_custom_patterns(text: str) -> str:
    privacy = _privacy_config()
    patterns = privacy.get("custom_patterns", [])
    if not isinstance(patterns, list):
        return text
    cleaned = text
    for pattern in patterns:
        try:
            cleaned = re.sub(str(pattern), "[REDACTED_CUSTOM]", cleaned, flags=re.IGNORECASE)
        except re.error:
            continue
    return cleaned


def _redact_entropy(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        token = match.group(0)
        # Shannon entropy approximation
        freq = {ch: token.count(ch) for ch in set(token)}
        entropy = -sum((count / len(token)) * math.log(count / len(token), 2) for count in freq.values())
        has_alpha = any(c.isalpha() for c in token)
        has_digit = any(c.isdigit() for c in token)
        if entropy >= 3.0 and has_alpha and has_digit:
            return "[REDACTED_TOKEN]"
        return token

    return _ENTROPY_RE.sub(repl, text)


def scrub_text(text: str | None, mode: Optional[str] = None) -> str | None:
    if text is None:
        return None
    mode = (mode or privacy_mode_for()).lower()
    if mode == "strict":
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
        return f"[HASH:{digest}]"

    cleaned = text
    cleaned = _EMAIL_RE.sub("[REDACTED_EMAIL]", cleaned)
    cleaned = _SSN_RE.sub("[REDACTED_SSN]", cleaned)
    cleaned = _PHONE_RE.sub("[REDACTED_PHONE]", cleaned)
    cleaned = _redact_entropy(cleaned)
    cleaned = _apply_custom_patterns(cleaned)
    return cleaned


def scrub_record(record: Dict[str, object], keys: Optional[Iterable[str]] = None, mode: Optional[str] = None) -> Dict[str, object]:
    mode = (mode or privacy_mode_for()).lower()
    if keys is None:
        keys = [k for k, v in record.items() if isinstance(v, str)]
    for key in keys:
        value = record.get(key)
        if isinstance(value, str):
            record[key] = scrub_text(value, mode=mode)  # type: ignore[assignment]
    return record


__all__ = ["scrub_text", "scrub_record", "privacy_mode_for"]
