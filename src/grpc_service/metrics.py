"""gRPC aio server Prometheus metrics interceptor.

This module provides a lightweight, optional Prometheus interceptor for
grpc.aio servers. When the prometheus_client package is not available,
the interceptor factory returns None to avoid any overhead.

Exported API:
- get_prometheus_interceptor() -> Optional[grpc.aio.ServerInterceptor]
  Returns an interceptor that tracks:
    - grpc_requests_total{service,method,code}
    - grpc_request_duration_seconds{service,method} (Histogram)

Metrics are registered on the default process REGISTRY so they can be
exposed by an existing HTTP /metrics endpoint.
"""

from __future__ import annotations

import time
from typing import Optional, Tuple

try:  # Optional dependency; when missing, we noop entirely
    from prometheus_client import Counter, Histogram, REGISTRY
    _PROM_AVAILABLE = True
except Exception:  # pragma: no cover
    _PROM_AVAILABLE = False
    Counter = Histogram = object  # type: ignore[assignment]
    class REGISTRY:  # type: ignore[no-redef]
        _names_to_collectors = {}

try:  # grpc imports
    import grpc  # type: ignore
except Exception:  # pragma: no cover
    grpc = None  # type: ignore


def _parse_method(full_method: str) -> Tuple[str, str]:
    """Parse "/package.Service/Method" into (service, method)."""
    # Expected format: "/<full.service.Name>/<Method>"
    try:
        _, svc, mtd = full_method.split("/", 2)
        return svc, mtd
    except Exception:
        return "unknown", "unknown"


def _get_or_create_metrics():
    names = getattr(REGISTRY, "_names_to_collectors", {})
    if "grpc_requests_total" in names:
        req = names["grpc_requests_total"]
    else:
        req = Counter(
            "grpc_requests_total",
            "Total gRPC requests",
            labelnames=["service", "method", "code"],
        )

    if "grpc_request_duration_seconds" in names:
        dur = names["grpc_request_duration_seconds"]
    else:
        dur = Histogram(
            "grpc_request_duration_seconds",
            "gRPC request duration in seconds",
            labelnames=["service", "method"],
            # Reasonable default buckets for RPC latency (in seconds)
            buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
        )
    return req, dur


def get_prometheus_interceptor() -> Optional["grpc.aio.ServerInterceptor"]:
    """Return a grpc.aio ServerInterceptor that records Prometheus metrics.

    If prometheus_client or grpc.aio is unavailable, returns None.
    """
    if not _PROM_AVAILABLE or grpc is None or not hasattr(grpc, "aio"):
        return None

    requests_counter, duration_hist = _get_or_create_metrics()

    class _Interceptor(grpc.aio.ServerInterceptor):  # type: ignore[attr-defined]
        async def intercept_service(self, continuation, handler_call_details):  # type: ignore[no-untyped-def]
            handler = await continuation(handler_call_details)
            if handler is None:
                return handler

            service, method = _parse_method(getattr(handler_call_details, "method", ""))

            # Only wrap unary-unary in this project (Score, BatchScore).
            if handler.unary_unary:
                unary = handler.unary_unary

                async def _wrapped(request, context):  # type: ignore[no-untyped-def]
                    start = time.perf_counter()
                    code = None
                    try:
                        response = await unary(request, context)
                        code = context.code() or grpc.StatusCode.OK
                        return response
                    except Exception:
                        code = context.code() or grpc.StatusCode.UNKNOWN
                        raise
                    finally:
                        duration = max(time.perf_counter() - start, 0.0)
                        try:
                            duration_hist.labels(service=service, method=method).observe(duration)
                            # Map StatusCode to numeric code if possible
                            code_label = str(getattr(getattr(code, "value", (None,)), 0, "")) if code is not None else ""
                            if not code_label:
                                code_label = getattr(code, "name", "UNKNOWN")
                            requests_counter.labels(service=service, method=method, code=code_label).inc()
                        except Exception:
                            pass

                try:
                    return grpc.aio.unary_unary_rpc_method_handler(  # type: ignore[attr-defined]
                        _wrapped,
                        request_deserializer=handler.request_deserializer,
                        response_serializer=handler.response_serializer,
                    )
                except Exception:
                    # Fallback: return original handler if wrapper construction fails
                    return handler

            # Other streaming types can be added when needed; pass through by default
            return handler

    return _Interceptor()


