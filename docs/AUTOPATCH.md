# AutoPatch Workflow

AutoPatch scans the red-team swarm findings, proposes guard adjustments, evaluates them, and prepares a local PR bundle you can review before pushing upstream.

## Running AutoPatch

```bash
# Ensure redteam_cases.jsonl exists (run `make redteam-swarm` first)
make autopatch  # invokes python -m src.autopatch.run
```

You can invoke the CLI directly for fine-grained control:

```bash
python -m src.autopatch.run \
  --target "self_harm/en,malware/en" \
  --max-patches 3
```

This produces the following artifacts:

- `.autopatch/diff/*.patch` – unified diffs for `config.yaml` (and `tuned_thresholds.yaml` if present).
- `.autopatch/PR_BODY.md` – ready-to-paste PR description with metrics, fixed samples, and follow-up suggestions.
- `report/ab_result.json` – baseline vs patched metrics (precision/recall/FPR) including per-slice deltas.

## Acceptance Guardrails

AutoPatch only accepts threshold patches that:

1. Improve recall on at least one target slice, and
2. Increase slice-level FPR by **no more than 0.005**.

If no candidate passes, the CLI exits with a non-zero status and retains the evaluation outputs for manual inspection.

## Patch Types

- **Threshold tweaks**: lower `slice_thresholds[category][language]` just enough to capture observed failures.
- **Regex suggestions**: keyword-driven expressions with safe-context exclusions; review before integrating into `src/guards/candidate.py`.
- **Prompt-guard blocks**: textual snippets describing runtime SDK rules you might adopt later.

Currently only threshold patches are auto-evaluated; regex and prompt suggestions are surfaced in the PR template for manual review.

## Safety Checklist

- Always review `.autopatch/PR_BODY.md` and the generated diffs before committing.
- Re-run `make validate` after applying a chosen patch to confirm the CI gate remains green.
- Monitor the duplicate rate in `report/ab_result.json` and the red-team section of `report/index.html` to ensure improvements persist over time.
