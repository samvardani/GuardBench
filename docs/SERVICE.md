# Safety Service API

A FastAPI application exposes the guard as a local service.

## Running

```bash
make service
```

Two endpoints:

- `POST /score` → `{text, category?, language?}` returns guard prediction, score,
  and threshold.
- `POST /batch` → `{rows: [{text, category, language, label}]}` evaluates the
  batch, renders an HTML scorecard (same pipeline as the main report), and
  returns the path to a bundled tarball.

Example smoke test (requires the service to be running):

```bash
make service-test
```

## Output

Batch requests produce `dist/scorecards/<run_id>/` containing:

- `report/index.html` – rendered via the standard report template
- `assets/` – latency charts
- `scorecard_<run_id>.tar.gz` – bundle of the above, referenced in the API
  response

Use these bundles for ad-hoc analyses or to share evidence with clients without
re-running the entire offline pipeline.
