from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping

from service.api import _resolve_guard, _wrap_guard_sync


def predict(text: str, category: str, language: str, *, guard: str = "candidate") -> Dict[str, Any]:
    spec = _resolve_guard(guard)
    fn = _wrap_guard_sync(guard, spec)
    result = fn(text, category, language)
    return result  # type: ignore[no-any-return]


def batch_predict(rows: Iterable[Mapping[str, str]], *, guard: str = "candidate") -> List[Dict[str, Any]]:
    spec = _resolve_guard(guard)
    fn = _wrap_guard_sync(guard, spec)
    out: List[Dict[str, Any]] = []
    for row in rows:
        out.append(fn(row.get("text", ""), row.get("category", "misc"), row.get("language", "en")))
    return out



