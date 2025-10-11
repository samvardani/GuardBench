from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping

from service.api import _resolve_guard, _wrap_guard_sync


def predict(text: str, category: str, language: str, *, guard: str = "candidate") -> Dict[str, Any]:
    spec = _resolve_guard(guard)
    fn = _wrap_guard_sync(guard, spec)
    return fn(text, category, language)  # type: ignore[no-any-return]


def batch_predict(rows: Iterable[Mapping[str, str]], *, guard: str = "candidate") -> List[Dict[str, Any]]:
    spec = _resolve_guard(guard)
    fn = _wrap_guard_sync(guard, spec)
    return [fn(r.get("text", ""), r.get("category", "misc"), r.get("language", "en")) for r in rows]



