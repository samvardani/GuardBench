"""Action primitives referenced by the policy DSL."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ActionType(str, Enum):
    BLOCK = "block"
    WARN = "warn"
    ROUTE = "route"
    ESCALATE = "escalate"
    PASS = "pass"


@dataclass(frozen=True)
class Action:
    type: ActionType
    metadata: dict[str, str] | None = None

    def is_blocking(self) -> bool:
        return self.type in {ActionType.BLOCK, ActionType.ESCALATE}


DEFAULT_ACTION = Action(ActionType.BLOCK)

__all__ = ["Action", "ActionType", "DEFAULT_ACTION"]
