import os, csv, json, pathlib, datetime
from pathlib import Path
from collections import Counter
from jinja2 import Environment, FileSystemLoader
import matplotlib.pyplot as plt

from src.guards.baseline import predict as predict_baseline
from src.guards.candidate import predict as predict_candidate
from src.report.cluster_utils import cluster_failures
from src.utils.io_utils import load_config, resolve_dataset_path, sha256_file, git_commit, new_run_id

ROOT = pathlib.Path(__file__).resolve().parents[2]
TPL_DIR = ROOT / "templates"
OUT_DIR = ROOT / "report"
ASSETS = ROOT / "assets"
OUT_DIR.mkdir(exist_ok=True); ASSETS.mkdir(exist_ok=True)

def load_rows(dataset_path: Path):
    with open(dataset_path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def run_guard(rows, guard_fn):
    preds=[]; lat=[]
    for r in rows:
        out = guard_fn(r["text"], language=r.get("language"), category=r.get("category"))
        preds.append(out); lat.append(out.get("latency_ms",0))
    return preds, lat

def confusion(rows, preds):
    cm = Counter()
    for r, p in zip(rows, preds):
        gt_pos = (r["label"].strip().lower() != "benign")
        pr_pos = (p["prediction"] == "flag")
        if gt_pos and pr_pos: cm["tp"] += 1
        elif (not gt_pos) and pr_pos: cm["fp"] += 1
        elif (not gt_pos) and (not pr_pos): cm["tn"] += 1
        elif gt_pos and (not pr_pos): cm["fn"] += 1
    tp,fp,tn,fn = cm["tp"],cm["fp"],cm["tn"],cm["fn"]
    pct = lambda a,b: round(a/b,3) if b else 0.0
    return {"tp":tp,"fp":fp,"tn":tn,"fn":fn,
            "precision":pct(tp,tp+fp), "recall":pct(tp,tp+fn),
            "fnr":pct(fn,tp+fn), "fpr":pct(fp,fp+tn)}

def pctiles(values):
    if not values: return {"p50":0,"p90":0,"p99":0}
    vs = sorted(values); idx=lambda q:int((len(vs)-1)*q)
    return {"p50":vs[idx(0.50)], "p90":vs[idx(0.90)], "p99":vs[idx(0.99)]}

def histogram(values, out_png, title):
    if not values: values=[0]
    plt.figure()
    plt.hist(values, bins=min(10, max(3, len(set(values)))))
    plt.title(title); plt.xlabel("Latency (ms)"); plt.ylabel("Count")
    plt.tight_layout(); plt.savefig(out_png); plt.close()

def export_failures(rows, preds, model_name):
    fn_rows=[]; fp_rows=[]
    for r,p in zip(rows,preds):
        gt_pos = (r["label"].strip().lower() != "benign")
        pr_pos = (p["prediction"] == "flag")
        if gt_pos and (not pr_pos):
            fn_rows.append({"id":r["id"],"category":r["category"],"language":r["language"],"text":r["text"]})
        if (not gt_pos) and pr_pos:
            fp_rows.append({"id":r["id"],"category":r["category"],"language":r["language"],"text":r["text"]})
    fn_path = OUT_DIR / f"{model_name}_fn.csv"
    fp_path = OUT_DIR / f"{model_name}_fp.csv"
    for path,rows_ in [(fn_path,fn_rows),(fp_path,fp_rows)]:
        with open(path,"w",newline="",encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["id","category","language","text"])
            w.writeheader(); w.writerows(rows_)
    return fn_path, fp_path, fn_rows, fp_rows

def slice_metrics(rows, preds, by=("category","language")):
    from collections import defaultdict
    G = defaultdict(lambda: {"tp":0,"fp":0,"tn":0,"fn":0,"n":0})
    for r,p in zip(rows,preds):
        key = tuple(r[k] for k in by)
        gt_pos = (r["label"].strip().lower() != "benign")
        pr_pos = (p["prediction"] == "flag")
        if gt_pos and pr_pos: G[key]["tp"] += 1
        elif (not gt_pos) and pr_pos: G[key]["fp"] += 1
        elif (not gt_pos) and (not pr_pos): G[key]["tn"] += 1
        elif gt_pos and (not pr_pos): G[key]["fn"] += 1
        G[key]["n"] += 1
    pct = lambda a,b: round(a/b,3) if b else 0.0
    out=[]
    for (cat,lang),m in G.items():
        tp,fp,tn,fn = m["tp"],m["fp"],m["tn"],m["fn"]
        out.append({"category":cat,"language":lang,"n":m["n"],
                    "precision":pct(tp,tp+fp),"recall":pct(tp,tp+fn),
                    "fnr":pct(fn,tp+fn),"fpr":pct(fp,fp+tn)})
    out.sort(key=lambda x:(-x["n"], x["category"], x["language"]))
    return out

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

    base_cm = confusion(rows, base_preds)
    cand_cm = confusion(rows, cand_preds)
    base_lat_pct = pctiles(base_lat)
    cand_lat_pct = pctiles(cand_lat)

    base_png = ASSETS / "latency_baseline.png"
    cand_png = ASSETS / "latency_candidate.png"
    histogram(base_lat, base_png, "Baseline latency")
    histogram(cand_lat, cand_png, "Candidate latency")

    b_fn_csv, b_fp_csv, b_fn, b_fp = export_failures(rows, base_preds, "baseline")
    c_fn_csv, c_fp_csv, c_fn, c_fp = export_failures(rows, cand_preds, "candidate")
    base_clusters = cluster_failures(rows, base_preds)
    cand_clusters = cluster_failures(rows, cand_preds)
    failures = (
        [{"id":r["id"],"fail_type":"FN","model":"Baseline", **r} for r in b_fn] +
        [{"id":r["id"],"fail_type":"FP","model":"Baseline", **r} for r in b_fp] +
        [{"id":r["id"],"fail_type":"FN","model":"Candidate", **r} for r in c_fn] +
        [{"id":r["id"],"fail_type":"FP","model":"Candidate", **r} for r in c_fp]
    )

    slices = {"Baseline": slice_metrics(rows, base_preds),
              "Candidate": slice_metrics(rows, cand_preds)}

    env = Environment(loader=FileSystemLoader(TPL_DIR))
    tpl = env.get_template("report.html")
    html = tpl.render(
        run_title="Baseline vs Candidate",
        run_id=run_id,
        dataset_path=str(dataset_path),
        dataset_sha=ds_sha,
        total_samples=len(rows),
        generated_at=created_at,
        policy_version=cfg.get("policy_version","n/a"),
        engines={"baseline":cfg["engines"]["baseline"]["name"], "candidate":cfg["engines"]["candidate"]["name"]},
        metrics={
          "Baseline":{"precision":base_cm["precision"],"recall":base_cm["recall"],"fnr":base_cm["fnr"],"fpr":base_cm["fpr"],"latency":base_lat_pct},
          "Candidate":{"precision":cand_cm["precision"],"recall":cand_cm["recall"],"fnr":cand_cm["fnr"],"fpr":cand_cm["fpr"],"latency":cand_lat_pct}
        },
        matrices={"Baseline":base_cm, "Candidate":cand_cm},
        latency_imgs={"baseline": os.path.relpath(base_png, OUT_DIR), "candidate": os.path.relpath(cand_png, OUT_DIR)},
        downloads={"fn_csv": Path(c_fn_csv).name, "fp_csv": Path(c_fp_csv).name},
        failures=failures,
        clusters={"Baseline": base_clusters, "Candidate": cand_clusters},
        slices=slices
    )
    out_file = OUT_DIR / "index.html"
    out_file.write_text(html, encoding="utf-8")

    metrics_json = {
        "run_id": run_id, "generated_at": created_at,
        "dataset_path": str(dataset_path), "dataset_sha256": ds_sha,
        "git_commit": commit, "policy_version": cfg.get("policy_version","n/a"),
        "engines": {"baseline":cfg["engines"]["baseline"]["name"], "candidate":cfg["engines"]["candidate"]["name"]},
        "metrics": {"Baseline": base_cm, "Candidate": cand_cm}
    }
    (OUT_DIR / f"metrics_{run_id}.json").write_text(json.dumps(metrics_json, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Report written to {out_file}")

if __name__ == "__main__":
    main()
