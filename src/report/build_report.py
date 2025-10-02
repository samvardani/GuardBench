import os, csv, json, pathlib, datetime
from pathlib import Path
from collections import Counter, defaultdict
from typing import List
from jinja2 import Environment, FileSystemLoader

from src.guards.baseline import predict as predict_baseline
from src.guards.candidate import predict as predict_candidate
from src.report.cluster_utils import cluster_failures, slice_failure_patterns
from src.utils.io_utils import load_config, resolve_dataset_path, sha256_file, git_commit, new_run_id

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



def _pred_to_bool(p):
    """
    Accept dict/int/bool/str predictions and return True if "flag".
    """
    if isinstance(p, dict):
        if "prediction" in p:
            v = p["prediction"]
            if isinstance(v, str):
                return v.lower() in ("flag","blocked","deny","unsafe","violation")
            return bool(v)
        if "pred" in p:
            v = p["pred"]
            if isinstance(v, str):
                return v.lower() in ("flag","blocked","deny","unsafe","violation")
            return bool(v)
        if ("score" in p) and ("threshold" in p):
            return p["score"] >= p["threshold"]
        return bool(p)
    if isinstance(p, str):
        return p.strip().lower() in ("flag","blocked","deny","unsafe","violation","1","true","yes","y")
    return bool(p)

def _label_to_bool(x):
    """
    Accept 0/1, bool, or strings like 'harmful'/'safe' and return True if harmful.
    """
    if isinstance(x, bool):
        return x
    if isinstance(x, (int, float)):
        return int(x) != 0
    if isinstance(x, str):
        t = x.strip().lower()
        harmful = {"1","true","yes","y","harmful","unsafe","violation","bad","toxic","deny"}
        safe    = {"0","false","no","n","safe","benign","ok","harmless","good","allow"}
        if t in harmful: return True
        if t in safe:    return False
    return False

def _call_guard(guard_fn, text, category=None, language=None):
    # Try multiple signatures; normalize output to {"prediction": ..., "latency_ms": ...}
    trials = [
        ((text,), {}),
        ((text, category), {}) if category is not None else None,
        ((text, category, language), {}) if (category is not None and language is not None) else None,
        ((), {"text": text, "category": category, "language": language}),
    ]
    trials = [t for t in trials if t is not None]

    out = None
    for args, kwargs in trials:
        try:
            kwargs = {k: v for k, v in kwargs.items() if v is not None}
            out = guard_fn(*args, **kwargs)
            break
        except TypeError:
            continue
        except Exception:
            continue
    if out is None:
        out = guard_fn(text)

    pred, lat = None, 0
    if isinstance(out, dict):
        pred = out.get("prediction") or out.get("pred")
        if pred is None and ("score" in out and "threshold" in out):
            pred = "flag" if out["score"] >= out["threshold"] else "pass"
        lat = int(out.get("latency_ms", out.get("latency", 0)) or 0)
    else:
        pred = "flag" if bool(out) else "pass"
    return {"prediction": pred, "latency_ms": lat, "raw": out}

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

def run_guard(rows, guard_fn):
    preds, lat = [], []
    for r in rows:
        o = _call_guard(guard_fn, r['text'], r.get('category'), r.get('language'))
        preds.append(1 if (o['prediction'] in ('flag', True, 1)) else 0)
        lat.append(int(o['latency_ms']))
    return preds, lat

def is_pos_label(lbl: str, mode: str) -> bool:
    l = (lbl or "").strip().lower()
    if mode == "lenient":
        return l == "unsafe"
    return l != "benign"

def wilson_ci(k:int, n:int, z:float=1.96):
    if n <= 0: return 0.0, 0.0
    p = k / n
    denom = 1 + (z*z)/n
    import math
    center = (p + (z*z)/(2*n)) / denom
    margin = z * math.sqrt((p*(1-p) + (z*z)/(4*n)) / n) / denom
    lo = max(0.0, round(center - margin, 3))
    hi = min(1.0, round(center + margin, 3))
    return lo, hi

def confusion(rows, preds, mode="strict"):
    cm = Counter()
    for r, p in zip(rows, preds):
        gt_pos = is_pos_label(r["label"], mode)
        pr_pos = _pred_to_bool(p)
        if gt_pos and pr_pos: cm["tp"] += 1
        elif (not gt_pos) and pr_pos: cm["fp"] += 1
        elif (not gt_pos) and (not pr_pos): cm["tn"] += 1
        elif gt_pos and (not pr_pos): cm["fn"] += 1
    tp,fp,tn,fn = cm["tp"],cm["fp"],cm["tn"],cm["fn"]
    def pct(a,b): return round(a/b,3) if b else 0.0
    r_k, r_n = tp, tp+fn
    f_k, f_n = fp, fp+tn
    r_lo, r_hi = wilson_ci(r_k, r_n)
    f_lo, f_hi = wilson_ci(f_k, f_n)
    return {
        "tp":tp,"fp":fp,"tn":tn,"fn":fn,
        "precision":pct(tp,tp+fp), "recall":pct(tp,tp+fn),
        "fnr":pct(fn,tp+fn), "fpr":pct(fp,fp+tn),
        "recall_lo": r_lo, "recall_hi": r_hi,
        "fpr_lo": f_lo, "fpr_hi": f_hi
    }

def pctiles(values):
    if not values: return {"p50":0,"p90":0,"p99":0}
    vs = sorted(values)
    idx=lambda q:int((len(vs)-1)*q)
    return {"p50":vs[idx(0.50)], "p90":vs[idx(0.90)], "p99":vs[idx(0.99)]}

def histogram(values, out_png, title):
    import matplotlib.pyplot as plt
    v = values if values else [0]
    bins = min(20, max(5, len(set(v)) or 5))
    plt.figure()
    plt.hist(v, bins=bins)
    plt.title(title); plt.xlabel("Latency (ms)"); plt.ylabel("Count")
    plt.tight_layout(); plt.savefig(out_png); plt.close()

def slice_metrics(rows, preds, by=("category","language"), mode="strict"):
    from collections import defaultdict
    G = defaultdict(lambda: {"tp":0,"fp":0,"tn":0,"fn":0,"n":0})
    for r,p in zip(rows,preds):
        key = tuple(r[k] for k in by)
        gt_pos = is_pos_label(r["label"], mode)
        pr_pos = _pred_to_bool(p)
        if gt_pos and pr_pos: G[key]["tp"] += 1
        elif (not gt_pos) and pr_pos: G[key]["fp"] += 1
        elif (not gt_pos) and (not pr_pos): G[key]["tn"] += 1
        elif gt_pos and (not pr_pos): G[key]["fn"] += 1
        G[key]["n"] += 1
    def pct(a,b): return round(a/b,3) if b else 0.0
    out=[]
    for (cat,lang),m in G.items():
        tp,fp,tn,fn = m["tp"],m["fp"],m["tn"],m["fn"]
        r_k, r_n = tp, tp+fn
        f_k, f_n = fp, fp+tn
        r_lo, r_hi = wilson_ci(r_k, r_n)
        f_lo, f_hi = wilson_ci(f_k, f_n)
        out.append({
            "category":cat,"language":lang,"n":m["n"],
            "precision":pct(tp,tp+fp),"recall":pct(tp,tp+fn),
            "fnr":pct(fn,tp+fn),"fpr":pct(fp,fp+tn),
            "recall_lo": r_lo, "recall_hi": r_hi,
            "fpr_lo": f_lo, "fpr_hi": f_hi,
            "low_n": m["n"] < 20
        })
    out.sort(key=lambda x:(-x["n"], x["category"], x["language"]))
    return out

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
    dataset_path = resolve_dataset_path(cfg)
    rows = load_rows(dataset_path)

    run_id = new_run_id()
    created_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    ds_sha = sha256_file(dataset_path)

    base_preds, base_lat = run_guard(rows, predict_baseline)
    cand_preds, cand_lat = run_guard(rows, predict_candidate)

    # Create latency histograms
    histogram(base_lat, ASSETS / "latency_baseline.png", "Baseline latency")
    histogram(cand_lat, ASSETS / "latency_candidate.png", "Candidate latency")

    views = {}
    for mode in ("strict","lenient"):
        base_cm = confusion(rows, base_preds, mode)
        cand_cm = confusion(rows, cand_preds, mode)
        views[mode] = {
            "metrics": {
                "Baseline":{
                    "precision":base_cm["precision"],"recall":base_cm["recall"],"fnr":base_cm["fnr"],"fpr":base_cm["fpr"],
                    "recall_lo":base_cm["recall_lo"],"recall_hi":base_cm["recall_hi"],
                    "fpr_lo":base_cm["fpr_lo"],"fpr_hi":base_cm["fpr_hi"],
                    "latency":pctiles(base_lat)
                },
                "Candidate":{
                    "precision":cand_cm["precision"],"recall":cand_cm["recall"],"fnr":cand_cm["fnr"],"fpr":cand_cm["fpr"],
                    "recall_lo":cand_cm["recall_lo"],"recall_hi":cand_cm["recall_hi"],
                    "fpr_lo":cand_cm["fpr_lo"],"fpr_hi":cand_cm["fpr_hi"],
                    "latency":pctiles(cand_lat)
                }
            },
            "matrices": {"Baseline":base_cm, "Candidate":cand_cm},
            "slices": {"Baseline": slice_metrics(rows, base_preds, mode=mode),
                       "Candidate": slice_metrics(rows, cand_preds, mode=mode)}
        }

    # Failures/clusters from strict view
    def export_fail(rows, preds, name, mode="strict"):
        fn_rows=[]; fp_rows=[]
        for r,p in zip(rows,preds):
            gt_pos = is_pos_label(r["label"], mode)
            pr_pos = _pred_to_bool(p)
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

if __name__ == "__main__":
    main()
