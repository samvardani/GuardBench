"""CLI entry-point for the adaptive red-team swarm."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .dedupe import TextDeduper
from .search import SwarmSearch, load_seed_rows
from .store import CaseStore


def _parse_budget(raw: str) -> dict[str, int]:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive
        raise SystemExit(f"Invalid budget JSON: {exc}")
    if not isinstance(parsed, dict):  # pragma: no cover
        raise SystemExit("Budget must be a JSON object mapping slice -> limit")
    budget: dict[str, int] = {}
    for key, value in parsed.items():
        try:
            budget[str(key)] = int(value)
        except (TypeError, ValueError):  # pragma: no cover
            raise SystemExit(f"Budget value for {key} must be an integer")
    return budget


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Adaptive red-team swarm")
    parser.add_argument("--max-iters", type=int, default=200)
    parser.add_argument("--budget", type=str, required=True, help='JSON mapping, e.g. {"violence/en": 50}')
    parser.add_argument("--output", type=str, default="report/redteam_cases.jsonl")
    parser.add_argument("--dedupe-threshold", type=float, default=0.9)
    args = parser.parse_args(argv)

    budget = _parse_budget(args.budget)
    if not budget:
        print("No positive budgets provided; nothing to do.", file=sys.stderr)
        return 0

    store_path = Path(args.output)
    store = CaseStore(store_path)
    existing_texts = store.load_texts()
    deduper = TextDeduper(threshold=args.dedupe_threshold, existing_texts=existing_texts)

    seeds = load_seed_rows()
    if not seeds:
        print("No seed rows found; ensure dataset/sample.csv or data/rows.yaml exists.", file=sys.stderr)
        return 1

    search = SwarmSearch()
    stats = search.run(seeds=seeds, store=store, deduper=deduper, budgets=budget, max_iters=args.max_iters)

    remaining = stats.get("budget_remaining", {})

    print(
        json.dumps(
            {
                "attempts": stats["attempts"],
                "successes": stats["successes"],
                "duplicates": stats["duplicates"],
                "dedupe_rate": round(stats.get("dedupe_rate", 0.0), 3),
                "elapsed": round(stats.get("elapsed", 0.0), 2),
                "budget_remaining": remaining,
            },
            indent=2,
        )
    )
    if stats.get("dedupe_rate", 0.0) > 0.1:
        print("Warning: duplicate rate exceeded 10%; consider adjusting threshold.", file=sys.stderr)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
