from __future__ import annotations

import threading
from functools import lru_cache
from pathlib import Path
from typing import Optional

from .compiler import load_compiled_policy, CompiledPolicy


LOAD_COUNTER: int = 0
_COUNTER_LOCK = threading.Lock()


def _policy_mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except FileNotFoundError:
        return 0.0


@lru_cache(maxsize=8)
def _load_by_mtime(path_str: str, mtime: float) -> CompiledPolicy:
    global LOAD_COUNTER
    with _COUNTER_LOCK:
        LOAD_COUNTER += 1
    return load_compiled_policy(Path(path_str))


def get_compiled_policy(path: Optional[Path] = None) -> CompiledPolicy:
    # Resolve POLICY_PATH dynamically to honor test monkeypatches
    if path is None:
        from . import compiler as comp  # local import to pick up patched POLICY_PATH
        p = comp.POLICY_PATH.resolve()
    else:
        p = path.resolve()
    mtime = _policy_mtime(p)
    return _load_by_mtime(str(p), mtime)


def load_count() -> int:
    with _COUNTER_LOCK:
        return LOAD_COUNTER


def clear_cache() -> None:
    global LOAD_COUNTER
    with _COUNTER_LOCK:
        LOAD_COUNTER = 0
    _load_by_mtime.cache_clear()  # type: ignore[attr-defined]


def reload_policy() -> None:
    clear_cache()


__all__ = ["get_compiled_policy", "load_count", "clear_cache"]

