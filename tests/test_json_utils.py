from src.utils.json import orjson_dumps, orjson_loads


def test_orjson_roundtrip_simple():
    payload = {"a": 1, "b": "x", "c": [1, 2, 3]}
    s = orjson_dumps(payload)
    out = orjson_loads(s)
    assert out == payload


def test_orjson_roundtrip_nested():
    payload = {"nested": {"k": [
        {"x": True},
        {"y": None},
    ]}}
    s = orjson_dumps(payload)
    out = orjson_loads(s)
    assert out == payload

