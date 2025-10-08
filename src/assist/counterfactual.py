from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from src.guards.candidate import predict as candidate_predict
from src.policy.compiler import load_compiled_policy, POLICY_PATH


_TRANSFORMS = [
    (r"\bkill\b", "harm"),
    (r"\bbomb\b", "device"),
    (r"\bsteal\b", "obtain"),
    (r"\bhack\b", "test"),
    (r"\bcredit\s*card\b", "payment card"),
]


def _apply_rules_first(text: str, category: Optional[str]) -> Tuple[str, List[str]]:
    tags: List[str] = []
    suggestion = text
    # Rule-level redactions guided by policy patterns when available
    try:
        policy = load_compiled_policy(POLICY_PATH)
    except Exception:
        policy = None

    if policy and category:
        # If there is a matching slice in any language, replace matched regex with safer synonyms
        for (cat, _lang), slice_ in policy.slices.items():
            if cat != category:
                continue
            for rule in slice_.rules:
                for pat in rule.regex:
                    if pat.search(suggestion):
                        suggestion = pat.sub(" ", suggestion)
                        tags.append(f"rule:{rule.id}")

    # Fallback lightweight transforms
    for pat, repl in _TRANSFORMS:
        if re.search(pat, suggestion, flags=re.IGNORECASE):
            suggestion = re.sub(pat, repl, suggestion, flags=re.IGNORECASE)
            tags.append(f"rewrite:{pat}->{repl}")

    return suggestion, tags


@dataclass
class Counterfactual:
    safe_suggestion: str
    transformation_tags: List[str]
    score_before: float
    score_after: float
    threshold: float


def generate_safe_rewrite(prompt: str, category: Optional[str] = None, language: Optional[str] = None) -> Counterfactual:
    before = candidate_predict(prompt, category=category, language=language)
    score_before = float(before.get("score", 0.0))
    threshold = float(before.get("threshold", 0.0))

    suggestion, tags = _apply_rules_first(prompt, category)

    after = candidate_predict(suggestion, category=category, language=language)
    score_after = float(after.get("score", 0.0))

    # If LLM present (not in this codebase), it could re-score here; we strictly avoid using it for raw decisions.

    return Counterfactual(
        safe_suggestion=suggestion,
        transformation_tags=tags,
        score_before=score_before,
        score_after=score_after,
        threshold=threshold,
    )


__all__ = ["generate_safe_rewrite", "Counterfactual"]


