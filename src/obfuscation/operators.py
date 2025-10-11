"""Shared obfuscation operators for the stress lab."""

from __future__ import annotations

import random
import re

from redteam.operators import (
    leet_speak,
    insert_zero_width,
    swap_homoglyphs,
    add_punctuation_noise,
    mixed_casing,
    add_emoji_noise,
)


def camel_to_snake(text: str, rng: random.Random | None = None) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", text).replace(" ", "_").lower()


def mask_numbers(text: str, rng: random.Random | None = None) -> str:
    return re.sub(r"\d", "*", text)


__all__ = [
    "leet_speak",
    "insert_zero_width",
    "swap_homoglyphs",
    "add_punctuation_noise",
    "mixed_casing",
    "add_emoji_noise",
    "camel_to_snake",
    "mask_numbers",
]
