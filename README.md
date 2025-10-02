# Safety Eval Mini

One-screen harness to compare a Baseline vs. Candidate safety guard.

- Reproducible runs (run_id + dataset SHA + git commit)
- HTML report (KPIs, confusion, latency, failures)
- Threshold sweep (precision/recall trade-off)
- SQLite history

## Quick Start
```bash
python -m venv .venv && source .venv/bin/activate
pip install --upgrade pip && pip install pandas numpy scikit-learn jinja2 matplotlib pyyaml
make demo   # compare + report + sweep
```

- Gate: tuned per-slice thresholds in `config.yaml`; stricter overrides in `gate.json`.

## Documentation

- [Getting Started](docs/GETTING_STARTED.md): environment setup, validation flow, serving reports, CI expectations.
- [Red-Team Swarm](docs/REDTEAM.md): adaptive red-team workflow, budgets, and outputs.

## Working with the dataset

- New evaluation rows live in `data/rows.yaml` (YAML list). Keep the minimal
  shape of `text`, `category`, `language`, and `label`; any extra metadata is
  preserved in the report and red-team generator.
- After editing, run the loader smoke test: `pytest tests/test_dataset_schema.py -q`.

## Validation + report

```bash
export MPLBACKEND=Agg MPLCONFIGDIR=/tmp/mpl
make validate  # compare -> report -> ci gate
```

- When the gate fails, inspect `report/index.html`. Serve it locally via:

  ```bash
  make serve-report
  # → Open http://localhost:8000/index.html
  ```
