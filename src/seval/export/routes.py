"""Export endpoints for reports."""

from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse

from .builder import ReportBuilder, sanitize_for_export
from .schema import ReportSchemaModel
from .markdown import render_markdown_report

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/export", tags=["export"])


def _load_latest_evaluation() -> Dict[str, Any]:
    """Load latest evaluation results.
    
    Returns:
        Evaluation data dictionary
    """
    try:
        # Try to load from run history
        from pathlib import Path
        import json
        
        # Check if runs.jsonl exists
        runs_file = Path("runs.jsonl")
        if runs_file.exists():
            # Get last line (latest run)
            with open(runs_file) as f:
                lines = f.readlines()
                if lines:
                    latest_run = json.loads(lines[-1])
                    return latest_run.get("evaluation", {})
        
        # Fallback: return mock data for demonstration
        logger.warning("No evaluation data found, returning sample data")
        return _get_sample_evaluation()
    
    except Exception as e:
        logger.error(f"Failed to load evaluation data: {e}")
        return _get_sample_evaluation()


def _get_sample_evaluation() -> Dict[str, Any]:
    """Get sample evaluation data for when no real data exists.
    
    Returns:
        Sample evaluation dictionary
    """
    return {
        "guards": {
            "candidate": {
                "name": "candidate-v1",
                "predictions": [True, False, True, False, True],
                "latencies": [10, 15, 12, 20, 18],
                "latency": {"p50": 15.0, "p90": 19.0, "p95": 19.5, "p99": 20.0},
                "modes": {
                    "strict": {
                        "confusion": {
                            "tp": 2,
                            "fp": 1,
                            "tn": 1,
                            "fn": 1,
                            "precision": 0.667,
                            "recall": 0.667,
                            "fnr": 0.333,
                            "fpr": 0.500,
                        },
                        "slices": [
                            {
                                "category": "violence",
                                "language": "en",
                                "n": 3,
                                "tp": 2,
                                "fp": 0,
                                "tn": 0,
                                "fn": 1,
                                "precision": 1.0,
                                "recall": 0.667,
                                "fnr": 0.333,
                                "fpr": 0.0,
                            }
                        ]
                    }
                }
            }
        }
    }


def _load_config() -> Dict[str, Any]:
    """Load configuration.
    
    Returns:
        Config dictionary
    """
    try:
        from utils.io_utils import load_config
        return load_config()
    except Exception as e:
        logger.warning(f"Failed to load config: {e}")
        return {
            "dataset_path": "./dataset/sample.csv",
            "policy_version": "v0.1"
        }


@router.get("/report.json")
async def export_json_report(guard: str = "candidate") -> JSONResponse:
    """Export report as JSON.
    
    Args:
        guard: Guard name to report on
        
    Returns:
        JSON response with report data
    """
    try:
        # Load evaluation data
        evaluation_data = _load_latest_evaluation()
        config = _load_config()
        
        # Build report
        builder = ReportBuilder(evaluation_data, config)
        report = builder.build_report(guard_name=guard)
        
        # Sanitize to prevent secret leakage
        safe_report = sanitize_for_export(report)
        
        # Validate against schema
        try:
            ReportSchemaModel(**safe_report)
        except Exception as e:
            logger.warning(f"Report validation warning: {e}")
        
        return JSONResponse(content=safe_report)
    
    except Exception as e:
        logger.error(f"Failed to generate JSON report: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate report: {str(e)}"
        )


@router.get("/report.md")
async def export_markdown_report(guard: str = "candidate") -> PlainTextResponse:
    """Export report as Markdown.
    
    Args:
        guard: Guard name to report on
        
    Returns:
        Plain text response with Markdown content
    """
    try:
        # Load evaluation data
        evaluation_data = _load_latest_evaluation()
        config = _load_config()
        
        # Build report
        builder = ReportBuilder(evaluation_data, config)
        report = builder.build_report(guard_name=guard)
        
        # Sanitize
        safe_report = sanitize_for_export(report)
        
        # Render as Markdown
        markdown = render_markdown_report(safe_report)
        
        return PlainTextResponse(
            content=markdown,
            media_type="text/markdown"
        )
    
    except Exception as e:
        logger.error(f"Failed to generate Markdown report: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate report: {str(e)}"
        )

