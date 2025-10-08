from __future__ import annotations

import orjson


def dumps(obj) -> str:
    return orjson.dumps(obj).decode()


def loads(s: str):
    return orjson.loads(s)



