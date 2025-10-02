"""CLI to orchestrate AutoPatch end-to-end."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.autopatch import ab_eval, candidates, pr_bot


def _parse_targets(raw: str) -> list[str]:
    return [part.strip() for part in raw.split(",") if part.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AutoPatch runner")
    parser.add_argument("--target", required=True, help="Comma separated slice keys, e.g. self_harm/en,malware/en")
    parser.add_argument("--max-patches", type=int, default=3)
    parser.add_argument("--cases", type=str, default=str(candidates.DEFAULT_CASES_PATH))
    args = parser.parse_args(argv)

    target_slices = _parse_targets(args.target)
    if not target_slices:
        print("No target slices provided.", file=sys.stderr)
        return 1

    cases_path = Path(args.cases)
    if not cases_path.exists():
        print(f"Red-team cases not found at {cases_path}. Run `make redteam-swarm` first.", file=sys.stderr)
        return 1

    generated = candidates.generate_candidates(target_slices, max_patches=args.max_patches, cases_path=cases_path)
    threshold_candidates = generated.get("threshold", [])
    if not threshold_candidates:
        print("No threshold candidates generated for the requested slices.", file=sys.stderr)
        return 1

    best_result = None
    best_candidate = None
    cases = generated.get("cases")
    report_result = ab_eval.DEFAULT_RESULT_PATH
    report_result.parent.mkdir(parents=True, exist_ok=True)

    for idx, cand in enumerate(threshold_candidates):
        tmp_result = pr_bot.AUTOPATCH_DIR / f"ab_result_{idx}.json"
        tmp_result.parent.mkdir(parents=True, exist_ok=True)
        result = ab_eval.evaluate_threshold_candidate(
            cand.data,
            target_slices=target_slices,
            result_path=tmp_result,
            cases=cases,
        )
        if not ab_eval.accepts_improvement(result, target_slices):
            tmp_result.unlink(missing_ok=True)
            continue
        if best_result is None or result["delta"]["recall"] > best_result["delta"]["recall"]:
            best_result = result
            best_candidate = cand
            if tmp_result.exists():
                tmp_result.replace(report_result)

    # Ensure final result JSON exists for the winning candidate
    if best_candidate and not report_result.exists():
        report_result.write_text(json.dumps(best_result, indent=2), encoding="utf-8")

    if not best_candidate or not best_result:
        print("No candidate met acceptance criteria (ΔFPR <= 0.005 and recall improvement).", file=sys.stderr)
        return 2

    pr_path = pr_bot.generate_pr_bundle(
        threshold_updates=best_candidate.data,
        evaluation=best_result,
        regex_suggestions=generated.get("regex", []),
        prompt_suggestions=generated.get("prompt", []),
    )

    summary = {
        "candidate": best_candidate.id,
        "threshold_updates": best_candidate.data,
        "per_slice": {
            key: data["delta"] for key, data in best_result.get("per_slice", {}).items()
        },
        "pr_body": str(pr_path),
        "diff_dir": str(pr_bot.DIFF_DIR),
    }

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
