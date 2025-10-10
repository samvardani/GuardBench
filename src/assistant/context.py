"""Context gathering for Safety Copilot assistant."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)


@dataclass
class RunContext:
    """Context from an evaluation run."""
    
    run_id: str
    metrics: Dict[str, Any] = field(default_factory=dict)
    dataset_info: Optional[Dict[str, Any]] = None
    policy_version: Optional[str] = None
    baseline_guard: Optional[str] = None
    candidate_guard: Optional[str] = None
    
    def to_summary(self) -> str:
        """Convert to human-readable summary.
        
        Returns:
            Summary text
        """
        lines = [f"Run ID: {self.run_id}"]
        
        if self.baseline_guard and self.candidate_guard:
            lines.append(f"Guards: {self.baseline_guard} (baseline) vs {self.candidate_guard} (candidate)")
        
        if self.policy_version:
            lines.append(f"Policy Version: {self.policy_version}")
        
        if self.metrics:
            lines.append("\nMetrics:")
            for model, metrics in self.metrics.items():
                lines.append(f"  {model}:")
                if "precision" in metrics:
                    lines.append(f"    Precision: {metrics['precision']:.3f}")
                if "recall" in metrics:
                    lines.append(f"    Recall: {metrics['recall']:.3f}")
                if "fnr" in metrics:
                    lines.append(f"    FNR: {metrics['fnr']:.3f}")
                if "fpr" in metrics:
                    lines.append(f"    FPR: {metrics['fpr']:.3f}")
                if "tp" in metrics:
                    lines.append(f"    TP: {metrics['tp']}, FP: {metrics.get('fp', 0)}, "
                               f"TN: {metrics.get('tn', 0)}, FN: {metrics.get('fn', 0)}")
        
        return "\n".join(lines)


@dataclass
class PolicyContext:
    """Context from safety policy."""
    
    categories: List[str] = field(default_factory=list)
    languages: List[str] = field(default_factory=list)
    rules_count: int = 0
    policy_description: Optional[str] = None
    
    def to_summary(self) -> str:
        """Convert to human-readable summary.
        
        Returns:
            Summary text
        """
        lines = []
        
        if self.policy_description:
            lines.append(f"Policy: {self.policy_description}")
        
        if self.categories:
            lines.append(f"Supported Categories: {', '.join(self.categories)}")
        
        if self.languages:
            lines.append(f"Supported Languages: {', '.join(self.languages)}")
        
        if self.rules_count:
            lines.append(f"Total Rules: {self.rules_count}")
        
        return "\n".join(lines)


def gather_run_context(run_id: str, tenant_id: str) -> Optional[RunContext]:
    """Gather context from an evaluation run.
    
    Args:
        run_id: Run ID
        tenant_id: Tenant ID
        
    Returns:
        RunContext or None if not found
    """
    try:
        from service import db
        
        # Get metrics
        metrics = db.latest_metrics(run_id)
        
        if not metrics:
            return None
        
        # Get run record
        runs = db.list_runs(tenant_id, limit=100)
        run_record = next((r for r in runs if r["run_id"] == run_id), None)
        
        if not run_record:
            return None
        
        return RunContext(
            run_id=run_id,
            metrics=metrics,
            policy_version=run_record.get("policy_version"),
            baseline_guard=run_record.get("engine_baseline"),
            candidate_guard=run_record.get("engine_candidate"),
        )
    
    except Exception as e:
        logger.error(f"Error gathering run context: {e}")
        return None


def gather_policy_context() -> PolicyContext:
    """Gather context from the safety policy.
    
    Returns:
        PolicyContext
    """
    try:
        # Load policy file
        policy_path = Path("policy/policy.yaml")
        
        if not policy_path.exists():
            return PolicyContext()
        
        policy_data = yaml.safe_load(policy_path.read_text())
        
        # Extract categories
        categories = set()
        languages = set()
        rules_count = 0
        
        if "slices" in policy_data:
            for slice_config in policy_data["slices"].values():
                if "category" in slice_config:
                    categories.add(slice_config["category"])
                if "language" in slice_config:
                    languages.add(slice_config["language"])
        
        if "rules" in policy_data:
            rules_count = len(policy_data.get("rules", []))
        
        return PolicyContext(
            categories=sorted(categories),
            languages=sorted(languages),
            rules_count=rules_count,
            policy_description="Safety evaluation policy for content moderation",
        )
    
    except Exception as e:
        logger.error(f"Error gathering policy context: {e}")
        return PolicyContext()


def gather_context(
    tenant_id: str,
    run_id: Optional[str] = None
) -> Dict[str, Any]:
    """Gather all relevant context for assistant.
    
    Args:
        tenant_id: Tenant ID
        run_id: Optional run ID
        
    Returns:
        Context dictionary
    """
    context = {}
    
    # Policy context (always include)
    policy_ctx = gather_policy_context()
    context["policy"] = policy_ctx.to_summary()
    
    # Run context (if provided)
    if run_id:
        run_ctx = gather_run_context(run_id, tenant_id)
        if run_ctx:
            context["run"] = run_ctx.to_summary()
        else:
            context["run"] = f"Run {run_id} not found or no metrics available"
    
    return context


__all__ = [
    "gather_context",
    "gather_run_context",
    "gather_policy_context",
    "RunContext",
    "PolicyContext",
]

