from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


TELEMETRY_PATH = Path("runtime_telemetry.jsonl")


@dataclass
class ImageInput:
    content_type: str  # e.g., image/png, image/jpeg
    bytes: bytes


@dataclass
class AudioInput:
    content_type: str  # e.g., audio/wav, audio/mpeg
    bytes: bytes


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _log_telemetry(payload: Dict[str, Any]) -> None:
    TELEMETRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with TELEMETRY_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def score_image(inp: ImageInput, *, slice_category: str = "image/*") -> Dict[str, Any]:
    if not inp.content_type.startswith("image/"):
        raise ValueError("Invalid content_type for image input")
    digest = _sha256(inp.bytes)
    payload = {
        "modality": "image",
        "content_type": inp.content_type,
        "hash": digest,
        "category_guess": slice_category,
        "language_guess": "n/a",
        "score": 0.0,
        "threshold": 1.0,
    }
    _log_telemetry(payload)
    return payload


def score_audio(inp: AudioInput, *, slice_category: str = "audio/*") -> Dict[str, Any]:
    if not inp.content_type.startswith("audio/"):
        raise ValueError("Invalid content_type for audio input")
    digest = _sha256(inp.bytes)
    payload = {
        "modality": "audio",
        "content_type": inp.content_type,
        "hash": digest,
        "category_guess": slice_category,
        "language_guess": "n/a",
        "score": 0.0,
        "threshold": 1.0,
    }
    _log_telemetry(payload)
    return payload


__all__ = ["ImageInput", "AudioInput", "score_image", "score_audio"]


