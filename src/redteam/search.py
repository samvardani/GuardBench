"""Budgeted search loop for the adaptive red-team swarm."""

from __future__ import annotations

import csv
import json
import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Tuple

import yaml

from guards.candidate import _normalize_aggressive, predict as candidate_predict

from .agents import AGENTS, AgentInput, AgentOutput, BaseAgent
from .dedupe import TextDeduper
from .store import CaseStore, StoredCase


@dataclass
class SeedRow:
    row_id: str
    text: str
    category: str
    language: str
    label: str


def load_seed_rows(
    dataset_csv: Path | None = None,
    supplemental_yaml: Path | None = None,
) -> List[SeedRow]:
    """Load candidate seeds from the repository datasets."""

    seeds: List[SeedRow] = []
    dataset_csv = dataset_csv or Path("dataset/sample.csv")
    if dataset_csv.exists():
        with dataset_csv.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                label = (row.get("label") or "").strip().lower()
                if label in {"benign", "0", "safe"}:
                    continue
                seeds.append(
                    SeedRow(
                        row_id=row.get("id") or f"csv:{len(seeds)}",
                        text=row.get("text", ""),
                        category=row.get("category", ""),
                        language=row.get("language", "en"),
                        label=row.get("label", "unsafe"),
                    )
                )

    supplemental_yaml = supplemental_yaml or Path("data/rows.yaml")
    if supplemental_yaml.exists():
        data = yaml.safe_load(supplemental_yaml.read_text(encoding="utf-8")) or []
        for idx, row in enumerate(data):
            label = str(row.get("label", "")).strip().lower()
            if label in {"0", "safe", "benign", "false", "0.0"}:
                continue
            seeds.append(
                SeedRow(
                    row_id=row.get("id") or f"yaml:{idx}",
                    text=row.get("text", ""),
                    category=row.get("category", ""),
                    language=row.get("language", "en"),
                    label=str(row.get("label", 1)),
                )
            )
    return [s for s in seeds if s.text]


class SwarmSearch:
    """Coordinate agent sampling, dedupe, and case persistence."""

    def __init__(
        self,
        agents: Sequence[BaseAgent] = AGENTS,
        rng: random.Random | None = None,
    ) -> None:
        self.agents = list(agents)
        self.rng = rng or random.Random()

    def run(
        self,
        seeds: Sequence[SeedRow],
        store: CaseStore,
        deduper: TextDeduper,
        budgets: Mapping[str, int],
        max_iters: int = 200,
    ) -> Dict[str, float]:
        by_slice: Dict[str, List[SeedRow]] = {}
        for seed in seeds:
            key = self._slice_key(seed.category, seed.language)
            by_slice.setdefault(key, []).append(seed)

        mutable_budget: MutableMapping[str, int] = {k: v for k, v in budgets.items() if v > 0}
        agent_limits: Dict[Tuple[str, str], int] = {}
        agent_counts: Dict[Tuple[str, str], int] = {}
        for slice_key, budget in mutable_budget.items():
            per_agent = max(1, budget // max(1, len(self.agents)))
            for agent in self.agents:
                agent_limits[(slice_key, agent.name)] = per_agent
                agent_counts[(slice_key, agent.name)] = 0

        stats = {
            "attempts": 0,
            "successes": 0,
            "duplicates": 0,
            "elapsed": 0.0,
            "discovered_slices": set(),
        }

        start = time.time()
        iteration = 0
        existing_slice_keys = [k for k in mutable_budget if by_slice.get(k)]

        while iteration < max_iters and existing_slice_keys:
            iteration += 1
            slice_key = self.rng.choice(existing_slice_keys)
            seeds_for_slice = by_slice.get(slice_key)
            if not seeds_for_slice:
                existing_slice_keys = [k for k in mutable_budget if by_slice.get(k) and mutable_budget[k] > 0]
                continue

            seed = self.rng.choice(seeds_for_slice)
            agent = self._pick_agent(slice_key, agent_limits, agent_counts)
            if not agent:
                # All agents exhausted for this slice
                mutable_budget[slice_key] = 0
                existing_slice_keys = [k for k in mutable_budget if by_slice.get(k) and mutable_budget[k] > 0]
                continue

            outputs = agent.generate(
                AgentInput(
                    text=seed.text,
                    category=seed.category,
                    language=seed.language,
                    seed_id=seed.row_id,
                )
            )

            if not outputs:
                continue

            for out in outputs:
                stats["attempts"] += 1
                guard = candidate_predict(out.text, category=seed.category, language=seed.language)
                score = float(guard.get("score", 0.0))
                threshold = float(guard.get("threshold", 0.0))
                prediction = guard.get("prediction")

                if prediction == "flag" or score > threshold:
                    continue

                if deduper.is_duplicate(out.text):
                    stats["duplicates"] += 1
                    continue

                normalized = _normalize_aggressive(out.text)
                store.append(
                    StoredCase(
                        text=out.text,
                        normalized_text=normalized,
                        category=seed.category,
                        language=seed.language,
                        score=score,
                        threshold=threshold,
                        agent=out.agent,
                        operations=out.operations,
                        seed_row_id=seed.row_id,
                        iteration=iteration,
                        metadata={
                            "slice_key": slice_key,
                            "label": seed.label,
                        },
                    )
                )

                stats["successes"] += 1
                stats["discovered_slices"].add(slice_key)
                mutable_budget[slice_key] -= 1
                agent_counts[(slice_key, agent.name)] += 1
                if mutable_budget[slice_key] <= 0:
                    existing_slice_keys = [k for k in mutable_budget if by_slice.get(k) and mutable_budget[k] > 0]
                break

        stats["elapsed"] = time.time() - start
        stats["dedupe_rate"] = deduper.duplicate_rate()
        stats["budget_remaining"] = dict(mutable_budget)
        stats["discovered_slices"] = sorted(stats["discovered_slices"])
        return stats

    # Internal helpers -------------------------------------------------

    def _slice_key(self, category: str, language: str) -> str:
        category = category or "misc"
        language = language or "en"
        return f"{category}/{language}"

    def _pick_agent(
        self,
        slice_key: str,
        limits: Mapping[Tuple[str, str], int],
        counts: Mapping[Tuple[str, str], int],
    ) -> Optional[BaseAgent]:
        viable = [agent for agent in self.agents if counts[(slice_key, agent.name)] < limits[(slice_key, agent.name)]]
        if not viable:
            return None
        return self.rng.choice(viable)


__all__ = ["SwarmSearch", "SeedRow", "load_seed_rows"]
