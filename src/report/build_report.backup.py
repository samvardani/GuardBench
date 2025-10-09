import csv, pathlib, yaml, datetime
from statistics import mean
from collections import Counter
from jinja2 import Environment, FileSystemLoader
import matplotlib.pyplot as plt

from guards.baseline import predict as predict_baseline
from guards.candidate import predict as predict_candidate

ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA = ROOT / "dataset" / "sample.csv"
TPL_DIR = ROOT / "templates"
OUT_DIR = ROOT / "report"
ASSETS = ROOT / "assets"
OUT_DIR.mkdir(exist_ok=True)
ASSETS.mkdir(exist_ok=True)

def load_cfg():
    with open(ROOT / "config.yaml","r") as f:
        return yaml.safe_load(f)

def load_rows():
    rows=[]
    with open(DATA, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r: rows.append(row)
    return rows

def run_guard(rows, guard_fn, name):
    preds=[]; lat=[]
    for r in rows:
        out = guard_fn(r["text"])
        preds.append(out)
        lat.append(out.get("latency_ms",0))
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
    precision = tp/(tp+fp) if (tp+fp) else 0.0
    recall    = tp/(tp+fn) if (tp+fn) else 0.0
    fnr       = fn/(tp+fn) if (tp+fn) else 0.0
    fpr       = fp/(fp+tn) if (fp+tn) else 0.0
    return {"tp":tp,"fp":fp,"tn":tn,"fn":fn,"precision":round(precision,3),"recall":round(recall,3),"fnr":round(fnr,3),"fpr":round(fpr,3)}

def pctiles(values):
    if not values: return {"p50":0,"p90":0,"p99":0}
    vs = sorted(values)
    def p(pct): return vs[int((len(vs)-1)*pct)]
    return {"p50":p(0.50),"p90":p(0.90),"p99":p(0.99)}

def histogram(values, out_png, title):
    if not values: values=[0]
    plt.figure()
    plt.hist(values, bins=min(10, max(3, len(set(values)))))
    plt.title(title)
    plt.xlabel("Latency (ms)")
    plt.ylabel("Count")
    plt.tight_layout()
    plt.savefig(out_png)
    plt.close()

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

def main():
    cfg = load_cfg()
    rows = load_rows()

    base_preds, base_lat = run_guard(rows, predict_baseline, "baseline")
    cand_preds, cand_lat = run_guard(rows, predict_candidate, "candidate")

    base_cm = confusion(rows, base_preds)
    cand_cm = confusion(rows, cand_preds)

    base_lat_pct = pctiles(base_lat)
    cand_lat_pct = pctiles(cand_lat)

    # charts
    base_png = ASSETS / "latency_baseline.png"
    cand_png = ASSETS / "latency_candidate.png"
    histogram(base_lat, base_png, "Baseline latency")
    histogram(cand_lat, cand_png, "Candidate latency")

    # failure exports (combine both for the table view)
    b_fn_csv, b_fp_csv, b_fn, b_fp = export_failures(rows, base_preds, "baseline")
    c_fn_csv, c_fp_csv, c_fn, c_fp = export_failures(rows, cand_preds, "candidate")

    failures = []
    for r in b_fn: failures.append({"id":r["id"],"fail_type":"FN","model":"Baseline", **r})
    for r in b_fp: failures.append({"id":r["id"],"fail_type":"FP","model":"Baseline", **r})
    for r in c_fn: failures.append({"id":r["id"],"fail_type":"FN","model":"Candidate", **r})
    for r in c_fp: failures.append({"id":r["id"],"fail_type":"FP","model":"Candidate", **r})

    env = Environment(loader=FileSystemLoader(TPL_DIR))
    tpl = env.get_template("report.html")
    html = tpl.render(
        run_title="Baseline vs Candidate",
        dataset_path=str(DATA),
        total_samples=len(rows),
        generated_at=datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        policy_version=cfg.get("policy_version","n/a"),
        engines={"baseline":cfg["engines"]["baseline"]["name"], "candidate":cfg["engines"]["candidate"]["name"]},
        metrics={
          "Baseline":{"precision":base_cm["precision"],"recall":base_cm["recall"],"fnr":base_cm["fnr"],"fpr":base_cm["fpr"],"latency":base_lat_pct},
          "Candidate":{"precision":cand_cm["precision"],"recall":cand_cm["recall"],"fnr":cand_cm["fnr"],"fpr":cand_cm["fpr"],"latency":cand_lat_pct}
        },
        matrices={"Baseline":base_cm, "Candidate":cand_cm},
        latency_imgs={"baseline":str(base_png.relative_to(ROOT)), "candidate":str(cand_png.relative_to(ROOT))},
        downloads={"fn_csv":str((OUT_DIR/"candidate_fn.csv").relative_to(ROOT)), "fp_csv":str((OUT_DIR/"candidate_fp.csv").relative_to(ROOT))},
        failures=failures
    )
    out_file = OUT_DIR / "index.html"
    with open(out_file,"w",encoding="utf-8") as f:
        f.write(html)
    print(f"Report written to {out_file}")

if __name__ == "__main__":
    main()
