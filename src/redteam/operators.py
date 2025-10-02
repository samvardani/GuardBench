"""Text transformation operators used by the adaptive red-team swarm."""

from __future__ import annotations

import random
import re
from typing import Callable, Iterable, List, Sequence

_LEET_MAP = str.maketrans({
    "a": "4",
    "e": "3",
    "i": "1",
    "o": "0",
    "s": "5",
    "t": "7",
    "g": "9",
    "b": "8",
})

_HOMOGLYPHS = {
    "a": ["а", "ᴀ", "α"],
    "e": ["е", "ɛ", "℮"],
    "i": ["і", "ɩ", "𝚒"],
    "o": ["ο", "օ", "ȯ"],
    "p": ["р", "ƿ"],
    "c": ["с", "ϲ"],
    "x": ["х", "𝔵"],
    "y": ["у", "ɏ"],
    "m": ["ｍ", "ᵯ"],
    "h": ["һ", "ћ"],
}

_PUNCTUATION = ["-", "_", ".", ",", "|", "·", "~"]

_ZERO_WIDTH = ["\u200b", "\u200c", "\u200d", "\ufeff"]

_EMOJI = ["🔥", "💣", "⚠️", "🧨", "😈", "💀", "🗡️", "🕳️", "🤫", "📡"]


def _ensure_rng(rng: random.Random | None) -> random.Random:
    return rng if rng is not None else random.Random()


def leet_speak(text: str, ratio: float = 0.35, rng: random.Random | None = None) -> str:
    """Apply classic leet-speak substitutions with the given ratio."""
    if not text:
        return text
    rng = _ensure_rng(rng)
    chars = []
    for ch in text:
        repl = _LEET_MAP.get(ch.lower())
        if repl and rng.random() < ratio:
            repl = repl.upper() if ch.isupper() else repl
            chars.append(repl)
        else:
            chars.append(ch)
    return "".join(chars)


def insert_zero_width(text: str, probability: float = 0.2, rng: random.Random | None = None) -> str:
    """Insert zero-width characters between graphemes."""
    if not text:
        return text
    rng = _ensure_rng(rng)
    out: List[str] = []
    for ch in text:
        out.append(ch)
        if ch.strip() and rng.random() < probability:
            out.append(rng.choice(_ZERO_WIDTH))
    return "".join(out)


def swap_homoglyphs(text: str, probability: float = 0.25, rng: random.Random | None = None) -> str:
    """Swap characters for visually similar homoglyphs."""
    if not text:
        return text
    rng = _ensure_rng(rng)
    out: List[str] = []
    for ch in text:
        options = _HOMOGLYPHS.get(ch.lower())
        if options and rng.random() < probability:
            replacement = rng.choice(options)
            replacement = replacement.upper() if ch.isupper() else replacement
            out.append(replacement)
        else:
            out.append(ch)
    return "".join(out)


def add_punctuation_noise(text: str, probability: float = 0.25, rng: random.Random | None = None) -> str:
    """Inject lightweight punctuation into longer tokens."""
    if not text:
        return text
    rng = _ensure_rng(rng)
    tokens = text.split()
    noisy: List[str] = []
    for token in tokens:
        if len(token) < 4 or rng.random() > probability:
            noisy.append(token)
            continue
        insert_pos = rng.randint(1, len(token) - 1)
        punct = rng.choice(_PUNCTUATION)
        noisy.append(token[:insert_pos] + punct + token[insert_pos:])
    return " ".join(noisy)


def mixed_casing(text: str, rng: random.Random | None = None) -> str:
    """Randomly flip casing to create mixed-script like presentation."""
    if not text:
        return text
    rng = _ensure_rng(rng)
    chars = [ch.upper() if rng.random() < 0.5 else ch.lower() for ch in text]
    return "".join(chars)


def add_emoji_noise(text: str, max_emojis: int = 3, rng: random.Random | None = None) -> str:
    """Append low-information emoji noise near sentence boundaries."""
    if not text:
        return text
    rng = _ensure_rng(rng)
    emojis = rng.sample(_EMOJI, k=min(max_emojis, len(_EMOJI)))
    if rng.random() < 0.5:
        return text + " " + "".join(emojis[: rng.randint(1, max_emojis)])
    return "".join(emojis[: rng.randint(1, max_emojis)]) + " " + text


Operator = Callable[[str], str]


def apply_operators(text: str, operators: Sequence[Callable[[str], str]]) -> str:
    """Apply a sequence of operator callables to text."""
    out = text
    for op in operators:
        out = op(out)
    return out


def random_operator_pipeline(
    rng: random.Random | None = None,
    max_depth: int = 3,
) -> List[Callable[[str], str]]:
    """Generate a random pipeline of operators for exploration."""
    rng = _ensure_rng(rng)
    def _named(func: Callable[[str], str], name: str) -> Callable[[str], str]:
        setattr(func, "__name__", name)
        return func

    available: List[Callable[[str], str]] = [
        _named(lambda t: leet_speak(t, rng=rng), "leet_speak"),
        _named(lambda t: insert_zero_width(t, rng=rng), "insert_zero_width"),
        _named(lambda t: swap_homoglyphs(t, rng=rng), "swap_homoglyphs"),
        _named(lambda t: add_punctuation_noise(t, rng=rng), "punctuation_noise"),
        _named(lambda t: mixed_casing(t, rng=rng), "mixed_casing"),
        _named(lambda t: add_emoji_noise(t, rng=rng), "emoji_noise"),
    ]
    depth = rng.randint(1, max_depth)
    return [rng.choice(available) for _ in range(depth)]


__all__ = [
    "leet_speak",
    "insert_zero_width",
    "swap_homoglyphs",
    "add_punctuation_noise",
    "mixed_casing",
    "add_emoji_noise",
    "apply_operators",
    "random_operator_pipeline",
]
