"""Unified guard evaluation utilities."""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Callable, Dict, Iterable, List, Mapping, MutableMapping, Sequence, Tuple

DEFAULT_MODES: Tuple[str, ...] = ("strict", "lenient")
_POSITIVE_STRINGS = {
    "1",
    "true",
    "yes",
    "y",
    "harmful",
    "unsafe",
    "violation",
    "bad",
    "toxic",
    "deny",
    "flag",
    "blocked",
}
_NEGATIVE_STRINGS = {"0", "false", "no", "n", "safe", "benign", "ok", "harmless", "good", "allow", "pass"}


def evaluate(
    engine: Mapping[str, Any],
    dataset: Sequence[Any],
    policy: Mapping[str, Any] | None = None,
    modes: Iterable[str] = DEFAULT_MODES,
) -> Dict[str, Any]:
    """Run one or more guard configs on a dataset and return metrics summary."""
    rows = _normalize_rows(dataset)
    guard_specs = _normalize_guards(engine)
    modes_tuple = tuple(dict.fromkeys(modes)) or ("strict",)
    risk_weights = dict((policy or {}).get("risk_weights", {}))

    summary: Dict[str, Any] = {
        "dataset": {"size": len(rows)},
        "policy": {"risk_weights": risk_weights},
        "guards": {},
    }

    for guard_key, spec in guard_specs.items():
        guard_fn = spec["predict"]
        guard_name = spec.get("name", guard_key)

        preds_bool: List[bool] = []
        latencies: List[int] = []
        raw_outputs: List[Any] = []

        for row in rows:
            flag, latency, raw = _call_guard(guard_fn, row)
            preds_bool.append(flag)
            latencies.append(latency)
            raw_outputs.append(raw)

        latency_stats = latency_percentiles(latencies)
        guard_modes: Dict[str, Any] = {}
        aggregate_risk: float | None = None

        for mode in modes_tuple:
            cm = confusion(rows, preds_bool, mode=mode)
            slices = slice_metrics(rows, preds_bool, mode=mode)
            _apply_risk(slices, risk_weights)
            risk_total = round(sum(slice_row.get("risk_score", 0.0) for slice_row in slices), 3)
            if aggregate_risk is None or mode == "strict":
                aggregate_risk = risk_total
            guard_modes[mode] = {
                "confusion": cm,
                "latency": latency_stats,
                "slices": slices,
                "risk_total": risk_total,
            }

        summary["guards"][guard_key] = {
            "name": guard_name,
            "predictions": preds_bool,
            "latencies": latencies,
            "raw_outputs": raw_outputs,
            "latency": latency_stats,
            "aggregate_risk": aggregate_risk if aggregate_risk is not None else 0.0,
            "modes": guard_modes,
        }

    return summary


def confusion(rows: Sequence[Mapping[str, Any]], preds: Sequence[bool], mode: str = "strict") -> Dict[str, Any]:
    cm: Counter[str] = Counter()
    for row, pred in zip(rows, preds):
        gt_pos = _is_pos_label(row.get("label"), mode)
        if gt_pos and pred:
            cm["tp"] += 1
        elif (not gt_pos) and pred:
            cm["fp"] += 1
        elif (not gt_pos) and (not pred):
            cm["tn"] += 1
        elif gt_pos and (not pred):
            cm["fn"] += 1
    tp = cm["tp"]
    fp = cm["fp"]
    tn = cm["tn"]
    fn = cm["fn"]
    precision = _ratio(tp, tp + fp)
    recall = _ratio(tp, tp + fn)
    fnr = _ratio(fn, tp + fn)
    fpr = _ratio(fp, fp + tn)
    recall_lo, recall_hi = _wilson_ci(tp, tp + fn)
    fpr_lo, fpr_hi = _wilson_ci(fp, fp + tn)
    return {
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "fnr": fnr,
        "fpr": fpr,
        "recall_lo": recall_lo,
        "recall_hi": recall_hi,
        "fpr_lo": fpr_lo,
        "fpr_hi": fpr_hi,
    }


def slice_metrics(
    rows: Sequence[Mapping[str, Any]],
    preds: Sequence[bool],
    mode: str = "strict",
    by: Tuple[str, str] = ("category", "language"),
) -> List[Dict[str, Any]]:
    buckets: MutableMapping[Tuple[Any, ...], Dict[str, int]] = defaultdict(lambda: {"tp": 0, "fp": 0, "tn": 0, "fn": 0, "n": 0})
    for row, pred in zip(rows, preds):
        key = tuple(row.get(field) for field in by)
        gt_pos = _is_pos_label(row.get("label"), mode)
        if gt_pos and pred:
            buckets[key]["tp"] += 1
        elif (not gt_pos) and pred:
            buckets[key]["fp"] += 1
        elif (not gt_pos) and (not pred):
            buckets[key]["tn"] += 1
        elif gt_pos and (not pred):
            buckets[key]["fn"] += 1
        buckets[key]["n"] += 1

    rows_out: List[Dict[str, Any]] = []
    for key, metrics in buckets.items():
        category = key[0] if len(key) > 0 else None
        language = key[1] if len(key) > 1 else None
        tp = metrics["tp"]
        fp = metrics["fp"]
        tn = metrics["tn"]
        fn = metrics["fn"]
        recall = _ratio(tp, tp + fn)
        fnr = _ratio(fn, tp + fn)
        fpr = _ratio(fp, fp + tn)
        recall_lo, recall_hi = _wilson_ci(tp, tp + fn)
        fpr_lo, fpr_hi = _wilson_ci(fp, fp + tn)
        rows_out.append(
            {
                "category": category,
                "language": language,
                "n": metrics["n"],
                "tp": tp,
                "fp": fp,
                "tn": tn,
                "fn": fn,
                "precision": _ratio(tp, tp + fp),
                "recall": recall,
                "fnr": fnr,
                "fpr": fpr,
                "low_n": metrics["n"] < 20,
                "recall_lo": recall_lo,
                "recall_hi": recall_hi,
                "fpr_lo": fpr_lo,
                "fpr_hi": fpr_hi,
            }
        )

    rows_out.sort(key=lambda s: (-s["n"], str(s["category"]), str(s["language"])))
    return rows_out


def latency_percentiles(latencies: Sequence[int]) -> Dict[str, float]:
    if not latencies:
        return {"p50": 0.0, "p90": 0.0, "p99": 0.0}
    ordered = sorted(latencies)
    if len(ordered) == 1:
        value = float(ordered[0])
        return {"p50": value, "p90": value, "p99": value}
    # statistics.quantiles uses exclusive quantile by default; align with simple index logic when possible
    def _pct(q: float) -> float:
        idx = int(round(q * (len(ordered) - 1)))
        idx = max(0, min(idx, len(ordered) - 1))
        return float(ordered[idx])
    return {"p50": _pct(0.5), "p90": _pct(0.9), "p99": _pct(0.99)}


def _apply_risk(slice_rows: List[Dict[str, Any]], risk_weights: Mapping[str, float]) -> None:
    for row in slice_rows:
        category = row.get("category") or "misc"
        weight = float(risk_weights.get(category, 1.0))
        row["risk_weight"] = weight
        row["risk_score"] = round(weight * row.get("fnr", 0.0), 3)


def _normalize_rows(dataset: Sequence[Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for idx, entry in enumerate(dataset):
        if isinstance(entry, str):
            rows.append(
                {
                    "id": f"row_{idx}",
                    "text": entry,
                    "label": "benign",
                    "category": None,
                    "language": "en",
                }
            )
            continue
        if not isinstance(entry, Mapping):
            raise TypeError(f"Unsupported dataset row type: {type(entry)!r}")
        text = _row_text(entry)
        if not text:
            raise ValueError(f"Dataset row {idx} missing text-like content")
        rows.append(
            {
                "id": entry.get("id", f"row_{idx}"),
                "text": text,
                "label": entry.get("label", "benign"),
                "category": entry.get("category"),
                "language": entry.get("language", "en"),
                **{k: v for k, v in entry.items() if k not in {"id", "text", "label", "category", "language"}},
            }
        )
    return rows


def _row_text(row: Mapping[str, Any]) -> str:
    for key in ("text", "prompt", "question", "input", "content", "message", "utterance"):
        value = row.get(key)
        if value:
            return str(value)
    return ""


def _normalize_guards(engine: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    if "guards" in engine and isinstance(engine["guards"], Mapping):
        guard_map = engine["guards"]
    else:
        guard_map = engine
    normalized: Dict[str, Dict[str, Any]] = {}
    for key, spec in guard_map.items():
        if callable(spec):
            normalized[key] = {"predict": spec}
            continue
        if not isinstance(spec, Mapping):
            raise TypeError(f"Guard spec for '{key}' must be callable or mapping")
        if "predict" not in spec:
            raise ValueError(f"Guard spec for '{key}' requires a 'predict' callable")
        normalized[key] = dict(spec)
    return normalized


def _call_guard(guard_fn: Callable[..., Any], row: Mapping[str, Any]) -> Tuple[bool, int, Any]:
    trials = [
        ((row["text"],), {}),
        ((row["text"], row.get("category")), {}),
        ((row["text"], row.get("category"), row.get("language")), {}),
        ((), {"text": row["text"], "category": row.get("category"), "language": row.get("language")}),
    ]
    result: Any = None
    for args, kwargs in trials:
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        try:
            result = guard_fn(*args, **kwargs)
            break
        except TypeError:
            continue
    if result is None:
        result = guard_fn(row["text"])

    flag = _pred_to_bool(result)
    latency = 0
    if isinstance(result, Mapping):
        latency = int(result.get("latency_ms", result.get("latency", 0)) or 0)
    return flag, latency, result


def _pred_to_bool(pred: Any) -> bool:
    if isinstance(pred, Mapping):
        if "prediction" in pred:
            value = pred["prediction"]
            return _coerce_truth(value)
        if "pred" in pred:
            value = pred["pred"]
            return _coerce_truth(value)
        if "score" in pred and "threshold" in pred:
            try:
                return float(pred["score"]) >= float(pred["threshold"])
            except (TypeError, ValueError):
                return False
        return bool(pred)
    return _coerce_truth(pred)


def _coerce_truth(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return float(value) != 0.0
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in _POSITIVE_STRINGS:
            return True
        if lowered in _NEGATIVE_STRINGS:
            return False
    return bool(value)


def _is_pos_label(label: Any, mode: str) -> bool:
    if isinstance(label, bool):
        positive = label
    elif isinstance(label, (int, float)):
        positive = float(label) != 0.0
    elif isinstance(label, str):
        lowered = label.strip().lower()
        if lowered in _POSITIVE_STRINGS:
            positive = True
        elif lowered in _NEGATIVE_STRINGS:
            positive = False
        else:
            positive = lowered != "benign"
    else:
        positive = False
    if mode == "lenient":
        return str(label).strip().lower() == "unsafe"
    return positive


def _ratio(num: float, denom: float) -> float:
    if denom == 0:
        return 0.0
    return round(num / denom, 3)


def _wilson_ci(k: int, n: int, z: float = 1.96) -> Tuple[float, float]:
    if n <= 0:
        return 0.0, 0.0
    p = k / n
    denom = 1 + (z * z) / n
    center = (p + (z * z) / (2 * n)) / denom
    import math
    margin = z * math.sqrt((p * (1 - p) + (z * z) / (4 * n)) / n) / denom
    lo = max(0.0, round(center - margin, 3))
    hi = min(1.0, round(center + margin, 3))
    return lo, hi

__all__ = ["evaluate", "confusion", "slice_metrics", "latency_percentiles"]
