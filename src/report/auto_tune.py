import argparse
import csv
import json
from pathlib import Path
from collections import defaultdict
from utils.io_utils import load_config, resolve_dataset_path
from utils.text_norm import normalize
from guards import candidate as C

# Reuse Candidate’s patterns/normalize so tuning matches runtime
PATTERNS = C.PATTERNS
WHITELIST = getattr(C, "WHITELIST", [])
SELF_HARM_SUPPORT = getattr(C, "SELF_HARM_SUPPORT", [])

def matches(text: str):
    t = normalize(text)
    hits = []
    for cat, pats in PATTERNS.items():
        import re
        if any(re.search(p, t) for p in pats):
            hits.append(cat)
    # whitelist only matters when hits == 0
    whitelisted = False
    if not hits:
        import re
        whitelisted = any(re.search(w, t) for w in WHITELIST)
    return hits, whitelisted

def load_rows(dataset_path: Path):
    with open(dataset_path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def grid():
    # thresholds operate on raw len(hits); typical values 0..2
    # this grid gives you useful breakpoints
    xs = [round(x,2) for x in [0.8, 0.85, 0.9, 0.95, 1.0, 1.05, 1.1, 1.2]]
    return xs

def eval_slice(rows, per_sample_hits, category_key, lang, thr, benign_key="benign"):
    TP=FP=TN=FN=0
    for r, hits in zip(rows, per_sample_hits):
        label = r["label"].strip().lower()
        sample_lang = r.get("language")
        gt_pos = (label != benign_key)
        # treat this slice as positives where GT category matches and language matches
        in_slice_pos = (r.get("category")==category_key and sample_lang==lang and gt_pos)
        # For negatives in this slice: benign rows (same language) that would be flagged due to this category
        in_slice_neg = (label==benign_key and sample_lang==lang)

        # candidate flags if ANY matched category has raw_score >= thr
        raw_score = len(hits)
        would_flag_due_to_cat = (category_key in hits or (category_key=="violence" and "fa_violence" in hits)) and (raw_score >= thr)

        if in_slice_pos:
            if would_flag_due_to_cat: TP+=1
            else: FN+=1
        elif in_slice_neg:
            if would_flag_due_to_cat: FP+=1
            else: TN+=1
        else:
            # ignore rows outside the slice
            pass

    def pct(a,b): return round(a/b,3) if b else 0.0
    return {
        "tp":TP,"fp":FP,"tn":TN,"fn":FN,
        "recall": pct(TP, TP+FN),
        "fpr": pct(FP, FP+TN),
        "n_pos": TP+FN, "n_neg": FP+TN
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target_fpr", type=float, default=0.01, help="max allowed FPR per slice")
    ap.add_argument("--update_config", action="store_true", help="write best thresholds into config.yaml slice_thresholds")
    args = ap.parse_args()

    cfg = load_config()
    ds = resolve_dataset_path(cfg)
    rows = load_rows(ds)

    # precompute hits/whitelist per sample
    per_sample_hits=[]
    for r in rows:
        hits, whitelisted = matches(r["text"])
        # whitelist doesn’t change tuning if hits>0; if hits==0 it will never flag regardless of threshold
        # so we store only hits
        per_sample_hits.append(hits)

    # discover slices present in data
    present = defaultdict(set)  # category -> {langs}
    for r in rows:
        present[r["category"]].add(r.get("language"))

    # tune
    best = defaultdict(dict)  # category -> lang -> {thr, recall, fpr}
    for cat, langs in present.items():
        for lang in sorted(langs):
            if cat.lower()=="benign":  # skip benign as a GT category
                continue
            # skip tiny slices (no signal)
            npos = sum(1 for r in rows if r.get("category")==cat and r.get("language")==lang and r["label"].lower()!="benign")
            if npos == 0:
                continue
            cand = []
            for thr in grid():
                m = eval_slice(rows, per_sample_hits, cat, lang, thr)
                cand.append((thr, m["recall"], m["fpr"], m["n_pos"], m["n_neg"]))
            # choose max recall with fpr <= target; tie-breaker: higher thr (more conservative)
            feasible = [c for c in cand if c[2] <= args.target_fpr]
            if not feasible:
                continue
            feasible.sort(key=lambda x: (x[1], x[0]))  # recall asc, thr asc
            thr, rec, fpr, npos, nneg = feasible[-1]
            best[cat][lang] = {"thr":thr,"recall":rec,"fpr":fpr,"npos":npos,"nneg":nneg}

    # print summary + YAML snippet
    print("\nSuggested per-slice thresholds (target FPR <= {:.3f}):".format(args.target_fpr))
    for cat in sorted(best.keys()):
        for lang, vals in best[cat].items():
            print(f"  {cat}/{lang}: thr={vals['thr']}  recall={vals['recall']}  fpr={vals['fpr']}  npos={vals['npos']} nneg={vals['nneg']}")

    # YAML snippet (write both 'violence' and 'fa_violence' for fa)
    print("\nYAML snippet (add under slice_thresholds:)")
    snippet = defaultdict(dict)
    for cat, langs in best.items():
        for lang, vals in langs.items():
            snippet[cat][lang] = vals["thr"]
            if cat=="violence" and lang=="fa":
                snippet["fa_violence"][lang] = vals["thr"]
    print(json.dumps(snippet, indent=2))

    if args.update_config:
        p = Path("config.yaml")
        s = p.read_text()
        # naive merge: append/overwrite a block at end
        s += "\n# --- auto-tuned slice thresholds ---\nslice_thresholds:\n"
        for cat in sorted(snippet.keys()):
            s += f"  {cat}:\n"
            for lang, thr in snippet[cat].items():
                s += f"    {lang}: {thr}\n"
        p.write_text(s)
        print("\nconfig.yaml updated with auto-tuned slice_thresholds.")
