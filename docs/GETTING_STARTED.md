# Getting Started

This guide covers the basics for setting up the local environment, running validation, viewing reports, and understanding the CI expectations for **safety-eval-mini**.

## 1. Create a virtual environment

```bash
/usr/bin/python3 -m venv .venv  # or python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip wheel
pip install -r requirements.txt
```

> Tip: Re-run `source .venv/bin/activate` whenever you start a new shell session.

## 2. Run the validation pipeline

```bash
export MPLBACKEND=Agg MPLCONFIGDIR=/tmp/mpl
mkdir -p /tmp/mpl
make validate
```

`make validate` runs the compare script, rebuilds the HTML report, and executes the CI gate (`python -m src.runner.ci_gate --config gate.json`). If the gate fails, details are written to `report/ci_slices.json` and logged in the console output.

## 3. Serve the HTML report locally

```bash
python -m http.server --directory report 8000
# Visit: http://localhost:8000/index.html
```

The generated report lives in `report/index.html`, with supporting latency charts under `assets/`.

## 4. Continuous Integration

- **validate workflow** (`.github/workflows/validate.yml`): runs on pull requests, executes the validation pipeline, and uploads the report + assets as an artifact.
- **deploy-pages workflow** (`.github/workflows/pages.yml`): runs on pushes to `main` (or manual dispatch) and publishes the packaged `report/` directory to GitHub Pages.

Keep the CI gate green before merging. When updating thresholds or datasets, re-run `make validate` locally and inspect `report/index.html` to confirm the expected behaviour.

