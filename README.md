## SafetyEval — real-time safety scoring with REST, gRPC, shadow telemetry, chaos drills, evidence packs

SafetyEval is an embeddable AI safety engine. It provides low-latency safety scoring via REST and gRPC, operational telemetry for shadow traffic, chaos/incident drills, and signed evidence packs for governance.

### Quickstart (one screen)

```bash
# Create venv (Python 3.13 recommended)
python -m venv .venv && source .venv/bin/activate

# Install deps
pip install -r requirements.txt -r requirements-dev.txt

# Generate gRPC stubs
python -m grpc_tools.protoc -I src/grpc_service \
  --python_out=src/grpc_generated \
  --grpc_python_out=src/grpc_generated \
  src/grpc_service/score.proto

# Start REST API (port 8001)
PYTHONPATH=src uvicorn service.api:app --host 0.0.0.0 --port 8001 --workers 4
# Health
curl -s http://127.0.0.1:8001/healthz | jq .

# Start gRPC server (in another tab)
PYTHONPATH=$(pwd) python -m src.grpc.server

# grpcurl (using the local proto — no reflection required)
grpcurl -plaintext \
  -import-path src/grpc \
  -proto score.proto \
  -d '{"text":"hello","category":"violence","language":"en","guard":"candidate"}' \
  127.0.0.1:50051 seval.ScoreService/Score

grpcurl -plaintext \
  -import-path src/grpc \
  -proto score.proto \
  -d '{"items":[{"text":"a","category":"violence","language":"en","guard":"candidate"}]}' \
  127.0.0.1:50051 seval.ScoreService/BatchScore

# gRPC Health (standard)
mkdir -p src/grpc_service/google/grpc/health/v1 && \
curl -fsSL https://raw.githubusercontent.com/grpc/grpc/v1.64.0/src/proto/grpc/health/v1/health.proto \
  -o src/grpc_service/google/grpc/health/v1/health.proto
grpcurl -plaintext \
  -import-path src/grpc \
  -proto google/grpc/health/v1/health.proto \
  -d '{}' 127.0.0.1:50051 grpc.health.v1.Health/Check
```

Tips:
- Enable server reflection for grpcurl discovery: `ENABLE_GRPC_REFLECTION=true python -m src.grpc.server`
- TLS for gRPC: run `tools/mkdevcert.sh`, then `make grpc-serve-tls`; probe with `grpcurl -cacert certs/server.crt localhost:5443 grpc.health.v1.Health/Check`.

### Performance note

Local Apple Silicon (M3) single-node benchmark using `ghz`:

```text
Throughput (gRPC): ~7.3k req/s (16 conns, 5k requests)
Latency: avg 2.13 ms, p95 2.27 ms, p99 2.41 ms
Health/Reflection: Health OK; reflection optional — prefer local protos with grpcurl
```

Actual throughput and latency vary by hardware, guard configuration, and workload mix.

### How to test

**Quick Test**: `PYTHONPATH=src MPLBACKEND=Agg pytest -q`

**With Coverage**: `pytest --cov=src --cov-report=html` → `open htmlcov/index.html`

**Quality Gates**: `pre-commit run --all-files` (ruff, mypy, tests)

See [TESTING.md](docs/TESTING.md) for comprehensive guide, coverage requirements, and CI configuration.

- **Unit/API**: `MPLBACKEND=Agg PYTHONPATH=src pytest -q`
- **Coverage**: `pytest --cov=src --cov-fail-under=70`
- **Linting**: `ruff check src/ tests/`
- **Type Check**: `mypy src/ --ignore-missing-imports`
- **REST Smoke**:
  - `curl -sf http://127.0.0.1:8011/healthz`
  - `curl -s -X POST http://127.0.0.1:8011/score -H 'Content-Type: application/json' -d '{"text":"hello","category":"violence","language":"en"}'`
  - `curl -sf http://127.0.0.1:8011/metrics | head`
- **gRPC Smoke**:
  - `grpcurl -plaintext -import-path src/grpc -proto google/grpc/health/v1/health.proto -d '{}' 127.0.0.1:50051 grpc.health.v1.Health/Check`
  - `grpcurl -plaintext -import-path src/grpc -proto score.proto -d '{"text":"hello","category":"violence","language":"en","guard":"candidate"}' 127.0.0.1:50051 seval.ScoreService/Score`
- **Load**:
  - REST: `export RATE_LIMIT_ENABLED=false` then run your load tool against `/score`
  - gRPC: `make load-grpc`

### Architecture

```text
          +-------------------+
          |  Clients/Apps     |
          +---------+---------+
                    |
        +-----------v------------+
        | REST (FastAPI) / gRPC  |
        +-----------+------------+
                    |
              +-----v-----+
              |  Guards   |  (baseline, candidate, etc.)
              +-----+-----+
                    |
          +---------v-----------+
          | Policy compiler +   |
          | cache, slices, thrs |
          +---------+-----------+
                    |
     +--------------v--------------+
     | Decision + slices + metadata |
     +-------+-----------+---------+
             |           |
     +-------v--+   +--- v ------+
     | Prometheus|   | JSON logs |
     | /metrics  |   | (structured)
     +-----------+   +-----------+

     +-----------+
     | Evidence  |  (SBOM + signed manifest)
     | packs     |
     +-----------+
```

### Why teams use it

- Governance evidence packs: SBOM, manifest signing (ed25519), verification CLI
- Obfuscation lab: evaluate robustness to prompt obfuscation
- Multilingual parity: identify slices with recall deltas and suggested actions
- Incident drills: chaos/scenario simulators with shadow telemetry
- Webhook/alerts: hook into your monitoring stack for thresholds and incidents

### Production hardening checklist

- TLS for gRPC (env flags) and conditional server reflection
- Prometheus metrics on REST and gRPC (same registry) exposed at `/metrics`
- Autoscaling via containerization; multi-stage Dockerfile and docker-compose provided
- Structured JSON logging with request IDs
- Rate limiting (token/IP), CORS allowlist, JSON body size limits, security headers
- Policy hot-reload with checksum and CSRF; immutable policy checksum in responses
- CI workflow (pytest, lint, typecheck) with gRPC stub generation
- Evidence: SBOM generation and signed manifests (verification subcommand)

### License & contact

Licensed under the MIT License. See `LICENSE`.

Made by SeaTechOne LLC — Developed by Saeed M. Vardani

# Safety Eval Mini

One-screen harness to compare a Baseline vs. Candidate safety guard.

- Reproducible runs (run_id + dataset SHA + git commit)
- HTML report (KPIs, confusion, latency, failures)
- Threshold sweep (precision/recall trade-off)
- SQLite history
- Multi-tenant FastAPI service with RBAC, real-time telemetry, integrations, and audit logs

## Quick Start
```bash
python -m venv .venv && source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
make demo   # compare + report + sweep
```

### Quick Start HTTP

```bash
# Start the HTTP API locally (FastAPI + Uvicorn)
PYTHONPATH=src uvicorn service.api:app --host 127.0.0.1 --port 8001

# Health
curl -sf http://127.0.0.1:8001/healthz | jq .

# Score
curl -sf -X POST http://127.0.0.1:8001/score \
  -H 'Content-Type: application/json' \
  -d '{"text":"hello","category":"violence","language":"en"}' | jq .
```

- Gate: tuned per-slice thresholds in `config.yaml`; stricter overrides in `gate.json`.

## Documentation

- [Getting Started](docs/GETTING_STARTED.md): environment setup, validation flow, serving reports, CI expectations.
- [Red-Team Swarm](docs/REDTEAM.md): adaptive red-team workflow, budgets, and outputs.
- [AutoPatch](docs/AUTOPATCH.md): generate candidate patches, run A/B validation, and stage a PR bundle.
- [Policy DSL](docs/POLICY.md): declarative guard rules, validation, and compilation pipeline.
- [Obfuscation Lab](docs/OBFUSCATION.md): stress suite metrics and hardness charts.
- [Multilingual Parity](docs/MULTILINGUAL.md): language recall checks and targets.
- [Incident Runbooks](docs/RUNBOOKS.md): chaos drill guidance and mitigation steps.
- [Evidence Packs](docs/EVIDENCE.md): bundle reports, policy, and telemetry for regulators.
- [Service API](docs/SERVICE.md): local FastAPI endpoints for scoring and batch scorecards.
- Embedding (SDK):

```python
from seval import predict, batch_predict

r = predict("hello", "violence", "en", guard="candidate")
rows = [{"text":"hi","category":"violence","language":"en"}]
rs = batch_predict(rows, guard="candidate")
```

- gRPC Guide:

```bash
python -m grpc_tools.protoc -I grpc --python_out=src/grpc_generated --grpc_python_out=src/grpc_generated grpc/score.proto
PYTHONPATH=src python -m src.service.grpc_server
```

### gRPC usage (Python client)

```python
import asyncio
import grpc
from src.grpc_generated import score_pb2, score_pb2_grpc

async def main():
    async with grpc.aio.insecure_channel("127.0.0.1:50051") as channel:
        stub = score_pb2_grpc.ScoreServiceStub(channel)
        req = score_pb2.ScoreRequest(text="hello", category="violence", language="en", guard="candidate")
        resp = await stub.Score(req)
        print(resp)

if __name__ == "__main__":
    asyncio.run(main())
```
- [Interactive Dashboard](dashboard/index.html): sign in to monitor runs in real time, manage integrations, review alerts, and stream guard telemetry.
- [Dataset Upload UI](dashboard/upload.html): reuse your dashboard token to upload prompt CSVs, trigger evaluations, and download scorecards.

## Documentation Portal

Render the consolidated site with MkDocs (includes Quick Start, policy, obfuscation, parity, runbooks, evidence, and service guides):

```bash
mkdocs serve
# → http://127.0.0.1:8000/
```

## Containerisation & Deployment

Build the production image (Gunicorn + Uvicorn workers) and run the API, background worker, and static dashboard via Docker Compose:

```bash
docker compose up --build
# API → http://localhost:8000
# Dashboard → http://localhost:3000
```

Run detached with healthchecks and volumes mounted for artifacts:

```bash
docker compose up -d
# Inspect health
docker compose ps
```

The API exposes `/healthz` for liveness/readiness and `/metrics` for Prometheus scraping. The `report/` and `dist/` directories are mounted as volumes so reports and tarballs persist on the host.

Each service mounts the `report/` and `dist/` directories so scorecards and artefacts persist on the host. The worker currently emits heartbeats and is the recommended hook for future scheduled jobs (red-team sweeps, telemetry sync, etc.).

## Working with the dataset

- New evaluation rows live in `data/rows.yaml` (YAML list). Keep the minimal
  shape of `text`, `category`, `language`, and `label`; any extra metadata is
  preserved in the report and red-team generator.
- After editing, run the loader smoke test: `pytest tests/test_dataset_schema.py -q`.

## Validation + report

```bash
export MPLBACKEND=Agg MPLCONFIGDIR=/tmp/mpl
make validate  # compare -> report -> ci gate
```

- When the gate fails, inspect `dashboard/index.html` (after regenerating artifacts). Serve it locally via:

  ```bash
  make serve-report
  # → Open http://localhost:8000/dashboard/index.html
  ```
