"""HTML report generator for EvalResults."""

from __future__ import annotations

import datetime
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from jinja2 import Environment, PackageLoader

from guardbench import __version__
from guardbench.engine.metrics import MetricsBundle
from guardbench.engine.results import EvalResults
from guardbench.report.charts import threshold_sweep_data

logger = logging.getLogger(__name__)

_DEFAULT_GATE = {
    "global_thresholds": {"min_recall": 0.55, "max_fpr": 0.05}
}


def _slice_row(key: tuple, bundle: MetricsBundle, gate_config: Optional[dict]) -> dict:
    """Convert a slice key + MetricsBundle into a template-friendly dict."""
    cat = key[0] if len(key) > 0 else "?"
    lang = key[1] if len(key) > 1 else "?"
    n = bundle.tp + bundle.fp + bundle.tn + bundle.fn

    # Colour coding based on gate thresholds
    thresholds = {}
    if gate_config:
        thresholds = gate_config.get("global_thresholds", {})
    min_recall = thresholds.get("min_recall", 0.0)
    max_fpr = thresholds.get("max_fpr", 1.0)

    recall_class = ""
    if gate_config:
        recall_class = "pass-cell" if bundle.recall >= min_recall else "fail-cell"
    fpr_class = ""
    if gate_config:
        fpr_class = "pass-cell" if bundle.fpr <= max_fpr else "fail-cell"

    return {
        "category": cat,
        "language": lang,
        "n": n,
        "recall": bundle.recall,
        "recall_lo": bundle.recall_lo,
        "recall_hi": bundle.recall_hi,
        "fpr": bundle.fpr,
        "fpr_lo": bundle.fpr_lo,
        "fpr_hi": bundle.fpr_hi,
        "fnr": bundle.fnr,
        "recall_class": recall_class,
        "fpr_class": fpr_class,
    }


class ReportGenerator:
    """Renders an EvalResults object to an interactive HTML report."""

    def __init__(self, results: EvalResults, gate_config: Optional[dict] = None) -> None:
        """Initialise with evaluation results and optional gate config for colour coding."""
        self.results = results
        self.gate_config = gate_config

    def build(self, output_path: Optional[Path] = None) -> Path:
        """Render the HTML report and write it to output_path.

        Returns the path of the written file.
        """
        if output_path is None:
            output_path = Path("report") / "index.html"

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        env = Environment(loader=PackageLoader("guardbench.report", "templates"))
        template = env.get_template("report.html")

        results = self.results
        gate = self.gate_config

        # Extract metrics bundles
        strict_base = results.baseline_metrics.get("strict", MetricsBundle())
        strict_cand = results.candidate_metrics.get("strict", MetricsBundle())
        lenient_base = results.baseline_metrics.get("lenient", MetricsBundle())
        lenient_cand = results.candidate_metrics.get("lenient", MetricsBundle())

        # Slice rows sorted by category, language
        def _slice_rows(slices_dict: Dict) -> List[dict]:
            rows = []
            for key in sorted(slices_dict.keys(), key=lambda k: (str(k[0]), str(k[1]) if len(k) > 1 else "")):
                rows.append(_slice_row(key, slices_dict[key], gate))
            return rows

        strict_base_slices = _slice_rows(results.baseline_slices.get("strict", {}))
        strict_cand_slices = _slice_rows(results.candidate_slices.get("strict", {}))

        # Latency arrays for Chart.js
        base_latencies = [s for s in [strict_base.latency_p50, strict_base.latency_p90,
                                       strict_base.latency_p95, strict_base.latency_p99]
                          if s > 0]
        cand_latencies = [s for s in [strict_cand.latency_p50, strict_cand.latency_p90,
                                       strict_cand.latency_p95, strict_cand.latency_p99]
                          if s > 0]

        # For richer latency chart, extract from sample results if available
        if results.sample_results:
            base_lats_raw = []
            cand_lats_raw = []
            # We don't store raw latencies in sample results, use aggregate percentiles
            # Simulate a distribution from the percentiles
            base_latencies = _simulate_latencies(strict_base)
            cand_latencies = _simulate_latencies(strict_cand)

        sweep = threshold_sweep_data(results)

        has_judge = any(s.judge_verdict is not None for s in results.sample_results)

        html = template.render(
            run_id=results.run_id,
            total_samples=len(results.sample_results),
            dataset_sha=results.dataset_sha,
            git_commit=results.git_commit,
            generated_at=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            baseline_name=results.baseline_name,
            candidate_name=results.candidate_name,
            mcnemar_p=results.mcnemar_p,
            version=__version__,
            strict_base=strict_base,
            strict_cand=strict_cand,
            lenient_base=lenient_base,
            lenient_cand=lenient_cand,
            strict_base_slices=strict_base_slices,
            strict_cand_slices=strict_cand_slices,
            sample_results=results.sample_results[:200],  # cap at 200 for performance
            has_judge=has_judge,
            base_latencies_json=json.dumps(base_latencies),
            cand_latencies_json=json.dumps(cand_latencies),
            sweep_data=bool(sweep),
            sweep_data_json=json.dumps(sweep),
        )

        output_path.write_text(html, encoding="utf-8")
        logger.info("Report written to %s", output_path)
        return output_path


def _simulate_latencies(bundle: MetricsBundle) -> List[float]:
    """Create a small list of representative latency values from percentiles."""
    if bundle.latency_p50 == 0 and bundle.latency_p99 == 0:
        return []
    return [
        bundle.latency_p50,
        bundle.latency_p90,
        bundle.latency_p95,
        bundle.latency_p99,
        bundle.latency_max,
    ]
