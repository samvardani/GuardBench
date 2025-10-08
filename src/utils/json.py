from __future__ import annotations

import orjson
from typing import Any


def orjson_dumps(v: Any, *, default: Any = None) -> str:
    # FastAPI expects a str-returning callable
    return orjson.dumps(v, default=default).decode()


def orjson_loads(s: str) -> Any:
    return orjson.loads(s)


__all__ = ["orjson_dumps", "orjson_loads"]

