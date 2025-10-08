from __future__ import annotations

import json
import logging
from typing import Any, Dict


def log_json(logger: logging.Logger, level: int, **kwargs: Any) -> None:
    try:
        logger.log(level, json.dumps(kwargs, separators=(",", ":")))
    except Exception:
        logger.log(level, str(kwargs))



