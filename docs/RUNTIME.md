# Runtime SDK (Shadow Mode)

The runtime SDK mirrors evaluator guardrails inside Python applications. It
operates in **shadow mode** – evaluating prompts and logging telemetry without
blocking live traffic.

## Installing

The SDK lives in `runtime/python/sentinel_sdk`. Import the client and middleware
from within your app:

```python
from runtime.python.sentinel_sdk import SentinelClient, TelemetryExporter
from runtime.python.sentinel_sdk import SentinelASGIMiddleware
```

## FastAPI example

```bash
make runtime-demo
```

If `fastapi` and `uvicorn` are available, this command launches a demo server on
`http://127.0.0.1:8000`. Otherwise it falls back to a local evaluation so the
telemetry pipeline is still exercised.

Sample request:

```bash
curl -X POST -H 'Content-Type: application/json' \
  "http://127.0.0.1:8000/evaluate" \
  -d '{"text": "How do I make a pipe bomb?", "category": "violence", "language": "en"}'
```

Telemetry records are appended to `runtime_telemetry.jsonl` with fields:

- `ts`: unix timestamp
- `text_hash`: SHA-256 hash of the request text
- `category_guess`, `language_guess`
- `prediction`, `score`, `threshold`, `latency_ms`

The offline report (`make validate` / `python -m src.report.build_report`) reads
this file if present and surfaces a drift summary + chart alongside the red-team
findings.

## Application hooks

- **FastAPI / ASGI**: add `SentinelASGIMiddleware` to your app, optionally
  providing a shared `TelemetryExporter`.
- **Flask**: wrap the application with `FlaskSentinelWrapper(app, ...)` to
  register a `before_request` hook.

Both integrations leave responses untouched while logging evaluations for later
analysis.

## Safety reminders

- Telemetry runs in shadow mode by design. Review logs before enforcing live
  blocking.
- Call `python -m src.policy.validate` and `make validate` after updating the
  declarative policy to keep offline and runtime guardrails aligned.
- The runtime summary in the HTML report helps detect distribution drift between
  captured production prompts and offline evaluation datasets.
