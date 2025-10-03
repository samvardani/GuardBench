import csv, pathlib, yaml
from src.guards.baseline import predict
from src.evaluation import evaluate

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

def summarize_baseline(cfg, rows):
    engine = {
        "guards": {
            "baseline": {
                "name": cfg.get("engines", {}).get("baseline", {}).get("name", "baseline"),
                "predict": predict,
            }
        }
    }
    summary = evaluate(engine, rows, policy=cfg)
    guard = summary["guards"]["baseline"]
    strict_view = guard["modes"]["strict"]
    cm = strict_view["confusion"]
    lat = guard["latency"]
    return {
        "counts": cm,
        "latency": lat,
        "slices": strict_view["slices"],
    }

def main():
    cfg, rows = load_cfg_and_data()
    m = summarize_baseline(cfg, rows)
    c = m["counts"]
    print("=== Baseline Evaluation ===")
    print(f"TP={c['tp']} FP={c['fp']} TN={c['tn']} FN={c['fn']}")
    print(f"Precision={c['precision']}  Recall={c['recall']}  FNR={c['fnr']}  FPR={c['fpr']}")
    print(f"Latency p50/p90/p99 (ms): {m['latency']['p50']}/{m['latency']['p90']}/{m['latency']['p99']}")
    print("\nPer-category quick look (n / fn / fp / risk):")
    for slice_row in m["slices"]:
        cat = slice_row.get("category") or "unknown"
        lang = slice_row.get("language") or "?"
        risk = slice_row.get("risk_score", 0.0)
        print(
            "  - "
            f"{cat}/{lang}: n={slice_row['n']} fn={slice_row['fn']} fp={slice_row['fp']} risk={risk}"
        )

if __name__ == "__main__":
    main()
