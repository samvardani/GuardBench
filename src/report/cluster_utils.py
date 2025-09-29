from collections import defaultdict

def cluster_failures(rows, preds):
    """
    Group FNs/FPs by (category, language, attack_type) and return top 5 clusters.
    """
    clusters = defaultdict(list)
    for r, p in zip(rows, preds):
        label = r["label"].strip().lower()
        gt_pos = (label != "benign")
        pr_pos = (p.get("prediction") == "flag")

        if gt_pos and not pr_pos:
            key = ("FN", r["category"], r["language"], r["attack_type"])
            clusters[key].append(r)
        if (not gt_pos) and pr_pos:
            key = ("FP", r["category"], r["language"], r["attack_type"])
            clusters[key].append(r)

    out = []
    for (ft, cat, lang, atk), items in clusters.items():
        examples = [{"id": it["id"], "text": it["text"]} for it in items[:3]]
        out.append({
            "fail_type": ft, "category": cat, "language": lang,
            "attack_type": atk, "count": len(items), "examples": examples
        })
    # FN first (riskier), then most frequent
    out.sort(key=lambda x: (0 if x["fail_type"]=="FN" else 1, -x["count"]))
    return out[:5]
