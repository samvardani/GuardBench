import csv
from guards.baseline import predict as predict_baseline
from guards.candidate import predict as predict_candidate
from utils.io_utils import load_config, resolve_dataset_path
from evaluation import evaluate

def load_cfg_and_data():
    cfg = load_config()
    data_path = resolve_dataset_path(cfg)
    rows = []
    with open(data_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return cfg, rows

def main():
    cfg, rows = load_cfg_and_data()
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
    summary = evaluate(engine, rows, policy=cfg)

    for key in ("baseline", "candidate"):
        guard = summary["guards"][key]
        strict_view = guard["modes"]["strict"]
        cm = strict_view["confusion"]
        lat = guard["latency"]
        print(f"=== {guard['name']} ({key}) ===")
        print(
            {
                "tp": cm["tp"],
                "fp": cm["fp"],
                "tn": cm["tn"],
                "fn": cm["fn"],
                "precision": cm["precision"],
                "recall": cm["recall"],
                "fnr": cm["fnr"],
                "fpr": cm["fpr"],
                "latency_ms": lat,
            }
        )

if __name__ == "__main__":
    main()
