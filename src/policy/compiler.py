"""Compile policy.yaml into runtime structures."""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import yaml

from .actions import Action, ActionType, DEFAULT_ACTION
from .schema import validate_policy, PolicyValidationError

POLICY_PATH = Path("policy/policy.yaml")


@dataclass(frozen=True)
class CompiledRule:
    id: str
    weight: float
    action: Action
    regex: Tuple[re.Pattern, ...]
    substrings: Tuple[str, ...]


@dataclass(frozen=True)
class CompiledSlice:
    category: str
    language: str
    threshold: float
    rules: Tuple[CompiledRule, ...]


@dataclass(frozen=True)
class CompiledPolicy:
    slices: Dict[Tuple[str, str], CompiledSlice]
    safe_context_patterns: Tuple[re.Pattern, ...]
    safe_context_penalty: float


def _compile_action(name: str | None) -> Action:
    if not name:
        return DEFAULT_ACTION
    name = name.lower()
    try:
        action_type = ActionType(name)
    except ValueError as exc:
        raise PolicyValidationError(f"unknown action '{name}'") from exc
    return Action(action_type)


def _compile_rule(rule: Dict[str, object]) -> CompiledRule:
    regex_patterns = []
    for pattern in rule.get("match", {}).get("regex", []) or []:
        regex_patterns.append(re.compile(pattern, re.IGNORECASE))
    substrings = tuple(str(s).lower() for s in (rule.get("match", {}).get("substrings") or []))
    return CompiledRule(
        id=str(rule["id"]),
        weight=float(rule["weight"]),
        action=_compile_action(rule.get("action")),
        regex=tuple(regex_patterns),
        substrings=substrings,
    )


def _compile_slice(entry: Dict[str, object]) -> CompiledSlice:
    rules = tuple(_compile_rule(rule) for rule in entry.get("rules", []))
    return CompiledSlice(
        category=str(entry["category"] or "misc"),
        language=str(entry["language"] or "en"),
        threshold=float(entry.get("threshold", 1.0)),
        rules=rules,
    )


def compile_policy(data: Dict[str, object]) -> CompiledPolicy:
    validate_policy(data)

    safe_patterns = []
    for entry in data.get("safe_contexts", []) or []:
        for pattern in entry.get("patterns", []):
            safe_patterns.append(re.compile(pattern, re.IGNORECASE))

    slices: Dict[Tuple[str, str], CompiledSlice] = {}
    for entry in data.get("slices"):
        compiled = _compile_slice(entry)
        key = (compiled.category, compiled.language)
        slices[key] = compiled

    penalty = float(data.get("penalties", {}).get("safe_context", 0.0))

    return CompiledPolicy(
        slices=slices,
        safe_context_patterns=tuple(safe_patterns),
        safe_context_penalty=penalty,
    )


@lru_cache(maxsize=1)
def load_compiled_policy(path: Path = POLICY_PATH) -> CompiledPolicy:
    if not path.exists():
        raise FileNotFoundError(f"Policy file not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return compile_policy(data)


__all__ = ["CompiledPolicy", "CompiledRule", "CompiledSlice", "compile_policy", "load_compiled_policy", "POLICY_PATH"]
