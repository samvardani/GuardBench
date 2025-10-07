# Contributing

Thank you for your interest in contributing! Please follow standard GitHub workflows for PRs.

## Last-Touch Polish Checklist

Repo hygiene
- README.md updated
- CHANGELOG.md v0.3.0 entry added
- LICENSE present and attribution footer in report template
- requirements.txt includes: fastapi uvicorn python-multipart prometheus-client grpcio grpcio-tools grpcio-reflection httpx jinja2 pyyaml numpy matplotlib
- src/__init__.py exists; src/grpc_generated/__init__.py exists

Build & tests
- Headless CI sets MPLBACKEND=Agg
- pytest -q green locally; flaky markers isolated
- make grpc-gen regenerates stubs cleanly

UX polish (report)
- Apple-ish light UI: soft gray background, clean type scale, airy spacing
- Footer: “Made by SeaTechOne.com — designed by Sam Vardani”
- Empty-state cards render helpful guidance, not blank panes
- PNGs inline with alt text; lazy-loaded to keep first paint quick

Ops
- PROMETHEUS_MULTIPROC_DIR doc’d; /metrics verified under concurrent load
- Rate limiter default sensible; env var to disable for perf tests
- Evidence pack includes manifest checksums and version metadata

Security & privacy
- privacy_mode defaults to strict in sample config
- Scrubber rules cover PII tokens likely in your domain
- No raw secrets in repo (scan with git secrets or truffleHog)
