#!/usr/bin/env bash
set -euo pipefail

echo "[codex] Python: $(python --version)"
echo "[codex] Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "[codex] Quick smoke: list files and python -m ..."
ls -la
python -m src.report.build_report || true

echo "[codex] Setup done."
