import csv, pathlib, yaml
from collections import Counter
from guards.baseline import predict as predict_baseline
from guards.candidate import predict as predict_candidate

def load_cfg_and_data():
    root = pathlib.Path(__file__).resolve().parents[2]
    with open(root / "config.yaml", "r") as f:
        cfg = yaml.safe_load(f)
    data_path = root / "dataset" / "sample.csv"
    rows = []
    with open(data_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return cfg, rows

def metrics_for(preds, rows):
    cm = Counter(); latencies = []
    for pred, r in zip(preds, rows):
        gt_pos = (r["label"].strip().lower() != "benign")
        pr_pos = (pred["prediction"] == "flag")
        latencies.append(pred.get("latency_ms", 0))
        if gt_pos and pr_pos: cm["tp"] += 1
        elif (not gt_pos) and pr_pos: cm["fp"] += 1
        elif (not gt_pos) and (not pr_pos): cm["tn"] += 1
        elif gt_pos and (not pr_pos): cm["fn"] += 1
    tp, fp, tn, fn = cm["tp"], cm["fp"], cm["tn"], cm["fn"]
    precision = tp/(tp+fp) if (tp+fp) else 0.0
    recall    = tp/(tp+fn) if (tp+fn) else 0.0
    fnr       = fn/(tp+fn) if (tp+fn) else 0.0
    fpr       = fp/(fp+tn) if (fp+tn) else 0.0
    lat_sorted = sorted(latencies) or [0]
    p50 = lat_sorted[int(0.50*(len(lat_sorted)-1))]
    p90 = lat_sorted[int(0.90*(len(lat_sorted)-1))]
    p99 = lat_sorted[int(0.99*(len(lat_sorted)-1))]
    return {
        "tp":tp,"fp":fp,"tn":tn,"fn":fn,
        "precision":round(precision,3),
        "recall":round(recall,3),
        "fnr":round(fnr,3),
        "fpr":round(fpr,3),
        "latency_ms":{"p50":p50,"p90":p90,"p99":p99}
    }

def main():
    cfg, rows = load_cfg_and_data()
    base_preds = [predict_baseline(r["text"]) for r in rows]
    cand_preds = [predict_candidate(r["text"]) for r in rows]
    bm = metrics_for(base_preds, rows)
    cm = metrics_for(cand_preds, rows)
    print("=== Baseline ==="); print(bm)
    print("=== Candidate ==="); print(cm)

if __name__ == "__main__":
    main()
