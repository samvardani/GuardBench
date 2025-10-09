import csv, json
from pathlib import Path
from collections import defaultdict
from utils.io_utils import load_config, resolve_dataset_path
from guards.candidate import predict as predict_candidate

TARGET_FPR = 0.01  # change via --fpr later if you want

def is_pos(label, mode="strict"):
    l = (label or "").strip().lower()
    return (l == "unsafe") if mode == "lenient" else (l != "benign")

def pct(a,b): return round(a/b,3) if b else 0.0

def load_rows(p: Path):
    with open(p, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def sweep(rows, mode="strict", fpr_target=TARGET_FPR):
    # Collect scores by slice
    S = defaultdict(lambda: {"pos":[], "neg":[]})
    for r in rows:
        out = predict_candidate(r["text"], language=r.get("language"), category=r.get("category"))
        score = float(out.get("score", 1.0))  # candidate returns 0..1
        key = (r.get("category","?"), r.get("language","?"))
        (S[key]["pos"] if is_pos(r["label"], mode) else S[key]["neg"]).append(score)

    results = {}
    for key, bag in S.items():
        pos = sorted(bag["pos"], reverse=True)
        neg = sorted(bag["neg"], reverse=True)
        if not pos and not neg:
            continue

        # Candidate thresholds = all unique scores (plus 1.0)
        threshes = sorted({*pos, *neg, 1.0}, reverse=True)

        best = {"thr":1.0, "recall":0.0, "fpr":0.0, "tp":0, "fp":0, "tn":0, "fn":0, "n":len(pos)+len(neg)}
        for t in threshes:
            tp = sum(s >= t for s in pos)
            fn = len(pos) - tp
            fp = sum(s >= t for s in neg)
            tn = len(neg) - fp
            recall = pct(tp, tp+fn)
            fpr = pct(fp, fp+tn)
            if fpr <= fpr_target and recall >= best["recall"]:
                best = {"thr":round(float(t),3), "recall":recall, "fpr":fpr, "tp":tp,"fp":fp,"tn":tn,"fn":fn,"n":len(pos)+len(neg)}

        results[key] = best
    return results

def main():
    cfg = load_config()
    ds = resolve_dataset_path(cfg)
    rows = load_rows(ds)

    tuned = sweep(rows, mode="strict", fpr_target=TARGET_FPR)

    # Write back to config.yaml format (category -> language -> threshold)
    out = {}
    for (cat, lang), b in tuned.items():
        out.setdefault(cat or "unknown", {})[lang or "unknown"] = b["thr"]

    # Save a YAML-ish block the simplest way to avoid pulling PyYAML here
    lines = ["slice_thresholds:"]
    for cat in sorted(out):
        lines.append(f"  {cat}:")
        for lang in sorted(out[cat]):
            lines.append(f"    {lang}: {out[cat][lang]}")
    Path("tuned_thresholds.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")

    Path("report/auto_tune.json").write_text(
        json.dumps({f"{k[0]}|{k[1]}": v for k,v in tuned.items()}, indent=2),
        encoding="utf-8"
    )

    print("Wrote tuned per-slice thresholds to tuned_thresholds.yaml")
    print("Detailed metrics: report/auto_tune.json")

if __name__ == "__main__":
    main()
