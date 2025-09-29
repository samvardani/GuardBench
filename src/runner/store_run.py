import csv, json, sqlite3, datetime, hashlib, pathlib
from pathlib import Path
from collections import Counter, defaultdict
from jinja2 import Environment, FileSystemLoader

from src.guards.baseline import predict as predict_baseline
from src.guards.candidate import predict as predict_candidate
from src.utils.io_utils import load_config, resolve_dataset_path, sha256_file, git_commit, new_run_id

ROOT = pathlib.Path(__file__).resolve().parents[2]
TPL_DIR = ROOT / "templates"
OUT_DIR = ROOT / "report"
ASSETS = ROOT / "assets"
DB_PATH = ROOT / "history.db"
OUT_DIR.mkdir(exist_ok=True); ASSETS.mkdir(exist_ok=True)

def load_rows(p: Path):
    with open(p, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def run_guard(rows, guard_fn):
    preds=[]; lat=[]
    for r in rows:
        out = guard_fn(r["text"], language=r.get("language"), category=r.get("category"))
        preds.append(out); lat.append(out.get("latency_ms",0))
    return preds, lat

def is_pos_label(lbl: str, mode: str) -> bool:
    l = (lbl or "").strip().lower()
    if mode == "lenient":
        return l == "unsafe"
    return l != "benign"

def pct(a,b): 
    return round(a/b,3) if b else 0.0

def confusion(rows, preds, mode="strict"):
    cm = Counter()
    for r, p in zip(rows, preds):
        gt_pos = is_pos_label(r["label"], mode)
        pr_pos = (p["prediction"] == "flag")
        if gt_pos and pr_pos: cm["tp"] += 1
        elif (not gt_pos) and pr_pos: cm["fp"] += 1
        elif (not gt_pos) and (not pr_pos): cm["tn"] += 1
        elif gt_pos and (not pr_pos): cm["fn"] += 1
    tp,fp,tn,fn = cm["tp"],cm["fp"],cm["tn"],cm["fn"]
    return {
        "tp":tp,"fp":fp,"tn":tn,"fn":fn,
        "precision":pct(tp,tp+fp), "recall":pct(tp,tp+fn),
        "fnr":pct(fn,tp+fn), "fpr":pct(fp,fp+tn)
    }

def slice_metrics(rows, preds, by=("category","language"), mode="strict"):
    G = defaultdict(lambda: {"tp":0,"fp":0,"tn":0,"fn":0,"n":0})
    for r,p in zip(rows,preds):
        key = tuple(r.get(k) for k in by)
        gt_pos = is_pos_label(r["label"], mode)
        pr_pos = (p["prediction"] == "flag")
        if gt_pos and pr_pos: G[key]["tp"] += 1
        elif (not gt_pos) and pr_pos: G[key]["fp"] += 1
        elif (not gt_pos) and (not pr_pos): G[key]["tn"] += 1
        elif gt_pos and (not pr_pos): G[key]["fn"] += 1
        G[key]["n"] += 1
    out=[]
    for (cat,lang),m in G.items():
        tp,fp,tn,fn = m["tp"],m["fp"],m["tn"],m["fn"]
        out.append({"category":cat,"language":lang,"n":m["n"],
                    "precision":pct(tp,tp+fp),"recall":pct(tp,tp+fn),
                    "fnr":pct(fn,tp+fn),"fpr":pct(fp,fp+tn)})
    out.sort(key=lambda x:(-x["n"], x["category"] or "", x["language"] or ""))
    return out

def export_fail(rows, preds, name, mode="strict"):
    fn_rows=[]; fp_rows=[]
    for r,p in zip(rows,preds):
        gt_pos = is_pos_label(r["label"], mode)
        pr_pos = (p["prediction"] == "flag")
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
    dataset_path = resolve_dataset_path(cfg)
    rows = load_rows(dataset_path)

    run_id = new_run_id()
    created_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    ds_sha = sha256_file(dataset_path)
    commit = git_commit()

    base_preds, base_lat = run_guard(rows, predict_baseline)
    cand_preds, cand_lat = run_guard(rows, predict_candidate)

    # Build both policy views (strict/lenient)
    views = {}
    for mode in ("strict","lenient"):
        base_cm = confusion(rows, base_preds, mode)
        cand_cm = confusion(rows, cand_preds, mode)
        views[mode] = {
            "metrics": {
                "Baseline":{"precision":base_cm["precision"],"recall":base_cm["recall"],"fnr":base_cm["fnr"],"fpr":base_cm["fpr"],"latency":{"p50":0,"p90":0,"p99":0}},
                "Candidate":{"precision":cand_cm["precision"],"recall":cand_cm["recall"],"fnr":cand_cm["fnr"],"fpr":cand_cm["fpr"],"latency":{"p50":0,"p90":0,"p99":0}}
            },
            "matrices": {"Baseline":base_cm, "Candidate":cand_cm},
            "slices": {"Baseline": slice_metrics(rows, base_preds, mode=mode),
                       "Candidate": slice_metrics(rows, cand_preds, mode=mode)}
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

    print(f"Stored run {run_id}")
    print(f" → HTML: {out_html}")
    print(f" → DB:   {DB_PATH}")

if __name__ == "__main__":
    main()
