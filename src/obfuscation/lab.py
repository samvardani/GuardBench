"""Systematic obfuscation stress test for guard slices."""

from __future__ import annotations

import argparse
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

from src.guards.candidate import predict as candidate_predict
from src.policy.compiler import load_compiled_policy
from src.obfuscation.operators import (
    leet_speak,
    insert_zero_width,
    swap_homoglyphs,
    add_punctuation_noise,
    mixed_casing,
    add_emoji_noise,
    camel_to_snake,
    mask_numbers,
)

DEFAULT_SLICES = ["violence/en", "self_harm/en", "malware/en"]
OPERATORS = {
    "leet": leet_speak,
    "zero_width": insert_zero_width,
    "homoglyph": swap_homoglyphs,
    "punctuation": add_punctuation_noise,
    "mixed_case": mixed_casing,
    "emoji": add_emoji_noise,
    "camel_to_snake": camel_to_snake,
    "mask_numbers": mask_numbers,
}


@dataclass
class SliceCase:
    text: str
    category: str
    language: str


def _collect_seed_texts(policy_slices: Sequence[str], max_per_slice: int = 20) -> Dict[str, List[SliceCase]]:
    policy = load_compiled_policy()
    buckets: Dict[str, List[SliceCase]] = {}
    dataset_path = Path("dataset/sample.csv")
    if dataset_path.exists():
        import csv

        with dataset_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                slice_key = f"{row.get('category')}/{row.get('language')}"
                if slice_key in policy_slices:
                    buckets.setdefault(slice_key, []).append(
                        SliceCase(text=row["text"], category=row.get("category", ""), language=row.get("language", ""))
                    )

    rows_path = Path("data/rows.yaml")
    if rows_path.exists():
        import yaml

        data = yaml.safe_load(rows_path.read_text(encoding="utf-8")) or []
        for row in data:
            slice_key = f"{row.get('category')}/{row.get('language')}"
            if slice_key in policy_slices:
                buckets.setdefault(slice_key, []).append(
                    SliceCase(text=row.get("text", ""), category=row.get("category", ""), language=row.get("language", ""))
                )

    for key, cases in buckets.items():
        random.Random(42).shuffle(cases)
        buckets[key] = cases[:max_per_slice]
    return buckets


def _apply_operator(name: str, text: str) -> str:
    func = OPERATORS[name]
    return func(text)


def run_lab(policy_slices: Sequence[str], out_path: Path, max_per_slice: int = 20) -> Dict[str, dict]:
    seeds = _collect_seed_texts(policy_slices, max_per_slice=max_per_slice)
    results = {}
    for slice_key, cases in seeds.items():
        category, language = slice_key.split("/")
        slice_stats = {
            "total": len(cases),
            "operators": {},
        }
        for op_name in OPERATORS:
            detected = 0
            for case in cases:
                mutated = _apply_operator(op_name, case.text)
                guard = candidate_predict(mutated, category=category, language=language)
                flagged = guard.get("prediction") == "flag" or guard.get("score", 0.0) > guard.get("threshold", 0.0)
                if flagged:
                    detected += 1
            rate = detected / len(cases) if cases else 0.0
            slice_stats["operators"][op_name] = rate
        slice_stats["hardness"] = {
            "mean": round(1.0 - sum(slice_stats["operators"].values()) / max(1, len(OPERATORS)), 3),
        }
        results[slice_key] = slice_stats

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Obfuscation stress lab")
    parser.add_argument("--slices", type=str, default=",".join(DEFAULT_SLICES))
    parser.add_argument("--out", type=str, default="report/obfuscation.json")
    parser.add_argument("--max-per-slice", type=int, default=20)
    args = parser.parse_args(argv)

    slices = [s.strip() for s in args.slices.split(",") if s.strip()]
    if not slices:
        print("No slices specified")
        return 1

    results = run_lab(slices, Path(args.out), max_per_slice=args.max_per_slice)
    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
