import re
LEETSPEAK = {"0":"o","1":"i","3":"e","4":"a","5":"s","7":"t","!":"i","$":"s"}

def normalize(text: str) -> str:
    t = text.lower()
    for k,v in LEETSPEAK.items(): t = t.replace(k, v)
    # remove zero-width joiner and Arabic tatweel
    t = t.replace("\u200b", "").replace("\u0640", "")
    # collapse "b o m b" → "bomb" (>=4 letters spaced)
    def _join(m): return m.group(0).replace(" ", "")
    t = re.sub(r"(?:[a-zA-Z]\s){3,}[a-zA-Z]", _join, t)
    # clean spacing/punct
    t = re.sub(r"[_\-]{2,}", "-", t)
    t = re.sub(r"\s{2,}", " ", t).strip()
    return t
