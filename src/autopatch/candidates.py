"""Generate candidate fixes based on discovered red-team failures."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

import yaml

from guards.candidate import predict as candidate_predict


DEFAULT_CASES_PATH = Path("report/redteam_cases.jsonl")
DEFAULT_CONFIG_PATH = Path("config.yaml")


SAFE_CONTEXT_TERMS = [
    "therapy",
    "support",
    "hotline",
    "prevention",
    "education",
    "awareness",
]


@dataclass
class CandidatePatch:
    """Generic view of an auto-generated patch suggestion."""

    id: str
    type: str
    description: str
    target_slices: List[str]
    data: Dict[str, float] = field(default_factory=dict)
    score: float = 0.0
    metadata: Dict[str, object] = field(default_factory=dict)


@dataclass
class Suggestion:
    kind: str
    payload: Dict[str, object]


def load_cases(path: Path = DEFAULT_CASES_PATH) -> List[dict]:
    if not path.exists():
        return []
    cases: List[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict) and payload.get("text"):
                cases.append(payload)
    return cases


def _load_config(path: Path = DEFAULT_CONFIG_PATH) -> dict:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _slice_key(category: str, language: str) -> str:
    category = category or "misc"
    language = language or "en"
    return f"{category}/{language}"


def _round_threshold(value: float) -> float:
    value = max(0.0, value)
    return round(math.floor(value / 0.05 + 1e-9) * 0.05, 2)


def _keyword_regex_suggestion(texts: Sequence[str]) -> str:
    tokens = []
    for text in texts:
        tokens.extend(re.findall(r"[a-zA-Z]{4,}", text.lower()))
    if not tokens:
        return r"\b(high risk phrase)\b"
    freq: Dict[str, int] = {}
    for tok in tokens:
        freq[tok] = freq.get(tok, 0) + 1
    keywords = [t for t, _ in sorted(freq.items(), key=lambda kv: -kv[1])[:4]]
    pattern = r"\b(?:" + "|".join(re.escape(w) for w in keywords) + r")\b"
    exclusions = "|".join(SAFE_CONTEXT_TERMS)
    return pattern + f"(?!.*(?:{exclusions}))"


def generate_candidates(
    target_slices: Sequence[str],
    max_patches: int = 3,
    cases_path: Path = DEFAULT_CASES_PATH,
    config_path: Path = DEFAULT_CONFIG_PATH,
) -> Dict[str, List[CandidatePatch]]:
    cases = load_cases(cases_path)
    config = _load_config(config_path)
    thresholds = (config.get("slice_thresholds") or {}) if isinstance(config, dict) else {}

    threshold_candidates: List[CandidatePatch] = []
    regex_suggestions: List[Suggestion] = []
    prompt_suggestions: List[Suggestion] = []

    for slice_key in target_slices:
        try:
            category, language = slice_key.split("/")
        except ValueError:
            continue
        slice_cases = [c for c in cases if _slice_key(c.get("category", ""), c.get("language", "")) == slice_key]
        if not slice_cases:
            continue

        current_thr = float(thresholds.get(category, {}).get(language, 1.0))
        scores: List[tuple[float, dict]] = []
        for case in slice_cases:
            guard = candidate_predict(case["text"], category=category, language=language)
            score = float(guard.get("score", 0.0))
            threshold = float(guard.get("threshold", current_thr))
            case["score"] = score
            case["threshold"] = threshold
            if score <= threshold + 1e-6:
                scores.append((score, case))

        if scores:
            max_score = max(score for score, _ in scores)
            proposed = _round_threshold(max_score - 0.01)
            if proposed < current_thr - 1e-6:
                impacted_ids = [case.get("seed_row_id") or case.get("id") for _, case in scores]
                threshold_candidates.append(
                    CandidatePatch(
                        id=f"threshold::{slice_key}",
                        type="threshold",
                        description=f"Lower {slice_key} threshold from {current_thr:.2f} to {proposed:.2f} (fix {len(scores)} cases)",
                        target_slices=[slice_key],
                        data={slice_key: proposed},
                        score=float(len(scores)),
                        metadata={"impacted_cases": impacted_ids[:5]},
                    )
                )

        # Regex suggestion for the slice
        regex = _keyword_regex_suggestion([c["text"] for c in slice_cases])
        regex_suggestions.append(
            Suggestion(
                kind="regex",
                payload={
                    "slice": slice_key,
                    "pattern": regex,
                    "safe_context": SAFE_CONTEXT_TERMS,
                },
            )
        )

        prompt_suggestions.append(
            Suggestion(
                kind="prompt",
                payload={
                    "slice": slice_key,
                    "block_text": f"Reject requests that imply {category} in {language.upper()} even when obfuscated (emoji, mixed casing, homoglyphs).",
                },
            )
        )

    threshold_candidates.sort(key=lambda c: (-c.score, c.id))
    if max_patches:
        threshold_candidates = threshold_candidates[:max_patches]

    return {
        "threshold": threshold_candidates,
        "regex": regex_suggestions,
        "prompt": prompt_suggestions,
        "cases": cases,
        "config": config,
    }


def apply_threshold_patch_to_config(config_text: str, updates: Dict[str, float]) -> str:
    data = yaml.safe_load(config_text) or {}
    data.setdefault("slice_thresholds", {})
    for slice_key, value in updates.items():
        try:
            category, language = slice_key.split("/")
        except ValueError:
            continue
        data["slice_thresholds"].setdefault(category, {})[language] = float(value)
    return yaml.safe_dump(data, sort_keys=True, allow_unicode=True)


def apply_threshold_patch_to_tuned(tuned_text: str, updates: Dict[str, float]) -> str:
    data = yaml.safe_load(tuned_text) or {}
    data.setdefault("slice_thresholds", {})
    for slice_key, value in updates.items():
        try:
            category, language = slice_key.split("/")
        except ValueError:
            continue
        data["slice_thresholds"].setdefault(category, {})[language] = float(value)
    return yaml.safe_dump(data, sort_keys=True, allow_unicode=True)


__all__ = [
    "CandidatePatch",
    "Suggestion",
    "generate_candidates",
    "apply_threshold_patch_to_config",
    "apply_threshold_patch_to_tuned",
    "load_cases",
]
