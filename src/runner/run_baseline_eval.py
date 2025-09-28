import csv, pathlib, yaml
from collections import Counter
from statistics import quantiles
from src.guards.baseline import predict

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

def compute_metrics(rows):
    """
    label: 'benign' | 'borderline' | 'unsafe'
    For metrics, treat 'benign' as negative, everything else as positive (unsafe).
    """
    y_true, y_pred, latencies = [], [], []
    per_cat = Counter()
    cm = Counter()  # (tp, fp, tn, fn)

    for r in rows:
        label = r["label"].strip().lower()
        gt_is_positive = (label != "benign")

        out = predict(r["text"])
        pred_is_positive = (out["prediction"] == "flag")
        latencies.append(out["latency_ms"])

        # overall confusion
        if gt_is_positive and pred_is_positive: cm["tp"] += 1
        elif (not gt_is_positive) and pred_is_positive: cm["fp"] += 1
        elif (not gt_is_positive) and (not pred_is_positive): cm["tn"] += 1
        elif gt_is_positive and (not pred_is_positive): cm["fn"] += 1

        # quick per-category counts (by r['category'])
        per_cat[(r["category"], "gt_pos")] += int(gt_is_positive)
        per_cat[(r["category"], "pred_pos")] += int(pred_is_positive)
        per_cat[(r["category"], "fn")] += int(gt_is_positive and (not pred_is_positive))
        per_cat[(r["category"], "fp")] += int((not gt_is_positive) and pred_is_positive)

    tp, fp, tn, fn = cm["tp"], cm["fp"], cm["tn"], cm["fn"]
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall    = tp / (tp + fn) if (tp + fn) else 0.0
    fnr       = fn / (tp + fn) if (tp + fn) else 0.0
    fpr       = fp / (fp + tn) if (fp + tn) else 0.0

    p50, p90, p99 = _latency_stats(latencies)

    return {
        "counts": {"tp": tp, "fp": fp, "tn": tn, "fn": fn},
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "fnr": round(fnr, 3),
        "fpr": round(fpr, 3),
        "latency_ms": {"p50": p50, "p90": p90, "p99": p99},
        "per_category": per_cat
    }

def _latency_stats(latencies):
    if not latencies:
        return 0,0,0
    lat_sorted = sorted(latencies)
    # simple percentiles; for tiny sets, approximate
    p50 = lat_sorted[int(0.50*(len(lat_sorted)-1))]
    p90 = lat_sorted[int(0.90*(len(lat_sorted)-1))]
    p99 = lat_sorted[int(0.99*(len(lat_sorted)-1))]
    return p50, p90, p99

def main():
    cfg, rows = load_cfg_and_data()
    m = compute_metrics(rows)
    c = m["counts"]
    print("=== Baseline Evaluation ===")
    print(f"TP={c['tp']} FP={c['fp']} TN={c['tn']} FN={c['fn']}")
    print(f"Precision={m['precision']}  Recall={m['recall']}  FNR={m['fnr']}  FPR={m['fpr']}")
    print(f"Latency p50/p90/p99 (ms): {m['latency_ms']['p50']}/{m['latency_ms']['p90']}/{m['latency_ms']['p99']}")
    print("\nPer-category quick look (pred_pos / fn / fp):")
    # Summarize per category
    cats = sorted({k[0] for k in m["per_category"].keys()})
    for cat in cats:
        pred_pos = m["per_category"][(cat, "pred_pos")]
        fn = m["per_category"][(cat, "fn")]
        fp = m["per_category"][(cat, "fp")]
        print(f"  - {cat}: pred_pos={pred_pos}, fn={fn}, fp={fp}")

if __name__ == "__main__":
    main()
