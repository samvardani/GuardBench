import re, time
import time
from typing import Dict
from src.utils.text_norm import normalize
from src.utils.io_utils import load_config

CFG = load_config()

# ---------- PATTERNS ----------
PATTERNS = {
    # Violence (incl. glued/spaced variants)
    "violence": [
        r"\bbomb\b",
        r"b\ o\ m\ b",
        r"\bmakeabomb\b",
        r"make\s*a\s*bomb",
        r"\bexplosive(s)?\b",
        r"\bknife\b", r"\bgun\b",
        r"\bkill\b", r"\bhurt\b",
        r"hurt\s+someone\s+quiet(?:ly)?",
    ],

    # Self-harm
    "self_harm": [
        r"\bself[-\s]?harm\b",
        r"\bsuicide\b",
        r"\bkill myself\b",
        r"\bcut(ting)?\b",
    ],

    # Crime (focus: SQLi & common exploit verbs)
    "crime": [
        r"\bsql\s*injection\b",
        r"\bunion\s+select\b",
        r"(?:'|%27)\s*or\s*(?:'|%27)?\s*1\s*=\s*1",   # ' OR 1=1
        r"\bor\s+1\s*=\s*1\b",
        r"1\s*=\s*1\s*--",
        r"\bsleep\s*\(",
        r"\bdrop\s+table\b",
        r"\binformation_schema\b",
        r"\bxp_cmdshell\b",
        r"\bhack\b", r"\bhow to hack\b", r"\bquietly break in\b",
        r"\bwi[-\s]?fi\b.*\bhack\b",
    ],

    # Malware (inc. spaced/leet variants)
    "malware": [
        r"\bmalware\b", r"m\ a\ l\ w\ a\ r\ e",
        r"\bransomware\b", r"\bkeylogger\b", r"\bbackdoor\b",
        r"\bwrite\s+(a|some)\s+malware\b",
        r"\bteach[_\s-]?malware\b",
    ],

    # PII / Extremism
    "pii": [r"\bssn\b", r"\bsocial\s+security\s+number\b", r"\bcredit\s*card\b"],
    "extremism": [r"\bisis\b", r"\bal[-\s]?qaeda\b", r"\bneo[-\s]?nazi\b"],

    # Farsi violence
    "fa_violence": [r"\bبمب\b", r"\bچاقو\b", r"\bاسلحه\b", r"\bکشتن\b"],
}

# Narrow whitelist — only used if there were NO matches
WHITELIST = [
    r"\bhow to prevent\b", r"\bmitigat(e|ion)\b", r"\bdefen[cs]e\b",
    r"\bbest practices\b", r"\blegal\b"
]

# Supportive self-harm phrases (classify as unsafe, but mark context)
SELF_HARM_SUPPORT = [
    r"\bfirst[-\s]?aid\b", r"\bwound\s*care\b", r"\bsafety\s*plan\b",
    r"\bhotline\b", r"\bseek\s*help\b"
]

THRESHOLDS = CFG.get("thresholds", {"default": 1.0})
SLICE_THRESHOLDS = CFG.get("slice_thresholds", {})   # { category: { lang: thr } }

def _whitelisted(t: str) -> bool:
    return any(re.search(w, t) for w in WHITELIST)

def _supportive_self_harm(t: str) -> bool:
    return any(re.search(w, t) for w in SELF_HARM_SUPPORT)

def predict(text: str, timeout_ms: int = 800, **meta) -> Dict:
    start = time.time()
    t = normalize(text)

    # 1) detect categories first
    hits = []
    for cat, pats in PATTERNS.items():
        if any(re.search(p, t) for p in pats):
            hits.append(cat)

    # 2) only if no hits, apply whitelist to allow pass
    if not hits and _whitelisted(t):
        latency = int((time.time()-start)*1000)
        return {"prediction": "pass", "score": 0.2, "latency_ms": latency}

    # 3) scoring + slice thresholds
    score = float(len(hits))
    lang = (meta.get("language") or meta.get("lang")) if meta else None

    flagged = False
    for h in hits:
        slice_thr = SLICE_THRESHOLDS.get(h, {}).get(lang) if (lang is not None) else None
        thr = slice_thr if slice_thr is not None else THRESHOLDS.get(h, THRESHOLDS.get("default", 1.0))
        if score >= thr:
            flagged = True
            break

    # 4) annotate supportive self-harm (still flag)
    extra = {}
    if flagged and "self_harm" in hits and _supportive_self_harm(t):
        extra["context"] = "supportive_self_harm"

    latency = int((time.time()-start)*1000)
    return {"prediction": "flag" if flagged else "pass",
            "score": min(score/5.0, 1.0),
            "latency_ms": latency,
            **extra}
