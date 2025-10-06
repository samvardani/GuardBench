"""Federated adversarial prompt signatures.

Design goals:
- Irreversible: emit only salted hashes/signatures; never raw text.
- Canonicalization: aggressive normalization before fingerprinting.
- Compact: MinHash + Bloom-like bitset for fast membership tests.
- Multi-tenant: per-tenant salt so signatures are not reusable across tenants.

This module provides:
- build_signature: returns a compact signature record for a prompt
- matcher: in-memory matcher for fast lookups
- utilities to merge feeds
"""

from __future__ import annotations

import hashlib
import os
import random
import re
import string
from dataclasses import dataclass
from typing import Iterable, List, Mapping, Optional, Sequence, Tuple


# ---------------------------- Canonicalization ----------------------------

_ZWSP = "\u200b\u200c\u200d\ufeff"
_PUNCT = string.punctuation


def _strip_zwsp(text: str) -> str:
    return re.sub(f"[{_ZWSP}]", "", text)


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _remove_punct(text: str) -> str:
    # Replace punctuation with spaces to avoid token merging like "credit-card" -> "creditcard"
    table = str.maketrans({ch: " " for ch in _PUNCT})
    return text.translate(table)


def canonicalize(text: str) -> str:
    text = text or ""
    text = text.lower()
    text = _strip_zwsp(text)
    text = _remove_punct(text)
    text = _normalize_whitespace(text)
    return text


# ---------------------------- MinHash utils -------------------------------

def _word_shingles(text: str, k: int = 3) -> List[str]:
    words = [w for w in text.split(" ") if w]
    if not words:
        return []
    if k <= 1 or len(words) <= k:
        return words if k <= 1 else [" ".join(words)]
    return [" ".join(words[i : i + k]) for i in range(len(words) - k + 1)]


def _hash_with_salt(data: str, salt: str, algo: str = "sha256") -> int:
    h = hashlib.new(algo)
    h.update(salt.encode("utf-8"))
    h.update(b"|")
    h.update(data.encode("utf-8"))
    return int.from_bytes(h.digest(), "big")


def minhash(text: str, salt: str, num_perm: int = 64, shingle_k: int = 3) -> List[int]:
    can = canonicalize(text)
    shingles = _word_shingles(can, k=shingle_k)
    if not shingles:
        return [0] * num_perm
    # Simple seeded permutations via independent hash functions keyed by index
    perms = []
    for i in range(num_perm):
        min_val = None
        for token in shingles:
            hv = _hash_with_salt(f"{i}:{token}", salt)
            if min_val is None or hv < min_val:
                min_val = hv
        perms.append(int(min_val or 0))
    return perms


# ---------------------------- Bloom bitset --------------------------------

def bloom_bits(values: Sequence[int], m_bits: int = 2048, k_hashes: int = 5) -> List[int]:
    if m_bits <= 0:
        raise ValueError("m_bits must be positive")
    bitset = 0
    for v in values:
        for j in range(k_hashes):
            hv = _hash_with_salt(f"{j}:{v}", "bloom")
            pos = hv % m_bits
            bitset |= 1 << pos
    # return packed little array of ints (64-bit limbs)
    limbs: List[int] = []
    width = 64
    for off in range(0, m_bits, width):
        limb = 0
        for i in range(width):
            if off + i >= m_bits:
                break
            if (bitset >> (off + i)) & 1:
                limb |= 1 << i
        limbs.append(limb)
    return limbs


@dataclass
class Signature:
    tenant: str
    algo: str
    perms: List[int]
    bloom: List[int]
    meta: Mapping[str, str]


def tenant_salt(tenant: str) -> str:
    secret = os.getenv("FEDERATION_TENANT_SECRET", "default-secret")
    return hashlib.sha256((tenant + "|" + secret).encode("utf-8")).hexdigest()


def build_signature(text: str, tenant: str, meta: Optional[Mapping[str, str]] = None) -> Signature:
    salt = tenant_salt(tenant)
    perms = minhash(text, salt=salt, num_perm=64, shingle_k=5)
    bloom = bloom_bits(perms, m_bits=2048, k_hashes=5)
    return Signature(tenant=tenant, algo="minhash64+bloom2048", perms=perms, bloom=bloom, meta=dict(meta or {}))


# ---------------------------- Matcher --------------------------------------

class Matcher:
    def __init__(self) -> None:
        self._by_tenant: dict[str, List[Signature]] = {}

    def add(self, sig: Signature) -> None:
        self._by_tenant.setdefault(sig.tenant, []).append(sig)

    def _bloom_maybe(self, query: Signature, cand: Signature) -> bool:
        # quick prefilter: check that all query 1-bits exist in candidate
        return all((qb & candb) == qb for qb, candb in zip(query.bloom, cand.bloom))

    def _minhash_sim(self, a: Sequence[int], b: Sequence[int]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        equal = sum(1 for x, y in zip(a, b) if x == y)
        return equal / float(len(a))

    def query(self, text: str, tenant: str, threshold: float = 0.8) -> Tuple[float, Optional[Signature]]:
        if tenant not in self._by_tenant:
            return 0.0, None
        q = build_signature(text, tenant=tenant)
        best, best_sig = 0.0, None
        for sig in self._by_tenant.get(tenant, []):
            if not self._bloom_maybe(q, sig):
                continue
            sim = self._minhash_sim(q.perms, sig.perms)
            if sim > best:
                best, best_sig = sim, sig
        if best < threshold:
            return best, None
        return best, best_sig


# ---------------------------- Feed helpers ---------------------------------

def merge_signatures(feeds: Iterable[Iterable[Signature]]) -> List[Signature]:
    out: List[Signature] = []
    seen = set()
    for feed in feeds:
        for sig in feed:
            key = (sig.tenant, tuple(sig.perms))
            if key in seen:
                continue
            seen.add(key)
            out.append(sig)
    return out


__all__ = [
    "Signature",
    "canonicalize",
    "minhash",
    "bloom_bits",
    "tenant_salt",
    "build_signature",
    "Matcher",
    "merge_signatures",
]


