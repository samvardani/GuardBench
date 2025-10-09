"""Monitoring dashboard routes."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from jinja2 import Environment, FileSystemLoader

from .metrics import get_global_collector
from .alerts import get_global_alerter

logger = logging.getLogger(__name__)

# Router setup
router = APIRouter(prefix="/ui/monitor", tags=["monitoring"])

# Template setup
ROOT_DIR = Path(__file__).resolve().parents[3]
MONITOR_TEMPLATE_DIR = ROOT_DIR / "templates" / "monitoring"
MONITOR_TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)

_env = Environment(loader=FileSystemLoader(MONITOR_TEMPLATE_DIR))


@router.get("/", response_class=HTMLResponse)
async def monitor_dashboard(request: Request) -> HTMLResponse:
    """Render the monitoring dashboard.
    
    Returns:
        HTML response with monitoring dashboard
    """
    try:
        collector = get_global_collector()
        summary = collector.get_summary(seconds=900)  # Last 15 minutes
        
        template = _env.get_template("dashboard.html")
        html = template.render(
            summary=summary,
            window_minutes=15,
        )
        return HTMLResponse(content=html)
    except Exception as e:
        logger.error(f"Failed to render monitoring dashboard: {e}")
        return HTMLResponse(
            content=f"<html><body><h1>Error loading dashboard</h1><p>{e}</p></body></html>",
            status_code=500
        )


@router.get("/api/metrics", response_class=JSONResponse)
async def get_metrics(window_seconds: int = 900) -> JSONResponse:
    """Get metrics as JSON.
    
    Args:
        window_seconds: Time window in seconds (default: 900 = 15 minutes)
        
    Returns:
        JSON response with metrics
    """
    try:
        collector = get_global_collector()
        summary = collector.get_summary(seconds=window_seconds)
        return JSONResponse(content=summary)
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )


@router.get("/api/timeseries", response_class=JSONResponse)
async def get_timeseries(
    window_seconds: int = 900,
    bucket_seconds: int = 60
) -> JSONResponse:
    """Get time series data for charts.
    
    Args:
        window_seconds: Time window in seconds
        bucket_seconds: Bucket size for aggregation
        
    Returns:
        JSON response with time series data
    """
    try:
        collector = get_global_collector()
        snapshots = collector.get_recent_snapshots(seconds=window_seconds)
        
        if not snapshots:
            return JSONResponse(content={
                "timestamps": [],
                "qps": [],
                "latency_p50": [],
                "latency_p95": [],
                "blocked_rate": [],
            })
        
        # Group snapshots into buckets
        import time
        from collections import defaultdict
        
        start_time = snapshots[0].timestamp
        end_time = snapshots[-1].timestamp
        
        buckets: Dict[int, list] = defaultdict(list)
        for snapshot in snapshots:
            bucket_idx = int((snapshot.timestamp - start_time) / bucket_seconds)
            buckets[bucket_idx].append(snapshot)
        
        # Compute metrics per bucket
        timestamps = []
        qps_values = []
        latency_p50_values = []
        latency_p95_values = []
        blocked_rate_values = []
        
        for bucket_idx in sorted(buckets.keys()):
            bucket_snapshots = buckets[bucket_idx]
            bucket_time = start_time + (bucket_idx * bucket_seconds)
            
            timestamps.append(int(bucket_time * 1000))  # JavaScript timestamp
            qps_values.append(len(bucket_snapshots) / bucket_seconds)
            
            latencies = sorted([s.latency_ms for s in bucket_snapshots])
            if latencies:
                p50_idx = int(len(latencies) * 0.50)
                p95_idx = int(len(latencies) * 0.95)
                latency_p50_values.append(latencies[p50_idx])
                latency_p95_values.append(latencies[p95_idx])
            else:
                latency_p50_values.append(0)
                latency_p95_values.append(0)
            
            blocked = sum(1 for s in bucket_snapshots if s.blocked)
            blocked_rate_values.append(blocked / len(bucket_snapshots) if bucket_snapshots else 0)
        
        return JSONResponse(content={
            "timestamps": timestamps,
            "qps": qps_values,
            "latency_p50": latency_p50_values,
            "latency_p95": latency_p95_values,
            "blocked_rate": blocked_rate_values,
        })
    
    except Exception as e:
        logger.error(f"Failed to get timeseries: {e}")
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )


@router.post("/api/check-alerts", response_class=JSONResponse)
async def check_alerts() -> JSONResponse:
    """Manually trigger alert threshold check.
    
    Returns:
        JSON response with check results
    """
    try:
        collector = get_global_collector()
        alerter = get_global_alerter()
        
        summary = collector.get_summary(seconds=900)
        
        # Default thresholds
        thresholds = {
            "blocked_rate": 0.5,
            "violence_blocked_rate": 0.7,
            "self_harm_blocked_rate": 0.7,
            "crime_blocked_rate": 0.7,
        }
        
        alerter.check_thresholds(summary, thresholds)
        
        return JSONResponse(content={
            "status": "checked",
            "summary": summary,
            "webhook_configured": alerter.webhook_url is not None
        })
    
    except Exception as e:
        logger.error(f"Failed to check alerts: {e}")
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )

