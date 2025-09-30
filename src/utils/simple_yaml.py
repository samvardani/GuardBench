"""Minimal YAML parser supporting simple mappings.

This fallback is intentionally small and only supports the subset of YAML
used by the project configuration files. It handles dictionaries with string
keys, nested mappings via indentation, and scalar values consisting of
strings, integers, or floats. The implementation is deterministic and raises
``ValueError`` when the input contains constructs outside of this subset.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

_INDENT_SIZE = 2


def _parse_scalar(token: str) -> Any:
    lowered = token.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if lowered == "null" or lowered == "none":
        return None
    try:
        if token.startswith("0") and token != "0" and not token.startswith("0."):
            # Keep leading-zero strings as-is to avoid octal interpretation.
            raise ValueError
        return int(token)
    except ValueError:
        pass
    try:
        return float(token)
    except ValueError:
        return token


@dataclass
class _Frame:
    indent: int
    mapping: Dict[str, Any]


def safe_load(text: str) -> Dict[str, Any]:
    if not isinstance(text, str):
        text = text.read()
    lines = text.splitlines()
    root: Dict[str, Any] = {}
    stack: List[_Frame] = [_Frame(indent=-_INDENT_SIZE, mapping=root)]

    for raw_line in lines:
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        if "\t" in raw_line:
            raise ValueError("Tabs are not supported in YAML indentation.")
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        if indent % _INDENT_SIZE != 0:
            raise ValueError("Invalid indentation level in YAML input.")
        key_value = raw_line.strip()
        if ":" not in key_value:
            raise ValueError("Expected a mapping entry in YAML input.")
        key, _, value = key_value.partition(":")
        key = key.strip()
        value = value.strip()

        while stack and indent <= stack[-1].indent:
            stack.pop()
        if not stack:
            raise ValueError("Invalid YAML structure: unmatched indentation.")
        current = stack[-1].mapping

        if not value:
            new_mapping: Dict[str, Any] = {}
            current[key] = new_mapping
            stack.append(_Frame(indent=indent, mapping=new_mapping))
        else:
            current[key] = _parse_scalar(value)
    return root


__all__ = ["safe_load"]
