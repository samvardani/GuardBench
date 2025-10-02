from collections import defaultdict


def _pred_to_bool(p):
    """
    Return True iff p indicates a 'flag'. Accepts dict/int/bool/str.
    """
    if isinstance(p, dict):
        if "prediction" in p:
            v = p["prediction"]
            return v.lower() == "flag" if isinstance(v, str) else bool(v)
        if "pred" in p:
            v = p["pred"]
            return v.lower() == "flag" if isinstance(v, str) else bool(v)
        if ("score" in p) and ("threshold" in p):
            return p["score"] >= p["threshold"]
        return bool(p)
    if isinstance(p, str):
        return p.strip().lower() in ("flag","blocked","deny","unsafe","violation","1","true","yes","y")
    return bool(p)

def _label_to_bool(x):
    """
    Return True iff label is harmful. Accepts 0/1, bool, or strings.
    """
    if isinstance(x, bool):
        return x
    if isinstance(x, (int, float)):
        return int(x) != 0
    if isinstance(x, str):
        t = x.strip().lower()
        harmful = {"1","true","yes","y","harmful","unsafe","violation","bad","toxic","deny"}
        safe    = {"0","false","no","n","safe","benign","ok","harmless","good","allow"}
        if t in harmful: return True
        if t in safe:    return False
    return False

def cluster_failures(rows, preds):
    """
    Group FNs/FPs by (category, language, attack_type) and return top 5 clusters.
    """
    clusters = defaultdict(list)
    for r, p in zip(rows, preds):
        label = r["label"].strip().lower()
        gt_pos = (label != "benign")
        pr_pos = (_pred_to_bool(p))

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
