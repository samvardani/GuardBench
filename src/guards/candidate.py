import re, time
from typing import Dict
from src.utils.text_norm import normalize
from src.utils.io_utils import load_config

CFG = load_config()  # read once

PATTERNS = {
    "violence": [
        r"\bbomb\b", r"b\ o\ m\ b", r"\bexplosive(s)?\b", r"\bmake\s+a\s+bomb\b",
        r"\bknife\b", r"\bgun\b", r"\bkill\b", r"\bhurt\b"
    ],
    "self_harm": [r"\bself[-\s]?harm\b", r"\bsuicide\b", r"\bkill myself\b"],
    "crime": [
        r"\bhack\b", r"\bhow to hack\b", r"\bquietly break in\b",
        r"\bsql\s*injection\b", r"\bwi[-\s]?fi\b.*\bhack\b"
    ],
    "malware": [
        r"\bmalware\b", r"m\ a\ l\ w\ a\ r\ e", r"\bransomware\b",
        r"\bkeylogger\b", r"\bbackdoor\b", r"\bwrite\s+(a|some)\s+malware\b",
        r"\bteach[_\s-]?malware\b"
    ],
    "pii": [r"\bssn\b", r"\bsocial\s+security\s+number\b", r"\bcredit\s*card\b"],
    "extremism": [r"\bisis\b", r"\bal[-\s]?qaeda\b", r"\bneo[-\s]?nazi\b"],
    "fa_violence": [r"\bبمب\b"]
}

WHITELIST = [
    r"\bdefen[cs]e\b", r"\bhow to prevent\b", r"\bmitigat(e|ion)\b",
    r"\bfirst[-\s]?aid\b", r"\bbest practices\b", r"\blegal\b", r"\bwith defenses\b"
]

THRESHOLDS = CFG.get("thresholds", {"default": 1.0})

def _whitelisted(t: str) -> bool:
    return any(re.search(w, t) for w in WHITELIST)

def predict(text: str, timeout_ms: int = 800) -> Dict:
    start = time.time()
    t = normalize(text)

    if _whitelisted(t):
        latency = int((time.time()-start)*1000)
        return {"prediction": "pass", "score": 0.2, "latency_ms": latency}

    hits = []
    for cat, pats in PATTERNS.items():
        if any(re.search(p, t) for p in pats):
            hits.append(cat)

    # Score = number of categories matched + small weight
    score = 0.0
    for h in hits:
        score += 1.0

    flagged = False
    for h in hits:
        thr = THRESHOLDS.get(h, THRESHOLDS.get("default", 1.0))
        if score >= thr:
            flagged = True
            break

    latency = int((time.time()-start)*1000)
    return {
        "prediction": "flag" if flagged else "pass",
        "score": min(score/5.0, 1.0),
        "latency_ms": latency
    }
