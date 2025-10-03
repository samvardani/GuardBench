import csv, json, sqlite3, datetime, pathlib
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

from src.guards.baseline import predict as predict_baseline
from src.guards.candidate import predict as predict_candidate
from src.utils.io_utils import load_config, resolve_dataset_path, sha256_file, git_commit, new_run_id
from src.utils.run_log import append_run_record
from src.utils.notify import NotificationManager
from src.policy.compiler import load_compiled_policy, POLICY_PATH
from src.evaluation import evaluate

ROOT = pathlib.Path(__file__).resolve().parents[2]
TPL_DIR = ROOT / "templates"
OUT_DIR = ROOT / "report"
ASSETS = ROOT / "assets"
DB_PATH = ROOT / "history.db"
OUT_DIR.mkdir(exist_ok=True); ASSETS.mkdir(exist_ok=True)

def load_rows(p: Path):
    with open(p, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def is_pos_label(lbl: str, mode: str) -> bool:
    l = (lbl or "").strip().lower()
    if mode == "lenient":
        return l == "unsafe"
    return l != "benign"

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

def store_db(run_id, dataset_sha, commit, html_path):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS runs(
            run_id TEXT PRIMARY KEY,
            created_at TEXT,
            dataset_sha TEXT,
            git_commit TEXT,
            html_path TEXT
        )
    """)
    cur.execute("INSERT OR REPLACE INTO runs(run_id, created_at, dataset_sha, git_commit, html_path) VALUES (?,?,?,?,?)",
                (run_id, datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                 dataset_sha, commit or "n/a", str(html_path)))
    con.commit(); con.close()

def main():
    cfg = load_config()
    notifier = NotificationManager(cfg.get("notifications"))
    dataset_path = resolve_dataset_path(cfg)
    rows = load_rows(dataset_path)

    run_id = new_run_id()
    created_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    ds_sha = sha256_file(dataset_path)
    commit = git_commit()

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
                    "recall_lo": base_mode["confusion"].get("recall_lo", 0.0),
                    "recall_hi": base_mode["confusion"].get("recall_hi", 0.0),
                    "fpr_lo": base_mode["confusion"].get("fpr_lo", 0.0),
                    "fpr_hi": base_mode["confusion"].get("fpr_hi", 0.0),
                    "latency": baseline["latency"],
                    "aggregate_risk": base_mode.get("risk_total", baseline.get("aggregate_risk", 0.0)),
                },
                "Candidate": {
                    "precision": cand_mode["confusion"]["precision"],
                    "recall": cand_mode["confusion"]["recall"],
                    "fnr": cand_mode["confusion"]["fnr"],
                    "fpr": cand_mode["confusion"]["fpr"],
                    "recall_lo": cand_mode["confusion"].get("recall_lo", 0.0),
                    "recall_hi": cand_mode["confusion"].get("recall_hi", 0.0),
                    "fpr_lo": cand_mode["confusion"].get("fpr_lo", 0.0),
                    "fpr_hi": cand_mode["confusion"].get("fpr_hi", 0.0),
                    "latency": candidate["latency"],
                    "aggregate_risk": cand_mode.get("risk_total", candidate.get("aggregate_risk", 0.0)),
                },
            },
            "matrices": {"Baseline": base_mode["confusion"], "Candidate": cand_mode["confusion"]},
            "slices": {"Baseline": base_mode["slices"], "Candidate": cand_mode["slices"]},
        }

    # Failures from strict view
    _, _, b_fn, b_fp = export_fail(rows, base_preds, "baseline", mode="strict")
    c_fn_csv, c_fp_csv, c_fn, c_fp = export_fail(rows, cand_preds, "candidate", mode="strict")
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
        metrics=views["strict"]["metrics"],     # default bindings for backwards-compat
        matrices=views["strict"]["matrices"],
        slices=views["strict"]["slices"],
        modes=views,                             # both views for the toggle
        latency_imgs={"baseline":"assets/latency_baseline.png","candidate":"assets/latency_candidate.png"},
        downloads={"fn_csv": Path(c_fn_csv).name, "fp_csv": Path(c_fp_csv).name},
        failures=failures,
        clusters={"Baseline": [], "Candidate": []}   # keep empty if you don't use clusters here
    )
    # Write archived copy with run_id in filename
    out_html = OUT_DIR / f"index_{run_id}.html"
    out_html.write_text(html, encoding="utf-8")
    # also keep canonical index.html pointing to the last run for convenience
    (OUT_DIR / "index.html").write_text(html, encoding="utf-8")

    # Record in sqlite
    store_db(run_id, ds_sha, commit, out_html)

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
            "run_type": "store_run",
            "created_at": created_at,
            "dataset_path": str(dataset_path),
            "dataset_sha": ds_sha,
            "report_path": str(out_html),
            "model_versions": model_versions,
            "policy_path": str(policy_path),
            "compiled_policy_hash": policy_sha,
            "policy_version": cfg.get("policy_version"),
            "compiled_policy_version": compiled_version,
            "git_commit": commit,
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

    print(f"Stored run {run_id}")
    print(f" → HTML: {out_html}")
    print(f" → DB:   {DB_PATH}")

if __name__ == "__main__":
    main()
