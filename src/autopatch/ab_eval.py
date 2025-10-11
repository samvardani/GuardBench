"""A/B evaluation utilities for AutoPatch."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping

from autopatch.candidates import apply_threshold_patch_to_config
from guards.candidate import predict as candidate_predict
from evaluation import evaluate
from runner.run_compare import load_cfg_and_data


CONFIG_PATH = Path("config.yaml")
TUNED_PATH = Path("tuned_thresholds.yaml")
DEFAULT_RESULT_PATH = Path("report/ab_result.json")


def _get_slice_key(row: Mapping[str, str]) -> str:
    return f"{row.get('category', 'misc')}/{row.get('language', 'en')}"


def _evaluate_candidate(rows: List[dict]) -> Dict[str, object]:
    engine = {
        "guards": {
            "candidate": {"name": "candidate", "predict": candidate_predict},
        }
    }
    summary = evaluate(engine, rows, policy={})
    guard = summary["guards"]["candidate"]
    strict_view = guard["modes"]["strict"]
    metrics = dict(strict_view["confusion"])
    metrics["latency_ms"] = guard["latency"]
    slices = {f"{s['category']}/{s['language']}": s for s in strict_view["slices"]}
    return {"metrics": metrics, "slices": slices}


def evaluate_threshold_candidate(
    updates: Dict[str, float],
    target_slices: Iterable[str],
    result_path: Path = DEFAULT_RESULT_PATH,
    cases: Iterable[dict] | None = None,
) -> Dict[str, Any]:
    cfg, rows = load_cfg_and_data()
    baseline: Dict[str, Any] = _evaluate_candidate(rows)

    original_config = CONFIG_PATH.read_text(encoding="utf-8")
    patched_config = apply_threshold_patch_to_config(original_config, updates)

    fixed_samples: List[str] = []

    CONFIG_PATH.write_text(patched_config, encoding="utf-8")
    try:
        patched: Dict[str, Any] = _evaluate_candidate(rows)
        if cases:
            for case in cases:
                slice_key = _get_slice_key(case)
                if slice_key not in target_slices:
                    continue
                before = candidate_predict(case["text"], category=case.get("category"), language=case.get("language"))
                before_flag = before.get("prediction") == "flag" or before.get("score", 0.0) > before.get("threshold", 0.0)

                # With patched config already active, compute status
                after = candidate_predict(case["text"], category=case.get("category"), language=case.get("language"))
                after_flag = after.get("prediction") == "flag" or after.get("score", 0.0) > after.get("threshold", 0.0)
                if after_flag and not before_flag:
                    fixed_samples.append(case["text"])
                if len(fixed_samples) >= 5:
                    break
    finally:
        CONFIG_PATH.write_text(original_config, encoding="utf-8")

    deltas = {
        "precision": patched["metrics"]["precision"] - baseline["metrics"]["precision"],
        "recall": patched["metrics"]["recall"] - baseline["metrics"]["recall"],
        "fpr": patched["metrics"]["fpr"] - baseline["metrics"]["fpr"],
    }

    per_slice = {}
    for slice_key in target_slices:
        base_slice = baseline["slices"].get(slice_key)
        patched_slice = patched["slices"].get(slice_key)
        if not base_slice or not patched_slice:
            continue
        per_slice[slice_key] = {
            "baseline": base_slice,
            "patched": patched_slice,
            "delta": {
                "recall": patched_slice["recall"] - base_slice["recall"],
                "fpr": patched_slice["fpr"] - base_slice["fpr"],
            },
        }

    result = {
        "baseline": baseline,
        "patched": patched,
        "delta": deltas,
        "per_slice": per_slice,
        "fixed_samples": fixed_samples,
        "threshold_updates": updates,
    }
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def accepts_improvement(
    result: Dict[str, object],
    target_slices: Iterable[str],
    max_fpr_increase: float = 0.005,
) -> bool:
    per_slice = result.get("per_slice", {})
    improved = False
    for slice_key in target_slices:
        slice_data = per_slice.get(slice_key)  # type: ignore[attr-defined]
        if not slice_data:
            continue
        delta = slice_data.get("delta", {})  # type: ignore[attr-defined]
        if delta.get("fpr", 0.0) > max_fpr_increase + 1e-9:
            return False
        if delta.get("recall", 0.0) > 1e-6:
            improved = True
    return improved


__all__ = ["evaluate_threshold_candidate", "accepts_improvement", "DEFAULT_RESULT_PATH"]
