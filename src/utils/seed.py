from __future__ import annotations

import os
import random


def seed_all_from_env(env_var: str = "SEVAL_SEED") -> int | None:
    value = os.getenv(env_var)
    if not value:
        return None
    try:
        seed = int(value)
    except ValueError:
        return None
    random.seed(seed)
    try:
        import numpy as _np  # type: ignore
        _np.random.seed(seed)
    except Exception:
        pass
    # Add other libs if needed (torch, tf) guarded by imports
    return seed



