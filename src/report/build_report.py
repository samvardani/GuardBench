import os, csv, json, pathlib, datetime
from pathlib import Path
from collections import defaultdict
from typing import List
from jinja2 import Environment, FileSystemLoader

from src.guards.baseline import predict as predict_baseline
from src.guards.candidate import predict as predict_candidate
from src.report.cluster_utils import cluster_failures, slice_failure_patterns
from src.utils.io_utils import load_config, resolve_dataset_path, sha256_file, git_commit, new_run_id
from src.utils.run_log import append_run_record
from src.utils.notify import NotificationManager
from src.policy.compiler import load_compiled_policy, POLICY_PATH
from src.evaluation import evaluate

REQUIRED_KEYS = ("text",)


def get_text(row):
    for key in ("text", "prompt", "question", "input", "content", "message", "utterance"):
        value = None
        if hasattr(row, key):
            value = getattr(row, key)
        elif isinstance(row, dict):
            value = row.get(key)
        if value:
            return str(value)
    return ""


def _row_text(row):
    """Return the best-effort textual content for a dataset row."""
    return get_text(row)


def _row_field(row, key):
    if isinstance(row, dict):
        return row.get(key)
    if hasattr(row, key):
        return getattr(row, key)
    return None


def _is_valid_row(row):
    return bool(_row_text(row))


ROOT = pathlib.Path(__file__).resolve().parents[2]
TPL_DIR = ROOT / "templates"
OUT_DIR = ROOT / "report"
ASSETS = ROOT / "assets"
OUT_DIR.mkdir(exist_ok=True); ASSETS.mkdir(exist_ok=True)
def load_rows(dataset_path: Path):
    import yaml, pathlib, sys

    path = pathlib.Path(dataset_path)
    suffix = path.suffix.lower()

    if suffix in {".yaml", ".yml"}:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    else:
        with path.open(newline="", encoding="utf-8") as handle:
            data = list(csv.DictReader(handle))
    rows, dropped = [], 0

    for idx, raw in enumerate(data):
        if _is_valid_row(raw):
            normalized = dict(raw) if isinstance(raw, dict) else {}
            normalized["text"] = _row_text(raw)
            normalized["category"] = normalized.get("category") or _row_field(raw, "category")
            normalized["language"] = normalized.get("language") or _row_field(raw, "language")
            normalized["label"] = normalized.get("label", _row_field(raw, "label") or 0)
            normalized["id"] = normalized.get("id") or _row_field(raw, "id")
            rows.append(normalized)
        else:
            dropped += 1

    if dropped:
        print(f"[load_rows] skipped {dropped} malformed row(s) lacking text-like content.", file=sys.stderr)

    return rows

def is_pos_label(lbl: str, mode: str) -> bool:
    l = (lbl or "").strip().lower()
    if mode == "lenient":
        return l == "unsafe"
    return l != "benign"

def histogram(values, out_png, title):
    import matplotlib.pyplot as plt
    v = values if values else [0]
    bins = min(20, max(5, len(set(v)) or 5))
    plt.figure()
    plt.hist(v, bins=bins)
    plt.title(title); plt.xlabel("Latency (ms)"); plt.ylabel("Count")
    plt.tight_layout(); plt.savefig(out_png); plt.close()

def load_redteam_summary(path: Path, max_clusters: int = 6, max_examples: int = 3):
    if not path.exists():
        return []
    clusters = defaultdict(list)
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(payload, dict):
                continue
            slice_key = f"{payload.get('category', '?')}/{payload.get('language', '?')}"
            agent = payload.get("agent", "unknown")
            clusters[(slice_key, agent)].append(payload)

    summary = []
    for (slice_key, agent), items in clusters.items():
        operations = sorted({op for item in items for op in item.get("operations", [])})
        examples = [item.get("text", "") for item in items[:max_examples]]
        summary.append(
            {
                "slice": slice_key,
                "agent": agent,
                "count": len(items),
                "operations": operations,
                "examples": examples,
            }
        )
    summary.sort(key=lambda x: -x["count"])
    return summary[:max_clusters]


def load_runtime_telemetry(path: Path, assets_root: Path, offline_slices: dict):
    if not path.exists():
        return [], None
    telemetry = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                telemetry.append(payload)
    if not telemetry:
        return [], None

    by_slice = defaultdict(list)
    for entry in telemetry:
        slice_key = f"{entry.get('category_guess')}/{entry.get('language_guess')}"
        diff = float(entry.get("score", 0.0)) - float(entry.get("threshold", 0.0))
        by_slice[slice_key].append(diff)

    summary = []
    for slice_key, diffs in by_slice.items():
        avg_margin = sum(diffs) / len(diffs)
        offline = (offline_slices.get(slice_key) or {}).get("recall", 0.0)
        summary.append({
            "slice": slice_key,
            "count": len(diffs),
            "avg_margin": round(avg_margin, 3),
            "offline_recall": offline,
        })
    summary.sort(key=lambda x: -x["count"])

    chart_path = assets_root / "runtime_drift.png"
    relative_chart = None
    try:
        import matplotlib.pyplot as plt

        top = summary[:5]
        if top:
            labels = [item["slice"] for item in top]
            margins = [item["avg_margin"] for item in top]
            recalls = [item["offline_recall"] for item in top]

            plt.figure(figsize=(6, 3.5))
            x = range(len(top))
            plt.bar(x, margins, label="Avg(score - threshold)")
            plt.plot(x, recalls, marker="o", color="orange", label="Offline recall")
            plt.xticks(x, labels, rotation=30, ha="right")
            plt.ylabel("Margin / Recall")
            plt.title("Runtime telemetry vs offline guard")
            plt.legend()
            plt.tight_layout()
            chart_path.parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(chart_path)
            plt.close()
            relative_chart = os.path.relpath(chart_path, OUT_DIR)
    except Exception:
        relative_chart = None

    return summary, relative_chart


def load_parity_summary(path: Path):
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    languages = data.get("languages", {})
    rows = []
    for lang, stats in languages.items():
        rows.append({
            "language": lang,
            "total": stats.get("total", 0),
            "flagged": stats.get("flagged", 0),
            "recall": stats.get("recall", 0.0),
        })
    rows.sort(key=lambda r: r["language"])
    return {
        "category": data.get("category"),
        "rows": rows,
        "max_delta": data.get("max_delta", 0.0),
        "variance": data.get("variance", 0.0),
        "target_delta": data.get("target_delta", 0.05),
    }


def load_incident_reports(directory: Path) -> List[dict]:
    incidents = []
    if not directory.exists():
        return incidents
    for path in directory.glob("incident_*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        metrics = data.get("metrics", {})
        incidents.append(
            {
                "scenario": data.get("scenario", path.stem.replace("incident_", "")),
                "duration_s": data.get("duration_s"),
                "rate_rps": data.get("rate_rps"),
                "detection_time_s": metrics.get("detection_time_s"),
                "mitigation_time_s": metrics.get("mitigation_time_s"),
                "residual_risk": metrics.get("residual_risk"),
            }
        )
    incidents.sort(key=lambda x: x["scenario"])
    return incidents


def main():
    cfg = load_config()
    notifier = NotificationManager(cfg.get("notifications"))
    dataset_path = resolve_dataset_path(cfg)
    rows = load_rows(dataset_path)

    run_id = new_run_id()
    created_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    ds_sha = sha256_file(dataset_path)

    engine = {
        "guards": {
            "baseline": {
                "name": cfg.get("engines", {}).get("baseline", {}).get("name", "baseline"),
                "predict": predict_baseline,
            },
            "candidate": {
                "name": cfg.get("engines", {}).get("candidate", {}).get("name", "candidate"),
                "predict": predict_candidate,
            },
        }
    }
    evaluation = evaluate(engine, rows, policy=cfg)
    baseline = evaluation["guards"]["baseline"]
    candidate = evaluation["guards"]["candidate"]

    base_preds = baseline["predictions"]
    cand_preds = candidate["predictions"]
    base_lat = baseline["latencies"]
    cand_lat = candidate["latencies"]

    # Create latency histograms
    histogram(base_lat, ASSETS / "latency_baseline.png", "Baseline latency")
    histogram(cand_lat, ASSETS / "latency_candidate.png", "Candidate latency")

    available_modes = sorted({"strict", "lenient"} | set(baseline["modes"].keys()) | set(candidate["modes"].keys()))
    views = {}
    for mode in available_modes:
        base_mode = baseline["modes"].get(mode, baseline["modes"]["strict"])
        cand_mode = candidate["modes"].get(mode, candidate["modes"]["strict"])
        views[mode] = {
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
                    "latency": baseline["latency"],
                    "aggregate_risk": base_mode.get("risk_total", baseline.get("aggregate_risk", 0.0)),
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
                    "latency": candidate["latency"],
                    "aggregate_risk": cand_mode.get("risk_total", candidate.get("aggregate_risk", 0.0)),
                },
            },
            "matrices": {"Baseline": base_mode["confusion"], "Candidate": cand_mode["confusion"]},
            "slices": {"Baseline": base_mode["slices"], "Candidate": cand_mode["slices"]},
        }

    # Failures/clusters from strict view
    def export_fail(rows, preds, name, mode="strict"):
        fn_rows=[]; fp_rows=[]
        for r,p in zip(rows,preds):
            gt_pos = is_pos_label(r["label"], mode)
            pr_pos = bool(p)
            if gt_pos and (not pr_pos):
                fn_rows.append({"id":r["id"],"category":r["category"],"language":r["language"],"text":r["text"]})
            if (not gt_pos) and pr_pos:
                fp_rows.append({"id":r["id"],"category":r["category"],"language":r["language"],"text":r["text"]})
        fn_path = OUT_DIR / f"{name}_fn.csv"
        fp_path = OUT_DIR / f"{name}_fp.csv"
        for path,rows_ in [(fn_path,fn_rows),(fp_path,fp_rows)]:
            with open(path,"w",newline="",encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=["id","category","language","text"])
                w.writeheader(); w.writerows(rows_)
        return fn_path, fp_path, fn_rows, fp_rows

    b_fn_csv, b_fp_csv, b_fn, b_fp = export_fail(rows, base_preds, "baseline", mode="strict")
    c_fn_csv, c_fp_csv, c_fn, c_fp = export_fail(rows, cand_preds, "candidate", mode="strict")
    base_clusters = cluster_failures(rows, base_preds, mode="strict")
    cand_clusters = cluster_failures(rows, cand_preds, mode="strict")
    failure_patterns = slice_failure_patterns(
        rows,
        cand_preds,
        mode="strict",
        per_slice=6,
        per_pattern=3,
        example_limit=2,
    )
    redteam_summary = load_redteam_summary(OUT_DIR / "redteam_cases.jsonl")
    runtime_offline = {f"{s['category']}/{s['language']}": s for s in views["strict"]["slices"]["Candidate"]}
    runtime_summary, runtime_chart = load_runtime_telemetry(Path("runtime_telemetry.jsonl"), ASSETS, runtime_offline)
    parity_summary = load_parity_summary(Path("report/parity.json"))
    incident_summary = load_incident_reports(OUT_DIR)
    failures = (
        [{"id":r["id"],"fail_type":"FN","model":"Baseline", **r} for r in b_fn] +
        [{"id":r["id"],"fail_type":"FP","model":"Baseline", **r} for r in b_fp] +
        [{"id":r["id"],"fail_type":"FN","model":"Candidate", **r} for r in c_fn] +
        [{"id":r["id"],"fail_type":"FP","model":"Candidate", **r} for r in c_fp]
    )

    env = Environment(loader=FileSystemLoader(TPL_DIR))
    tpl = env.get_template("report.html")
    html = tpl.render(
        run_title="Baseline vs Candidate",
        run_id=run_id,
        dataset_path=str(dataset_path),
        dataset_sha=ds_sha,
        total_samples=len(rows),
        generated_at=created_at,
        policy_version=cfg.get("policy_version","v0.1"),
        engines={"baseline":cfg["engines"]["baseline"]["name"], "candidate":cfg["engines"]["candidate"]["name"]},
        metrics=views["strict"]["metrics"],  # default binding
        matrices=views["strict"]["matrices"],
        slices=views["strict"]["slices"],
        modes=views,  # both views for toggle
        latency_imgs={"baseline": os.path.relpath(ASSETS / "latency_baseline.png", OUT_DIR),
                      "candidate": os.path.relpath(ASSETS / "latency_candidate.png", OUT_DIR)},
        downloads={"fn_csv": Path(c_fn_csv).name, "fp_csv": Path(c_fp_csv).name},
        failures=failures,
        clusters={"Baseline": base_clusters, "Candidate": cand_clusters},
        failure_patterns=failure_patterns,
        redteam_summary=redteam_summary,
        runtime_summary=runtime_summary,
        runtime_chart=runtime_chart,
        parity_summary=parity_summary,
        incident_summary=incident_summary,
    )
    out_file = OUT_DIR / "index.html"
    out_file.write_text(html, encoding="utf-8")
    print(f"Report written to {out_file}")

    policy_path = (ROOT / POLICY_PATH).resolve()
    policy_sha = sha256_file(policy_path) if policy_path.exists() else None
    compiled_version = None
    try:
        compiled_policy = load_compiled_policy(policy_path)
        compiled_version = getattr(compiled_policy, "version", None)
    except FileNotFoundError:
        compiled_version = None

    engines_cfg = cfg.get("engines", {}) if isinstance(cfg, dict) else {}
    model_versions = {}
    for key in ("baseline", "candidate"):
        value = engines_cfg.get(key)
        if isinstance(value, dict):
            model_versions[key] = value.get("name")
        elif value is not None:
            model_versions[key] = str(value)

    append_run_record(
        {
            "run_id": run_id,
            "run_type": "report",
            "created_at": created_at,
            "dataset_path": str(dataset_path),
            "dataset_sha": ds_sha,
            "report_path": str(out_file),
            "model_versions": model_versions,
            "policy_path": str(policy_path),
            "compiled_policy_hash": policy_sha,
            "policy_version": cfg.get("policy_version"),
            "compiled_policy_version": compiled_version,
            "git_commit": git_commit(),
        }
    )

    candidate_fnr = views["strict"]["metrics"]["Candidate"].get("fnr", 0.0)
    fnr_threshold = notifier.threshold("fnr", 0.3)
    if candidate_fnr > fnr_threshold:
        notifier.notify(
            subject="High candidate FNR detected",
            message=f"Candidate FNR {candidate_fnr:.3f} exceeded threshold {fnr_threshold:.3f}",
            metadata={
                "run_id": run_id,
                "fnr": candidate_fnr,
                "threshold": fnr_threshold,
            },
        )

    runtime_margins = [entry.get("avg_margin", 0.0) for entry in (runtime_summary or []) if isinstance(entry, dict)]
    if runtime_margins:
        max_margin = max(runtime_margins)
        margin_threshold = notifier.threshold("runtime_margin", 0.1)
        if max_margin > margin_threshold:
            notifier.notify(
                subject="Runtime drift margin exceeded",
                message=f"Runtime avg margin {max_margin:.3f} exceeded threshold {margin_threshold:.3f}",
                metadata={
                    "run_id": run_id,
                    "max_margin": max_margin,
                    "threshold": margin_threshold,
                },
            )

if __name__ == "__main__":
    main()
