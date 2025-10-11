import re
import time
from typing import Any, Dict

# Very small dictionaries for demo purposes.
# In real life, you expand/maintain these via config or external lists.
KEYWORDS = {
    "violence": [
        r"\bbomb\b", r"\bgun\b", r"\bknife\b", r"\bk!ll\b", r"\bkill\b",
        r"\bhurt\b", r"\bexplosive\b"
    ],
    "self_harm": [
        r"\bself[-\s]?harm\b", r"\bsuicide\b", r"\bkill myself\b"
    ],
    "crime": [
        r"\bhack\b", r"\bsteal\b", r"\bquietly break in\b", r"\bcard skimming\b",
        r"\bsql injection\b", r"\bwi[-\s]?fi\b.*\bhack\b"
    ],
    "malware": [
        r"\bmalware\b", r"\bransomware\b", r"\bkeylogger\b"
    ],
    "pii": [
        r"\bssn\b", r"\bsocial security number\b", r"\bcredit card\b"
    ],
    # Farsi minimal examples (demo only)
    "violence_fa": [r"\bبمب\b"],
}

SAFE_WHITELIST = [
    # Allow legit security/first-aid context words to reduce false positives
    r"\bdefen[cs]e\b", r"\bhow to prevent\b", r"\bmitigat(e|ion)\b",
    r"\bfirst[-\s]?aid\b", r"\bbest practices\b"
]

LEETSPEAK_MAP = {
    "0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "!": "i", "$": "s"
}

def _normalize(text: str) -> str:
    t = text.lower()
    for k, v in LEETSPEAK_MAP.items():
        t = t.replace(k, v)
    # Normalize some punctuation spacing
    t = re.sub(r"[_\-]{2,}", "-", t)
    t = re.sub(r"\s{2,}", " ", t).strip()
    return t

def predict(text: str, timeout_ms: int = 800, **kwargs) -> Dict[str, Any]:
    """
    Returns:
      {
        "prediction": "pass" | "flag",
        "score": float,   # naive confidence 0..1 (optional)
        "latency_ms": int
      }
    """
    start = time.time()
    t = _normalize(text)

    # Whitelist check (if text clearly educational/defensive, lean "pass")
    for w in SAFE_WHITELIST:
        if re.search(w, t):
            latency = int((time.time() - start) * 1000)
            return {"prediction": "pass", "score": 0.2, "latency_ms": latency}

    # Category triggers
    patterns = []
    for patt_list in KEYWORDS.values():
        patterns.extend(patt_list)

    flagged = any(re.search(p, t) for p in patterns)

    latency = int((time.time() - start) * 1000)
    if flagged:
        return {"prediction": "flag", "score": 0.9, "latency_ms": latency}
    else:
        return {"prediction": "pass", "score": 0.1, "latency_ms": latency}
