"""Systematic obfuscation and multimodal stress tests for guard slices."""

from __future__ import annotations

import argparse
import csv
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Sequence

from guards.candidate import predict as candidate_predict
from policy.compiler import load_compiled_policy
from obfuscation.operators import (
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
SUPPORTED_MODES = {"text", "image", "audio"}
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


@dataclass
class MediaSample:
    path: Path
    label: str
    category: str


def _collect_seed_texts(policy_slices: Sequence[str], max_per_slice: int = 20) -> Dict[str, List[SliceCase]]:
    _ = load_compiled_policy()  # Load to ensure policy is initialized
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


def _load_media_samples(dataset_path: Path) -> List[MediaSample]:
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")
    samples: List[MediaSample] = []
    with dataset_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            path_value = row.get("path") or row.get("file")
            if not path_value:
                continue
            label = (row.get("label") or "").strip().lower()
            category = (row.get("category") or "media").strip() or "media"
            samples.append(MediaSample(path=Path(path_value), label=label, category=category))
    if not samples:
        raise ValueError(f"Dataset {dataset_path} did not contain any valid rows")
    return samples


def _media_confusion(samples: Sequence[MediaSample], detector: Callable[[Path], bool]) -> Dict[str, float]:
    counts = {"tp": 0, "fp": 0, "tn": 0, "fn": 0}
    for sample in samples:
        gt_pos = sample.label not in {"benign", "safe", "0", "false"}
        pred_pos = detector(sample.path)
        if gt_pos and pred_pos:
            counts["tp"] += 1
        elif (not gt_pos) and pred_pos:
            counts["fp"] += 1
        elif (not gt_pos) and (not pred_pos):
            counts["tn"] += 1
        elif gt_pos and (not pred_pos):
            counts["fn"] += 1
    tp, fp, tn, fn = counts["tp"], counts["fp"], counts["tn"], counts["fn"]
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    fnr = fn / (tp + fn) if (tp + fn) else 0.0
    fpr = fp / (fp + tn) if (fp + tn) else 0.0
    return {
        **counts,
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "fnr": round(fnr, 3),
        "fpr": round(fpr, 3),
        "total": len(samples),
    }


def _nsfw_image_detector(path: Path) -> bool:
    name = path.name.lower()
    triggers = ("nsfw", "nude", "explicit", "lewd")
    return any(token in name for token in triggers)


def _audio_profanity_detector(path: Path) -> bool:
    name = path.name.lower()
    triggers = ("explicit", "profanity", "nsfw", "curse", "swear")
    return any(token in name for token in triggers)


def run_media_lab(dataset_path: Path, out_path: Path, mode: str) -> Dict[str, object]:
    samples = _load_media_samples(dataset_path)
    if mode == "image":
        detector = _nsfw_image_detector
    elif mode == "audio":
        detector = _audio_profanity_detector
    else:
        raise ValueError(f"Unsupported media mode: {mode}")

    by_category: Dict[str, List[MediaSample]] = {}
    for sample in samples:
        by_category.setdefault(sample.category, []).append(sample)

    results: Dict[str, object] = {}
    for category, rows in by_category.items():
        results[category] = _media_confusion(rows, detector)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Obfuscation stress lab")
    parser.add_argument("--slices", type=str, default=",".join(DEFAULT_SLICES))
    parser.add_argument("--out", type=str, default="report/obfuscation.json")
    parser.add_argument("--max-per-slice", type=int, default=20)
    parser.add_argument("--mode", type=str, default="text", choices=sorted(SUPPORTED_MODES))
    parser.add_argument("--dataset", type=str, help="Dataset CSV for image/audio evaluation")
    args = parser.parse_args(argv)

    mode = args.mode.lower()

    if mode == "text":
        slices = [s.strip() for s in args.slices.split(",") if s.strip()]
        if not slices:
            print("No slices specified")
            return 1
        results = run_lab(slices, Path(args.out), max_per_slice=args.max_per_slice)
    else:
        if not args.dataset:
            print("--dataset is required for media modes")
            return 1
        results = run_media_lab(Path(args.dataset), Path(args.out), mode=mode)
    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
