# Language Parity Checks

The multilingual parity tool ensures guard performance remains consistent across
languages/scripts for the same abuse category.

## Running parity evaluation

```bash
python -m src.multilingual.parity --category violence --langs en,fa --out report/parity.json
```

The command uses curated seed prompts (`src/multilingual/parity.py`) to evaluate
the candidate guard across the requested languages. The output JSON includes
per-language recall, total samples, and aggregate metrics:

- `max_delta`: maximum recall difference across languages (target ≤ 0.05)
- `variance`: variance of recall values

## Report integration

`make validate` loads `report/parity.json` (if present) and renders a **Language
Parity** section in `report/index.html`, summarising recall per language and the
observed delta versus the 5% target.

Use this report to identify languages that require additional tuning or seed
coverage. Pair the checks with the obfuscation lab and runtime telemetry to get
full visibility into guard behavior.
