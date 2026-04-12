"""Pydantic schema for a single dataset record."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel


class DatasetRecord(BaseModel):
    """A single labelled evaluation sample."""

    text: str
    label: Literal["benign", "borderline", "unsafe"]
    category: str
    language: str = "en"
    source: str = "unknown"
    attack_type: Optional[str] = None
