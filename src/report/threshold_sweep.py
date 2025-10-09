import csv, pathlib, yaml
from collections import Counter
import numpy as np
import matplotlib.pyplot as plt

from guards.candidate import predict as predict_candidate

ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA = ROOT / "dataset" / "sample.csv"
OUT_DIR = ROOT / "report"
ASSETS = ROOT / "assets"
OUT_DIR.mkdir(exist_ok=True); ASSETS.mkdir(exist_ok=True)

def load_rows():
    rows=[]
    with open(DATA, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r: rows.append(row)
    return rows

def evaluate_at_threshold(rows, scores, thr):
    cm = Counter()
    for r, s in zip(rows, scores):
        gt_pos = (r["label"].strip().lower() != "benign")
        pr_pos = (s >= thr)
        if gt_pos and pr_pos: cm["tp"] += 1
        elif (not gt_pos) and pr_pos: cm["fp"] += 1
        elif (not gt_pos) and (not pr_pos): cm["tn"] += 1
        elif gt_pos and (not pr_pos): cm["fn"] += 1
    tp,fp,tn,fn = cm["tp"],cm["fp"],cm["tn"],cm["fn"]
    precision = tp/(tp+fp) if (tp+fp) else 0.0
    recall    = tp/(tp+fn) if (tp+fn) else 0.0
    fpr       = fp/(fp+tn) if (fp+tn) else 0.0
    return precision, recall, fpr

def main():
    rows = load_rows()
    # Run candidate once to get scores (independent of its internal flag)
    scores=[]
    for r in rows:
        out = predict_candidate(r["text"])
        scores.append(out.get("score", 0.0))

    thresholds = [round(x,2) for x in np.linspace(0.0,1.0,21)]
    pr_points=[]; roc_like=[]
    with open(OUT_DIR / "threshold_sweep.csv","w",newline="",encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["threshold","precision","recall","fpr"])
        for t in thresholds:
            p, r, fpr = evaluate_at_threshold(rows, scores, t)
            w.writerow([t, round(p,3), round(r,3), round(fpr,3)])
            pr_points.append((r,p))
            roc_like.append((fpr,r))

    # Plot PR curve
    plt.figure()
    xs = [r for r,p in pr_points]
    ys = [p for r,p in pr_points]
    plt.plot(xs, ys, marker="o")
    plt.xlabel("Recall")
    plt.ylabel("Precision")
    plt.title("Candidate Precision–Recall (threshold sweep)")
    plt.tight_layout()
    plt.savefig(ASSETS / "precision_recall.png")
    plt.close()

    # Plot FPR vs Recall (ROC-like)
    plt.figure()
    xs = [x for x,y in roc_like]
    ys = [y for x,y in roc_like]
    plt.plot(xs, ys, marker="o")
    plt.xlabel("FPR")
    plt.ylabel("Recall")
    plt.title("Candidate FPR vs Recall (threshold sweep)")
    plt.tight_layout()
    plt.savefig(ASSETS / "fpr_recall.png")
    plt.close()

    print("Wrote:", OUT_DIR / "threshold_sweep.csv")
    print("Saved charts:", ASSETS / "precision_recall.png", "and", ASSETS / "fpr_recall.png")

if __name__ == "__main__":
    main()
