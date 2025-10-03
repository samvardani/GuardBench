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
- [AutoPatch](docs/AUTOPATCH.md): generate candidate patches, run A/B validation, and stage a PR bundle.
- [Policy DSL](docs/POLICY.md): declarative guard rules, validation, and compilation pipeline.
- [Obfuscation Lab](docs/OBFUSCATION.md): stress suite metrics and hardness charts.
- [Multilingual Parity](docs/MULTILINGUAL.md): language recall checks and targets.
- [Incident Runbooks](docs/RUNBOOKS.md): chaos drill guidance and mitigation steps.
- [Evidence Packs](docs/EVIDENCE.md): bundle reports, policy, and telemetry for regulators.
- [Service API](docs/SERVICE.md): local FastAPI endpoints for scoring and batch scorecards.
- [Interactive Dashboard](dashboard/index.html): SPA visualising telemetry, parity, obfuscation, incidents, and red-team clusters.
- [Dataset Upload UI](dashboard/upload.html): upload prompt CSVs, choose guards, run evaluations, and download scorecards.

## Documentation Portal

Render the consolidated site with MkDocs (includes Quick Start, policy, obfuscation, parity, runbooks, evidence, and service guides):

```bash
mkdocs serve
# → http://127.0.0.1:8000/
```

## Containerisation & Deployment

Build the production image (Gunicorn + Uvicorn workers) and run the API, background worker, and static dashboard via Docker Compose:

```bash
docker compose up --build
# API → http://localhost:8000
# Dashboard → http://localhost:3000
```

Each service mounts the `report/` and `dist/` directories so scorecards and artefacts persist on the host. The worker currently emits heartbeats and is the recommended hook for future scheduled jobs (red-team sweeps, telemetry sync, etc.).

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

- When the gate fails, inspect `dashboard/index.html` (after regenerating artifacts). Serve it locally via:

  ```bash
  make serve-report
  # → Open http://localhost:8000/dashboard/index.html
  ```
