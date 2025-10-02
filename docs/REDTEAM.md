# Red-Team Swarm

This project includes an adaptive red-team swarm designed to stress-test the candidate guard with progressively obfuscated or semantically altered prompts.

## Running the swarm

```bash
export MPLBACKEND=Agg MPLCONFIGDIR=/tmp/mpl
python -m src.redteam.swarm \
  --max-iters 200 \
  --budget '{"violence/en": 50, "self_harm/en": 50, "malware/en": 50, "violence/fa": 50}'
```

The command writes discoveries to `report/redteam_cases.jsonl`. Each line contains metadata describing the originating seed, agent, applied operators, and guard response.

For convenience the Makefile provides:

```bash
make redteam-swarm
```

which runs the swarm, rebuilds the HTML report, and keeps the CI gate guardrails intact.

## Budgets and coverage

Budgets are specified per `"category/language"` slice. The search loop automatically spreads wins across the available agent types (synonym rewriter, obfuscator, paraphraser, topic-twister, and code-switcher) so that one obfuscation style cannot dominate a slice. Update the JSON budget payload to emphasise particular risk areas.

## Outputs and deduplication

- `report/redteam_cases.jsonl`: raw findings, one JSON record per failure. The deduper keeps the near-duplicate rate below ~10% by combining MinHash/SimHash screening with a cosine similarity fallback.
- `report/index.html`: now includes a **Red-Team Findings** section summarising the most common agents/operations and example prompts.

To analyse the raw cases programmatically:

```python
import json
from pathlib import Path

cases = [json.loads(line) for line in Path("report/redteam_cases.jsonl").open()]
```

## CI considerations

- `make validate` still enforces the guard’s benign FPR (no changes expected). Run it after updating thresholds or adding significant numbers of cases.
- The GitHub `validate` workflow uploads the report (including the red-team section) as a build artifact, while `deploy-pages` republishes GitHub Pages for the latest `report/` contents.

If the dedupe warning indicates a high duplicate rate (>10%), consider raising the `--dedupe-threshold` or expanding the synonym dictionary before committing new results.
