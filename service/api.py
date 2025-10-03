"""Local service exposing guard scorecard endpoints and upload utilities."""

from __future__ import annotations

import os
import tarfile
import uuid
from pathlib import Path
from typing import List, Optional

import csv
import io
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.guards.candidate import predict as candidate_predict
from src.guards.baseline import predict as baseline_predict
from src.evaluation import evaluate
from src.utils.scrub import scrub_text, scrub_record, privacy_mode_for
from src.report.build_report import (
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
SCORECARD_ROOT.mkdir(parents=True, exist_ok=True)
app.mount("/scorecards", StaticFiles(directory=SCORECARD_ROOT), name="scorecards")

GUARD_REGISTRY = {
    "baseline": {"name": "Baseline Guard", "predict": baseline_predict},
    "candidate": {"name": "Candidate Guard", "predict": candidate_predict},
}


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
    privacy_mode = privacy_mode_for("score")
    result = candidate_predict(request.text, category=request.category, language=request.language)
    input_repr = scrub_text(request.text, mode=privacy_mode)
    return {
        "prediction": result.get("prediction"),
        "score": result.get("score"),
        "threshold": result.get("threshold"),
        "latency_ms": result.get("latency_ms"),
        "privacy_mode": privacy_mode,
        "input": input_repr,
    }


def _resolve_guard(choice: str) -> dict:
    key = choice.strip().lower()
    if key not in GUARD_REGISTRY:
        raise HTTPException(status_code=400, detail=f"Unknown guard '{choice}'")
    return GUARD_REGISTRY[key]


def _render_report(rows: List[dict], run_id: str, guard_config: Optional[dict] = None) -> Path:
    report_dir = SCORECARD_ROOT / run_id / "report"
    assets_dir = SCORECARD_ROOT / run_id / "assets"
    report_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)

    guards = guard_config or {
        "baseline": {"name": "rules-v1", "predict": baseline_predict},
        "candidate": {"name": "candidate-v1", "predict": candidate_predict},
    }
    engine = {"guards": guards}
    evaluation = evaluate(engine, rows, policy={})
    base_view = evaluation["guards"]["baseline"]
    cand_view = evaluation["guards"]["candidate"]

    base_preds = base_view["predictions"]
    cand_preds = cand_view["predictions"]
    base_lat = base_view["latencies"]
    cand_lat = cand_view["latencies"]

    available_modes = sorted({"strict", "lenient"} | set(base_view["modes"].keys()) | set(cand_view["modes"].keys()))
    mode_payloads = {}
    for mode_key in available_modes:
        base_mode = base_view["modes"].get(mode_key, base_view["modes"]["strict"])
        cand_mode = cand_view["modes"].get(mode_key, cand_view["modes"]["strict"])

        mode_payloads[mode_key] = {
            "metrics": {
                "Baseline": {
                    "precision": base_mode["confusion"]["precision"],
                    "recall": base_mode["confusion"]["recall"],
                    "fnr": base_mode["confusion"]["fnr"],
                    "fpr": base_mode["confusion"]["fpr"],
                    "recall_lo": base_mode["confusion"]["recall_lo"],
                    "recall_hi": base_mode["confusion"]["recall_hi"],
                    "fpr_lo": base_mode["confusion"]["fpr_lo"],
                    "fpr_hi": base_mode["confusion"]["fpr_hi"],
                    "latency": base_view["latency"],
                },
                "Candidate": {
                    "precision": cand_mode["confusion"]["precision"],
                    "recall": cand_mode["confusion"]["recall"],
                    "fnr": cand_mode["confusion"]["fnr"],
                    "fpr": cand_mode["confusion"]["fpr"],
                    "recall_lo": cand_mode["confusion"]["recall_lo"],
                    "recall_hi": cand_mode["confusion"]["recall_hi"],
                    "fpr_lo": cand_mode["confusion"]["fpr_lo"],
                    "fpr_hi": cand_mode["confusion"]["fpr_hi"],
                    "latency": cand_view["latency"],
                },
            },
            "matrices": {"Baseline": base_mode["confusion"], "Candidate": cand_mode["confusion"]},
            "slices": {"Baseline": base_mode["slices"], "Candidate": cand_mode["slices"]},
        }

    metrics = mode_payloads["strict"]["metrics"]
    matrices = mode_payloads["strict"]["matrices"]
    slices = mode_payloads["strict"]["slices"]

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
        engines={
            "baseline": guards["baseline"]["name"],
            "candidate": guards["candidate"]["name"],
        },
        metrics=metrics,
        matrices=matrices,
        slices=slices,
        modes=mode_payloads,
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


def _load_rows_from_csv(file_bytes: bytes, default_category: Optional[str], default_language: Optional[str]) -> List[dict]:
    try:
        text = file_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = file_bytes.decode("latin-1")
    reader = csv.DictReader(io.StringIO(text))
    rows: List[dict] = []
    for raw in reader:
        text_value = (raw.get("text") or raw.get("prompt") or "").strip()
        if not text_value:
            continue
        category = (raw.get("category") or default_category or "misc").strip()
        language = (raw.get("language") or default_language or "en").strip()
        label = (raw.get("label") or "unsafe").strip() or "unsafe"
        rows.append(
            {
                "text": text_value,
                "category": category,
                "language": language,
                "label": label,
            }
        )
    if not rows:
        raise HTTPException(status_code=400, detail="CSV must contain at least one row with 'text'")
    return rows


@app.post("/batch")
def batch_endpoint(request: BatchRequest):
    if not request.rows:
        raise HTTPException(status_code=400, detail="rows list cannot be empty")
    rows = [row.dict() for row in request.rows]
    run_id = uuid.uuid4().hex[:8]
    bundle_path = _render_report(rows, run_id)
    return {"bundle": str(bundle_path)}


@app.get("/guards")
def list_guards():
    return {key: value["name"] for key, value in GUARD_REGISTRY.items()}


@app.post("/upload-evaluate")
async def upload_evaluate(
    file: UploadFile = File(...),
    baseline_guard: str = Form("baseline"),
    candidate_guard: str = Form("candidate"),
    default_category: Optional[str] = Form(None),
    default_language: Optional[str] = Form(None),
):
    contents = await file.read()
    rows = _load_rows_from_csv(contents, default_category, default_language)

    baseline_spec = _resolve_guard(baseline_guard)
    candidate_spec = _resolve_guard(candidate_guard)

    guard_config = {
        "baseline": {"name": baseline_spec["name"], "predict": baseline_spec["predict"]},
        "candidate": {"name": candidate_spec["name"], "predict": candidate_spec["predict"]},
    }

    run_id = uuid.uuid4().hex[:8]
    bundle_path = _render_report(rows, run_id, guard_config=guard_config)
    bundle_url = f"/scorecards/{run_id}/scorecard_{run_id}.tar.gz"

    engine = {"guards": guard_config}
    evaluation = evaluate(engine, rows, policy={})
    candidate_metrics = evaluation["guards"]["candidate"]["modes"]["strict"]["confusion"]

    privacy_mode = privacy_mode_for("upload_evaluate")
    sample_input = scrub_text(rows[0]["text"], mode=privacy_mode)

    return {
        "run_id": run_id,
        "bundle_url": bundle_url,
        "candidate_metrics": candidate_metrics,
        "total_rows": len(rows),
        "privacy_mode": privacy_mode,
        "sample_input": sample_input,
    }
