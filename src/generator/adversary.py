
"""Generate adversarial dataset augmentations to probe guard model coverage."""

from __future__ import annotations
from dataclasses import dataclass
import time
from pathlib import Path
from typing import List, Dict, Any, Tuple
import csv
import yaml
import random
import re

from src.report.build_report import get_text



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
    "a":"4","e":"3","i":"1","o":"0","s":"5","t":"7","g":"9","b":"8"
})

CONFUSABLES = {
    # latin -> visually similar
    "a":"а", # cyrillic a
    "e":"е", # cyrillic ie
    "o":"ο", # greek omicron
    "p":"р", # cyrillic er
    "c":"с", # cyrillic es
    "x":"х", # cyrillic ha
    "y":"у", # cyrillic u
    "H":"Н", # cyrillic en
    "K":"Κ", # greek kappa
    "M":"М", # cyrillic em
}

SYNONYMS = [
    # very small illustrative pairs; extend per category as needed
    ("suicide", "take my own life"),
    ("kill myself", "end my life"),
    ("weapon", "firearm"),
    ("steal", "take without paying"),
    ("hack", "break into"),
    ("attack", "assault"),
]

ZWSP = "\u200b"

def leetify(t: str) -> str:
    """Replace Latin characters with simple leetspeak substitutions."""
    return t.translate(LEET)

def insert_confusables(t: str) -> str:
    """Swap characters for visually similar homoglyphs with 25% probability."""
    out = []
    for ch in t:
        if ch in CONFUSABLES and random.random() < 0.25:
            out.append(CONFUSABLES[ch])
        else:
            out.append(ch)
    return "".join(out)

def insert_zwsp(t: str) -> str:
    """Slip zero-width spaces between characters to disrupt tokenization."""
    # Insert ZWSP between some letters to bypass naive filters
    chars = list(t)
    i = 1
    out = [chars[0]] if chars else []
    while i < len(chars):
        out.append(ZWSP if random.random() < 0.2 else "")
        out.append(chars[i])
        i += 1
    return "".join(out)

def jitter_spacing(t: str) -> str:
    """Insert random spaces or hyphens into long words."""
    # random spaces/hyphens in words longer than 6
    def j(word):
        if len(word) < 7: return word
        i = random.randint(2, len(word)-3)
        return word[:i] + (" " if random.random()<0.5 else "-") + word[i:]
    return " ".join(j(w) for w in t.split())

def synonym_swap(t: str) -> str:
    """Swap curated synonym pairs bidirectionally to vary phrasing."""
    out = t
    for a,b in SYNONYMS:
        if random.random() < 0.5:
            out = re.sub(rf"\\b{re.escape(a)}\\b", b, out, flags=re.I)
        else:
            out = re.sub(rf"\\b{re.escape(b)}\\b", a, out, flags=re.I)
    return out

def chain(*funcs):
    """Compose multiple text transforms into a single callable."""
    def _f(t):
        for f in funcs:
            t = f(t)
        return t
    return _f

VARIANTS = [
    ("easy",      [synonym_swap]),
    ("medium",    [leetify, synonym_swap]),
    ("medium",    [insert_confusables]),
    ("hard",      [insert_zwsp, synonym_swap]),
    ("hard",      [jitter_spacing, insert_confusables]),
    ("hard",      [leetify, insert_zwsp, insert_confusables]),
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

def generate_variants(row: Row, k_per_case: int = 3) -> List[Row]:
    """Create perturbed variants for ``row`` using the local transform library."""
    random.seed(42)  # reproducible-ish
    variants = []
    seen = set()
    for (diff, fs) in VARIANTS:
        if len(variants) >= k_per_case: break
        f = chain(*fs)
        v = f(row.text)
        if v and v != row.text and v not in seen:
            seen.add(v)
            variants.append(Row(
                text=v,
                label=row.label,
                category=row.category,
                language=row.language,
                meta={**row.meta, "source":"redteam", "difficulty":diff}
            ))
    return variants

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

def run(max_cases_per_category: int = 5, k_per_case: int = 3) -> Dict[str,int]:
    """Generate red-team variants and append them to the configured dataset.

    Args:
        max_cases_per_category: Upper bound on source rows considered per
            category. Keeps generation balanced across topics.
        k_per_case: Number of variant attempts per source row.

    Returns:
        Mapping with ``{"picked": int, "generated": int}`` summarizing work.
    """
    rows_path = _get_rows_path()
    rows = load_rows(rows_path)
    fns = find_false_negatives(rows)

    # Fallback: if no FNs, seed with all harmful rows

    if not fns:

        fns = [(r, -1) for r in rows if getattr(r, "label", 0) == 1]

    # limit per category
    picked = []
    per_cat = {}
    for r,_idx in fns:
        c = r.category or "misc"
        if per_cat.get(c,0) >= max_cases_per_category: 
            continue
        picked.append(r)
        per_cat[c] = per_cat.get(c,0)+1

    generated = []
    for r in picked:
        generated.extend(generate_variants(r, k_per_case=k_per_case))

    if not generated:
        return {"picked":0, "generated":0}

    backup = append_generated(rows_path, generated)

    # write a small summary
    report_dir = Path("report"); report_dir.mkdir(exist_ok=True)
    (report_dir / "redteam_summary.yaml").write_text(
        yaml.safe_dump({
            "picked": len(picked),
            "generated": len(generated),
            "by_category": {k:int(v) for k,v in per_cat.items()},
            "backup": backup
        }, sort_keys=False),
        encoding="utf-8"
    )
    return {"picked":len(picked), "generated":len(generated)}
