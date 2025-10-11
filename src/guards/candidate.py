
from __future__ import annotations
import re
import time
import unicodedata
from pathlib import Path
from typing import Dict, Optional
import yaml

try:
    from src.policy.compiler import load_compiled_policy
except Exception:  # pragma: no cover - policy optional during bootstrap
    load_compiled_policy = None  # type: ignore

# ---------- Config access ----------
ROOT = Path(__file__).resolve().parents[2]
_CFG_CACHE: dict | None = None
_CFG_MTIME: float | None = None


def _load_cfg() -> dict:
    global _CFG_CACHE, _CFG_MTIME
    cfgp = ROOT / "config.yaml"
    if not cfgp.exists():
        _CFG_CACHE = None
        _CFG_MTIME = None
        return {}
    try:
        mtime = cfgp.stat().st_mtime
    except OSError:
        return _CFG_CACHE or {}
    if _CFG_CACHE is not None and _CFG_MTIME == mtime:
        return _CFG_CACHE
    try:
        _CFG_CACHE = yaml.safe_load(cfgp.read_text(encoding="utf-8")) or {}
        _CFG_MTIME = mtime
    except Exception:
        _CFG_CACHE = {}
    return _CFG_CACHE or {}


_POLICY_CACHE = None
_POLICY_MTIME: float | None = None


def _load_policy():
    global _POLICY_CACHE, _POLICY_MTIME
    if load_compiled_policy is None:
        return None
    path = ROOT / "policy" / "policy.yaml"
    if not path.exists():
        _POLICY_CACHE = None
        _POLICY_MTIME = None
        return None
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return _POLICY_CACHE
    if _POLICY_CACHE is None or _POLICY_MTIME != mtime:
        try:
            _POLICY_CACHE = load_compiled_policy(path)
            _POLICY_MTIME = mtime
        except FileNotFoundError:
            _POLICY_CACHE = None
            _POLICY_MTIME = None
    return _POLICY_CACHE


def _slice_threshold(category: Optional[str], language: Optional[str], default: float = 0.5) -> float:
    policy = _load_policy()
    if policy and category:
        key = (category, language or "en")
        slice_ = policy.slices.get(key)
        if not slice_ and language:
            slice_ = policy.slices.get((category, "en"))
        if slice_:
            return slice_.threshold

    cfg = _load_cfg()
    st = (cfg.get("slice_thresholds") or {}) if isinstance(cfg, dict) else {}
    if isinstance(st, dict) and category and (category in st):
        langs = st[category] or {}
        if isinstance(langs, dict):
            if language in langs and langs[language] is not None:
                try:
                    return float(langs[language])
                except Exception:
                    pass
            # fall back to any one value under category if lang missing
            for v in langs.values():
                try:
                    return float(v)
                except Exception:
                    continue
    # fall back to global default_threshold if present
    if isinstance(cfg, dict) and "default_threshold" in cfg:
        try:
            return float(cfg["default_threshold"])
        except Exception:
            pass
    return float(default)

# ---------- Aggressive normalization ----------
ZERO_WIDTH = {"\u200b", "\u200c", "\u200d", "\ufeff"}
TATWEEL = "\u0640"
CONFUSABLES_REV = {
    "а":"a","е":"e","ο":"o","р":"p","с":"c","х":"x","у":"y",  # Cyrillic/Greek → Latin
    "Н":"H","Κ":"K","М":"M",
}
LEET_REV = str.maketrans({"4":"a","3":"e","1":"i","0":"o","5":"s","7":"t","8":"b","9":"g","!":"i","@":"a","$":"s"})

def _normalize_aggressive(t: str) -> str:
    t = unicodedata.normalize("NFKC", t or "")
    t = "".join(ch for ch in t if ch not in ZERO_WIDTH)
    t = t.replace(TATWEEL, "")
    t = "".join(CONFUSABLES_REV.get(ch, ch) for ch in t)
    t = t.translate(LEET_REV)
    t = re.sub(r"[\\/_]+", " ", t)
    t = re.sub(r"-+", " ", t)
    t = re.sub(r"\s+", " ", t)
    return t.lower().strip()


def _wordify(text: str) -> str:
    """Collapse spaced-out characters into words to undo simple obfuscation."""
    tokens = re.findall(r"[0-9a-z\u0600-\u06FF]+", text)
    words = []
    buffer = []

    for tok in tokens:
        if len(tok) == 1 and tok.isalpha():
            buffer.append(tok)
            continue
        if buffer:
            words.append("".join(buffer))
            buffer.clear()
        words.append(tok)

    if buffer:
        words.append("".join(buffer))

    return " ".join(words)


def _text_variants(text: str) -> tuple[str, ...]:
    variants = []
    for candidate in (text, _wordify(text)):
        candidate = candidate.strip()
        if candidate and candidate not in variants:
            variants.append(candidate)
    compact = variants[-1].replace(" ", "") if variants else ""
    if compact and compact not in variants:
        variants.append(compact)
    return tuple(variants)

# ---------- Patterns (expanded) ----------
CATEGORY_PATTERNS = {
    "violence": [
        r"\bkill\b", r"\bpoison\b", r"\bhurt\b", r"\bassault\b",
        r"\bbomb\b", r"\bpipe\s*bomb\b",
        r"\bmake\s+(a\s+)?(pipe\s*)?bomb\b",
        r"\bhow\s+to\s+make\s+(a\s+)?bomb\b",
    ],
    "self_harm": [
        r"\bkill\s+myself\b", r"\bend\s+my\s+life\b",
        r"\bhow\s+to\s+(?:harm|hurt)\s+myself\b",
        r"\bself[-\s]*harm\b",
        r"\bmethods?\b.*\b(suicide|self[-\s]*harm)\b",
        r"\bcut(?:ting)?\b.*\b(myself|wrists?|veins)\b",
        # drop generic "coping strategies" and "feeling down" to reduce benign FPR
    ],
    "crime": [
        r"\bhack\b", r"\bwireless\b.*\bhack\b", r"\bsql injection\b",
        r"\bsteal\b", r"\bbreak in\b",
    ],
    "malware": [
        r"/etc/shadow",
        r"\b(exfiltrat\w+).*(/etc|shadow|passwd)\b",
        r"\b(powershell|wget|curl|certutil)\b.*\b(base64|payload|xor)\b",
        r"\b(keylogger|backdoor|c2|command\s+and\s+control)\b",
        r"\bmalware\b",
        r"\bteach\W*malware\b",
    ],
    "pii": [
        r"\bssn\b", r"\bsocial security number\b", r"\bcredit card\b", r"\bcvv\b",
    ],
    # minimal Farsi violence coverage
    "violence_fa": [r"بمب", r"کشت(ن|ار)", r"انفجار", r"چاقو", r"حمله", r"خشونت", r"آسیب"],
}

CATEGORY_SUBSTRINGS = {
    "violence": [
        "makeabomb", "buildabomb", "pipebomb", "hurtsomeone", "killpeople",
        "killperson", "killhim", "killher",
    ],
    "self_harm": [
        "selfharm", "killmyself", "endmylife", "hurtmyself", "harmmyself",
        "cutmyself", "cutmywrists", "cuttingwrists", "cutmyveins", "cuttingveins",
    ],
    "malware": [
        "malware", "teachmalware", "spreadmalware", "deploymalware",
        "installmalware", "etcshadow", "shadowfile", "stealpasswd",
    ],
}

SAFE_CONTEXT = [
    r"\bdefen[cs]e\b", r"\bprevent(ion)?\b", r"\bmitigat(e|ion)\b",
    r"\bfirst[-\s]?aid\b", r"\bresponsible disclosure\b", r"\bhow to avoid\b",
    r"\bbest practices\b",
    r"\btherapy\b", r"\bhelpline\b", r"\bresourc(es|e)\b",
    r"\bawareness\b", r"\beducation(al)?\b", r"\bpolicy\b",
    r"\bprevention\b",
]

WEIGHTS = {
    "violence": 1.0, "self_harm": 1.2, "crime": 1.0, "malware": 1.3,
    "pii": 1.0, "violence_fa": 1.0,
}


def _score_text_legacy(t: str) -> float:
    variants = _text_variants(t)
    compact_variants = tuple(v.replace(" ", "") for v in variants)
    penalty = 0.8 if any(re.search(w, variant, re.I) for variant in variants for w in SAFE_CONTEXT) else 0.0
    score = 0.0
    for cat, patterns in CATEGORY_PATTERNS.items():
        matched = any(re.search(p, variant, re.I) for variant in variants for p in patterns)
        if not matched:
            substrings = CATEGORY_SUBSTRINGS.get(cat, ())
            if substrings:
                matched = any(sub in cv for cv in compact_variants for sub in substrings if cv)
        if matched:
            score += WEIGHTS.get(cat, 1.0)
    return max(0.0, score - penalty)


def _score_text_policy(t: str, category: Optional[str], language: Optional[str]) -> Optional[float]:
    policy = _load_policy()
    if not policy or not category:
        return None
    key = (category, language or "en")
    slice_ = policy.slices.get(key)
    if not slice_ and language:
        slice_ = policy.slices.get((category, "en"))
    if not slice_:
        return None

    lang_norm = (language or "en").lower()

    variants = _text_variants(t)
    lower_variants = [v.lower() for v in variants]
    compact_variants = [v.replace(" ", "") for v in lower_variants]

    score = 0.0
    for rule in slice_.rules:
        if rule.languages and lang_norm not in rule.languages:
            continue
        matched = False
        if rule.regex:
            for pattern in rule.regex:
                if any(pattern.search(variant) for variant in variants):
                    matched = True
                    break
        if not matched and rule.substrings:
            for compact in compact_variants:
                if any(sub in compact for sub in rule.substrings if compact):
                    matched = True
                    break
        if matched:
            score += rule.weight

    if policy.safe_context_penalty > 0 and policy.safe_context_patterns:
        if any(pattern.search(variant) for pattern in policy.safe_context_patterns for variant in variants):
            score -= policy.safe_context_penalty

    return max(0.0, score)


def _score_text(t: str, category: Optional[str], language: Optional[str]) -> float:
    policy_score = _score_text_policy(t, category, language)
    if policy_score is not None:
        return policy_score
    return _score_text_legacy(t)

# NOTE: Accept **kwargs so callers can pass category/language without breaking
def predict(text: str,
            category: Optional[str] = None,
            language: Optional[str] = None,
            default_threshold: Optional[float] = None,
            **kwargs) -> Dict:
    """
    Returns: {"prediction": "flag"|"pass", "score": float, "threshold": float, "latency_ms": int}
    Pred threshold is read from config.yaml slice_thresholds[category][language] when provided.
    """
    start = time.time()
    t = _normalize_aggressive(text)
    s = _score_text(t, category, language)
    thr = float(default_threshold) if default_threshold is not None else _slice_threshold(category, language, default=0.5)
    pred = "flag" if s > thr else "pass"
    latency = int((time.time() - start) * 1000)
    cfg = _load_cfg()
    policy_version = cfg.get("policy_version") or getattr(_load_policy(), "version", None)
    return {
        "prediction": pred,
        "score": float(s),
        "threshold": float(thr),
        "latency_ms": latency,
        "policy_version": policy_version,
    }
