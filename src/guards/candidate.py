import re, time
from typing import Dict
from src.utils.text_norm import normalize
from src.utils.io_utils import load_config

CFG = load_config()

PATTERNS = {
    # Violence
    "violence": [
        r"\bbomb\b",                      # plain bomb
        r"b\ o\ m\ b",                    # spaced letters
        r"make\s*a\s*bomb",               # spaces optional via \s*
        r"\bmakeabomb\b",                 # glued variant
        r"\bexplosive(s)?\b",
        r"\bknife\b", r"\bgun\b",
        r"\bkill\b", r"\bhurt\b",
        r"hurt\s+someone\s+quiet(?:ly)?", # “hurt someone quietly”
    ],
    # Self-harm
    "self_harm": [
        r"\bself[-\s]?harm\b",
        r"\bsuicide\b",
        r"\bkill myself\b",
        r"\bcut(ting)?\b"
    ],
    # Crime / cyber
    "crime": [
        r"\bhack\b", r"\bhow to hack\b",
        r"\bquietly break in\b",
        r"\bsql\s*injection\b",
        r"\bwi[-\s]?fi\b.*\bhack\b"
    ],
    # Malware
    "malware": [
        r"\bmalware\b", r"m\ a\ l\ w\ a\ r\ e",
        r"\bransomware\b", r"\bkeylogger\b", r"\bbackdoor\b",
        r"\bwrite\s+(a|some)\s+malware\b",
        r"\bteach[_\s-]?malware\b"
    ],
    # PII
    "pii": [r"\bssn\b", r"\bsocial\s+security\s+number\b", r"\bcredit\s*card\b"],
    # Extremism
    "extremism": [r"\bisis\b", r"\bal[-\s]?qaeda\b", r"\bneo[-\s]?nazi\b"],
    # Farsi violence (kept simple)
    "fa_violence": [r"\bبمب\b", r"\bچاقو\b", r"\bاسلحه\b", r"\bکشتن\b"]
}

# Narrow whitelist (used only if no harms detected)
WHITELIST = [
    r"\bhow to prevent\b",
    r"\bmitigat(e|ion)\b",
    r"\bdefen[cs]e\b",
    r"\bbest practices\b",
    r"\blegal\b"
    # NOTE: we intentionally do NOT include "with defenses" or "first-aid"
]

THRESHOLDS = CFG.get("thresholds", {"default": 1.0})
SLICE_THRESHOLDS = CFG.get("slice_thresholds", {})   # { category: { lang: thr } }

def _whitelisted(t: str) -> bool:
    return any(re.search(w, t) for w in WHITELIST)

def predict(text: str, timeout_ms: int = 800, **meta) -> Dict:
    start = time.time()
    t = normalize(text)

    # 1) Find matches first
    hits = []
    for cat, pats in PATTERNS.items():
        if any(re.search(p, t) for p in pats):
            hits.append(cat)

    # 2) Only then allow whitelist to pass queries with no hits
    if not hits and _whitelisted(t):
        latency = int((time.time()-start)*1000)
        return {"prediction": "pass", "score": 0.2, "latency_ms": latency}

    # 3) Score and thresholding
    score = float(len(hits))
    lang = (meta.get("language") or meta.get("lang")) if meta else None

    flagged = False
    for h in hits:
        slice_thr = SLICE_THRESHOLDS.get(h, {}).get(lang) if (lang is not None) else None
        thr = slice_thr if slice_thr is not None else THRESHOLDS.get(h, THRESHOLDS.get("default", 1.0))
        if score >= thr:
            flagged = True
            break

    latency = int((time.time()-start)*1000)
    return {
        "prediction": "flag" if flagged else "pass",
        "score": min(score/5.0, 1.0),
        "latency_ms": latency
    }
