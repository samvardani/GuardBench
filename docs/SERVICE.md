# Safety Service API

The safety control plane is now a multi-tenant FastAPI application that exposes
real-time guard evaluations, reporting, and integrations. It backs the new
React dashboard (`dashboard/index.html`) and any external automation that needs
scorecards, alerts, or audit logs.

## Features at a Glance

- **Role-based access control** with tenants, owners/admins/analysts/viewers.
- **Bearer tokens** (PBKDF2 credential store + hashed API tokens).
- **Real-time runs** via WebSocket streams (`/ws/runs/<run_id>`).
- **Offline scorecards** and latency charts written to `dist/scorecards/`.
- **Integrations registry** for ML platforms, SIEM, paging, and chat systems.
- **Audit & alert pipeline** persisted to `history.db` for compliance.

## Bootstrapping a Tenant

1. Create the first tenant + owner (only needs to be done once):

   ```bash
   curl -X POST http://localhost:8000/auth/signup \
     -H 'content-type: application/json' \
     -d '{
       "tenant_name": "Enterprise Safety",
       "email": "owner@example.com",
       "password": "Sup3rSecret123"
     }'
   ```

   The response contains an `accessToken`. Save it and reuse it for API calls or
   to sign in through the dashboard (credentials are stored server-side).

2. Future sign-ins use `/auth/login`:

   ```bash
   curl -X POST http://localhost:8000/auth/login \
     -H 'content-type: application/json' \
     -d '{"email": "owner@example.com", "password": "Sup3rSecret123"}'
   ```

3. The dashboard persists the token in `localStorage` under the key
   `safety-service-auth` so the upload UI can reuse it.

## Endpoint Overview

| Method | Path | Role | Description |
| ------ | ---- | ---- | ----------- |
| `POST` | `/auth/signup` | — | Bootstrap a tenant + owner (one-time). |
| `POST` | `/auth/login` | — | Issue a bearer token for subsequent calls. |
| `GET`  | `/auth/me` | any | Inspect the current tenant/user context. |
| `GET`  | `/guards` | viewer+ | List registered guard engines and metadata. |
| `POST` | `/score` | viewer+ | Real-time scoring for a single prompt. |
| `POST` | `/batch` | analyst+ | JSON batch compare (baseline vs candidate). |
| `POST` | `/upload-evaluate` | analyst+ | CSV upload → offline evaluation → tarball. |
| `GET`  | `/runs` | viewer+ | List recent runs for the tenant. |
| `GET`  | `/runs/{run_id}` | viewer+ | Run metadata + latest metrics. |
| `WS`   | `/ws/runs/{run_id}` | viewer+ | Push events through the run lifecycle. |
| `GET`  | `/alerts` | viewer+ | Active alerts (recall breaches, etc.). |
| `POST` | `/alerts/{id}/ack` | analyst+ | Acknowledge an alert. |
| `GET`  | `/integrations` | analyst+ | List configured integrations. |
| `POST` | `/integrations` | admin+ | Register a new integration (MLflow, SIEM, PagerDuty, Slack…). |
| `GET`  | `/integrations/catalog` | viewer+ | Supported integration templates. |
| `GET`  | `/audit/events` | admin+ | Audit log feed for the tenant. |
| `GET`  | `/users` | admin+ | Enumerate tenant users and roles. |
| `POST` | `/users` | admin+ | Invite/create a new user with a role. |
| `PATCH` | `/users/{user_id}` | admin+ | Update role or deactivate a user. |
| `GET`  | `/autopatch/status` | viewer+ | Inspect staged canaries, policy version, and rollback manifests. |
| `POST` | `/autopatch/promote` | admin+ | Promote the staged canary thresholds into production after guardrails. |
| `POST` | `/autopatch/rollback` | admin+ | Restore the previous thresholds/policy version from the latest manifest. |
| `GET`  | `/tenants/current` | viewer+ | Tenant identifier (id + slug). |

All endpoints require an `Authorization: Bearer <token>` header except signup
and login. AutoPatch features are controlled per-tenant via the
`autopatch_canary` feature flag in `config.yaml` (or tenant metadata); only
tenants with the flag enabled can stage or promote canary thresholds.

## Streaming Run Telemetry

- Start an evaluation via `/batch` or `/upload-evaluate`.
- The service immediately emits `accepted` → `metrics` → `report_ready` →
  `completed` events, and sends alerts when recall breaches given thresholds.
- Connect using `ws://localhost:8000/ws/runs/<run_id>?token=<accessToken>` to
  stream JSON payloads live.

The dashboard automatically opens a WebSocket when you select a run. The event
panel renders the last 50 messages and updates the metrics grid in-place.

## Observability

- `/metrics` exposes Prometheus-compatible metrics (latency histograms, request
  counters, and confusion-matrix counts). Mount it behind an auth proxy if you
  need to secure scraping.
- Set `OTEL_EXPORTER_OTLP_ENDPOINT=https://collector:4318` (optionally
  `OTEL_EXPORTER_OTLP_INSECURE=false`) to emit traces for `/score` and `/batch`
  requests via OTLP.
- Local Prometheus + Grafana snippet (`docker-compose.yml`):

  ```yaml
  services:
    prometheus:
      image: prom/prometheus:latest
      ports:
        - "9090:9090"
      volumes:
        - ./ops/prometheus.yml:/etc/prometheus/prometheus.yml:ro

    grafana:
      image: grafana/grafana:latest
      ports:
        - "3000:3000"
      environment:
        - GF_SECURITY_ADMIN_PASSWORD=admin
      depends_on:
        - prometheus
  ```

  Add the FastAPI service as a Prometheus scrape target and point Grafana at
  the Prometheus container for dashboards. For traces, deploy an OTLP collector
  (e.g., `otel/opentelemetry-collector-contrib`) and set the environment
  variables above.

## Scorecards & Limits

- Offline runs still produce HTML reports and tarballs under
  `dist/scorecards/<run_id>/` for sharing or evidence packs.
- Use the `SAFETY_MAX_ROWS` environment variable to cap large uploads (default
  `5000`).
- Inputs are scrubbed according to the `privacy` section in `config.yaml` before
  persisting or returning a sample payload.

## Data Persistence

All multi-tenant metadata lives in `history.db`:

- `tenants`, `users`, `api_tokens` for RBAC.
- `runs`, `metrics`, `reports` for evaluation artefacts.
- `integrations`, `alerts`, `audit_events` for operational hooks.

Run `python -m src.store.init_db` to apply migrations; the service also calls it
on startup.

## Dashboard + Upload UI

- `dashboard/index.html` now handles sign-in, visualises runs/alerts/audit
  events, and lets admins configure integrations.
- `dashboard/upload.html` reuses the saved token from the dashboard and submits
  CSVs through `/upload-evaluate`. Without a token the form is disabled and a
  notice prompts you to sign in first.

## Development Tips

- Install the new dependencies:

  ```bash
  pip install -r requirements.txt
  ```

- Launch the API with auto-reload:

  ```bash
  uvicorn src.service.api:app --reload
  ```

- When running tests, a temporary database is created via the helper fixtures to
  avoid polluting `history.db`.

- Tailor alerts or guard risk scoring by adjusting `config.yaml` and the policy
  weights passed into `evaluate`.

## Local Run (tuning)

```bash
export PYTHONPATH=src
export RATE_LIMIT_ENABLED=false
export PREDICT_MAX_WORKERS=32
uvicorn service.api:app --host 127.0.0.1 --port 8010 --workers 4 --timeout-keep-alive 5 --log-level warning
```

See also: [Configuration & Tuning](./CONFIG.md) and `config.example.yaml` for runtime knobs.
