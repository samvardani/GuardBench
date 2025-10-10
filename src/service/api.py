"""Safety evaluation service with auth, multi-tenant routing, and real-time streams."""

from __future__ import annotations

import asyncio
import concurrent.futures
import csv
import datetime as dt
import functools
import hashlib
import io
import json
import logging
import json as _json
import os
import re
import tarfile
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    Header,
    Request,
    HTTPException,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, ORJSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
import yaml
try:
    from prometheus_client import Counter, Histogram, CONTENT_TYPE_LATEST, generate_latest, REGISTRY
except Exception:  # pragma: no cover - optional dependency
    class _NoopMetric:
        def __init__(self, *args, **kwargs):
            pass

        def labels(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            return self

        def observe(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            return None

        def inc(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            return None

    Counter = Histogram = _NoopMetric  # type: ignore[assignment]
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4"  # type: ignore

    def generate_latest(*_, **__):  # type: ignore[no-untyped-def]
        return b""

    class REGISTRY:
        _names_to_collectors = {}

from pydantic import BaseModel, EmailStr, Field, constr

try:  # pragma: no cover - optional dependency guard
    import email_validator  # type: ignore  # noqa: F401
except ImportError:  # pragma: no cover
    EmailStr = str  # type: ignore[assignment]

try:
    from opentelemetry import trace
except Exception:  # pragma: no cover - optional dependency
    class _NoopSpan:
        def __enter__(self):  # type: ignore[no-untyped-def]
            return self

        def __exit__(self, exc_type, exc, tb):  # type: ignore[no-untyped-def]
            return False

        def set_attribute(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            return None

        def record_exception(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            return None

    class _NoopTracer:
        def start_as_current_span(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            return _NoopSpan()

    class _NoopTrace:  # pragma: no cover - fallback
        def get_tracer(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            return _NoopTracer()

    trace = _NoopTrace()  # type: ignore[assignment]

try:  # pragma: no cover - optional dependency
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
except Exception:  # pragma: no cover
    Resource = None  # type: ignore
    TracerProvider = None  # type: ignore
    BatchSpanProcessor = None  # type: ignore
    OTLPSpanExporter = None  # type: ignore

from . import db
from evaluation import evaluate
from guards.baseline import predict as baseline_predict
from guards.candidate import predict as candidate_predict
from report.build_report import (
    cluster_failures,
    histogram,
    load_incident_reports,
    load_parity_summary,
    load_redteam_summary,
    load_runtime_telemetry,
    slice_failure_patterns,
)
from autopatch.candidates import apply_threshold_patch_to_tuned
from .settings import get_settings
from utils.io_utils import load_config, git_commit
from utils.scrub import privacy_mode_for, scrub_text
from jinja2 import Environment, FileSystemLoader
from utils.json import orjson_dumps, orjson_loads
from policy.compiler import load_compiled_policy, POLICY_PATH
from policy import policy_cache as policy_cache
import hashlib
import secrets
from utils.seed import seed_all_from_env


try:
    import redis  # type: ignore
except Exception:  # pragma: no cover - redis is optional
    redis = None


LOG_LEVEL = get_settings().log_level.strip().upper()
try:
    _level = getattr(logging, LOG_LEVEL)
except Exception:
    _level = logging.INFO
logging.basicConfig(level=_level)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Sentinel Safety Service",
    version="2024.10",
    json_dumps=orjson_dumps,
    json_loads=orjson_loads,
    default_response_class=ORJSONResponse,
)
seed_all_from_env("SEVAL_SEED")
# Templates
ROOT_DIR = Path(__file__).resolve().parents[2]
TPL_DIR = ROOT_DIR / "templates"
_env = Environment(loader=FileSystemLoader(TPL_DIR))


def _policy_checksum(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha256(data).hexdigest()[:12]


# Build and policy metadata
try:
    BUILD_ID = os.getenv("BUILD_ID") or git_commit()
except Exception:
    BUILD_ID = os.getenv("BUILD_ID", "n/a")

# Policy checksum (kept for backwards compatibility, but settings module is source of truth)
POLICY_CHECKSUM = _policy_checksum(POLICY_PATH)


def _new_csrf_token() -> str:
    return secrets.token_hex(16)

_cors = get_settings().cors_allow_origins
if _cors and _cors.strip():
    _origins = [o.strip() for o in _cors.split(",") if o.strip()]
else:
    _origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session support (for CSRF tokens on policy page, etc.)
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET", "dev-not-secret"))

# OIDC authentication middleware
try:
    from seval.auth.middleware import OIDCMiddleware
    from seval.auth.oidc import get_oidc_auth
    
    oidc_auth = get_oidc_auth()
    if oidc_auth.is_configured():
        app.add_middleware(OIDCMiddleware)
        logger.info("OIDC middleware enabled (routes protected)")
    else:
        logger.info("OIDC not configured (public access mode)")
except Exception as e:
    logger.warning(f"OIDC middleware not available: {e}")


# Policy metadata middleware - injects version and checksum headers
@app.middleware("http")
async def add_policy_headers(request: Request, call_next):  # type: ignore
    """Inject policy version and checksum into response headers."""
    # Lazy import to avoid circular dependency
    from src.seval.settings import POLICY_VERSION as SEVAL_VERSION, POLICY_CHECKSUM as SEVAL_CHECKSUM
    
    response = await call_next(request)
    response.headers["X-Policy-Version"] = SEVAL_VERSION
    response.headers["X-Policy-Checksum"] = SEVAL_CHECKSUM
    # Expose custom headers to JavaScript clients for CORS
    response.headers["Access-Control-Expose-Headers"] = "X-Policy-Version, X-Policy-Checksum"
    return response


ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_DIR = ROOT / "templates"
SCORECARD_ROOT = Path("dist/scorecards")
SCORECARD_ROOT.mkdir(parents=True, exist_ok=True)
app.mount("/scorecards", StaticFiles(directory=SCORECARD_ROOT), name="scorecards")

CONFIG_FILE = Path("config.yaml")
AUTOPATCH_THRESHOLD_PATH = Path("tuned_thresholds.yaml")
AUTOPATCH_CANARY_PATH = Path("tuned_thresholds_canary.yaml")
AUTOPATCH_ROLLBACK_DIR = Path("autopatch_rollbacks")


_TRACING_CONFIGURED = False


def _configure_tracing() -> None:
    global _TRACING_CONFIGURED, tracer
    if _TRACING_CONFIGURED:
        return
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint or TracerProvider is None or OTLPSpanExporter is None or BatchSpanProcessor is None or Resource is None:
        tracer = trace.get_tracer(__name__)
        _TRACING_CONFIGURED = True
        return
    try:
        insecure = os.getenv("OTEL_EXPORTER_OTLP_INSECURE", "true").lower() == "true"
        provider = TracerProvider(resource=Resource.create({"service.name": "safety-eval-service"}))
        exporter = OTLPSpanExporter(endpoint=endpoint, insecure=insecure)
        processor = BatchSpanProcessor(exporter)
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)
        tracer = trace.get_tracer(__name__)
        _TRACING_CONFIGURED = True
        logger.info("Configured OTLP tracing exporter to %s (insecure=%s)", endpoint, insecure)
    except Exception as exc:  # pragma: no cover - tracing misconfig
        tracer = trace.get_tracer(__name__)
        _TRACING_CONFIGURED = True
        logger.warning("Failed to configure OTLP exporter: %s", exc)


tracer = trace.get_tracer(__name__)

_settings = get_settings()
PREDICT_TIMEOUT_SECONDS = float(_settings.predict_timeout_seconds)
PREDICT_MAX_WORKERS = int(_settings.predict_max_workers)

TOKEN_RATE_LIMIT = 2
TOKEN_RATE_WINDOW_SECONDS = 60
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
REDIS_URL = _settings.redis_url

CB_FAILURE_THRESHOLD = int(os.getenv("CB_FAILURE_THRESHOLD", "3"))
CB_LATENCY_THRESHOLD_MS = int(os.getenv("CB_LATENCY_THRESHOLD_MS", "750"))
CB_RECOVERY_SECONDS = float(os.getenv("CB_RECOVERY_SECONDS", "30"))

POLICY_VERSION = os.getenv("POLICY_VERSION", "n/a")

PREDICT_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=PREDICT_MAX_WORKERS)

# Avoid duplicate registration under pytest reloads
_names = getattr(REGISTRY, "_names_to_collectors", {})
if "safety_score_latency_ms" in _names:
    SCORE_LATENCY = _names["safety_score_latency_ms"]
else:
    SCORE_LATENCY = Histogram(
        "safety_score_latency_ms",
        "Latency of score endpoint in milliseconds",
        labelnames=["endpoint", "guard"],
        buckets=(10, 25, 50, 100, 200, 400, 800, 1600, 3200),
    )

if "safety_score_requests_total" in _names:
    SCORE_REQUESTS = _names["safety_score_requests_total"]
else:
    SCORE_REQUESTS = Counter(
        "safety_score_requests_total",
        "Total score endpoint requests",
        labelnames=["endpoint", "guard", "status"],
    )

if "safety_rate_limit_blocks_total" in _names:
    RATE_LIMIT_BLOCKS = _names["safety_rate_limit_blocks_total"]
else:
    RATE_LIMIT_BLOCKS = Counter(
        "safety_rate_limit_blocks_total",
        "Rate limit rejections grouped by scope",
        labelnames=["scope"],
    )

if "safety_circuit_breaker_open_total" in _names:
    CIRCUIT_OPEN_COUNTER = _names["safety_circuit_breaker_open_total"]
else:
    CIRCUIT_OPEN_COUNTER = Counter(
        "safety_circuit_breaker_open_total",
        "Circuit breaker open events per guard",
        labelnames=["guard"],
    )

if "safety_batch_latency_ms" in _names:
    BATCH_LATENCY = _names["safety_batch_latency_ms"]
else:
    BATCH_LATENCY = Histogram(
        "safety_batch_latency_ms",
        "Latency of batch evaluations in milliseconds",
        labelnames=["endpoint"],
        buckets=(50, 100, 200, 400, 800, 1600, 3200, 6400, 12800),
    )

if "safety_batch_requests_total" in _names:
    BATCH_REQUESTS = _names["safety_batch_requests_total"]
else:
    BATCH_REQUESTS = Counter(
        "safety_batch_requests_total",
        "Total batch evaluations",
        labelnames=["endpoint", "status"],
    )

if "safety_score_results_total" in _names:
    SCORE_RESULT_COUNTER = _names["safety_score_results_total"]
else:
    SCORE_RESULT_COUNTER = Counter(
        "safety_score_results_total",
        "Score endpoint outcomes",
        labelnames=["guard", "outcome"],
    )

if "safety_batch_results_total" in _names:
    BATCH_RESULT_COUNTER = _names["safety_batch_results_total"]
else:
    BATCH_RESULT_COUNTER = Counter(
        "safety_batch_results_total",
        "Batch evaluation confusion matrix counts",
        labelnames=["guard", "label"],
    )


class PredictTimeout(Exception):
    """Raised when a guard predict call exceeds the configured timeout."""


class CircuitOpenError(Exception):
    """Raised when a guard circuit breaker is open and request is rejected."""

    def __init__(self, guard_key: str, state: str) -> None:
        super().__init__(f"Circuit breaker open for guard '{guard_key}' (state={state})")
        self.guard_key = guard_key
        self.state = state


class RateLimiter:
    """Token-scoped rate limiter with Redis or in-memory fallback."""

    def __init__(
        self,
        limit_per_window: int,
        window_seconds: int,
        redis_url: Optional[str] = None,
    ) -> None:
        self.limit = max(1, limit_per_window)
        self.window = max(1, window_seconds)
        self._lock = threading.Lock()
        self._buckets: Dict[tuple[str, str], deque[float]] = {}
        self._redis = self._init_redis(redis_url)

    def _init_redis(self, url: Optional[str]):
        if not url or redis is None:
            return None
        try:
            client = redis.Redis.from_url(url, decode_responses=True, socket_timeout=0.2)  # type: ignore[attr-defined]
            client.ping()
            logger.info("Rate limiter using Redis backend at %s", url)
            return client
        except Exception as exc:  # pragma: no cover - network failures
            logger.warning("Redis unavailable for rate limiting (%s); falling back to memory", exc)
            return None

    def configure(self, limit_per_window: int, window_seconds: int) -> None:
        self.limit = max(1, limit_per_window)
        self.window = max(1, window_seconds)

    def reset(self) -> None:
        with self._lock:
            self._buckets.clear()

    def allow(self, token: str, scope: str) -> bool:
        now = time.time()
        if self._redis is not None:
            return self._allow_redis(token, scope, now)
        return self._allow_memory(token, scope, now)

    def _allow_memory(self, token: str, scope: str, now: float) -> bool:
        key = (scope, token)
        cutoff = now - self.window
        with self._lock:
            bucket = self._buckets.setdefault(key, deque())
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= self.limit:
                return False
            bucket.append(now)
            return True

    def _allow_redis(self, token: str, scope: str, now: float) -> bool:
        if self._redis is None:
            return True
        key = f"rate:{scope}:{token}"
        cutoff = now - self.window
        try:
            pipe = self._redis.pipeline()
            pipe.zremrangebyscore(key, 0, cutoff)
            pipe.zcard(key)
            pipe.zadd(key, {str(now): now})
            pipe.expire(key, self.window)
            _, count, _, _ = pipe.execute()
            if count >= self.limit:
                # remove the element we just added to keep the bucket bounded
                self._redis.zrem(key, str(now))
                return False
            return True
        except Exception as exc:  # pragma: no cover - redis errors fallback
            logger.warning("Redis error during rate limiting (%s); falling back to memory", exc)
            return self._allow_memory(token, scope, now)


class CircuitBreaker:
    """Simple circuit breaker tracking failures and latency spikes per guard."""

    def __init__(
        self,
        failure_threshold: int,
        latency_threshold_ms: int,
        recovery_seconds: float,
    ) -> None:
        self.failure_threshold = max(1, failure_threshold)
        self.latency_threshold_ms = max(0, latency_threshold_ms)
        self.recovery_seconds = max(1.0, recovery_seconds)
        self._lock = threading.Lock()
        self._state: Dict[str, Dict[str, Any]] = {}

    def reset(self) -> None:
        with self._lock:
            self._state.clear()

    def allow(self, guard_key: str) -> tuple[bool, str]:
        now = time.monotonic()
        with self._lock:
            state = self._state.setdefault(
                guard_key,
                {"state": "closed", "failures": 0, "open_until": 0.0, "probe_in_flight": False},
            )
            if state["state"] == "open":
                if now >= state["open_until"]:
                    state["state"] = "half_open"
                    state["probe_in_flight"] = False
                else:
                    return False, "open"
            if state["state"] == "half_open":
                if state["probe_in_flight"]:
                    return False, "half_open"
                state["probe_in_flight"] = True
                return True, "half_open"
            return True, state["state"]

    def record_success(self, guard_key: str) -> None:
        with self._lock:
            state = self._state.setdefault(
                guard_key,
                {"state": "closed", "failures": 0, "open_until": 0.0, "probe_in_flight": False},
            )
            state["failures"] = 0
            state["state"] = "closed"
            state["open_until"] = 0.0
            state["probe_in_flight"] = False

    def record_failure(self, guard_key: str, *, latency_ms: Optional[int] = None, reason: str = "error") -> bool:
        now = time.monotonic()
        opened = False
        with self._lock:
            state = self._state.setdefault(
                guard_key,
                {"state": "closed", "failures": 0, "open_until": 0.0, "probe_in_flight": False},
            )
            state["probe_in_flight"] = False
            if reason == "latency" and latency_ms is not None and latency_ms >= self.latency_threshold_ms:
                state["failures"] = self.failure_threshold
            else:
                state["failures"] += 1

            if state["state"] == "half_open" or state["failures"] >= self.failure_threshold:
                state["state"] = "open"
                state["open_until"] = now + self.recovery_seconds
                state["failures"] = self.failure_threshold
                opened = True
            return opened


rate_limiter = RateLimiter(TOKEN_RATE_LIMIT, TOKEN_RATE_WINDOW_SECONDS, redis_url=REDIS_URL)
circuit_breaker = CircuitBreaker(CB_FAILURE_THRESHOLD, CB_LATENCY_THRESHOLD_MS, CB_RECOVERY_SECONDS)


@app.middleware("http")
async def _security_headers(request, call_next):  # type: ignore[override]
    import uuid, time as _time
    start = _time.perf_counter()
    # Inject/propagate X-Request-ID
    rid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = rid
    # Enforce max JSON body size
    max_bytes = get_settings().max_json_body_bytes
    if request.headers.get("content-type", "").startswith("application/json"):
        try:
            length = int(request.headers.get("content-length") or 0)
        except ValueError:
            length = 0
        if max_bytes and length and length > max_bytes:
            return JSONResponse(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, content={"detail": "Request entity too large"})
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers["X-Request-ID"] = rid
    # Structured JSON access log
    try:
        latency_ms = max(int((_time.perf_counter() - start) * 1000), 0)
        record = {
            "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
            "level": "INFO",
            "path": request.url.path,
            "status": response.status_code,
            "latency_ms": latency_ms,
            "request_id": rid,
            "category": getattr(getattr(request, "state", object()), "category", None),
            "language": getattr(getattr(request, "state", object()), "language", None),
            "policy_checksum": POLICY_CHECKSUM,
            "build_id": BUILD_ID,
        }
        logger.info(_json.dumps(record, separators=(",", ":")))
    except Exception:
        pass
    return response


@app.get("/policy", response_class=HTMLResponse)
async def get_policy_page(request: Request):
    policy = load_compiled_policy(POLICY_PATH)
    tpl = _env.get_template("policy.html")
    csrf = _new_csrf_token()
    html = tpl.render(policy=policy, checksum=_policy_checksum(POLICY_PATH), csrf_token=csrf)
    return HTMLResponse(content=html)


@app.post("/policy/reload")
async def post_policy_reload(request: Request, csrf_token: str = Form(...), admin_token: Optional[str] = Header(None)):
    expected = os.getenv("POLICY_ADMIN_TOKEN")
    provided = (
        request.headers.get("X-Admin-Token")
        or request.headers.get("Admin-Token")
        or (admin_token or "")
    )
    if expected and provided != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")
    # basic CSRF token presence check; since we don't persist sessions, accept non-empty token
    if not csrf_token:
        raise HTTPException(status_code=400, detail="Missing CSRF token")
    # Bust cache by creating new mtime read
    policy_cache.reload_policy()
    # refresh checksum after reload
    global POLICY_CHECKSUM
    POLICY_CHECKSUM = _policy_checksum(POLICY_PATH)
    compiled = load_compiled_policy(POLICY_PATH)
    return JSONResponse({
        "status": "ok",
        "reloaded": True,
        "version": int(compiled.version),
        "checksum": POLICY_CHECKSUM,
    })

ROLE_RANK = {"viewer": 1, "analyst": 2, "admin": 3, "owner": 4}

MAX_ROWS_PER_RUN = int(os.getenv("SAFETY_MAX_ROWS", "5000"))

INTEGRATION_CATALOG: List[Dict[str, Any]] = [
    {
        "kind": "mlflow",
        "label": "MLflow Tracking",
        "description": "Sync offline runs and runtime telemetry into an MLflow experiment.",
        "fields": ["tracking_uri", "experiment_name", "api_token"],
    },
    {
        "kind": "datadog",
        "label": "Datadog Metrics",
        "description": "Emit latency, recall, and incident counts as Datadog metrics.",
        "fields": ["api_key", "app_key", "site"],
    },
    {
        "kind": "splunk",
        "label": "Splunk SIEM",
        "description": "Push audit events into Splunk for centralized detection & response.",
        "fields": ["hec_endpoint", "hec_token"],
    },
    {
        "kind": "pagerduty",
        "label": "PagerDuty Alerts",
        "description": "Trigger PagerDuty incidents when recall or latency breaches occur.",
        "fields": ["routing_key", "service"],
    },
    {
        "kind": "slack",
        "label": "Slack Notifications",
        "description": "Send evaluation summaries and alerts into Slack channels.",
        "fields": ["webhook_url", "channel"],
    },
]

RUN_STREAMS: Dict[str, List[asyncio.Queue]] = {}
RUN_EVENTS: Dict[str, List[Dict[str, Any]]] = {}
RUN_LOCK = asyncio.Lock()


@dataclass
class AuthContext:
    token: str
    tenant_id: str
    tenant_slug: str
    user_id: Optional[str]
    email: Optional[str]
    role: str


class SignUpRequest(BaseModel):
    tenant_name: constr(min_length=2, max_length=80)
    email: EmailStr
    password: constr(min_length=8, max_length=128)
    slug: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: constr(min_length=8, max_length=128)
    tenant_slug: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str = Field(alias="accessToken")
    token_type: str = Field(default="bearer", alias="tokenType")
    tenant: Dict[str, Any]
    user: Dict[str, Any]

    model_config = {
        "populate_by_name": True,
        "validate_by_name": True,
    }


class ScoreRequest(BaseModel):
    text: str
    category: Optional[str] = None
    language: Optional[str] = None
    guard: str = Field(default="candidate")


class BatchRow(BaseModel):
    text: str
    category: str
    language: str = "en"
    label: str = Field(default="unsafe")


class BatchRequest(BaseModel):
    rows: List[BatchRow]
    baseline_guard: str = "baseline"
    candidate_guard: str = "candidate"


class IntegrationRequest(BaseModel):
    kind: str
    name: Optional[str] = None
    config: Dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True


class UserCreateRequest(BaseModel):
    email: EmailStr
    password: constr(min_length=8, max_length=128)
    role: str = Field(default="viewer")


class UserUpdateRequest(BaseModel):
    role: Optional[str] = None
    status: Optional[str] = None


class RollbackRequest(BaseModel):
    manifest_id: Optional[str] = None


def enforce_rate_limit(ctx: AuthContext, scope: str) -> None:
    # Evaluate at request time so tests can toggle via env
    enabled_env = os.getenv("RATE_LIMIT_ENABLED", "true").lower() not in {"false", "0", "no"}
    if not enabled_env:
        return
    if not rate_limiter.allow(ctx.token, scope):
        RATE_LIMIT_BLOCKS.labels(scope=scope).inc()
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded for token")


def _key_from_request(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return f"token:{auth[7:]}"
    # fallback to IP or a generic bucket
    client = getattr(request, "client", None)
    host = getattr(client, "host", "unknown") if client is not None else "unknown"
    return f"ip:{host}"


def _predict_call(predict_fn, text: str, category: Optional[str], language: Optional[str]):
    trials = [
        ((text,), {}),
        ((text, category), {}),
        ((text, category, language), {}),
        ((), {"text": text, "category": category, "language": language}),
    ]
    for args, kwargs in trials:
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        try:
            return predict_fn(*args, **kwargs)
        except TypeError:
            continue
    return predict_fn(text)


def _update_circuit_after_call(guard_key: str, success: bool, latency_ms: int) -> None:
    opened = False
    if not success:
        opened = circuit_breaker.record_failure(guard_key, latency_ms=latency_ms, reason="error")
    elif circuit_breaker.latency_threshold_ms and latency_ms >= circuit_breaker.latency_threshold_ms:
        opened = circuit_breaker.record_failure(guard_key, latency_ms=latency_ms, reason="latency")
    else:
        circuit_breaker.record_success(guard_key)
    if opened:
        CIRCUIT_OPEN_COUNTER.labels(guard=guard_key).inc()


async def _invoke_guard_async(
    guard_key: str,
    guard_spec: Dict[str, Any],
    text: str,
    category: Optional[str],
    language: Optional[str],
) -> tuple[Any, int]:
    allowed, state = circuit_breaker.allow(guard_key)
    if not allowed:
        raise CircuitOpenError(guard_key, state)

    timeout = float(guard_spec.get("timeout", PREDICT_TIMEOUT_SECONDS))
    start_time = time.perf_counter()
    success = False
    latency_ms = 0
    result: Any = None
    predict_fn = guard_spec["predict"]
    loop = asyncio.get_running_loop()
    try:
        call = functools.partial(_predict_call, predict_fn, text, category, language)
        result = await asyncio.wait_for(loop.run_in_executor(PREDICT_EXECUTOR, call), timeout=timeout)
        success = True
    except (asyncio.TimeoutError, concurrent.futures.TimeoutError) as exc:
        raise PredictTimeout() from exc
    finally:
        latency_ms = max(int((time.perf_counter() - start_time) * 1000), 0)
        try:
            _update_circuit_after_call(guard_key, success, latency_ms)
        except Exception:  # pragma: no cover - defensive logging
            logger.exception("Failed to update circuit breaker for guard %s", guard_key)
    return result, latency_ms


def _invoke_guard_sync(
    guard_key: str,
    guard_spec: Dict[str, Any],
    text: str,
    category: Optional[str],
    language: Optional[str],
) -> tuple[Any, int]:
    allowed, state = circuit_breaker.allow(guard_key)
    if not allowed:
        raise CircuitOpenError(guard_key, state)

    timeout = float(guard_spec.get("timeout", PREDICT_TIMEOUT_SECONDS))
    start_time = time.perf_counter()
    success = False
    latency_ms = 0
    result: Any = None
    try:
        future = PREDICT_EXECUTOR.submit(_predict_call, guard_spec["predict"], text, category, language)
        result = future.result(timeout=timeout)
        success = True
    except concurrent.futures.TimeoutError as exc:
        raise PredictTimeout() from exc
    finally:
        latency_ms = max(int((time.perf_counter() - start_time) * 1000), 0)
        try:
            _update_circuit_after_call(guard_key, success, latency_ms)
        except Exception:  # pragma: no cover - defensive logging
            logger.exception("Failed to update circuit breaker for guard %s", guard_key)
    return result, latency_ms


def _wrap_guard_sync(guard_key: str, guard_spec: Dict[str, Any]):
    def _wrapped(text: str, category: Optional[str] = None, language: Optional[str] = None):
        result, _ = _invoke_guard_sync(guard_key, guard_spec, text, category, language)
        return result

    return _wrapped


def _predict_internal(text: str, category: Optional[str], language: Optional[str], guard: str = "candidate") -> Dict[str, Any]:
    guard_spec = _resolve_guard(guard)
    fn = _wrap_guard_sync(guard, guard_spec)
    return fn(text, category, language)


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _read_yaml_dict(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        return {}
    return data or {}


def _write_yaml_dict(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")


def _load_canary_payload() -> Optional[Dict[str, Any]]:
    if not AUTOPATCH_CANARY_PATH.exists():
        return None
    payload = _read_yaml_dict(AUTOPATCH_CANARY_PATH)
    return payload or None


def _apply_threshold_updates(base: Dict[str, Any], updates: Dict[str, float]) -> Dict[str, Any]:
    text = yaml.safe_dump(base or {}, sort_keys=False, allow_unicode=True)
    patched_text = apply_threshold_patch_to_tuned(text, updates)
    patched = yaml.safe_load(patched_text) or {}
    return patched


_VERSION_PATTERN = re.compile(r"^v?(?P<major>\d+)\.(?P<minor>\d+)$")


def _increment_policy_version(current: Optional[str]) -> str:
    current = current or "v0.0"
    match = _VERSION_PATTERN.match(current)
    if match:
        major = int(match.group("major"))
        minor = int(match.group("minor")) + 1
        return f"v{major}.{minor}"
    if current.endswith("Z"):
        return current + "+1"
    return f"{current}-1"


def _tenant_autopatch_enabled(ctx: AuthContext) -> bool:
    flag = db.get_autopatch_canary_flag(ctx.tenant_id)
    if flag is not None:
        return flag
    cfg = load_config() or {}
    tenants = cfg.get("tenants") or {}
    slug = ctx.tenant_slug or ctx.tenant_id
    if slug in tenants and isinstance(tenants[slug], dict) and "autopatch_canary" in tenants[slug]:
        return bool(tenants[slug]["autopatch_canary"])
    default_cfg = tenants.get("default", {})
    return bool(default_cfg.get("autopatch_canary", False))


def _sanitize_filename(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "-", value or "tenant")


def _manifest_path(tenant_slug: str, request_id: str) -> Path:
    _ensure_dir(AUTOPATCH_ROLLBACK_DIR)
    name = f"{_sanitize_filename(tenant_slug)}_{request_id}.json"
    return AUTOPATCH_ROLLBACK_DIR / name


def _save_manifest(tenant_slug: str, manifest: Dict[str, Any]) -> Path:
    request_id = manifest.get("request_id", uuid.uuid4().hex)
    manifest["request_id"] = request_id
    path = _manifest_path(tenant_slug, request_id)
    manifest["manifest_id"] = path.name
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return path


def _list_manifests(tenant_slug: str, limit: int = 5) -> List[Dict[str, Any]]:
    if not AUTOPATCH_ROLLBACK_DIR.exists():
        return []
    pattern = f"{_sanitize_filename(tenant_slug)}_*.json"
    manifests: List[Dict[str, Any]] = []
    for path in sorted(AUTOPATCH_ROLLBACK_DIR.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["manifest_id"] = path.name
            manifests.append(payload)
        except json.JSONDecodeError:
            continue
    return manifests


def _load_manifest(tenant_slug: str, manifest_id: Optional[str] = None) -> Dict[str, Any]:
    if manifest_id:
        path = AUTOPATCH_ROLLBACK_DIR / manifest_id
        if not path.exists():
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Rollback manifest not found")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Rollback manifest unreadable") from exc
        payload["manifest_id"] = manifest_id
        return payload

    manifests = _list_manifests(tenant_slug, limit=1)
    if not manifests:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="No rollback manifests available")
    return manifests[0]


def _run_offline_ab_check(canary_payload: Dict[str, Any]) -> tuple[bool, str]:
    return True, "offline checks stub"


def _run_shadow_check(canary_payload: Dict[str, Any]) -> tuple[bool, str]:
    return True, "shadow checks stub"


def _bump_policy_version() -> tuple[str, str]:
    cfg = _read_yaml_dict(CONFIG_FILE)
    before = cfg.get("policy_version")
    after = _increment_policy_version(before)
    cfg["policy_version"] = after
    _write_yaml_dict(CONFIG_FILE, cfg)
    return before or "", after


def _set_policy_version(version: str) -> None:
    cfg = _read_yaml_dict(CONFIG_FILE)
    cfg["policy_version"] = version
    _write_yaml_dict(CONFIG_FILE, cfg)


def _guard_catalogue() -> Dict[str, Dict[str, Any]]:
    return {
        "baseline": {
            "name": "Baseline Guard",
            "predict": baseline_predict,
            "description": "Rules-focused guard tuned for precision with tight thresholds.",
            "capabilities": ["PII", "self-harm", "extremism"],
            "latency_target_ms": 55,
            "version": "1.0.0",
        },
        "candidate": {
            "name": "Candidate Guard",
            "predict": candidate_predict,
            "description": "Transformer guard with broader coverage and adaptive thresholds.",
            "capabilities": ["jailbreak", "prompt-injection", "hate"],
            "latency_target_ms": 80,
            "version": "2.0.0",
        },
    }


GUARD_REGISTRY = _guard_catalogue()


@app.on_event("startup")
async def _startup() -> None:
    _configure_tracing()
    db.ensure_schema()
    logger.info("Safety service initialised with multi-tenant schema")


def _auth_from_token(token: str) -> AuthContext:
    record = db.resolve_token(token)
    if not record:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    role = record.get("role") or "viewer"
    return AuthContext(
        token=token,
        tenant_id=record["tenant_id"],
        tenant_slug=record.get("slug", ""),
        user_id=record.get("user_id"),
        email=record.get("email"),
        role=role,
    )


def require_auth(authorization: Optional[str] = Header(None)) -> AuthContext:
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization header")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Authorization header")
    return _auth_from_token(token)


def maybe_auth(authorization: Optional[str] = Header(None)) -> Optional[AuthContext]:
    """Return AuthContext when Authorization header is present; otherwise None.

    This enables select endpoints to operate in a public/demo mode.
    """
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    try:
        return _auth_from_token(token)
    except HTTPException:
        return None

def _require_role(ctx: AuthContext, *, minimum: str = "viewer") -> None:
    current_rank = ROLE_RANK.get(ctx.role, 0)
    required_rank = ROLE_RANK.get(minimum, 0)
    if current_rank < required_rank:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role for this operation")


async def _subscribe_run(run_id: str) -> tuple[asyncio.Queue, List[Dict[str, Any]]]:
    queue: asyncio.Queue = asyncio.Queue(maxsize=32)
    async with RUN_LOCK:
        subscribers = RUN_STREAMS.setdefault(run_id, [])
        subscribers.append(queue)
        history = list(RUN_EVENTS.get(run_id, []))
    return queue, history


async def _unsubscribe_run(run_id: str, queue: asyncio.Queue) -> None:
    async with RUN_LOCK:
        subscribers = RUN_STREAMS.get(run_id)
        if not subscribers:
            return
        if queue in subscribers:
            subscribers.remove(queue)
        if not subscribers:
            RUN_STREAMS.pop(run_id, None)


async def _broadcast_run(run_id: str, event: Dict[str, Any]) -> None:
    async with RUN_LOCK:
        history = RUN_EVENTS.setdefault(run_id, [])
        history.append(event)
        if len(history) > 50:
            del history[:-50]
        subscribers = list(RUN_STREAMS.get(run_id, []))
    for queue in subscribers:
        try:
            queue.put_nowait(event)
        except asyncio.QueueFull:
            try:
                queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                logger.debug("Dropping event for run %s due to saturated subscriber", run_id)


def _resolve_guard(choice: str) -> Dict[str, Any]:
    key = choice.strip().lower()
    if key not in GUARD_REGISTRY:
        raise HTTPException(status_code=400, detail=f"Unknown guard '{choice}'")
    return GUARD_REGISTRY[key]


def _prepare_metrics(summary: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    metrics: Dict[str, Dict[str, Any]] = {}
    for guard_key, guard_view in summary.get("guards", {}).items():
        modes = guard_view.get("modes", {})
        strict = modes.get("strict") or next(iter(modes.values()), {})
        confusion = strict.get("confusion", {})
        latency = guard_view.get("latency", {})
        metrics[guard_key] = {
            "tp": confusion.get("tp", 0),
            "fp": confusion.get("fp", 0),
            "tn": confusion.get("tn", 0),
            "fn": confusion.get("fn", 0),
            "precision": confusion.get("precision", 0.0),
            "recall": confusion.get("recall", 0.0),
            "fnr": confusion.get("fnr", 0.0),
            "fpr": confusion.get("fpr", 0.0),
            "p50_ms": int(latency.get("p50", 0)),
            "p90_ms": int(latency.get("p90", 0)),
            "p99_ms": int(latency.get("p99", 0)),
        }
    return metrics


async def _evaluate_run(
    rows: List[Dict[str, Any]],
    run_id: str,
    guard_config: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    engine = {"guards": guard_config}

    def _do_evaluate() -> Dict[str, Any]:
        return evaluate(engine, rows, policy={})

    summary = await run_in_threadpool(_do_evaluate)
    return summary


def _render_report(
    rows: List[Dict[str, Any]],
    run_id: str,
    guard_config: Optional[Dict[str, Dict[str, Any]]] = None,
    evaluation: Optional[Dict[str, Any]] = None,
) -> Path:
    report_dir = SCORECARD_ROOT / run_id / "report"
    assets_dir = SCORECARD_ROOT / run_id / "assets"
    report_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)

    guards = guard_config or _guard_catalogue()
    engine = {"guards": guards}
    evaluation = evaluation or evaluate(engine, rows, policy={})
    base_view = evaluation["guards"]["baseline"]
    cand_view = evaluation["guards"]["candidate"]

    base_preds = base_view["predictions"]
    cand_preds = cand_view["predictions"]
    base_lat = base_view["latencies"]
    cand_lat = cand_view["latencies"]

    available_modes = sorted({"strict", "lenient"} | set(base_view["modes"].keys()) | set(cand_view["modes"].keys()))
    mode_payloads: Dict[str, Any] = {}
    for mode_key in available_modes:
        base_mode = base_view["modes"].get(mode_key, base_view["modes"]["strict"])
        cand_mode = cand_view["modes"].get(mode_key, cand_view["modes"]["strict"])

        mode_payloads[mode_key] = {
            "metrics": {
                "Baseline": {
                    "precision": base_mode["confusion"]["precision"],
                    "recall": base_mode["confusion"]["recall"],
                    "fnr": base_mode["confusion"]["fnr"],
                    "fpr": base_mode["confusion"]["fpr"],
                    "recall_lo": base_mode["confusion"]["recall_lo"],
                    "recall_hi": base_mode["confusion"]["recall_hi"],
                    "fpr_lo": base_mode["confusion"]["fpr_lo"],
                    "fpr_hi": base_mode["confusion"]["fpr_hi"],
                    "latency": base_view["latency"],
                },
                "Candidate": {
                    "precision": cand_mode["confusion"]["precision"],
                    "recall": cand_mode["confusion"]["recall"],
                    "fnr": cand_mode["confusion"]["fnr"],
                    "fpr": cand_mode["confusion"]["fpr"],
                    "recall_lo": cand_mode["confusion"]["recall_lo"],
                    "recall_hi": cand_mode["confusion"]["recall_hi"],
                    "fpr_lo": cand_mode["confusion"]["fpr_lo"],
                    "fpr_hi": cand_mode["confusion"]["fpr_hi"],
                    "latency": cand_view["latency"],
                },
            },
            "matrices": {"Baseline": base_mode["confusion"], "Candidate": cand_mode["confusion"]},
            "slices": {"Baseline": base_mode["slices"], "Candidate": cand_mode["slices"]},
        }

    metrics = mode_payloads["strict"]["metrics"]
    matrices = mode_payloads["strict"]["matrices"]
    slices = mode_payloads["strict"]["slices"]

    base_clusters = cluster_failures(rows, base_preds, mode="strict")
    cand_clusters = cluster_failures(rows, cand_preds, mode="strict")
    failure_patterns = slice_failure_patterns(rows, cand_preds, mode="strict")

    runtime_offline = {f"{s['category']}/{s['language']}": s for s in slices["Candidate"]}
    runtime_summary, runtime_chart, _runtime_modalities = load_runtime_telemetry(Path("runtime_telemetry.jsonl"), assets_dir, runtime_offline)
    redteam_summary = load_redteam_summary(Path("report/redteam_cases.jsonl"))
    parity_summary = load_parity_summary(Path("report/parity.json"))
    incident_summary = load_incident_reports(Path("report"))

    histogram(base_lat, assets_dir / "latency_baseline.png", "Baseline latency")
    histogram(cand_lat, assets_dir / "latency_candidate.png", "Candidate latency")

    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    tpl = env.get_template("report.html")
    html = tpl.render(
        run_title="Scorecard",
        run_id=run_id,
        dataset_path="service",
        dataset_sha="service",
        total_samples=len(rows),
        generated_at="n/a",
        policy_version="n/a",
        engines={
            "baseline": guards["baseline"]["name"],
            "candidate": guards["candidate"]["name"],
        },
        metrics=metrics,
        matrices=matrices,
        slices=slices,
        modes=mode_payloads,
        latency_imgs={
            "baseline": os.path.relpath(assets_dir / "latency_baseline.png", report_dir),
            "candidate": os.path.relpath(assets_dir / "latency_candidate.png", report_dir),
        },
        downloads={"fn_csv": "candidate_fn.csv", "fp_csv": "candidate_fp.csv"},
        failures=[
            {"fail_type": "FN", "model": "Candidate", "category": r["category"], "language": r["language"], "text": r["text"]}
            for r, p in zip(rows, cand_preds)
            if r["label"].strip().lower() != "benign" and not p
        ],
        clusters={"Baseline": base_clusters, "Candidate": cand_clusters},
        failure_patterns=failure_patterns,
        redteam_summary=redteam_summary,
        runtime_summary=runtime_summary,
        runtime_chart=runtime_chart,
        parity_summary=parity_summary,
        incident_summary=incident_summary,
    )
    out_file = report_dir / "index.html"
    out_file.write_text(html, encoding="utf-8")

    bundle_path = SCORECARD_ROOT / run_id / f"scorecard_{run_id}.tar.gz"
    with tarfile.open(bundle_path, "w:gz") as tar:
        tar.add(report_dir, arcname="report")
        tar.add(assets_dir, arcname="assets")
    return bundle_path


def _load_rows_from_csv(file_bytes: bytes, default_category: Optional[str], default_language: Optional[str]) -> List[Dict[str, Any]]:
    try:
        text = file_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = file_bytes.decode("latin-1")
    reader = csv.DictReader(io.StringIO(text))
    rows: List[Dict[str, Any]] = []
    for raw in reader:
        text_value = (raw.get("text") or raw.get("prompt") or "").strip()
        if not text_value:
            continue
        category = (raw.get("category") or default_category or "misc").strip()
        language = (raw.get("language") or default_language or "en").strip()
        label = (raw.get("label") or "unsafe").strip() or "unsafe"
        rows.append(
            {
                "text": text_value,
                "category": category,
                "language": language,
                "label": label,
            }
        )
    if not rows:
        raise HTTPException(status_code=400, detail="CSV must contain at least one row with 'text'")
    return rows


def _summarise_candidate(metrics: Dict[str, Any]) -> str:
    recall = metrics.get("recall", 0.0)
    fnr = metrics.get("fnr", 0.0)
    return f"candidate recall={recall:.3f}, fnr={fnr:.3f}"


@app.post("/auth/signup", response_model=TokenResponse)
def signup(payload: SignUpRequest) -> TokenResponse:
    try:
        tenant = db.create_tenant(payload.tenant_name, slug=payload.slug)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    try:
        user = db.create_user(tenant["tenant_id"], payload.email, payload.password, role="owner")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    token = db.issue_token(user["user_id"], tenant["tenant_id"], label="bootstrap")
    db.create_audit_event(tenant["tenant_id"], action="tenant.signup", user_id=user["user_id"], actor_type="user", context={"email": payload.email})
    return TokenResponse(
        accessToken=token["token"],
        tenant={"id": tenant["tenant_id"], "slug": tenant["slug"], "name": tenant["name"]},
        user={"id": user["user_id"], "email": payload.email, "role": "owner"},
    )


@app.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest) -> TokenResponse:
    record = db.authenticate_user(payload.email, payload.password, tenant_slug=payload.tenant_slug)
    if not record:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = db.issue_token(record["user_id"], record["tenant_id"], label="login")
    db.create_audit_event(record["tenant_id"], action="auth.login", user_id=record["user_id"], actor_type="user", context={"email": payload.email})
    return TokenResponse(
        accessToken=token["token"],
        tenant={"id": record["tenant_id"], "slug": record["slug"], "name": record["name"]},
        user={"id": record["user_id"], "email": record["email"], "role": record["role"]},
    )


@app.get("/auth/me")
def me(ctx: AuthContext = Depends(require_auth)) -> Dict[str, Any]:
    return {
        "tenant": {"id": ctx.tenant_id, "slug": ctx.tenant_slug},
        "user": {"id": ctx.user_id, "email": ctx.email, "role": ctx.role},
    }


@app.get("/guards")
def list_guards() -> Dict[str, str]:
    # Public endpoint: return a simple mapping id -> display name for ease of discovery
    return {key: meta.get("name", key) for key, meta in GUARD_REGISTRY.items()}


@app.post("/score")
async def score_endpoint(request: ScoreRequest, ctx: Optional[AuthContext] = Depends(maybe_auth)) -> Dict[str, Any]:
    if ctx is None:
        ctx = AuthContext(
            token="public",
            tenant_id="public",
            tenant_slug="public",
            user_id=None,
            email=None,
            role="viewer",
        )
    else:
        _require_role(ctx, minimum="viewer")
    guard_spec = _resolve_guard(request.guard)
    request_id = uuid.uuid4().hex
    status_code = status.HTTP_200_OK
    response_payload: Optional[Dict[str, Any]] = None

    with tracer.start_as_current_span("score_request") as span:
        if span is not None:
            span.set_attribute("guard", request.guard)
            span.set_attribute("tenant.id", ctx.tenant_id)
            span.set_attribute("request.id", request_id)
        start_time = time.perf_counter()
        latency_ms = 0
        try:
            enforce_rate_limit(ctx, "score")
            result, latency_ms = await _invoke_guard_async(
                request.guard,
                guard_spec,
                request.text,
                request.category,
                request.language,
            )

            score_value = result.get("score")
            if score_value is None:
                prediction = result.get("prediction")
                if isinstance(prediction, (int, float)):
                    score_value = float(prediction)
                elif isinstance(prediction, bool):
                    score_value = 1.0 if prediction else 0.0
                else:
                    score_value = 0.0

            rationale = result.get("rationale") or result.get("explanation")
            slices = result.get("slices") or []

            privacy_mode = privacy_mode_for("score")
            response_payload = {
                "score": score_value,
                "slices": slices,
                "policy_version": POLICY_VERSION,
                "policy_checksum": POLICY_CHECKSUM,
                "guard_version": guard_spec.get("version", request.guard),
                "latency_ms": latency_ms,
                "request_id": request_id,
                "privacy_mode": privacy_mode,
                "input": scrub_text(request.text, mode=privacy_mode),
            }
            if rationale:
                response_payload["rationale"] = rationale

            prediction = result.get("prediction")
            if isinstance(prediction, bool):
                outcome_label = "flag" if prediction else "allow"
            else:
                outcome_label = str(prediction).strip().lower() or "unknown"
            SCORE_RESULT_COUNTER.labels(guard=request.guard, outcome=outcome_label).inc()

            db.create_audit_event(
                ctx.tenant_id,
                action="guard.score",
                resource=guard_spec["name"],
                user_id=ctx.user_id,
                context={"category": request.category, "language": request.language},
            )
        except HTTPException as http_exc:
            status_code = http_exc.status_code
            if span is not None:
                span.record_exception(http_exc)
            raise
        except CircuitOpenError as exc:
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            if span is not None:
                span.record_exception(exc)
            raise HTTPException(status_code=status_code, detail=f"Guard '{request.guard}' temporarily unavailable") from exc
        except PredictTimeout as exc:
            status_code = status.HTTP_504_GATEWAY_TIMEOUT
            if span is not None:
                span.record_exception(exc)
            raise HTTPException(status_code=status_code, detail=f"Guard '{request.guard}' timed out") from exc
        except Exception as exc:
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            if span is not None:
                span.record_exception(exc)
            logger.exception("Unexpected error during guard scoring", exc_info=exc)
            raise HTTPException(status_code=status_code, detail="Unexpected error during scoring") from exc
        finally:
            duration_ms = max(int((time.perf_counter() - start_time) * 1000), 0)
            SCORE_LATENCY.labels(endpoint="score", guard=request.guard).observe(duration_ms)
            SCORE_REQUESTS.labels(endpoint="score", guard=request.guard, status=str(status_code)).inc()
            if span is not None:
                span.set_attribute("http.status_code", status_code)
                span.set_attribute("latency_ms", duration_ms)
                span.set_attribute("request.latency_ms", latency_ms)

    assert response_payload is not None  # for mypy, unreachable when exception raised
    return response_payload


async def _process_run(
    ctx: AuthContext,
    rows: List[Dict[str, Any]],
    *,
    baseline_guard: str,
    candidate_guard: str,
) -> Dict[str, Any]:
    if len(rows) > MAX_ROWS_PER_RUN:
        raise HTTPException(status_code=400, detail=f"Row limit exceeded ({MAX_ROWS_PER_RUN})")
    enforce_rate_limit(ctx, "batch")
    baseline_spec = _resolve_guard(baseline_guard)
    candidate_spec = _resolve_guard(candidate_guard)
    guard_config = {
        "baseline": {
            "name": baseline_spec["name"],
            "predict": _wrap_guard_sync("baseline", baseline_spec),
            "version": baseline_spec.get("version"),
        },
        "candidate": {
            "name": candidate_spec["name"],
            "predict": _wrap_guard_sync("candidate", candidate_spec),
            "version": candidate_spec.get("version"),
        },
    }
    run_id = uuid.uuid4().hex[:8]
    await _broadcast_run(run_id, {"phase": "accepted", "total_rows": len(rows)})
    try:
        summary = await _evaluate_run(rows, run_id, guard_config)
    except CircuitOpenError as exc:
        await _broadcast_run(run_id, {"phase": "error", "reason": "circuit_open"})
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="Guard temporarily unavailable") from exc
    except PredictTimeout as exc:
        await _broadcast_run(run_id, {"phase": "error", "reason": "timeout"})
        raise HTTPException(status.HTTP_504_GATEWAY_TIMEOUT, detail="Guard execution timed out") from exc
    metrics_map = _prepare_metrics(summary)
    await _broadcast_run(run_id, {"phase": "metrics", "metrics": metrics_map})

    for guard_key, metrics in metrics_map.items():
        for label_name in ("tp", "fp", "tn", "fn"):
            value = metrics.get(label_name)
            if isinstance(value, (int, float)):
                BATCH_RESULT_COUNTER.labels(guard=guard_key, label=label_name).inc(float(value))

    def _render() -> Path:
        return _render_report(rows, run_id, guard_config=guard_config, evaluation=summary)

    bundle_path = await run_in_threadpool(_render)
    bundle_url = f"/scorecards/{run_id}/scorecard_{run_id}.tar.gz"
    await _broadcast_run(
        run_id,
        {
            "phase": "report_ready",
            "bundle_url": bundle_url,
        },
    )

    db.record_run(
        ctx.tenant_id,
        run_id,
        dataset_path="service/upload",
        dataset_sha="n/a",
        git_commit="n/a",
        policy_version="n/a",
        engine_baseline=baseline_spec["name"],
        engine_candidate=candidate_spec["name"],
    )
    db.upsert_metrics(run_id, ctx.tenant_id, metrics_map)
    candidate_metrics = metrics_map.get("candidate", {})
    db.store_report_record(
        ctx.tenant_id,
        run_id,
        title="Service Scorecard",
        summary=_summarise_candidate(candidate_metrics),
        path=str(bundle_path),
    )

    if candidate_metrics.get("recall", 1.0) < 0.85:
        alert = db.record_alert(
            ctx.tenant_id,
            severity="high",
            title="Candidate recall below target",
            message="Offline evaluation recall fell below 0.85 threshold",
            run_id=run_id,
            metadata={"metrics": candidate_metrics},
        )
        await _broadcast_run(run_id, {"phase": "alert", "alert": alert})

    db.create_audit_event(
        ctx.tenant_id,
        action="guard.batch_evaluate",
        resource=run_id,
        user_id=ctx.user_id,
        context={
            "rows": len(rows),
            "baseline": baseline_spec["name"],
            "candidate": candidate_spec["name"],
        },
    )

    await _broadcast_run(run_id, {"phase": "completed", "bundle_url": bundle_url, "metrics": metrics_map})

    return {
        "run_id": run_id,
        "bundle_path": str(bundle_path),
        "bundle_url": bundle_url,
        "metrics": metrics_map,
    }


@app.post("/batch")
async def batch_endpoint(request: BatchRequest, ctx: AuthContext = Depends(require_auth)) -> Dict[str, Any]:
    _require_role(ctx, minimum="analyst")
    if not request.rows:
        raise HTTPException(status_code=400, detail="rows list cannot be empty")
    rows = [row.model_dump() for row in request.rows]
    request_id = uuid.uuid4().hex
    start_time = time.perf_counter()
    status_label = "200"
    try:
        with tracer.start_as_current_span("batch_request") as span:
            if span is not None:
                span.set_attribute("tenant.id", ctx.tenant_id)
                span.set_attribute("request.id", request_id)
                span.set_attribute("baseline_guard", request.baseline_guard)
                span.set_attribute("candidate_guard", request.candidate_guard)
            payload = await _process_run(
                ctx,
                rows,
                baseline_guard=request.baseline_guard,
                candidate_guard=request.candidate_guard,
            )
    except HTTPException as exc:
        status_label = str(exc.status_code)
        raise
    except Exception as exc:
        status_label = "500"
        raise
    finally:
        duration_ms = max(int((time.perf_counter() - start_time) * 1000), 0)
        BATCH_LATENCY.labels(endpoint="batch").observe(duration_ms)
        BATCH_REQUESTS.labels(endpoint="batch", status=status_label).inc()

    return {
        "run_id": payload["run_id"],
        "bundle": payload["bundle_path"],
        "metrics": payload["metrics"],
        "policy_checksum": POLICY_CHECKSUM,
    }


@app.post("/upload-evaluate")
async def upload_evaluate(
    file: UploadFile = File(...),
    baseline_guard: str = Form("baseline"),
    candidate_guard: str = Form("candidate"),
    default_category: Optional[str] = Form(None),
    default_language: Optional[str] = Form(None),
    ctx: Optional[AuthContext] = Depends(maybe_auth),
):
    # Allow public/demo uploads when Authorization is missing; otherwise enforce analyst role
    if ctx is None:
        ctx = AuthContext(
            token="public",
            tenant_id="public",
            tenant_slug="public",
            user_id=None,
            email=None,
            role="analyst",
        )
    else:
        _require_role(ctx, minimum="analyst")
    contents = await file.read()
    rows = _load_rows_from_csv(contents, default_category, default_language)
    payload = await _process_run(
        ctx,
        rows,
        baseline_guard=baseline_guard,
        candidate_guard=candidate_guard,
    )
    privacy_mode = privacy_mode_for("upload_evaluate")
    sample_input = scrub_text(rows[0]["text"], mode=privacy_mode)
    return {
        "run_id": payload["run_id"],
        "bundle_url": payload["bundle_url"],
        "candidate_metrics": payload["metrics"].get("candidate", {}),
        "total_rows": len(rows),
        "privacy_mode": privacy_mode,
        "sample_input": sample_input,
    }


@app.get("/runs")
def list_runs_api(limit: int = 20, ctx: AuthContext = Depends(require_auth)) -> Dict[str, Any]:
    _require_role(ctx, minimum="viewer")
    runs = db.list_runs(ctx.tenant_id, limit=min(limit, 200))
    return {"runs": runs}


@app.get("/runs/{run_id}")
def run_detail(run_id: str, ctx: AuthContext = Depends(require_auth)) -> Dict[str, Any]:
    _require_role(ctx, minimum="viewer")
    metrics = db.latest_metrics(run_id)
    runs = db.list_runs(ctx.tenant_id, limit=200)
    record = next((run for run in runs if run["run_id"] == run_id), None)
    if not record:
        raise HTTPException(status_code=404, detail="Run not found for tenant")
    return {"run": record, "metrics": metrics}


@app.websocket("/ws/runs/{run_id}")
async def run_socket(websocket: WebSocket, run_id: str) -> None:
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    try:
        ctx = _auth_from_token(token)
    except HTTPException:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    await websocket.accept()
    queue, history = await _subscribe_run(run_id)
    try:
        for event in history:
            await websocket.send_json(event)
        while True:
            event = await queue.get()
            await websocket.send_json(event)
    except WebSocketDisconnect:
        pass
    finally:
        await _unsubscribe_run(run_id, queue)


@app.get("/integrations/catalog")
def integrations_catalog(ctx: AuthContext = Depends(require_auth)) -> Dict[str, Any]:
    _require_role(ctx, minimum="viewer")
    return {"catalog": INTEGRATION_CATALOG}


@app.get("/integrations")
def list_integrations_api(ctx: AuthContext = Depends(require_auth)) -> Dict[str, Any]:
    _require_role(ctx, minimum="analyst")
    return {"integrations": db.list_integrations(ctx.tenant_id)}


@app.post("/integrations")
def create_integration_api(payload: IntegrationRequest, ctx: AuthContext = Depends(require_auth)) -> Dict[str, Any]:
    _require_role(ctx, minimum="admin")
    record = db.upsert_integration(
        ctx.tenant_id,
        kind=payload.kind,
        name=payload.name,
        config=payload.config,
        enabled=payload.enabled,
    )
    db.create_audit_event(
        ctx.tenant_id,
        action="integration.create",
        resource=record["integration_id"],
        user_id=ctx.user_id,
        context={"kind": payload.kind},
    )
    return record


@app.get("/alerts")
def list_alerts_api(ctx: AuthContext = Depends(require_auth)) -> Dict[str, Any]:
    _require_role(ctx, minimum="viewer")
    return {"alerts": db.list_alerts(ctx.tenant_id, limit=50)}


@app.post("/alerts/{alert_id}/ack")
def acknowledge_alert(alert_id: str, ctx: AuthContext = Depends(require_auth)) -> JSONResponse:
    _require_role(ctx, minimum="analyst")
    db.acknowledge_alert(alert_id)
    db.create_audit_event(
        ctx.tenant_id,
        action="alert.acknowledge",
        resource=alert_id,
        user_id=ctx.user_id,
    )
    return JSONResponse({"status": "ok"})


@app.get("/audit/events")
def audit_events(ctx: AuthContext = Depends(require_auth)) -> Dict[str, Any]:
    _require_role(ctx, minimum="admin")
    return {"events": db.list_audit_events(ctx.tenant_id, limit=100)}


@app.get("/users")
def list_users_api(ctx: AuthContext = Depends(require_auth)) -> Dict[str, Any]:
    _require_role(ctx, minimum="admin")
    return {"users": db.list_users(ctx.tenant_id)}


@app.post("/users")
def create_user_api(payload: UserCreateRequest, ctx: AuthContext = Depends(require_auth)) -> Dict[str, Any]:
    _require_role(ctx, minimum="admin")
    if payload.role not in ROLE_RANK:
        raise HTTPException(status_code=400, detail="Unknown role")
    try:
        record = db.create_user(ctx.tenant_id, payload.email, payload.password, role=payload.role)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.create_audit_event(
        ctx.tenant_id,
        action="user.create",
        resource=record["user_id"],
        user_id=ctx.user_id,
        context={"role": payload.role, "email": payload.email},
    )
    return record


@app.patch("/users/{user_id}")
def update_user_api(user_id: str, payload: UserUpdateRequest, ctx: AuthContext = Depends(require_auth)) -> JSONResponse:
    _require_role(ctx, minimum="admin")
    if payload.role:
        if payload.role not in ROLE_RANK:
            raise HTTPException(status_code=400, detail="Unknown role")
        db.update_user_role(user_id, payload.role)
    if payload.status:
        db.update_user_status(user_id, payload.status)
    db.create_audit_event(
        ctx.tenant_id,
        action="user.update",
        resource=user_id,
        user_id=ctx.user_id,
        context={k: v for k, v in payload.dict().items() if v is not None},
    )
    return JSONResponse({"status": "ok"})


@app.get("/autopatch/status")
def autopatch_status(ctx: AuthContext = Depends(require_auth)) -> Dict[str, Any]:
    _require_role(ctx, minimum="viewer")
    canary = _load_canary_payload()
    enabled = _tenant_autopatch_enabled(ctx)
    policy_version = _read_yaml_dict(CONFIG_FILE).get("policy_version")
    rollbacks: List[Dict[str, Any]] = []
    for item in _list_manifests(ctx.tenant_slug or ctx.tenant_id):
        rollbacks.append(
            {
                "manifest_id": item.get("manifest_id"),
                "request_id": item.get("request_id"),
                "created_at": item.get("created_at"),
                "policy_version_before": item.get("policy_version_before"),
                "policy_version_after": item.get("policy_version_after"),
                "last_rollback_at": item.get("last_rollback_at"),
            }
        )
    return {
        "autopatch_canary": enabled,
        "policy_version": policy_version,
        "canary": canary,
        "pending_promotion": bool(canary and not canary.get("promoted_at")),
        "rollbacks": rollbacks,
    }


@app.post("/autopatch/promote")
def autopatch_promote(ctx: AuthContext = Depends(require_auth)) -> Dict[str, Any]:
    _require_role(ctx, minimum="admin")
    if not _tenant_autopatch_enabled(ctx):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="autopatch_canary disabled for this tenant")

    canary = _load_canary_payload()
    if not canary:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="No canary thresholds staged")

    canary_tenant = canary.get("tenant") or "default"
    tenant_aliases = {ctx.tenant_id, ctx.tenant_slug or ctx.tenant_id, "default"}
    if canary_tenant not in tenant_aliases:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Canary staged for a different tenant")

    updates = canary.get("threshold_updates")
    if not isinstance(updates, dict) or not updates:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Canary threshold updates missing")

    passed_ab, ab_note = _run_offline_ab_check(canary)
    if not passed_ab:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f"Offline A/B checks failed: {ab_note}")

    passed_shadow, shadow_note = _run_shadow_check(canary)
    if not passed_shadow:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f"Shadow checks failed: {shadow_note}")

    thresholds_before = _read_yaml_dict(AUTOPATCH_THRESHOLD_PATH)
    thresholds_after = _apply_threshold_updates(json.loads(json.dumps(thresholds_before)), updates)

    update_signature = hashlib.sha256(
        yaml.safe_dump(thresholds_after, sort_keys=True, allow_unicode=True).encode("utf-8")
    ).hexdigest()

    _write_yaml_dict(AUTOPATCH_THRESHOLD_PATH, thresholds_after)
    policy_before, policy_after = _bump_policy_version()

    request_id = uuid.uuid4().hex
    manifest = {
        "tenant_id": ctx.tenant_id,
        "tenant_slug": ctx.tenant_slug,
        "created_at": _now_iso(),
        "request_id": request_id,
        "policy_version_before": policy_before,
        "policy_version_after": policy_after,
        "thresholds_before": thresholds_before,
        "thresholds_after": thresholds_after,
        "canary_signature": canary.get("signature"),
        "promotion_signature": update_signature,
    }
    manifest_path = _save_manifest(ctx.tenant_slug or ctx.tenant_id, manifest)

    canary["promoted_at"] = _now_iso()
    canary["promotion_request_id"] = request_id
    canary["policy_version"] = policy_after
    canary["promotion_signature"] = update_signature
    _write_yaml_dict(AUTOPATCH_CANARY_PATH, canary)

    db.create_audit_event(
        ctx.tenant_id,
        action="autopatch.promote",
        resource=request_id,
        user_id=ctx.user_id,
        context={"policy_version": policy_after, "manifest": manifest_path.name},
    )

    return {
        "status": "promoted",
        "request_id": request_id,
        "policy_version": policy_after,
        "manifest": manifest_path.name,
        "signature": update_signature,
    }


@app.post("/autopatch/rollback")
def autopatch_rollback(
    payload: RollbackRequest | None = None,
    ctx: AuthContext = Depends(require_auth),
) -> Dict[str, Any]:
    _require_role(ctx, minimum="admin")
    manifest = _load_manifest(ctx.tenant_slug or ctx.tenant_id, manifest_id=payload.manifest_id if payload else None)
    tenant_id = manifest.get("tenant_id") or ctx.tenant_id
    if tenant_id != ctx.tenant_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Manifest belongs to a different tenant")

    thresholds_before = manifest.get("thresholds_before")
    if not isinstance(thresholds_before, dict):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Rollback manifest missing thresholds")

    policy_version_before = manifest.get("policy_version_before")
    if not isinstance(policy_version_before, str) or not policy_version_before:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Rollback manifest missing policy version")

    _write_yaml_dict(AUTOPATCH_THRESHOLD_PATH, thresholds_before)
    _set_policy_version(policy_version_before)

    canary = _load_canary_payload()
    if canary:
        canary["rolled_back_at"] = _now_iso()
        canary["rolled_back_request_id"] = manifest.get("request_id")
        _write_yaml_dict(AUTOPATCH_CANARY_PATH, canary)

    manifest["last_rollback_at"] = _now_iso()
    manifest["rolled_back_by"] = ctx.user_id
    if manifest.get("manifest_id"):
        (AUTOPATCH_ROLLBACK_DIR / manifest["manifest_id"]).write_text(
            json.dumps(manifest, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    db.create_audit_event(
        ctx.tenant_id,
        action="autopatch.rollback",
        resource=manifest.get("manifest_id"),
        user_id=ctx.user_id,
        context={"policy_version": policy_version_before},
    )

    return {
        "status": "rolled_back",
        "policy_version": policy_version_before,
        "manifest": manifest.get("manifest_id"),
    }


# Slack Integration
try:
    from integrations.slack_app import get_slack_handler
    slack_handler = get_slack_handler()
    if slack_handler:
        @app.post("/slack/events")
        async def slack_events(request: Request):
            """Handle Slack events and slash commands."""
            return await slack_handler.handle(request)
        
        logging.getLogger("service.api").info("Slack integration enabled at /slack/events")
    else:
        logging.getLogger("service.api").info("Slack integration disabled (missing config or slack-bolt)")
except ImportError:
    logging.getLogger("service.api").warning("slack-bolt not installed. Slack integration unavailable.")


@app.get("/metrics")
def metrics_endpoint() -> Response:
    payload = generate_latest()
    return Response(content=payload, media_type=CONTENT_TYPE_LATEST)


@app.get("/healthz", response_class=ORJSONResponse)
def healthz() -> Dict[str, Any]:
    cfg = load_config() or {}
    policy_version = cfg.get("policy_version") or POLICY_VERSION
    return {"status": "ok", "version": app.version, "policy_version": policy_version, "policy_checksum": POLICY_CHECKSUM, "build_id": BUILD_ID}


@app.get("/tenants/current")
def tenant_detail(ctx: AuthContext = Depends(require_auth)) -> Dict[str, Any]:
    _require_role(ctx, minimum="viewer")
    return {"tenant": {"id": ctx.tenant_id, "slug": ctx.tenant_slug}}
