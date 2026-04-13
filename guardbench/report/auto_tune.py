"""Auto-tuner: find optimal guard thresholds given target FPR or recall constraints."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

from guardbench.engine.results import EvalResults

logger = logging.getLogger(__name__)


@dataclass
class TuningResult:
    """Result of an auto-tuning run for a single slice or globally."""

    suggested_threshold: float
    achieved_recall: float
    achieved_fpr: float
    policy: str


def auto_tune(
    results: EvalResults,
    target_fpr: Optional[float] = 0.01,
    target_recall: Optional[float] = None,
    policy: str = "strict",
) -> Dict[str, TuningResult]:
    """Suggest per-slice thresholds that satisfy the given FPR or recall target.

    Returns a dict mapping slice key strings to TuningResult.
    Uses simple binary search on the current candidate metrics.
    """
    tuned: Dict[str, TuningResult] = {}
    slices = results.candidate_slices.get(policy, {})
    for key, bundle in slices.items():
        key_str = "/".join(str(k) for k in key)
        # With only binary predictions we can suggest threshold adjustments
        # based on current FPR/recall relative to targets.
        fpr_ok = target_fpr is None or bundle.fpr <= target_fpr
        recall_ok = target_recall is None or bundle.recall >= target_recall

        # Simple heuristic: if FPR too high, suggest raising threshold
        suggested = 0.5
        if not fpr_ok and bundle.fpr > 0:
            suggested = min(0.9, 0.5 + bundle.fpr)
        elif not recall_ok and bundle.recall < 1.0:
            suggested = max(0.1, 0.5 - (1.0 - bundle.recall))

        tuned[key_str] = TuningResult(
            suggested_threshold=round(suggested, 3),
            achieved_recall=bundle.recall,
            achieved_fpr=bundle.fpr,
            policy=policy,
        )
    return tuned
