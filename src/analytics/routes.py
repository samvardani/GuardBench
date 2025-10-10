"""Benchmark leaderboard API routes."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from .leaderboard import get_leaderboard, BenchmarkResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/leaderboard", tags=["Benchmark Leaderboard"])


class BenchmarkSubmission(BaseModel):
    """Submit benchmark result."""
    
    dataset_name: str = Field(..., description="Benchmark dataset name")
    guard_name: str = Field(..., description="Guard name")
    guard_version: Optional[str] = Field(default=None, description="Guard version")
    run_id: Optional[str] = Field(default=None, description="Associated run ID")
    
    # Metrics
    precision: float = Field(..., ge=0.0, le=1.0)
    recall: float = Field(..., ge=0.0, le=1.0)
    f1_score: float = Field(..., ge=0.0, le=1.0)
    fnr: float = Field(..., ge=0.0, le=1.0)
    fpr: float = Field(..., ge=0.0, le=1.0)
    
    # Confusion matrix
    tp: int = Field(..., ge=0)
    fp: int = Field(..., ge=0)
    tn: int = Field(..., ge=0)
    fn: int = Field(..., ge=0)
    
    # Performance
    avg_latency_ms: int = Field(default=0, ge=0)
    p50_latency_ms: int = Field(default=0, ge=0)
    p90_latency_ms: int = Field(default=0, ge=0)
    p99_latency_ms: int = Field(default=0, ge=0)
    
    # Metadata
    categories: List[str] = Field(default_factory=list)
    languages: List[str] = Field(default_factory=list)
    is_public: bool = Field(default=False, description="Make result publicly visible")


@router.get("")
async def get_leaderboard_entries(
    dataset: Optional[str] = Query(default=None, description="Filter by dataset"),
    metric: str = Query(default="f1_score", description="Metric to rank by"),
    limit: int = Query(default=100, ge=1, le=1000, description="Max entries"),
    public_only: bool = Query(default=False, description="Only public results")
) -> Dict[str, Any]:
    """Get benchmark leaderboard.
    
    Args:
        dataset: Optional dataset filter
        metric: Metric to rank by (f1_score, precision, recall)
        limit: Max entries to return
        public_only: Only return public results
        
    Returns:
        Leaderboard data
    """
    try:
        leaderboard = get_leaderboard()
        
        entries = leaderboard.get_leaderboard(
            dataset_name=dataset,
            metric=metric,
            limit=limit,
            public_only=public_only
        )
        
        return {
            "dataset": dataset or "all",
            "metric": metric,
            "count": len(entries),
            "entries": [entry.to_dict() for entry in entries],
        }
    
    except Exception as e:
        logger.exception(f"Error fetching leaderboard: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch leaderboard: {str(e)}"
        )


@router.post("/submit")
async def submit_benchmark_result(
    submission: BenchmarkSubmission,
    tenant_id: str = "public"
) -> Dict[str, Any]:
    """Submit a benchmark result to the leaderboard.
    
    Args:
        submission: Benchmark result submission
        tenant_id: Tenant ID (from auth)
        
    Returns:
        Submission confirmation
    """
    try:
        leaderboard = get_leaderboard()
        
        # Create BenchmarkResult
        result = BenchmarkResult(
            dataset_name=submission.dataset_name,
            guard_name=submission.guard_name,
            guard_version=submission.guard_version,
            run_id=submission.run_id,
            tenant_id=tenant_id,
            precision=submission.precision,
            recall=submission.recall,
            f1_score=submission.f1_score,
            fnr=submission.fnr,
            fpr=submission.fpr,
            tp=submission.tp,
            fp=submission.fp,
            tn=submission.tn,
            fn=submission.fn,
            avg_latency_ms=submission.avg_latency_ms,
            p50_latency_ms=submission.p50_latency_ms,
            p90_latency_ms=submission.p90_latency_ms,
            p99_latency_ms=submission.p99_latency_ms,
            dataset_size=submission.tp + submission.fp + submission.tn + submission.fn,
            categories=submission.categories,
            languages=submission.languages,
            is_public=submission.is_public,
        )
        
        result_id = leaderboard.add_result(result)
        
        return {
            "id": result_id,
            "dataset_name": submission.dataset_name,
            "guard_name": submission.guard_name,
            "f1_score": submission.f1_score,
            "message": "Benchmark result submitted successfully"
        }
    
    except Exception as e:
        logger.exception(f"Error submitting benchmark result: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit result: {str(e)}"
        )


@router.get("/datasets")
async def list_datasets() -> Dict[str, Any]:
    """List available benchmark datasets.
    
    Returns:
        List of datasets
    """
    try:
        leaderboard = get_leaderboard()
        datasets = leaderboard.get_datasets()
        
        # Get info for each dataset
        dataset_info = []
        for name in datasets:
            info = leaderboard.get_dataset_info(name)
            if info:
                dataset_info.append(info)
            else:
                dataset_info.append({"dataset_name": name})
        
        return {
            "count": len(datasets),
            "datasets": dataset_info
        }
    
    except Exception as e:
        logger.exception(f"Error listing datasets: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list datasets: {str(e)}"
        )


@router.get("/ui", response_class=HTMLResponse)
async def leaderboard_ui(
    dataset: Optional[str] = Query(default=None)
) -> HTMLResponse:
    """Serve the leaderboard UI.
    
    Args:
        dataset: Optional dataset filter
        
    Returns:
        HTML leaderboard interface
    """
    template_path = Path(__file__).resolve().parents[2] / "templates" / "leaderboard" / "index.html"
    
    if not template_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Leaderboard UI template not found"
        )
    
    return HTMLResponse(template_path.read_text())


__all__ = ["router"]

