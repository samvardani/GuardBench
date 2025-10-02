import sys, datetime
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[2]
CFG = ROOT / "config.yaml"
TUNED = ROOT / "tuned_thresholds.yaml"

def main():
    if not TUNED.exists():
        print("ERROR: tuned_thresholds.yaml not found. Run `make tune` first.")
        sys.exit(1)
    if not CFG.exists():
        print("ERROR: config.yaml not found in repo root.")
        sys.exit(1)

    tuned = yaml.safe_load(TUNED.read_text()) or {}
    if "slice_thresholds" not in tuned:
        print("ERROR: tuned_thresholds.yaml missing 'slice_thresholds' key.")
        sys.exit(1)
    cfg = yaml.safe_load(CFG.read_text()) or {}

    # backup
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    bak = CFG.with_suffix(f".yaml.bak-{ts}")
    bak.write_text(CFG.read_text(), encoding="utf-8")

    # apply
    cfg["slice_thresholds"] = tuned["slice_thresholds"]

    # write
    CFG.write_text(yaml.safe_dump(cfg, sort_keys=True, allow_unicode=True), encoding="utf-8")

    print(f"Applied tuned slice_thresholds to config.yaml")
    print(f"Backup saved → {bak}")
    print("New slice_thresholds:")
    for cat, langs in cfg["slice_thresholds"].items():
        print(f"  {cat}:")
        for lang, thr in langs.items():
            print(f"    {lang}: {thr}")

if __name__ == "__main__":
    main()
