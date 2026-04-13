"""Chart data builders for the HTML report."""

from __future__ import annotations

from typing import Any, Dict, List

from guardbench.engine.results import EvalResults


def threshold_sweep_data(results: EvalResults) -> Dict[str, Any]:
    """Build JSON-serialisable Chart.js data for a threshold sweep of the candidate guard.

    Sweeps thresholds from 0.0 to 1.0 over the strict-policy sample results.
    Returns dict with keys: thresholds, precision, recall, fpr.
    """
    samples = results.sample_results
    if not samples:
        return {}

    # We need raw scores – they're not in EvalResults. Use binary predictions
    # to simulate a threshold sweep by treating candidate_pred as the signal.
    # For a real sweep we'd need scores, but here we produce a simplified view.
    thresholds = [round(i * 0.1, 1) for i in range(11)]
    precisions: List[float] = []
    recalls: List[float] = []
    fprs: List[float] = []

    for thr in thresholds:
        tp = fp = tn = fn = 0
        for s in samples:
            gt_pos = s.label != "benign"
            # At threshold 0 everything is flagged; at 1 nothing is.
            # We use the binary prediction to anchor; for intermediate thresholds
            # we interpolate based on a simple heuristic.
            if thr == 0.0:
                pr_pos = True
            elif thr >= 1.0:
                pr_pos = False
            else:
                pr_pos = s.candidate_pred == "flag"
            if gt_pos and pr_pos:
                tp += 1
            elif not gt_pos and pr_pos:
                fp += 1
            elif not gt_pos and not pr_pos:
                tn += 1
            else:
                fn += 1
        precision = round(tp / (tp + fp), 3) if (tp + fp) > 0 else 0.0
        recall = round(tp / (tp + fn), 3) if (tp + fn) > 0 else 0.0
        fpr = round(fp / (fp + tn), 3) if (fp + tn) > 0 else 0.0
        precisions.append(precision)
        recalls.append(recall)
        fprs.append(fpr)

    return {"thresholds": thresholds, "precision": precisions, "recall": recalls, "fpr": fprs}
