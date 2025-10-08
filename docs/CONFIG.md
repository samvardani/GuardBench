# Configuration & Tuning

This project supports simple environment variable tuning for the service, with an optional example YAML (`config.example.yaml`) you can copy from.

## Environment Variables

Set before launching Uvicorn (or in `.env` you source locally):

- PYTHONPATH: `src`
- PREDICT_MAX_WORKERS: per-process predictor pool (default 8–32 local, higher on servers)
- PREDICT_TIMEOUT_SECONDS: guard call timeout (default 2.0)
- RATE_LIMIT_ENABLED: `true|false` (disable during load tests)
- TOKEN_RATE_LIMIT / TOKEN_RATE_WINDOW_SECONDS: token budget and window
- UVICORN_*: host, port, workers, timeout_keep_alive, log level
- REDIS_URL: optional rate limiter backend
- OTEL_EXPORTER_OTLP_ENDPOINT: optional tracing endpoint
- KAFKA_BROKERS / KAFKA_REST_PROXY: optional messaging egress

Example:
```bash
export PYTHONPATH=src
export PREDICT_MAX_WORKERS=32
export RATE_LIMIT_ENABLED=false
uvicorn service.api:app --host 127.0.0.1 --port 8010 --workers 4 --timeout-keep-alive 5 --log-level warning
```

## YAML Example

`config.example.yaml` includes a `runtime:` section with `uvicorn`, `predictor`, `rate_limit`, `tracing`, `redis`, and `kafka` keys. Treat it as a reference; environment variables take precedence.

## Recommendations

- Local M3:
  - `--workers 4`, `PREDICT_MAX_WORKERS=32`, `RATE_LIMIT_ENABLED=false`
- Small VM:
  - `--workers 4–6`, `PREDICT_MAX_WORKERS=32–64`, enable rate limiting for multi-user
- Production:
  - Front by ingress, HPA-enabled; configure Redis for rate limiting, OTEL for tracing
