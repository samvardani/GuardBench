"""Minimal validation helpers for policy.yaml."""

from __future__ import annotations

from typing import Any, Dict, Iterable

REQUIRED_TOP_LEVEL = {"version", "slices"}


class PolicyValidationError(ValueError):
    pass


def _require_keys(name: str, data: Dict[str, Any], keys: Iterable[str]) -> None:
    missing = [key for key in keys if key not in data]
    if missing:
        raise PolicyValidationError(f"{name}: missing required keys: {', '.join(missing)}")


def _validate_safe_contexts(contexts: Any) -> None:
    if contexts is None:
        return
    if not isinstance(contexts, list):
        raise PolicyValidationError("safe_contexts must be a list")
    for entry in contexts:
        if not isinstance(entry, dict):
            raise PolicyValidationError("safe_context entries must be objects")
        _require_keys("safe_context", entry, ["id", "type", "patterns"])
        if entry["type"] != "regex":
            raise PolicyValidationError("safe_context type must be 'regex'")
        patterns = entry.get("patterns")
        if not isinstance(patterns, list) or not all(isinstance(p, str) for p in patterns):
            raise PolicyValidationError("safe_context patterns must be list[str]")


def _validate_rules(rules: Any) -> None:
    if not isinstance(rules, list) or not rules:
        raise PolicyValidationError("each slice must define at least one rule")
    for rule in rules:
        if not isinstance(rule, dict):
            raise PolicyValidationError("rule entries must be objects")
        _require_keys("rule", rule, ["id", "weight", "action", "match"])
        if not isinstance(rule["weight"], (int, float)):
            raise PolicyValidationError("rule weight must be numeric")
        if rule["weight"] <= 0:
            raise PolicyValidationError("rule weight must be > 0")
        languages = rule.get("languages")
        if languages is not None:
            if isinstance(languages, str):
                if not languages.strip():
                    raise PolicyValidationError("rule languages entries must be non-empty strings")
            elif not (
                isinstance(languages, list)
                and all(isinstance(lang, str) and lang.strip() for lang in languages)
            ):
                raise PolicyValidationError("rule languages must be a string or list[str]")

        match = rule["match"]
        if not isinstance(match, dict):
            raise PolicyValidationError("rule match must be an object")
        regex = match.get("regex")
        substrings = match.get("substrings")
        if regex is None and substrings is None:
            raise PolicyValidationError("rule match requires regex and/or substrings")
        if regex is not None and (
            not isinstance(regex, list) or not all(isinstance(p, str) for p in regex)
        ):
            raise PolicyValidationError("rule match.regex must be list[str]")
        if substrings is not None and (
            not isinstance(substrings, list) or not all(isinstance(p, str) for p in substrings)
        ):
            raise PolicyValidationError("rule match.substrings must be list[str]")


def _validate_slices(slices: Any) -> None:
    if not isinstance(slices, list) or not slices:
        raise PolicyValidationError("policy requires slices list")
    for slice_ in slices:
        if not isinstance(slice_, dict):
            raise PolicyValidationError("slice entries must be objects")
        _require_keys("slice", slice_, ["category", "language", "threshold", "rules"])
        threshold = slice_["threshold"]
        if not isinstance(threshold, (int, float)):
            raise PolicyValidationError("slice threshold must be numeric")
        if not (0.0 <= float(threshold) <= 5.0):
            raise PolicyValidationError("slice threshold outside expected range [0, 5]")
        _validate_rules(slice_["rules"])


def validate_policy(data: Dict[str, Any]) -> None:
    if not isinstance(data, dict):
        raise PolicyValidationError("policy must be a mapping")
    _require_keys("policy", data, REQUIRED_TOP_LEVEL)
    if not isinstance(data["version"], int):
        raise PolicyValidationError("policy version must be integer")
    _validate_safe_contexts(data.get("safe_contexts"))
    _validate_slices(data["slices"])


__all__ = ["validate_policy", "PolicyValidationError"]
