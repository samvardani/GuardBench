"""Generate local PR bundle for AutoPatch results."""

from __future__ import annotations

import difflib
import textwrap
from pathlib import Path
from typing import Dict, Iterable, List

from src.autopatch import candidates as candidate_utils


AUTOPATCH_DIR = Path(".autopatch")
DIFF_DIR = AUTOPATCH_DIR / "diff"


def _write_patch(path: Path, before: str, after: str) -> None:
    diff = "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=str(path.name + " (base)"),
            tofile=str(path.name + " (patched)"),
        )
    )
    if not diff.strip():
        return
    target = DIFF_DIR / f"{path.name}.patch"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(diff, encoding="utf-8")


def generate_pr_bundle(
    threshold_updates: Dict[str, float],
    evaluation: Dict[str, object],
    regex_suggestions: Iterable[candidate_utils.Suggestion],
    prompt_suggestions: Iterable[candidate_utils.Suggestion],
) -> Path:
    AUTOPATCH_DIR.mkdir(exist_ok=True)
    DIFF_DIR.mkdir(exist_ok=True)

    config_before = Path("config.yaml").read_text(encoding="utf-8")
    config_after = candidate_utils.apply_threshold_patch_to_config(config_before, threshold_updates)
    _write_patch(Path("config.yaml"), config_before, config_after)

    tuned_path = Path("tuned_thresholds.yaml")
    if tuned_path.exists():
        tuned_before = tuned_path.read_text(encoding="utf-8")
        tuned_after = candidate_utils.apply_threshold_patch_to_tuned(tuned_before, threshold_updates)
        _write_patch(tuned_path, tuned_before, tuned_after)

    pr_body = AUTOPATCH_DIR / "PR_BODY.md"
    per_slice = evaluation.get("per_slice", {})
    metrics_lines: List[str] = ["| Slice | Recall Δ | FPR Δ |", "| --- | --- | --- |"]
    for slice_key, data in per_slice.items():
        delta = data.get("delta", {})
        metrics_lines.append(
            f"| {slice_key} | {delta.get('recall', 0.0):+.3f} | {delta.get('fpr', 0.0):+.3f} |"
        )

    fixed_samples = evaluation.get("fixed_samples", [])[:3]
    fixed_lines = ["- " + textwrap.shorten(sample, width=120) for sample in fixed_samples] or ["- (no new fixes)"]

    regex_lines = [
        f"- **{s.payload['slice']}**: `{s.payload['pattern']}` (exclude {', '.join(s.payload['safe_context'])})"
        for s in regex_suggestions
    ] or ["- (none)"]

    prompt_lines = [
        f"- **{s.payload['slice']}**: {s.payload['block_text']}"
        for s in prompt_suggestions
    ] or ["- (none)"]

    pr_body.write_text(
        "\n".join(
            [
                "## Summary",
                "- Auto-generated threshold update to capture swarm-discovered failures.",
                "",
                "## Metrics",
                *metrics_lines,
                "",
                "## Top Fixed Samples",
                *fixed_lines,
                "",
                "## Regex Candidates",
                *regex_lines,
                "",
                "## Prompt-Guard Suggestions",
                *prompt_lines,
            ]
        ),
        encoding="utf-8",
    )

    return pr_body


__all__ = ["generate_pr_bundle", "AUTOPATCH_DIR"]
