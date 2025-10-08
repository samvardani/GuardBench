import matplotlib
matplotlib.use("Agg")
import argparse
import hashlib
import os
import csv
import json
import pathlib
import tempfile
import datetime
import sys
from pathlib import Path
from collections import defaultdict
from typing import Iterable, List, Optional
from jinja2 import Environment, FileSystemLoader

from src.guards.baseline import predict as predict_baseline
from src.guards.candidate import predict as predict_candidate
from src.report.cluster_utils import cluster_failures, slice_failure_patterns
from src.utils.io_utils import load_config, resolve_dataset_path, sha256_file, git_commit, new_run_id
from src.utils.run_log import append_run_record
from src.utils.notify import NotificationManager
from src.policy.compiler import load_compiled_policy, POLICY_PATH
from src.evaluation import evaluate
from src.connectors import s3 as s3_connector, gcs as gcs_connector, azure as azure_connector, kafka as kafka_connector

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
REPORT_ASSETS = OUT_DIR / "assets"
OUT_DIR.mkdir(exist_ok=True); ASSETS.mkdir(exist_ok=True); REPORT_ASSETS.mkdir(exist_ok=True)


def _write_local_jsonl(path: Path, records: Iterable[dict], encoding: str = "utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding=encoding) as handle:
        for record in records:
            handle.write(json.dumps(record, separators=(",", ":")))
            handle.write("\n")


def _read_local_jsonl(path: Path, encoding: str = "utf-8") -> List[dict]:
    with path.open("r", encoding=encoding) as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _read_remote_jsonl(uri: str) -> List[dict]:
    if uri.startswith("s3://"):
        return s3_connector.read_jsonl(uri)
    if uri.startswith("gs://") or uri.startswith("gcs://"):
        return gcs_connector.read_jsonl(uri)
    if uri.startswith("azure://") or uri.startswith("az://") or uri.startswith("wasbs://"):
        return azure_connector.read_jsonl(uri)
    if uri.startswith("file://"):
        return _read_local_jsonl(Path(uri[len("file://") :]))
    raise ValueError(f"Unsupported input URI: {uri}")


def _write_remote_jsonl(uri: str, records: Iterable[dict]) -> None:
    if uri.startswith("s3://"):
        s3_connector.write_jsonl(uri, records)
        return
    if uri.startswith("gs://") or uri.startswith("gcs://"):
        gcs_connector.write_jsonl(uri, records)
        return
    if uri.startswith("azure://") or uri.startswith("az://") or uri.startswith("wasbs://"):
        azure_connector.write_jsonl(uri, records)
        return
    if uri.startswith("file://"):
        _write_local_jsonl(Path(uri[len("file://") :]), records)
        return
    raise ValueError(f"Unsupported output URI: {uri}")

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


def _normalize_records(records: Iterable[dict]) -> List[dict]:
    rows: List[dict] = []
    dropped = 0
    for raw in records:
        if not isinstance(raw, dict):
            continue
        if _is_valid_row(raw):
            normalized = dict(raw)
            normalized["text"] = _row_text(raw)
            normalized["category"] = normalized.get("category") or _row_field(raw, "category")
            normalized["language"] = normalized.get("language") or _row_field(raw, "language")
            normalized["label"] = normalized.get("label", _row_field(raw, "label") or 0)
            normalized["id"] = normalized.get("id") or _row_field(raw, "id")
            rows.append(normalized)
        else:
            dropped += 1
    if dropped:
        print(f"[load_rows] skipped {dropped} malformed remote row(s) lacking text-like content.", file=sys.stderr)
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
    modality_counts = defaultdict(int)
    for entry in telemetry:
        slice_key = f"{entry.get('category_guess')}/{entry.get('language_guess')}"
        diff = float(entry.get("score", 0.0)) - float(entry.get("threshold", 0.0))
        by_slice[slice_key].append(diff)
        m = entry.get("modality")
        if isinstance(m, str) and m:
            modality_counts[m] += 1

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

    return summary, relative_chart, dict(modality_counts)


def load_obfuscation_summary(path: Path, assets_root: Path):
    if not path.exists():
        return [], None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return [], None
    if not isinstance(data, dict):
        return [], None

    ordered = []
    operators = set()
    summary = []
    for slice_key in sorted(data.keys()):
        payload = data.get(slice_key) or {}
        ops = payload.get("operators") or {}
        operators.update(ops.keys())
        weakest = sorted(ops.items(), key=lambda kv: kv[1])[:3]
        summary.append(
            {
                "slice": slice_key,
                "total": payload.get("total", 0),
                "hardness": round((payload.get("hardness") or {}).get("mean", 0.0), 3),
                "weakest": [
                    {"operator": op, "recall": round(val, 3)}
                    for op, val in weakest
                ],
            }
        )
        ordered.append((slice_key, payload))

    chart_rel = None
    if summary and operators:
        chart_path = assets_root / "obfuscation_heatmap.png"
        try:
            import matplotlib.pyplot as plt

            operator_list = sorted(operators)
            slices = [item[0] for item in ordered]
            matrix = [
                [
                    (item[1].get("operators") or {}).get(op, 0.0)
                    for op in operator_list
                ]
                for item in ordered
            ]

            fig, ax = plt.subplots(
                figsize=(max(6, len(operator_list) * 0.9), max(3, len(slices) * 0.6))
            )
            im = ax.imshow(matrix, aspect="auto", vmin=0, vmax=1, cmap="Blues")
            ax.set_xticks(range(len(operator_list)))
            ax.set_xticklabels(operator_list, rotation=35, ha="right")
            ax.set_yticks(range(len(slices)))
            ax.set_yticklabels(slices)
            ax.set_xlabel("Operator")
            ax.set_ylabel("Slice")
            ax.set_title("Detection after obfuscation (recall)")

            for y, row in enumerate(matrix):
                for x, value in enumerate(row):
                    color = "#0f172a" if value < 0.7 else "#f8fafc"
                    ax.text(x, y, f"{value:.2f}", va="center", ha="center", color=color, fontsize=9)

            fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label="Recall")
            plt.tight_layout()
            chart_path.parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(chart_path, dpi=150)
            plt.close(fig)
            chart_rel = os.path.relpath(chart_path, OUT_DIR)
        except Exception:
            chart_rel = None

    return summary, chart_rel


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


def load_parity_actions(path: Path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def render_parity_chart(summary: dict, assets_root: Path):
    if not summary:
        return None
    rows = summary.get("rows") or []
    if not rows:
        return None
    chart_path = assets_root / f"parity_{summary.get('category', 'overview')}.png"
    try:
        import matplotlib.pyplot as plt

        languages = [row["language"] for row in rows]
        recalls = [row.get("recall", 0.0) for row in rows]
        top = max(recalls) if recalls else 0.0
        target_delta = summary.get("target_delta", 0.0)
        lower_band = max(0.0, top - target_delta)

        fig, ax = plt.subplots(figsize=(max(4, len(languages) * 1.2), 3.5))
        bars = ax.bar(languages, recalls, color="#3b82f6", edgecolor="#0f172a")
        ax.set_ylim(0, 1.05)
        ax.set_ylabel("Recall")
        ax.set_title(f"Language parity — {summary.get('category')}")
        ax.axhspan(lower_band, top, color="#fde68a", alpha=0.4, label="Target band")
        ax.set_yticks([i / 10 for i in range(0, 11, 2)])
        ax.set_xlabel("Language")
        ax.legend(loc="lower left")

        for bar, value in zip(bars, recalls):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.02,
                f"{value:.2f}",
                ha="center",
                va="bottom",
                fontsize=9,
                color="#0f172a",
            )

        plt.tight_layout()
        chart_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(chart_path, dpi=150)
        plt.close(fig)
        return os.path.relpath(chart_path, OUT_DIR)
    except Exception:
        return None


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


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build evaluation report")
    parser.add_argument("--input-uri", help="Optional JSONL dataset from cloud storage")
    parser.add_argument("--output-uri", help="Write summary JSONL to cloud storage")
    parser.add_argument("--kafka-topic", help="Publish summary payload to Kafka topic")
    parser.add_argument("--kafka-brokers", help="Kafka bootstrap servers")
    parser.add_argument("--kafka-rest-endpoint", help="Optional REST proxy endpoint for Kafka fallback")
    parser.add_argument("--kafka-retries", type=int, default=3)
    parser.add_argument("--kafka-backoff", type=float, default=0.5)
    return parser


def main(argv: Optional[Iterable[str]] = None):
    parser = _build_arg_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    cfg = load_config()
    notifier = NotificationManager(cfg.get("notifications"))

    dataset_display: str
    ds_sha: str
    dataset_rows: List[dict]

    if args.input_uri:
        remote_records = _read_remote_jsonl(args.input_uri)
        dataset_rows = _normalize_records(remote_records)
        dataset_display = args.input_uri
        serialized = json.dumps(dataset_rows, sort_keys=True).encode("utf-8")
        ds_sha = hashlib.sha256(serialized).hexdigest()
    else:
        dataset_path = resolve_dataset_path(cfg)
        dataset_rows = load_rows(dataset_path)
        dataset_display = str(dataset_path)
        ds_sha = sha256_file(dataset_path)

    rows = dataset_rows

    run_id = new_run_id()
    created_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

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
    histogram(base_lat, REPORT_ASSETS / "latency_baseline.png", "Baseline latency")
    histogram(cand_lat, REPORT_ASSETS / "latency_candidate.png", "Candidate latency")

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
    runtime_summary, runtime_chart, runtime_modalities = load_runtime_telemetry(Path("runtime_telemetry.jsonl"), REPORT_ASSETS, runtime_offline)
    obfuscation_summary, obfuscation_chart = load_obfuscation_summary(OUT_DIR / "obfuscation.json", REPORT_ASSETS)
    parity_summary = load_parity_summary(OUT_DIR / "parity.json")
    parity_chart = render_parity_chart(parity_summary, REPORT_ASSETS)
    parity_actions = load_parity_actions(OUT_DIR / "parity_actions.json")
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
        latency_imgs={"baseline": os.path.relpath(REPORT_ASSETS / "latency_baseline.png", OUT_DIR),
                      "candidate": os.path.relpath(REPORT_ASSETS / "latency_candidate.png", OUT_DIR)},
        downloads={"fn_csv": Path(c_fn_csv).name, "fp_csv": Path(c_fp_csv).name},
        failures=failures,
        clusters={"Baseline": base_clusters, "Candidate": cand_clusters},
        failure_patterns=failure_patterns,
        redteam_summary=redteam_summary,
        runtime_summary=runtime_summary,
        runtime_chart=runtime_chart,
        runtime_modalities=runtime_modalities,
        parity_summary=parity_summary,
        parity_chart=parity_chart,
        parity_json="parity.json",
        obfuscation_summary=obfuscation_summary,
        obfuscation_chart=obfuscation_chart,
        obfuscation_json="obfuscation.json",
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

    run_record = {
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

    # Persist to local lineage log
    append_run_record(run_record)

    # Optional: emit a single-line JSONL summary to remote storage when --output-uri is set
    if args.output_uri:
        try:
            _write_remote_jsonl(args.output_uri, [run_record])
            print(f"Wrote summary to {args.output_uri}")
        except Exception as e:
            print(f"[warn] Failed to write summary to {args.output_uri}: {e}", file=sys.stderr)

    # Optional: publish summary to Kafka when flags are provided
    if args.kafka_topic:
        try:
            producer = kafka_connector.Producer(
                brokers=args.kafka_brokers,
                retries=int(args.kafka_retries or 3),
                backoff_seconds=float(args.kafka_backoff or 0.5),
                rest_endpoint=args.kafka_rest_endpoint,
            )
            producer.send_json(args.kafka_topic, run_record)
            print(f"Published summary to Kafka topic {args.kafka_topic}")
        except Exception as e:
            print(f"[warn] Failed to publish to Kafka topic {args.kafka_topic}: {e}", file=sys.stderr)

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
