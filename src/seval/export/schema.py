"""Report schema definitions."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MetadataModel(BaseModel):
    """Report metadata."""
    report_id: str
    generated_at: str
    policy_version: str
    policy_checksum: str
    git_commit: str
    dataset_path: str
    total_samples: int


class KPIModel(BaseModel):
    """Key Performance Indicators."""
    precision: float = Field(ge=0, le=1)
    recall: float = Field(ge=0, le=1)
    fnr: float = Field(ge=0, le=1, description="False Negative Rate")
    fpr: float = Field(ge=0, le=1, description="False Positive Rate")
    latency_p50_ms: float = Field(ge=0)
    latency_p95_ms: float = Field(ge=0)
    latency_p99_ms: float = Field(ge=0)
    blocked_rate: float = Field(ge=0, le=1)


class ImprovementItemModel(BaseModel):
    """Improvement plan item."""
    category: str
    issue: str
    recommendation: str
    priority: str = Field(pattern="^(high|medium|low)$")
    source: str = "analysis"


class RiskModel(BaseModel):
    """Risk item."""
    category: str
    risk_level: str = Field(pattern="^(high|medium|low)$")
    description: str
    mitigation: Optional[str] = None


class ReferenceModel(BaseModel):
    """Reference/citation."""
    title: str
    url: Optional[str] = None
    type: str = "internal"  # internal, external


class ReportSchemaModel(BaseModel):
    """Complete report schema."""
    metadata: MetadataModel
    kpis: KPIModel
    improvement_plan: List[ImprovementItemModel]
    risks: List[RiskModel]
    references: List[ReferenceModel]
    market_data: Dict[str, Any] = Field(default_factory=dict, description="External market data (TBD)")

