#!/usr/bin/env python3
"""
Comprehensive Prometheus Metrics for Safety Evaluation Service
Tracks requests, latency, errors, model performance, and guard routing
"""
import time
from contextlib import contextmanager
from functools import wraps
from typing import Any, Callable, Dict, Optional

try:
    from prometheus_client import Counter, Histogram, Gauge, Info, REGISTRY
    PROMETHEUS_AVAILABLE = True
except ImportError:
    # Noop metrics for when Prometheus is not installed
    class _NoopMetric:
        def __init__(self, *args, **kwargs):
            pass
        
        def labels(self, *args, **kwargs):
            return self
        
        def observe(self, value):
            pass
        
        def inc(self, amount=1):
            pass
        
        def set(self, value):
            pass
        
        def info(self, value):
            pass
    
    Counter = Histogram = Gauge = Info = _NoopMetric  # type: ignore
    PROMETHEUS_AVAILABLE = False
    
    class REGISTRY:  # type: ignore
        _names_to_collectors: Dict[str, Any] = {}


# --- Request Metrics ---
REQUEST_COUNTER = Counter(
    "safety_requests_total",
    "Total HTTP requests",
    labelnames=["method", "endpoint", "status_code"]
)

REQUEST_LATENCY = Histogram(
    "safety_request_latency_seconds",
    "HTTP request latency in seconds",
    labelnames=["method", "endpoint"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)
)

# --- Guard Performance Metrics ---
GUARD_LATENCY = Histogram(
    "safety_guard_latency_seconds",
    "Guard inference latency in seconds",
    labelnames=["guard_type", "path"],  # guard_type: rules/ml/transformer, path: fast/medium/deep
    buckets=(0.001, 0.002, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5)
)

GUARD_PREDICTIONS = Counter(
    "safety_guard_predictions_total",
    "Guard prediction outcomes",
    labelnames=["guard_type", "prediction", "category"]  # prediction: flag/pass
)

GUARD_ROUTING = Counter(
    "safety_guard_routing_total",
    "Guard routing decisions",
    labelnames=["path", "reason"]  # path: fast/medium/deep, reason: high_confidence/low_confidence/weighted
)

# --- Model Performance Metrics ---
MODEL_INFERENCE_LATENCY = Histogram(
    "safety_model_inference_seconds",
    "Model inference time in seconds",
    labelnames=["model_name", "device"],  # model_name: nb_lr/bert_tiny, device: cpu/mps/cuda
    buckets=(0.001, 0.002, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5)
)

MODEL_LOAD_COUNTER = Counter(
    "safety_model_loads_total",
    "Model load/reload events",
    labelnames=["model_name", "status"]  # status: success/failure
)

# --- Policy Metrics ---
POLICY_LOAD_COUNTER = Counter(
    "safety_policy_loads_total",
    "Policy load/reload events",
    labelnames=["status"]  # status: success/failure
)

POLICY_CHECKSUM_GAUGE = Gauge(
    "safety_policy_checksum_hash",
    "Current policy checksum (first 8 hex digits as int)"
)

POLICY_RULES_GAUGE = Gauge(
    "safety_policy_rules_total",
    "Total number of rules in current policy"
)

# --- Content Analysis Metrics ---
CONTENT_CATEGORIES = Counter(
    "safety_content_categories_total",
    "Content flagged by category",
    labelnames=["category", "severity"]  # category: violence/harassment/sexual/etc, severity: high/medium/low
)

CONTENT_LENGTH = Histogram(
    "safety_content_length_chars",
    "Content length distribution in characters",
    buckets=(10, 50, 100, 250, 500, 1000, 2500, 5000, 10000)
)

# --- Error Metrics ---
ERROR_COUNTER = Counter(
    "safety_errors_total",
    "Total errors by type",
    labelnames=["error_type", "component"]  # component: api/guard/model/policy
)

TIMEOUT_COUNTER = Counter(
    "safety_timeouts_total",
    "Request timeouts",
    labelnames=["endpoint", "timeout_type"]  # timeout_type: inference/database/external
)

# --- Rate Limiting Metrics ---
RATE_LIMIT_BLOCKS = Counter(
    "safety_rate_limit_blocks_total",
    "Rate limit rejections",
    labelnames=["scope", "limit_type"]  # scope: global/user/ip, limit_type: requests/tokens
)

# --- Health & System Metrics ---
HEALTH_STATUS = Gauge(
    "safety_health_status",
    "Overall health status (1=healthy, 0=unhealthy)"
)

DEPENDENCY_STATUS = Gauge(
    "safety_dependency_status",
    "Dependency health status (1=healthy, 0=unhealthy)",
    labelnames=["dependency"]  # dependency: database/redis/ml_model/policy
)

UPTIME_SECONDS = Gauge(
    "safety_uptime_seconds",
    "Service uptime in seconds"
)

# --- Info Metrics ---
SERVICE_INFO = Info(
    "safety_service",
    "Service version and build information"
)

# --- Start time for uptime calculation ---
_start_time = time.time()


# --- Helper Functions ---

def update_service_info(version: str, build_id: str, policy_version: str):
    """Update service info metric"""
    if PROMETHEUS_AVAILABLE:
        SERVICE_INFO.info({
            "version": version,
            "build_id": build_id,
            "policy_version": policy_version
        })


def update_uptime():
    """Update uptime metric"""
    UPTIME_SECONDS.set(time.time() - _start_time)


def update_policy_metrics(metadata: Dict[str, Any]):
    """Update policy-related metrics"""
    # Convert first 8 hex chars of checksum to int for Gauge
    checksum_short = metadata.get("checksum_short", "00000000")
    try:
        checksum_int = int(checksum_short[:8], 16)
        POLICY_CHECKSUM_GAUGE.set(checksum_int)
    except (ValueError, TypeError):
        pass
    
    # Update rule count
    total_rules = metadata.get("total_rules", 0)
    POLICY_RULES_GAUGE.set(total_rules)


@contextmanager
def measure_latency(metric: Histogram, **labels):
    """Context manager to measure and record latency"""
    start = time.perf_counter()
    try:
        yield
    finally:
        duration = time.perf_counter() - start
        metric.labels(**labels).observe(duration)


def track_request(method: str, endpoint: str, status_code: int, duration_seconds: float):
    """Track a complete HTTP request"""
    REQUEST_COUNTER.labels(
        method=method,
        endpoint=endpoint,
        status_code=status_code
    ).inc()
    
    REQUEST_LATENCY.labels(
        method=method,
        endpoint=endpoint
    ).observe(duration_seconds)


def track_guard_prediction(
    guard_type: str,
    prediction: str,
    category: str,
    latency_seconds: float,
    path: str = "unknown",
    routing_reason: str = "unknown"
):
    """Track a guard prediction with full metrics"""
    # Prediction outcome
    GUARD_PREDICTIONS.labels(
        guard_type=guard_type,
        prediction=prediction,
        category=category
    ).inc()
    
    # Latency
    GUARD_LATENCY.labels(
        guard_type=guard_type,
        path=path
    ).observe(latency_seconds)
    
    # Routing decision
    GUARD_ROUTING.labels(
        path=path,
        reason=routing_reason
    ).inc()


def track_model_inference(model_name: str, device: str, latency_seconds: float):
    """Track model inference time"""
    MODEL_INFERENCE_LATENCY.labels(
        model_name=model_name,
        device=device
    ).observe(latency_seconds)


def track_content_analysis(category: str, severity: str, content_length: int):
    """Track content analysis results"""
    CONTENT_CATEGORIES.labels(
        category=category,
        severity=severity
    ).inc()
    
    CONTENT_LENGTH.observe(content_length)


def track_error(error_type: str, component: str):
    """Track an error"""
    ERROR_COUNTER.labels(
        error_type=error_type,
        component=component
    ).inc()


def track_timeout(endpoint: str, timeout_type: str):
    """Track a timeout"""
    TIMEOUT_COUNTER.labels(
        endpoint=endpoint,
        timeout_type=timeout_type
    ).inc()


def track_rate_limit_block(scope: str, limit_type: str):
    """Track a rate limit block"""
    RATE_LIMIT_BLOCKS.labels(
        scope=scope,
        limit_type=limit_type
    ).inc()


def update_health_status(is_healthy: bool):
    """Update overall health status"""
    HEALTH_STATUS.set(1 if is_healthy else 0)


def update_dependency_status(dependency: str, is_healthy: bool):
    """Update dependency health status"""
    DEPENDENCY_STATUS.labels(dependency=dependency).set(1 if is_healthy else 0)


# --- Decorator for automatic metric tracking ---

def track_endpoint_metrics(endpoint_name: str):
    """Decorator to automatically track endpoint metrics"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.perf_counter()
            status_code = 200
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status_code = getattr(e, "status_code", 500)
                track_error(type(e).__name__, "api")
                raise
            finally:
                duration = time.perf_counter() - start
                track_request("POST", endpoint_name, status_code, duration)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.perf_counter()
            status_code = 200
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                status_code = getattr(e, "status_code", 500)
                track_error(type(e).__name__, "api")
                raise
            finally:
                duration = time.perf_counter() - start
                track_request("POST", endpoint_name, status_code, duration)
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# --- Initialize metrics on module load ---
if PROMETHEUS_AVAILABLE:
    # Set initial values
    HEALTH_STATUS.set(0)  # Will be updated by health check
    UPTIME_SECONDS.set(0)
    update_uptime()
    
    print("✓ Prometheus metrics initialized")
else:
    print("⚠ Prometheus client not available, metrics disabled")


if __name__ == "__main__":
    # Test metrics
    print("\n🔧 Metrics Module Test\n")
    
    if PROMETHEUS_AVAILABLE:
        print("1. Testing request tracking...")
        track_request("POST", "/score", 200, 0.005)
        track_request("POST", "/score", 429, 0.001)
        print("   ✓ Requests tracked")
        
        print("\n2. Testing guard prediction tracking...")
        track_guard_prediction(
            guard_type="rules",
            prediction="flag",
            category="violence",
            latency_seconds=0.002,
            path="fast",
            routing_reason="high_confidence"
        )
        print("   ✓ Guard prediction tracked")
        
        print("\n3. Testing model inference tracking...")
        track_model_inference("bert_tiny", "mps", 0.004)
        print("   ✓ Model inference tracked")
        
        print("\n4. Testing policy metrics...")
        update_policy_metrics({
            "checksum_short": "e5b60875",
            "total_rules": 17
        })
        print("   ✓ Policy metrics updated")
        
        print("\n5. Testing health metrics...")
        update_health_status(True)
        update_dependency_status("database", True)
        update_dependency_status("ml_model", True)
        print("   ✓ Health metrics updated")
        
        print("\n6. Generating metrics output...")
        from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
        metrics_output = generate_latest(REGISTRY).decode('utf-8')
        
        # Show sample of metrics
        lines = [line for line in metrics_output.split('\n') if line and not line.startswith('#')]
        print(f"   Sample metrics ({len(lines)} total):")
        for line in lines[:10]:
            print(f"   {line}")
        
        print("\n✅ Metrics test complete")
    else:
        print("⚠ Prometheus not available, skipping tests")












