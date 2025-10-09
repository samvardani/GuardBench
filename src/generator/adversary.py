
"""Generate adversarial dataset augmentations to probe guard model coverage."""

from __future__ import annotations
from dataclasses import dataclass
from collections import defaultdict
import hashlib
import time
from pathlib import Path
from typing import List, Dict, Any, Tuple, Callable, Sequence
import csv
import yaml
import random
import re

from report.build_report import get_text



def _safe_predict(text, category, language):
    """Call ``predict`` while tolerating signature mismatches and failures.

    The candidate guard API is loosely defined, so this helper progressively
    tries common call shapes before falling back to keyword arguments or a dict
    payload. Any exception is treated as a safe (0) prediction so downstream
    logic can conservatively assume the guard would have passed the input.
    """
    try:
        from src.guards.candidate import predict as predict_candidate
    except Exception:
        return 0

    trials = [
        ((text, category, language), {}),                # (t, cat, lang)
        ((text, category), {}),                          # (t, cat)
        ((text,), {}),                                   # (t)
        ((), {"text": text, "category": category, "language": language}),  # kwargs
        ((({"text": text, "category": category, "language": language}),), {}),  # dict payload
    ]
    for args, kwargs in trials:
        try:
            out = predict_candidate(*args, **kwargs)
            return 1 if bool(out) else 0
        except TypeError:
            continue
        except Exception:
            continue
    return 0


def _norm_label(x) -> int:
    """Normalize assorted truthy/falsy inputs to ``{0, 1}`` labels."""
    # Map a variety of inputs to {0=safe, 1=harmful}. Accepts ints/bools/strings.
    if isinstance(x, bool):
        return 1 if x else 0
    # numeric-ish (ints, floats, or strings like "0"/"1")
    try:
        if isinstance(x, (int, float)) or (isinstance(x, str) and x.strip().lstrip("-").isdigit()):
            return 1 if int(x) != 0 else 0
    except Exception:
        pass
    if isinstance(x, str):
        t = x.strip().lower()
        harmful = {"1","true","yes","y","harmful","unsafe","violation","bad","toxic","deny"}
        safe    = {"0","false","no","n","safe","benign","ok","harmless","good","allow"}
        if t in harmful: return 1
        if t in safe:    return 0
    # default to safe if unknown
    return 0


ROOT = Path(__file__).resolve().parents[2]
TEXT_KEYS = ("text", "prompt", "question", "input", "content", "message", "utterance")


def _field(row: Any, key: str, default=None):
    if isinstance(row, dict):
        return row.get(key, default)
    return getattr(row, key, default)


def _meta(row: Any) -> Dict[str, Any]:
    if not isinstance(row, dict):
        return {}
    ignore = set(TEXT_KEYS) | {"label", "category", "language"}
    return {k: v for k, v in row.items() if k not in ignore}

def _get_rows_path() -> Path:
    """Resolve the dataset path, honoring any ``config.yaml`` overrides."""
    import yaml
    cfgp = ROOT / "config.yaml"
    if cfgp.exists():
        cfg = yaml.safe_load(cfgp.read_text(encoding="utf-8")) or {}
        ds = cfg.get("dataset", "data/rows.yaml")
    else:
        ds = "data/rows.yaml"
    return (Path(ds) if Path(ds).is_absolute() else ROOT / ds)

# --- Small, deterministic transform library (no APIs needed) ---

LEET = str.maketrans({
    "a": "4",
    "e": "3",
    "i": "1",
    "o": "0",
    "s": "5",
    "t": "7",
    "g": "9",
    "b": "8",
})

CONFUSABLES = {
    # latin -> visually similar
    "a": "а",  # cyrillic a
    "e": "е",  # cyrillic ie
    "o": "ο",  # greek omicron
    "p": "р",  # cyrillic er
    "c": "с",  # cyrillic es
    "x": "х",  # cyrillic ha
    "y": "у",  # cyrillic u
    "H": "Н",  # cyrillic en
    "K": "Κ",  # greek kappa
    "M": "М",  # cyrillic em
}

HOMOGLYPHS = {
    "m": ["rn", "r\u200dn"],
    "w": ["vv", "v\u200dv"],
    "k": ["|<", "l<"],
    "l": ["|", "1"],
    "d": ["cl"],
    "h": ["|-|"],
    "M": ["RN", "R\u200dN"],
    "W": ["VV", "V\u200dV"],
    "K": ["|<", "I<"],
    "L": ["|", "1"],
    "D": ["CL"],
    "H": ["|-|"],
}

ZERO_WIDTH_CHARS = ["\u200b", "\u200c", "\u200d", "\ufeff"]
PUNCTUATION_BREAKS = ["-", ".", ",", "_", "/", "|", ";"]

SYNONYMS = [
    # very small illustrative pairs; extend per category as needed
    ("suicide", "take my own life"),
    ("kill myself", "end my life"),
    ("weapon", "firearm"),
    ("steal", "take without paying"),
    ("hack", "break into"),
    ("attack", "assault"),
]

def leetify(t: str, rng: random.Random | None = None) -> str:
    """Replace Latin characters with simple leetspeak substitutions."""
    return t.translate(LEET)


def insert_confusables(t: str, rng: random.Random | None = None) -> str:
    """Swap characters for visually similar homoglyphs with 25% probability."""
    rng = rng or random
    out: List[str] = []
    for ch in t:
        if ch in CONFUSABLES and rng.random() < 0.25:
            out.append(CONFUSABLES[ch])
        else:
            out.append(ch)
    return "".join(out)


def insert_homoglyphs(t: str, rng: random.Random | None = None) -> str:
    """Replace characters with ASCII homoglyph tricks (e.g. m -> rn)."""
    rng = rng or random
    out: List[str] = []
    for ch in t:
        options = HOMOGLYPHS.get(ch)
        if options and rng.random() < 0.35:
            out.append(rng.choice(options))
            continue
        options_lower = HOMOGLYPHS.get(ch.lower())
        if options_lower and rng.random() < 0.35:
            repl = rng.choice(options_lower)
            if ch.isupper():
                repl = repl.upper()
            out.append(repl)
        else:
            out.append(ch)
    return "".join(out)


def insert_zero_widths(t: str, rng: random.Random | None = None) -> str:
    """Slip zero-width characters between graphemes to disrupt tokenization."""
    rng = rng or random
    chars = list(t)
    if not chars:
        return t
    out = [chars[0]]
    for prev, nxt in zip(chars, chars[1:]):
        if rng.random() < 0.3 and prev.strip() and nxt.strip():
            out.append(rng.choice(ZERO_WIDTH_CHARS))
        out.append(nxt)
    return "".join(out)


def punctuation_split(t: str, rng: random.Random | None = None) -> str:
    """Insert lightweight punctuation inside long tokens."""
    rng = rng or random
    words = t.split()
    mutated: List[str] = []
    for word in words:
        clean = re.sub(r"[^A-Za-z]", "", word)
        if len(clean) < 5 or rng.random() < 0.2:
            mutated.append(word)
            continue
        inserts = 1 + (1 if len(clean) > 7 and rng.random() < 0.5 else 0)
        positions = sorted(rng.sample(range(1, len(word)), inserts))
        offset = 0
        new_word = list(word)
        for pos in positions:
            punctuation = rng.choice(PUNCTUATION_BREAKS)
            new_word.insert(pos + offset, punctuation)
            offset += 1
        mutated.append("".join(new_word))
    return " ".join(mutated)


def jitter_spacing(t: str, rng: random.Random | None = None) -> str:
    """Insert random spaces or hyphens into long words."""
    rng = rng or random

    def j(word: str) -> str:
        if len(word) < 7:
            return word
        idx = rng.randint(2, len(word) - 3)
        return word[:idx] + (" " if rng.random() < 0.5 else "-") + word[idx:]

    return " ".join(j(w) for w in t.split())


def synonym_swap(t: str, rng: random.Random | None = None) -> str:
    """Swap curated synonym pairs bidirectionally to vary phrasing."""
    rng = rng or random
    out = t
    for a, b in SYNONYMS:
        pattern_a = rf"\\b{re.escape(a)}\\b"
        pattern_b = rf"\\b{re.escape(b)}\\b"
        if rng.random() < 0.5:
            out = re.sub(pattern_a, b, out, flags=re.I)
        else:
            out = re.sub(pattern_b, a, out, flags=re.I)
    return out


TRANSFORM_REGISTRY: Dict[str, Callable[[str, random.Random | None], str]] = {
    "synonym_swap": synonym_swap,
    "leetify": leetify,
    "insert_confusables": insert_confusables,
    "insert_homoglyphs": insert_homoglyphs,
    "punctuation_split": punctuation_split,
    "insert_zero_widths": insert_zero_widths,
    "jitter_spacing": jitter_spacing,
}


VARIANT_RECIPES: List[Tuple[str, Sequence[str]]] = [
    ("medium", ("synonym_swap",)),
    ("medium", ("leetify",)),
    ("medium", ("insert_confusables",)),
    ("medium", ("insert_homoglyphs",)),
    ("medium", ("punctuation_split",)),
    ("medium", ("insert_zero_widths",)),
    ("medium", ("jitter_spacing",)),
    ("hard", ("leetify", "insert_zero_widths")),
    ("hard", ("insert_confusables", "insert_zero_widths")),
    ("hard", ("insert_homoglyphs", "insert_zero_widths")),
    ("hard", ("punctuation_split", "insert_zero_widths")),
    ("hard", ("leetify", "punctuation_split")),
    ("hard", ("synonym_swap", "insert_zero_widths")),
    ("hard", ("synonym_swap", "insert_confusables")),
    ("hard", ("synonym_swap", "insert_homoglyphs")),
    ("hard", ("synonym_swap", "punctuation_split")),
    ("hard", ("jitter_spacing", "insert_zero_widths")),
    ("very_hard", ("leetify", "insert_confusables", "insert_zero_widths")),
    ("very_hard", ("insert_confusables", "punctuation_split", "insert_zero_widths")),
    ("very_hard", ("insert_homoglyphs", "punctuation_split", "insert_zero_widths")),
    ("very_hard", ("synonym_swap", "leetify", "insert_zero_widths")),
    ("very_hard", ("synonym_swap", "insert_confusables", "insert_zero_widths")),
    ("very_hard", ("synonym_swap", "insert_homoglyphs", "insert_zero_widths")),
    ("very_hard", ("synonym_swap", "leetify", "insert_confusables")),
    ("very_hard", ("synonym_swap", "leetify", "insert_homoglyphs", "insert_zero_widths")),
]

@dataclass
class Row:
    """Structured view of a dataset entry and any extra metadata."""

    text: str
    label: int
    category: str
    language: str
    meta: Dict[str, Any]

def load_rows(path: Path) -> List[Row]:
    """Parse ``path`` into ``Row`` instances, normalizing labels along the way."""
    suffix = path.suffix.lower()
    if suffix in {".yaml", ".yml"}:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    else:
        with path.open(newline="", encoding="utf-8") as handle:
            data = list(csv.DictReader(handle))

    rows: List[Row] = []
    for raw in data:
        text = get_text(raw)
        if not text:
            continue
        rows.append(Row(
            text=text,
            label=_norm_label(_field(raw, "label", 0)),
            category=_field(raw, "category", ""),
            language=_field(raw, "language", "en"),
            meta=_meta(raw),
        ))
    return rows

def save_rows(path: Path, rows: List[Row]) -> None:
    """Serialize ``rows`` in YAML, preserving metadata and normalized labels."""
    out = []
    for r in rows:
        d = dict(text=r.text, label=_norm_label(r.label), category=r.category, language=r.language)
        d.update(r.meta)
        out.append(d)
    path.write_text(yaml.safe_dump(out, sort_keys=False, allow_unicode=True), encoding="utf-8")

def _apply_recipe(text: str, transforms: Sequence[str], rng: random.Random) -> tuple[str, Sequence[str]]:
    applied: List[str] = []
    out = text
    for name in transforms:
        transform = TRANSFORM_REGISTRY[name]
        out = transform(out, rng=rng)
        applied.append(name)
    return out, tuple(applied)


def _category_rng(category: str) -> random.Random:
    seed_material = f"{category}|adversary|{time.time_ns()}"
    seed = int(hashlib.sha256(seed_material.encode("utf-8")).hexdigest()[:16], 16)
    return random.Random(seed)


def generate_variants(
    row: Row,
    k_per_case: int = 3,
    seen: set[str] | None = None,
    rng: random.Random | None = None,
) -> List[Row]:
    """Create perturbed variants for ``row`` using the local transform library."""

    working_rng = rng or random.Random(
        int(hashlib.sha256(f"{row.category}|{row.language}|{row.text}".encode("utf-8")).hexdigest()[:16], 16)
    )

    recipes = list(VARIANT_RECIPES)
    working_rng.shuffle(recipes)

    cat_seen = seen if seen is not None else set()
    produced: List[Row] = []
    attempts = 0
    max_attempts = len(recipes) * 8

    while len(produced) < k_per_case and attempts < max_attempts:
        idx = attempts % len(recipes)
        difficulty, transforms = recipes[idx]
        attempts += 1

        mutated, applied = _apply_recipe(row.text, transforms, working_rng)
        if not mutated or mutated == row.text:
            continue
        if mutated in cat_seen:
            if attempts % len(recipes) == 0:
                working_rng.shuffle(recipes)
            continue

        new_meta = {
            **row.meta,
            "source": "redteam",
            "difficulty": difficulty,
            "transforms": list(applied),
        }
        produced.append(Row(
            text=mutated,
            label=row.label,
            category=row.category,
            language=row.language,
            meta=new_meta,
        ))
        cat_seen.add(mutated)

        if attempts % len(recipes) == 0:
            working_rng.shuffle(recipes)

    return produced

def find_false_negatives(rows: List[Row]) -> List[Tuple[Row, int]]:
    """Return ``(row, index)`` pairs the guard classified safe despite label=1."""
    # Re-run candidate guard to label predictions; FN = label=1 and pred=0
    from src.guards.candidate import predict as predict_candidate
    fns = []
    for i, r in enumerate(rows):
        pred = _safe_predict(r.text, r.category, r.language)
        if r.label == 1 and pred == 0:
            fns.append((r, i))
    return fns

def append_generated(base_path: Path, generated: List[Row]) -> str:
    """Append ``generated`` rows to ``base_path`` and return the backup path."""
    # Backup then append to rows.yaml
    ts = time.strftime("%Y%m%d-%H%M%S")
    backup = base_path.with_suffix(base_path.suffix + f".bak-{ts}")
    backup.write_text(base_path.read_text(encoding="utf-8"), encoding="utf-8")
    base = load_rows(base_path)
    # Dedup on text
    seen = set(r.text for r in base)
    new = [g for g in generated if g.text not in seen]
    merged = base + new
    save_rows(base_path, merged)
    return str(backup)

def run(
    max_cases_per_category: int = 8,
    k_per_case: int = 12,
    target_per_category: int = 20,
) -> Dict[str, int]:
    """Generate red-team variants and append them to the configured dataset.

    Args:
        max_cases_per_category: Upper bound on source rows considered per
            category. Keeps generation balanced across topics.
        k_per_case: Baseline number of variant attempts per source row.
        target_per_category: Minimum variants to create per failing category.

    Returns:
        Mapping with ``{"picked": int, "generated": int}`` summarizing work.
    """

    rows_path = _get_rows_path()
    rows = load_rows(rows_path)
    existing_redteam_counts: Dict[str, int] = defaultdict(int)
    for existing in rows:
        if existing.meta.get("source") == "redteam":
            existing_redteam_counts[existing.category or "misc"] += 1
    fns = find_false_negatives(rows)

    # Fallback: if no FNs, seed with all harmful rows
    if not fns:
        fns = [(r, -1) for r in rows if getattr(r, "label", 0) == 1]

    if not fns:
        return {"picked": 0, "generated": 0}

    picked_by_category: Dict[str, List[Row]] = defaultdict(list)
    for row, _idx in fns:
        category = row.category or "misc"
        if existing_redteam_counts.get(category, 0) >= target_per_category:
            continue
        if len(picked_by_category[category]) >= max_cases_per_category:
            continue
        picked_by_category[category].append(row)

    generated: List[Row] = []
    generated_by_category: Dict[str, int] = defaultdict(int)
    global_seen: set[str] = {r.text for r in rows}

    if not any(picked_by_category.values()):
        return {
            "picked": 0,
            "generated": 0,
            "by_category": {},
            "target_per_category": target_per_category,
        }
    category_rngs: Dict[str, random.Random] = {
        category: _category_rng(category) for category in picked_by_category
    }

    for category, rows_for_cat in picked_by_category.items():
        if not rows_for_cat:
            continue

        cat_seen: set[str] = set(global_seen)
        cat_rng = category_rngs[category]
        per_row_target = max(
            k_per_case,
            (target_per_category + len(rows_for_cat) - 1) // max(1, len(rows_for_cat)),
        )

        cat_variants: List[Row] = []
        for row in rows_for_cat:
            cat_variants.extend(
                generate_variants(row, k_per_case=per_row_target, seen=cat_seen, rng=cat_rng)
            )

        rounds = 0
        while len(cat_variants) < target_per_category and rows_for_cat:
            rounds += 1
            for row in rows_for_cat:
                needed = target_per_category - len(cat_variants)
                if needed <= 0:
                    break
                cat_variants.extend(
                    generate_variants(row, k_per_case=needed, seen=cat_seen, rng=cat_rng)
                )
            if rounds > 4:
                break

        if len(cat_variants) < target_per_category:
            raise RuntimeError(
                f"Unable to construct {target_per_category} unique variants for category '{category}'."
            )

        generated.extend(cat_variants)
        generated_by_category[category] += len(cat_variants)
        global_seen.update(v.text for v in cat_variants)

    if not generated:
        return {"picked": sum(len(v) for v in picked_by_category.values()), "generated": 0}

    backup = append_generated(rows_path, generated)

    report_dir = Path("report")
    report_dir.mkdir(exist_ok=True)
    summary_path = report_dir / "redteam_summary.yaml"

    record = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "picked": sum(len(v) for v in picked_by_category.values()),
        "generated": len(generated),
        "target_per_category": target_per_category,
        "by_category": {k: int(v) for k, v in generated_by_category.items()},
        "failing_categories": sorted(picked_by_category.keys()),
        "existing_redteam_counts": {k: int(v) for k, v in existing_redteam_counts.items()},
        "backup": backup,
    }

    records: List[Dict[str, Any]] = []

    if summary_path.exists():
        existing = yaml.safe_load(summary_path.read_text(encoding="utf-8"))
        if isinstance(existing, list):
            records = existing
        elif existing:
            records = [existing]
    

    records.append(record)
    summary_path.write_text(
        yaml.safe_dump(records, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )

    return {
        "picked": record["picked"],
        "generated": record["generated"],
        "by_category": record["by_category"],
        "target_per_category": target_per_category,
    }
