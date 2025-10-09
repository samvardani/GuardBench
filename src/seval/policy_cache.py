from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from policy.compiler import load_compiled_policy, POLICY_PATH, CompiledPolicy


@lru_cache(maxsize=1)
def get_compiled_policy(path: str | Path = POLICY_PATH) -> CompiledPolicy:
    return load_compiled_policy(Path(path))



