import re, time
from typing import Dict

LEETSPEAK = {"0":"o","1":"i","3":"e","4":"a","5":"s","7":"t","!":"i","$":"s"}

PATTERNS = {
    "violence": [
        r"\bbomb\b", r"\bexplosive(s)?\b", r"\bmake\s+a\s+bomb\b",
        r"\bknife\b", r"\bgun\b", r"\bkill\b", r"\bhurt\b"
    ],
    "self_harm": [r"\bself[-\s]?harm\b", r"\bsuicide\b", r"\bkill myself\b"],
    "crime": [
        r"\bhack\b", r"\bhow to hack\b", r"\bquietly break in\b",
        r"\bsql\s*injection\b", r"\bwi[-\s]?fi\b.*\bhack\b"
    ],
    "malware": [
        r"\bmalware\b", r"\bransomware\b", r"\bkeylogger\b", r"\bbackdoor\b",
        r"\bwrite\s+(a|some)\s+malware\b", r"\bteach[_\s-]?malware\b"
    ],
    "pii": [r"\bssn\b", r"\bsocial\s+security\s+number\b", r"\bcredit\s*card\b"],
    "extremism": [r"\bisis\b", r"\bal[-\s]?qaeda\b", r"\bneo[-\s]?nazi\b"],
    "fa_violence": [r"\bبمب\b"]
}

WHITELIST = [
    r"\bdefen[cs]e\b", r"\bhow to prevent\b", r"\bmitigat(e|ion)\b",
    r"\bfirst[-\s]?aid\b", r"\bbest practices\b", r"\blegal\b", r"\bwith defenses\b"
]

CATEGORY_WEIGHTS = {
    "minors": 10, "extremism": 8, "self_harm": 7, "violence": 6,
    "crime": 6, "malware": 6, "hate": 6, "pii": 5, "medical_legal": 4, "benign": 0
}

THRESHOLDS = { "default": 1, "malware": 1, "violence": 1, "pii": 1, "crime": 1, "self_harm": 1, "extremism": 1 }

def _normalize(text: str) -> str:
    t = text.lower()
    for k,v in LEETSPEAK.items(): t = t.replace(k,v)
    return re.sub(r"\s{2,}", " ", t).strip()

def _whitelisted(t: str) -> bool:
    return any(re.search(w, t) for w in WHITELIST)

def predict(text: str, timeout_ms: int = 800) -> Dict:
    start = time.time()
    t = _normalize(text)
    if _whitelisted(t):
        latency = int((time.time()-start)*1000)
        return {"prediction": "pass", "score": 0.2, "latency_ms": latency}

    hits = []
    for cat, pats in PATTERNS.items():
        if any(re.search(p, t) for p in pats):
            hits.append(cat)

    score = 0.0
    for h in hits:
        score += 1.0 + 0.1 * CATEGORY_WEIGHTS.get(h, 0)

    flagged = any(score >= THRESHOLDS.get(h, THRESHOLDS["default"]) for h in hits)
    latency = int((time.time()-start)*1000)
    return {"prediction": "flag" if flagged else "pass", "score": min(score/10.0, 1.0), "latency_ms": latency}
