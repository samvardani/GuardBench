import os, csv, json, pathlib, datetime
from pathlib import Path
from collections import Counter
from jinja2 import Environment, FileSystemLoader

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
        pr_pos = (p["prediction"] == "flag")
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
        pr_pos = (p["prediction"] == "flag")
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

    b_fn_csv, b_fp_csv, b_fn, b_fp = export_fail(rows, base_preds, "baseline", mode="strict")
    c_fn_csv, c_fp_csv, c_fn, c_fp = export_fail(rows, cand_preds, "candidate", mode="strict")
    base_clusters = cluster_failures(rows, base_preds)
    cand_clusters = cluster_failures(rows, cand_preds)
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
        clusters={"Baseline": base_clusters, "Candidate": cand_clusters}
    )
    out_file = OUT_DIR / "index.html"
    out_file.write_text(html, encoding="utf-8")
    print(f"Report written to {out_file}")

if __name__ == "__main__":
    main()
