"""Adaptive red-team swarm package."""

from .operators import (
    leet_speak,
    insert_zero_width,
    swap_homoglyphs,
    add_punctuation_noise,
    mixed_casing,
    add_emoji_noise,
    apply_operators,
    random_operator_pipeline,
)

from .agents import AGENTS, AgentInput, AgentOutput
from .dedupe import TextDeduper
from .search import SwarmSearch, load_seed_rows

__all__ = [
    "leet_speak",
    "insert_zero_width",
    "swap_homoglyphs",
    "add_punctuation_noise",
    "mixed_casing",
    "add_emoji_noise",
    "apply_operators",
    "random_operator_pipeline",
    "AGENTS",
    "AgentInput",
    "AgentOutput",
    "TextDeduper",
    "SwarmSearch",
    "load_seed_rows",
]
