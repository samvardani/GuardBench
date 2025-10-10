"""Report builder from evaluation results."""

from __future__ import annotations

import datetime as dt
import hashlib
import logging
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class ReportBuilder:
    """Builds export reports from evaluation data."""
    
    def __init__(self, evaluation_data: Dict[str, Any], config: Dict[str, Any]):
        """Initialize report builder.
        
        Args:
            evaluation_data: Results from evaluation.evaluate()
            config: Configuration dictionary
        """
        self.evaluation_data = evaluation_data
        self.config = config
    
    def build_metadata(self) -> Dict[str, Any]:
        """Build metadata section.
        
        Returns:
            Metadata dictionary
        """
        # Generate report ID from timestamp
        now = dt.datetime.utcnow()
        report_id = now.strftime("%Y%m%d_%H%M%S")
        
        # Get policy info
        try:
            from seval.settings import POLICY_VERSION, POLICY_CHECKSUM
        except:
            POLICY_VERSION = self.config.get("policy_version", "unknown")
            POLICY_CHECKSUM = "unknown"
        
        # Get git commit
        try:
            from utils.io_utils import git_commit
            git_hash = git_commit()
        except:
            git_hash = "unknown"
        
        # Get dataset info
        dataset_path = self.config.get("dataset_path", "unknown")
        
        # Count samples from evaluation
        total_samples = 0
        if "guards" in self.evaluation_data:
            for guard_data in self.evaluation_data["guards"].values():
                if "predictions" in guard_data:
                    total_samples = len(guard_data["predictions"])
                    break
        
        return {
            "report_id": report_id,
            "generated_at": now.isoformat() + "Z",
            "policy_version": POLICY_VERSION,
            "policy_checksum": POLICY_CHECKSUM,
            "git_commit": git_hash,
            "dataset_path": dataset_path,
            "total_samples": total_samples,
        }
    
    def build_kpis(self, guard_name: str = "candidate") -> Dict[str, Any]:
        """Build KPIs from guard evaluation.
        
        Args:
            guard_name: Guard to extract KPIs from
            
        Returns:
            KPIs dictionary
        """
        guards = self.evaluation_data.get("guards", {})
        
        if guard_name not in guards:
            # Return defaults
            return {
                "precision": 0.0,
                "recall": 0.0,
                "fnr": 0.0,
                "fpr": 0.0,
                "latency_p50_ms": 0.0,
                "latency_p95_ms": 0.0,
                "latency_p99_ms": 0.0,
                "blocked_rate": 0.0,
            }
        
        guard_data = guards[guard_name]
        modes = guard_data.get("modes", {})
        
        # Use strict mode by default
        mode_data = modes.get("strict", modes.get(list(modes.keys())[0])) if modes else {}
        
        confusion = mode_data.get("confusion", {})
        latency = guard_data.get("latency", {})
        
        # Calculate blocked rate
        predictions = guard_data.get("predictions", [])
        blocked_count = sum(1 for p in predictions if p)
        blocked_rate = blocked_count / len(predictions) if predictions else 0.0
        
        return {
            "precision": round(confusion.get("precision", 0.0), 3),
            "recall": round(confusion.get("recall", 0.0), 3),
            "fnr": round(confusion.get("fnr", 0.0), 3),
            "fpr": round(confusion.get("fpr", 0.0), 3),
            "latency_p50_ms": latency.get("p50", 0.0),
            "latency_p95_ms": latency.get("p95", 0.0),
            "latency_p99_ms": latency.get("p99", 0.0),
            "blocked_rate": round(blocked_rate, 3),
        }
    
    def build_improvement_plan(self, guard_name: str = "candidate") -> List[Dict[str, Any]]:
        """Build improvement plan from evaluation results.
        
        Args:
            guard_name: Guard to analyze
            
        Returns:
            List of improvement items
        """
        improvements = []
        
        guards = self.evaluation_data.get("guards", {})
        if guard_name not in guards:
            return improvements
        
        guard_data = guards[guard_name]
        modes = guard_data.get("modes", {})
        mode_data = modes.get("strict", {})
        
        confusion = mode_data.get("confusion", {})
        slices = mode_data.get("slices", [])
        
        # Check FNR
        fnr = confusion.get("fnr", 0.0)
        if fnr > 0.1:
            improvements.append({
                "category": "recall",
                "issue": f"False Negative Rate is {fnr:.1%}, missing harmful content",
                "recommendation": "Review false negatives and add rules to catch missed patterns",
                "priority": "high",
                "source": "analysis"
            })
        
        # Check FPR
        fpr = confusion.get("fpr", 0.0)
        if fpr > 0.05:
            improvements.append({
                "category": "precision",
                "issue": f"False Positive Rate is {fpr:.1%}, blocking benign content",
                "recommendation": "Tune thresholds or add safe context patterns",
                "priority": "medium",
                "source": "analysis"
            })
        
        # Check latency
        latency = guard_data.get("latency", {})
        p95 = latency.get("p95", 0.0)
        if p95 > 100:
            improvements.append({
                "category": "performance",
                "issue": f"P95 latency is {p95:.0f}ms",
                "recommendation": "Optimize regex patterns or increase timeout thresholds",
                "priority": "medium",
                "source": "analysis"
            })
        
        # Check per-slice issues
        for slice_data in slices:
            slice_fnr = slice_data.get("fnr", 0.0)
            if slice_fnr > 0.15 and slice_data.get("n", 0) >= 10:
                cat = slice_data.get("category", "unknown")
                lang = slice_data.get("language", "unknown")
                improvements.append({
                    "category": f"{cat}/{lang}",
                    "issue": f"High FNR ({slice_fnr:.1%}) for {cat}/{lang}",
                    "recommendation": f"Add language-specific rules for {lang} in {cat} category",
                    "priority": "high",
                    "source": "analysis"
                })
        
        return improvements
    
    def build_risks(self, guard_name: str = "candidate") -> List[Dict[str, Any]]:
        """Build risk assessment.
        
        Args:
            guard_name: Guard to analyze
            
        Returns:
            List of risks
        """
        risks = []
        
        guards = self.evaluation_data.get("guards", {})
        if guard_name not in guards:
            return risks
        
        guard_data = guards[guard_name]
        modes = guard_data.get("modes", {})
        mode_data = modes.get("strict", {})
        
        confusion = mode_data.get("confusion", {})
        
        # High FNR risk
        fnr = confusion.get("fnr", 0.0)
        if fnr > 0.15:
            risks.append({
                "category": "safety",
                "risk_level": "high",
                "description": f"False Negative Rate of {fnr:.1%} means harmful content may bypass filtering",
                "mitigation": "Increase rule coverage, lower thresholds, add multilingual support"
            })
        elif fnr > 0.05:
            risks.append({
                "category": "safety",
                "risk_level": "medium",
                "description": f"FNR of {fnr:.1%} indicates some harmful content may be missed",
                "mitigation": "Monitor false negatives and update rules incrementally"
            })
        
        # High FPR risk
        fpr = confusion.get("fpr", 0.0)
        if fpr > 0.1:
            risks.append({
                "category": "user_experience",
                "risk_level": "medium",
                "description": f"False Positive Rate of {fpr:.1%} may frustrate legitimate users",
                "mitigation": "Add safe context patterns, tune thresholds higher"
            })
        
        # Latency risk
        latency = guard_data.get("latency", {})
        p99 = latency.get("p99", 0.0)
        if p99 > 500:
            risks.append({
                "category": "performance",
                "risk_level": "high",
                "description": f"P99 latency of {p99:.0f}ms may cause timeouts",
                "mitigation": "Optimize regex patterns, increase timeout, scale horizontally"
            })
        
        return risks
    
    def build_references(self) -> List[Dict[str, Any]]:
        """Build references section.
        
        Returns:
            List of references
        """
        return [
            {
                "title": "Policy Configuration",
                "url": "/policy/policy.yaml",
                "type": "internal"
            },
            {
                "title": "Evaluation Engine",
                "url": "/src/evaluation/engine.py",
                "type": "internal"
            },
            {
                "title": "Dataset",
                "url": self.config.get("dataset_path", "/dataset/sample.csv"),
                "type": "internal"
            },
            {
                "title": "Prometheus Metrics",
                "url": "/metrics",
                "type": "internal"
            },
        ]
    
    def build_market_data(self) -> Dict[str, Any]:
        """Build market data section (external data marked as TBD).
        
        Returns:
            Market data dictionary
        """
        return {
            "industry_benchmarks": {
                "value": "TBD",
                "source": "external",
                "note": "External benchmarking data not available"
            },
            "competitor_analysis": {
                "value": "TBD",
                "source": "external",
                "note": "Requires market research"
            },
            "market_size": {
                "value": "TBD",
                "source": "external",
                "note": "TAM/SAM data from market reports"
            }
        }
    
    def build_report(self, guard_name: str = "candidate") -> Dict[str, Any]:
        """Build complete report.
        
        Args:
            guard_name: Guard to report on
            
        Returns:
            Complete report dictionary
        """
        return {
            "metadata": self.build_metadata(),
            "kpis": self.build_kpis(guard_name),
            "improvement_plan": self.build_improvement_plan(guard_name),
            "risks": self.build_risks(guard_name),
            "references": self.build_references(),
            "market_data": self.build_market_data(),
        }


def sanitize_for_export(data: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize data to ensure no secrets leak.
    
    Args:
        data: Report data
        
    Returns:
        Sanitized data
    """
    # Remove any sensitive fields
    sensitive_keys = [
        "api_key",
        "secret",
        "password",
        "token",
        "credential",
        "private_key",
    ]
    
    def _recurse_sanitize(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {
                k: "[REDACTED]" if any(s in k.lower() for s in sensitive_keys) else _recurse_sanitize(v)
                for k, v in obj.items()
            }
        elif isinstance(obj, list):
            return [_recurse_sanitize(item) for item in obj]
        else:
            return obj
    
    return _recurse_sanitize(data)

