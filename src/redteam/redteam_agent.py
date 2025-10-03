"""Automated red-team agent combining heuristic search and bandit selection."""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence

from src.guards.candidate import _normalize_aggressive, predict as candidate_predict
from src.redteam.agents import AGENTS, AgentInput, BaseAgent
from src.redteam.dedupe import TextDeduper
from src.redteam.search import SeedRow, load_seed_rows
from src.redteam.store import CaseStore, StoredCase
from src.utils.io_utils import load_config


@dataclass
class AgentStats:
    attempts: int = 0
    wins: float = 0.0


@dataclass
class SliceStats:
    attempts: int = 0
    wins: float = 0.0


class RedTeamAgent:
    """Adaptive adversarial generator that searches for guard blind-spots."""

    def __init__(
        self,
        *,
        guard_fn=candidate_predict,
        store_path: Path | str = Path("report/redteam_cases.jsonl"),
        dedupe_threshold: float = 0.9,
        rng: random.Random | None = None,
        agents: Sequence[BaseAgent] | None = None,
        seed_rows: Sequence[SeedRow] | None = None,
    ) -> None:
        self.guard_fn = guard_fn
        self.store = CaseStore(Path(store_path))
        existing = self.store.load_texts()
        self.deduper = TextDeduper(threshold=dedupe_threshold, existing_texts=existing)
        self.rng = rng or random.Random()
        self.agents: List[BaseAgent] = list(agents) if agents else [agent for agent in AGENTS]
        self.agent_stats: Dict[str, AgentStats] = {agent.name: AgentStats() for agent in self.agents}
        provided_seeds = list(seed_rows) if seed_rows is not None else None
        self.seed_rows: List[SeedRow] = provided_seeds or load_seed_rows()
        if not self.seed_rows:
            raise ValueError("RedTeamAgent requires at least one harmful seed prompt")

        self.slice_pool: Dict[str, List[SeedRow]] = {}
        self.slice_stats: Dict[str, SliceStats] = {}
        for seed in self.seed_rows:
            key = self._slice_key(seed.category, seed.language)
            self.slice_pool.setdefault(key, []).append(seed)
            self.slice_stats.setdefault(key, SliceStats())

        self.slice_risk = self._load_risk_weights()
        self.ucb_c = 1.2  # exploration weight

    # Public API --------------------------------------------------

    def run(
        self,
        *,
        max_iters: int = 500,
        min_margin: float = 0.05,
        log_path: Optional[Path] = None,
    ) -> Dict[str, float]:
        """Execute heuristic search and return summary stats."""

        if log_path is not None and log_path != self.store.path:
            self.store = CaseStore(log_path)

        stats = {
            "attempts": 0,
            "successes": 0,
            "duplicates": 0,
            "elapsed": 0.0,
        }

        start = time.time()
        for iteration in range(1, max_iters + 1):
            slice_key = self._select_slice()
            if not slice_key:
                break
            seed = self.rng.choice(self.slice_pool[slice_key])
            agent = self._select_agent()
            if not agent:
                break

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
                response = self._evaluate(out.text, seed.category, seed.language)
                if response is None:
                    continue
                stats["attempts"] += 1
                self.agent_stats[agent.name].attempts += 1
                self.slice_stats[slice_key].attempts += 1

                score = float(response.get("score", 0.0))
                threshold = float(response.get("threshold", 0.0))
                prediction = (response.get("prediction") or "").lower()
                margin = threshold - score
                risk_weight = self.slice_risk.get(slice_key, 1.0)
                reward = max(0.0, margin) * risk_weight

                if prediction == "flag" or score >= threshold or margin < min_margin:
                    continue

                if self.deduper.is_duplicate(out.text):
                    stats["duplicates"] += 1
                    continue

                normalized = _normalize_aggressive(out.text)
                metadata = {
                    "slice_key": slice_key,
                    "label": seed.label,
                    "reward": round(reward, 3),
                    "margin": round(margin, 3),
                }

                self.store.append(
                    StoredCase(
                        text=out.text,
                        normalized_text=normalized,
                        category=seed.category,
                        language=seed.language,
                        score=score,
                        threshold=threshold,
                        agent=agent.name,
                        operations=getattr(out, "operations", []) if hasattr(out, "operations") else [],
                        seed_row_id=seed.row_id,
                        iteration=iteration,
                        metadata=metadata,
                    )
                )

                stats["successes"] += 1
                self.agent_stats[agent.name].wins += reward
                self.slice_stats[slice_key].wins += reward
                break

        stats["elapsed"] = time.time() - start
        stats["agent_stats"] = {
            name: {
                "attempts": data.attempts,
                "wins": round(data.wins, 3),
            }
            for name, data in self.agent_stats.items()
        }
        stats["slice_stats"] = {
            key: {
                "attempts": data.attempts,
                "wins": round(data.wins, 3),
            }
            for key, data in self.slice_stats.items()
        }
        stats["duplicate_rate"] = self.deduper.duplicate_rate()
        return stats

    # Internal helpers -------------------------------------------

    def _evaluate(self, text: str, category: str, language: str) -> Optional[Mapping[str, object]]:
        try:
            return self.guard_fn(text, category=category, language=language)
        except Exception:
            return None

    def _select_agent(self) -> Optional[BaseAgent]:
        total_attempts = sum(stat.attempts for stat in self.agent_stats.values()) + 1
        best_agent: Optional[BaseAgent] = None
        best_score = float("-inf")
        for agent in self.agents:
            stats = self.agent_stats[agent.name]
            attempts = stats.attempts
            wins = stats.wins
            if attempts == 0:
                score = float("inf")
            else:
                exploitation = wins / attempts
                exploration = math.sqrt(math.log(total_attempts) / attempts)
                score = exploitation + self.ucb_c * exploration
            if score > best_score:
                best_score = score
                best_agent = agent
        return best_agent

    def _select_slice(self) -> Optional[str]:
        available = [key for key, seeds in self.slice_pool.items() if seeds]
        if not available:
            return None
        total_attempts = sum(stat.attempts for stat in self.slice_stats.values()) + 1
        best_key: Optional[str] = None
        best_score = float("-inf")
        for key in available:
            stats = self.slice_stats[key]
            attempts = stats.attempts
            wins = stats.wins
            risk = self.slice_risk.get(key, 1.0)
            if attempts == 0:
                score = float("inf")
            else:
                exploitation = wins / attempts
                exploration = math.sqrt(math.log(total_attempts) / attempts)
                score = risk * (exploitation + self.ucb_c * exploration)
            if score > best_score:
                best_score = score
                best_key = key
        return best_key

    def _slice_key(self, category: str, language: str) -> str:
        category = (category or "misc").strip() or "misc"
        language = (language or "en").strip() or "en"
        return f"{category}/{language}"

    def _load_risk_weights(self) -> Dict[str, float]:
        risk_weights: Dict[str, float] = {}
        try:
            cfg = load_config() or {}
            weights = cfg.get("risk_weights", {}) if isinstance(cfg, dict) else {}
        except Exception:
            weights = {}
        for key in self.slice_pool:
            category = key.split("/")[0]
            risk_weights[key] = float(weights.get(category, 1.0))
        return risk_weights


__all__ = ["RedTeamAgent"]
