from collections import defaultdict
from typing import Dict, List, Tuple, Any, Optional


def _normalize_label(label: Any) -> str:
    return (str(label or "").strip().lower())


def _is_positive_label(label: Any, mode: str = "strict") -> bool:
    norm = _normalize_label(label)
    if mode == "lenient":
        return norm == "unsafe"
    return norm != "benign"


def _pattern_signature(row: Dict[str, Any]) -> Tuple[str, str]:
    """Return (pattern, normalization_note) tuple for a dataset row."""

    regex = (
        row.get("regex_name")
        or row.get("regex")
        or row.get("pattern")
        or row.get("pattern_name")
    )

    if not regex:
        # Fall back to structured transforms/attack metadata if available
        if isinstance(row.get("transforms"), list):
            regex = ", ".join(row["transforms"])
        elif row.get("attack_type"):
            regex = row["attack_type"]
        else:
            regex = row.get("source") or "unknown"

    normalization = (
        row.get("normalization")
        or row.get("notes")
        or row.get("difficulty")
        or ""
    )

    return regex, normalization


def _trim_text(text: str, limit: int = 140) -> str:
    if not text:
        return ""
    text = str(text)
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _pred_to_bool(p):
    """
    Return True iff p indicates a 'flag'. Accepts dict/int/bool/str.
    """
    if isinstance(p, dict):
        if "prediction" in p:
            v = p["prediction"]
            return v.lower() == "flag" if isinstance(v, str) else bool(v)
        if "pred" in p:
            v = p["pred"]
            return v.lower() == "flag" if isinstance(v, str) else bool(v)
        if ("score" in p) and ("threshold" in p):
            return p["score"] >= p["threshold"]
        return bool(p)
    if isinstance(p, str):
        return p.strip().lower() in ("flag","blocked","deny","unsafe","violation","1","true","yes","y")
    return bool(p)

def _label_to_bool(x):
    """
    Return True iff label is harmful. Accepts 0/1, bool, or strings.
    """
    if isinstance(x, bool):
        return x
    if isinstance(x, (int, float)):
        return int(x) != 0
    if isinstance(x, str):
        t = x.strip().lower()
        harmful = {"1","true","yes","y","harmful","unsafe","violation","bad","toxic","deny"}
        safe    = {"0","false","no","n","safe","benign","ok","harmless","good","allow"}
        if t in harmful: return True
        if t in safe:    return False
    return False

def cluster_failures(rows, preds, mode: str = "strict"):
    """
    Group FNs/FPs by (category, language, attack_type) and return top 5 clusters.
    """
    clusters = defaultdict(list)
    for r, p in zip(rows, preds):
        label = r.get("label")
        gt_pos = _is_positive_label(label, mode=mode)
        pr_pos = (_pred_to_bool(p))

        pattern_label, _ = _pattern_signature(r)
        category = r.get("category") or "unknown"
        language = r.get("language") or "unknown"

        if gt_pos and not pr_pos:
            key = ("FN", category, language, pattern_label)
            clusters[key].append(r)
        if (not gt_pos) and pr_pos:
            key = ("FP", category, language, pattern_label)
            clusters[key].append(r)

    out = []
    for (ft, cat, lang, atk), items in clusters.items():
        examples = [{"id": it.get("id"), "text": _trim_text(it.get("text"))} for it in items[:3]]
        out.append({
            "fail_type": ft,
            "category": cat,
            "language": lang,
            "pattern": atk,
            "count": len(items),
            "examples": examples,
        })
    # FN first (riskier), then most frequent
    out.sort(key=lambda x: (0 if x["fail_type"]=="FN" else 1, -x["count"]))
    return out[:5]


def slice_failure_patterns(
    rows: List[Dict[str, Any]],
    preds,
    mode: str = "strict",
    per_slice: Optional[int] = 5,
    per_pattern: int = 3,
    example_limit: int = 2,
) -> List[Dict[str, Any]]:
    """Summarize the most common FN patterns per (category, language) slice."""

    summaries: Dict[Tuple[str, str], Dict[str, Any]] = defaultdict(
        lambda: {"total": 0, "patterns": defaultdict(list)}
    )

    for row, pred in zip(rows, preds):
        if not _is_positive_label(row.get("label"), mode=mode):
            continue
        if _pred_to_bool(pred):
            continue

        category = row.get("category") or "unknown"
        language = row.get("language") or "unknown"
        pattern, normalization = _pattern_signature(row)

        key = (category, language)
        summaries[key]["total"] += 1
        summaries[key]["patterns"][(pattern, normalization)].append(row)

    results: List[Dict[str, Any]] = []
    for (category, language), info in summaries.items():
        pattern_rows = []
        for (pattern, normalization), rows_for_pattern in info["patterns"].items():
            examples = []
            for example_row in rows_for_pattern[:example_limit]:
                examples.append(
                    {
                        "id": example_row.get("id"),
                        "text": _trim_text(example_row.get("text")),
                    }
                )
            pattern_rows.append(
                {
                    "pattern": pattern,
                    "normalization": normalization,
                    "count": len(rows_for_pattern),
                    "examples": examples,
                }
            )

        pattern_rows.sort(key=lambda x: (-x["count"], x["pattern"]))
        results.append(
            {
                "category": category,
                "language": language,
                "total": info["total"],
                "patterns": pattern_rows[:per_pattern] if per_pattern else pattern_rows,
            }
        )

    results.sort(key=lambda x: (-x["total"], x["category"], x["language"]))
    if per_slice:
        return results[:per_slice]
    return results
