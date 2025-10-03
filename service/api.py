"""Local service exposing guard scorecard endpoints."""

from __future__ import annotations

import os
import tarfile
import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src.guards.candidate import predict as candidate_predict
from src.guards.baseline import predict as baseline_predict
from src.report.build_report import (
    run_guard,
    confusion,
    slice_metrics,
    pctiles,
    cluster_failures,
    slice_failure_patterns,
    load_redteam_summary,
    load_runtime_telemetry,
    load_parity_summary,
    load_incident_reports,
    OUT_DIR,
    ASSETS,
    histogram,
)
from jinja2 import Environment, FileSystemLoader

app = FastAPI(title="Sentinel Safety Service")

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = ROOT / "templates"
SCORECARD_ROOT = Path("dist/scorecards")


class ScoreRequest(BaseModel):
    text: str
    category: Optional[str] = None
    language: Optional[str] = None


class BatchRow(BaseModel):
    text: str
    category: str
    language: str = "en"
    label: str = Field(default="unsafe")


class BatchRequest(BaseModel):
    rows: List[BatchRow]


@app.post("/score")
def score_endpoint(request: ScoreRequest):
    result = candidate_predict(request.text, category=request.category, language=request.language)
    return {
        "prediction": result.get("prediction"),
        "score": result.get("score"),
        "threshold": result.get("threshold"),
        "latency_ms": result.get("latency_ms"),
    }


def _render_report(rows: List[dict], run_id: str) -> Path:
    report_dir = SCORECARD_ROOT / run_id / "report"
    assets_dir = SCORECARD_ROOT / run_id / "assets"
    report_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)

    base_preds, base_lat = run_guard(rows, baseline_predict)
    cand_preds, cand_lat = run_guard(rows, candidate_predict)

    base_cm = confusion(rows, base_preds, mode="strict")
    cand_cm = confusion(rows, cand_preds, mode="strict")

    metrics = {
        "Baseline": {
            "precision": base_cm["precision"],
            "recall": base_cm["recall"],
            "fnr": base_cm["fnr"],
            "fpr": base_cm["fpr"],
            "recall_lo": base_cm["recall_lo"],
            "recall_hi": base_cm["recall_hi"],
            "fpr_lo": base_cm["fpr_lo"],
            "fpr_hi": base_cm["fpr_hi"],
            "latency": pctiles(base_lat),
        },
        "Candidate": {
            "precision": cand_cm["precision"],
            "recall": cand_cm["recall"],
            "fnr": cand_cm["fnr"],
            "fpr": cand_cm["fpr"],
            "recall_lo": cand_cm["recall_lo"],
            "recall_hi": cand_cm["recall_hi"],
            "fpr_lo": cand_cm["fpr_lo"],
            "fpr_hi": cand_cm["fpr_hi"],
            "latency": pctiles(cand_lat),
        },
    }
    matrices = {"Baseline": base_cm, "Candidate": cand_cm}
    slices = {
        "Baseline": slice_metrics(rows, base_preds, mode="strict"),
        "Candidate": slice_metrics(rows, cand_preds, mode="strict"),
    }

    base_clusters = cluster_failures(rows, base_preds, mode="strict")
    cand_clusters = cluster_failures(rows, cand_preds, mode="strict")
    failure_patterns = slice_failure_patterns(rows, cand_preds, mode="strict")

    runtime_offline = {f"{s['category']}/{s['language']}": s for s in slices["Candidate"]}
    runtime_summary, runtime_chart = load_runtime_telemetry(Path("runtime_telemetry.jsonl"), assets_dir, runtime_offline)
    redteam_summary = load_redteam_summary(Path("report/redteam_cases.jsonl"))
    parity_summary = load_parity_summary(Path("report/parity.json"))
    incident_summary = load_incident_reports(Path("report"))

    histogram(base_lat, assets_dir / "latency_baseline.png", "Baseline latency")
    histogram(cand_lat, assets_dir / "latency_candidate.png", "Candidate latency")

    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    tpl = env.get_template("report.html")
    html = tpl.render(
        run_title="Scorecard",
        run_id=run_id,
        dataset_path="service",
        dataset_sha="service",
        total_samples=len(rows),
        generated_at="n/a",
        policy_version="n/a",
        engines={"baseline": "rules-v1", "candidate": "candidate-v1"},
        metrics=metrics,
        matrices=matrices,
        slices=slices,
        modes={"strict": {"metrics": metrics, "matrices": matrices, "slices": slices}},
        latency_imgs={
            "baseline": os.path.relpath(assets_dir / "latency_baseline.png", report_dir),
            "candidate": os.path.relpath(assets_dir / "latency_candidate.png", report_dir),
        },
        downloads={"fn_csv": "candidate_fn.csv", "fp_csv": "candidate_fp.csv"},
        failures=[
            {"fail_type": "FN", "model": "Candidate", "category": r["category"], "language": r["language"], "text": r["text"]}
            for r, p in zip(rows, cand_preds)
            if r["label"].strip().lower() != "benign" and not p
        ],
        clusters={"Baseline": base_clusters, "Candidate": cand_clusters},
        failure_patterns=failure_patterns,
        redteam_summary=redteam_summary,
        runtime_summary=runtime_summary,
        runtime_chart=runtime_chart,
        parity_summary=parity_summary,
        incident_summary=incident_summary,
    )
    out_file = report_dir / "index.html"
    out_file.write_text(html, encoding="utf-8")

    bundle_path = SCORECARD_ROOT / run_id / f"scorecard_{run_id}.tar.gz"
    with tarfile.open(bundle_path, "w:gz") as tar:
        tar.add(report_dir, arcname="report")
        tar.add(assets_dir, arcname="assets")
    return bundle_path


@app.post("/batch")
def batch_endpoint(request: BatchRequest):
    if not request.rows:
        raise HTTPException(status_code=400, detail="rows list cannot be empty")
    rows = [row.dict() for row in request.rows]
    run_id = uuid.uuid4().hex[:8]
    bundle_path = _render_report(rows, run_id)
    return {"bundle": str(bundle_path)}

