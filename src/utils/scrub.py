"""Utilities for scrubbing sensitive data before persistence."""

from __future__ import annotations

import hashlib
import re
from typing import Dict, Iterable, Optional

from src.utils.io_utils import load_config

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE_RE = re.compile(r"\b(?:\+?\d[\d\-\s]{7,}\d)\b")
_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_ENTROPY_RE = re.compile(r"[A-Za-z0-9+/]{12,}")


def _privacy_mode() -> str:
    cfg = load_config() or {}
    mode = str(cfg.get("privacy_mode", "off")).lower()
    return "strict" if mode == "strict" else "off"


def _redact_entropy(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        token = match.group(0)
        unique_ratio = len(set(token)) / len(token)
        if unique_ratio > 0.6 and any(c.isdigit() for c in token) and any(c.isalpha() for c in token):
            return "[REDACTED_TOKEN]"
        return token

    return _ENTROPY_RE.sub(repl, text)


def scrub_text(text: str | None, mode: Optional[str] = None) -> str | None:
    if text is None:
        return None
    mode = (mode or _privacy_mode()).lower()
    if mode == "strict":
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
        return f"[HASH:{digest}]"

    cleaned = text
    cleaned = _EMAIL_RE.sub("[REDACTED_EMAIL]", cleaned)
    cleaned = _PHONE_RE.sub("[REDACTED_PHONE]", cleaned)
    cleaned = _SSN_RE.sub("[REDACTED_SSN]", cleaned)
    cleaned = _redact_entropy(cleaned)
    return cleaned


def scrub_record(record: Dict[str, object], keys: Optional[Iterable[str]] = None, mode: Optional[str] = None) -> Dict[str, object]:
    mode = (mode or _privacy_mode()).lower()
    if keys is None:
        keys = [k for k, v in record.items() if isinstance(v, str)]
    for key in keys:
        value = record.get(key)
        if isinstance(value, str):
            record[key] = scrub_text(value, mode=mode)  # type: ignore[assignment]
    return record


__all__ = ["scrub_text", "scrub_record"]
