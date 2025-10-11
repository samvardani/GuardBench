import csv
import sys
import yaml
import pathlib

def main():
    root = pathlib.Path(__file__).resolve().parents[2]
    cfg_path = root / "config.yaml"
    data_path = root / "dataset" / "sample.csv"

    with open(cfg_path, "r") as f:
        cfg = yaml.safe_load(f)

    print("Loaded config:")
    print(f"  policy_version: {cfg.get('policy_version')}")
    print(f"  dataset_path:   {cfg.get('dataset_path')}")

    rows = 0
    with open(data_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for _ in reader:
            rows += 1

    print(f"CSV looks good. Rows: {rows}")
    print("Hello — skeleton ready.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("Error:", e)
        sys.exit(1)
