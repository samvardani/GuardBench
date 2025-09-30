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
- Gate: tuned per-slice thresholds in `config.yaml`; stricter overrides in `gate.json`.
