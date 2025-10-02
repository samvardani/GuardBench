"""Near-duplicate suppression for red-team discoveries."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence, Tuple


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def _shingles(text: str, size: int = 3) -> List[str]:
    text = text.replace(" ", "_")
    if len(text) < size:
        return [text]
    return [text[i : i + size] for i in range(len(text) - size + 1)]


class MinHasher:
    """Light-weight MinHash implementation based on hashed shingles."""

    def __init__(self, num_perm: int = 64, seed: int = 13) -> None:
        self.num_perm = num_perm
        rng = random.Random(seed)
        self.perms = [rng.randint(1, 2**31 - 1) for _ in range(num_perm)]

    def signature(self, shingles: Sequence[str]) -> Tuple[int, ...]:
        sig: List[int] = []
        if not shingles:
            return tuple([2**31 - 1] * self.num_perm)
        for perm in self.perms:
            min_hash = min((hash(s) ^ perm) & 0xFFFFFFFF for s in shingles)
            sig.append(min_hash)
        return tuple(sig)

    @staticmethod
    def jaccard(sig_a: Sequence[int], sig_b: Sequence[int]) -> float:
        matches = sum(1 for a, b in zip(sig_a, sig_b) if a == b)
        return matches / float(len(sig_a)) if sig_a else 0.0


def _simhash(shingles: Sequence[str]) -> int:
    if not shingles:
        return 0
    bits = [0] * 64
    for shingle in shingles:
        h = hash(shingle)
        for i in range(64):
            mask = 1 << i
            bits[i] += 1 if h & mask else -1
    fingerprint = 0
    for i, weight in enumerate(bits):
        if weight > 0:
            fingerprint |= 1 << i
    return fingerprint


def _hamming(a: int, b: int) -> int:
    return (a ^ b).bit_count()


def _term_freq(shingles: Sequence[str]) -> Dict[str, float]:
    counts: Dict[str, int] = {}
    for sh in shingles:
        counts[sh] = counts.get(sh, 0) + 1
    norm = math.sqrt(sum(v * v for v in counts.values())) or 1.0
    return {k: v / norm for k, v in counts.items()}


def _cosine(a: Dict[str, float], b: Dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    return sum(a.get(k, 0.0) * b.get(k, 0.0) for k in set(a) | set(b))


@dataclass
class _Entry:
    text: str
    normalized: str
    signature: Tuple[int, ...]
    simhash: int
    vector: Dict[str, float]


class TextDeduper:
    """Near-duplicate detector mixing MinHash, SimHash, and cosine fallback."""

    def __init__(
        self,
        threshold: float = 0.9,
        existing_texts: Iterable[str] | None = None,
        num_perm: int = 64,
    ) -> None:
        self.threshold = threshold
        self.minhasher = MinHasher(num_perm=num_perm)
        self.entries: List[_Entry] = []
        self.attempts = 0
        self.duplicates = 0
        if existing_texts:
            for text in existing_texts:
                self._add_internal(text)

    # Public API -----------------------------------------------------

    def is_duplicate(self, text: str) -> bool:
        self.attempts += 1
        entry = self._build_entry(text)
        for other in self.entries:
            jaccard = self.minhasher.jaccard(entry.signature, other.signature)
            if jaccard < self.threshold * 0.8:
                continue
            ham = _hamming(entry.simhash, other.simhash)
            if ham <= max(5, int((1 - self.threshold) * 64)):
                self.duplicates += 1
                return True
            cosine = _cosine(entry.vector, other.vector)
            if cosine >= self.threshold:
                self.duplicates += 1
                return True
        self.entries.append(entry)
        return False

    def duplicate_rate(self) -> float:
        if not self.attempts:
            return 0.0
        return self.duplicates / float(self.attempts)

    # Internal helpers ----------------------------------------------

    def _build_entry(self, text: str) -> _Entry:
        normalized = _normalize(text)
        shingles = _shingles(normalized)
        signature = self.minhasher.signature(shingles)
        simhash_value = _simhash(shingles)
        vector = _term_freq(shingles)
        return _Entry(text=text, normalized=normalized, signature=signature, simhash=simhash_value, vector=vector)

    def _add_internal(self, text: str) -> None:
        entry = self._build_entry(text)
        self.entries.append(entry)


__all__ = ["TextDeduper"]
