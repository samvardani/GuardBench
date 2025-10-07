# 3-Minute Live Demo Flow

Goal: Show end-to-end: policy → stress → evidence → API.

## 1) Open report (10s)
- Browser: http://localhost:3001/report/index.html
- Point at: Obfuscation hardness, Language parity, Incident drills.

## 2) Policy & validation (20s)
```bash
PYTHONPATH=src python -m src.policy.validate
```
- Call out: slices & thresholds, safe-context penalty.

## 3) Red-team swarm (30–40s)
```bash
PYTHONPATH=src python -m src.redteam.swarm --max-iters 25 --budget '{"violence/en":10}'
```
- “We discover FNs quickly; dedupe stops noisy duplicates.”

## 4) AutoPatch preview (20s)
```bash
PYTHONPATH=src python -m src.autopatch.run --target "violence/en"
```
- “We propose threshold updates & PR bundles, not just dashboards.”

## 5) Incident drill (20s)
```bash
PYTHONPATH=src python -m src.incidents.simulator --scenario jailbreak --duration 30 --rate 10
```
- “Scorecard goes into the same report & evidence pack.”

## 6) Runtime shadow telemetry (20s)
- Show a line from `runtime_telemetry.jsonl` (scrubbed text included).
- “Matches production flow without blocking requests.”

## 7) APIs (30s)
```bash
curl -s -X POST http://127.0.0.1:8011/score \
  -H 'Content-Type: application/json' \
  -d '{"text":"hello","category":"violence","language":"en"}' | jq .

grpcurl -plaintext -import-path src/grpc -proto score.proto \
  -d '{"text":"hello","category":"violence","language":"en","guard":"candidate"}' \
  127.0.0.1:50051 seval.ScoreService/Score
```
- “REST & gRPC fit any infra; Prometheus /metrics included.”

## 8) Evidence pack (10s)
```bash
PYTHONPATH=src python -m src.evidence.pack && ls -lh dist/
```
- “Hand this to compliance or a buyer; it’s all verifiable.”

Close with: “This reduces mean time to detection, shrinks unknown unknowns, and gives auditors what they need in one click.”
