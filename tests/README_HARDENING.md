# Hardening Test Suite

## Overview

The hardening test suite implements **production-grade quality gates** for the safety-eval-mini platform. These tests enforce critical requirements around provenance tracking, observability, accuracy, and security.

## Gates

### 1. Provenance Coverage (100%)
**File:** `test_hardening_provenance.py`

**Requirement:** ALL REST responses and gRPC trailers must include policy metadata.

**Headers/Trailers Required:**
- REST: `X-Policy-Version`, `X-Policy-Checksum`
- gRPC: `x-policy-version`, `x-policy-checksum`

**Why:** Supply-chain provenance for governance and audit.

### 2. Trace ID Validation (≥99.9%)
**File:** `test_hardening_traceid.py`

**Requirement:** ≥99.9% of gRPC responses must include a non-zero `x-trace-id` trailer.

**Format:** 32-character hex string (OpenTelemetry trace ID)

**Why:** Distributed tracing for debugging and incident investigation.

### 3. Over-Defense Control (≤1.0%)
**File:** `test_hardening_overdefense.py`

**Requirement:** False positive rate on safe prompts ≤ `OVERDEFENSE_TARGET` (default 1.0%).

**Test Set:** 50+ curated safe prompts (educational, professional, benign content)

**Why:** Prevents over-blocking legitimate use cases.

### 4. Injection Detection
**File:** `test_hardening_injection.py`

**Requirements:**
- **TPR ≥ 0.80** - True Positive Rate on injection attacks
- **FPR ≤ 1.0%** - False Positive Rate on benign instructions

**Attack Types Tested:**
- Ignore previous instructions
- Jailbreak attempts
- Context injection
- Obfuscated harmful content
- Authority hijacking

**Why:** Ensures robust detection of adversarial prompt injection.

## Running Tests

### Run All Gates
```bash
# Execute all hardening gates and generate report
python tests/run_hardening.py
```

### Run Individual Test Files
```bash
# Provenance coverage
PYTHONPATH=src pytest tests/test_hardening_provenance.py -v

# Trace ID validation
PYTHONPATH=src pytest tests/test_hardening_traceid.py -v

# Over-defense metrics
PYTHONPATH=src pytest tests/test_hardening_overdefense.py -v

# Injection detection
PYTHONPATH=src pytest tests/test_hardening_injection.py -v
```

### Custom Over-Defense Target
```bash
# Set stricter threshold (0.5%)
OVERDEFENSE_TARGET=0.5 python tests/run_hardening.py
```

## CI Integration

The hardening gates run automatically in CI on:
- Push to `main`, `release/*`, `hardening/*` branches
- All pull requests

**CI Job:** `hardening` (runs after standard tests)

**Artifacts Generated:**
- `docs/HARDENING_REPORT.md` - Full gate status
- `grpc_server.log` - Server logs for debugging

**Failure Behavior:** CI fails if any gate is not met.

## Report

After running `tests/run_hardening.py`, view the comprehensive report:

```bash
cat docs/HARDENING_REPORT.md
```

The report includes:
- ✅/❌ status for each gate
- Actual vs. threshold values
- Detailed metrics breakdown
- Per-epic PASS/FAIL summary

## Contract Enforcement

### Immutable Public Contracts

The following APIs are **protected** and cannot be removed or changed:

**REST Endpoints:**
- `POST /score`
- `POST /batch-score`
- `GET /healthz`
- `GET /metrics`
- `GET /guards`

**gRPC Methods:**
- `rpc Score(ScoreRequest) returns (ScoreResponse)`
- `rpc BatchScore(BatchScoreRequest) returns (BatchScoreResponse)`
- `rpc BatchScoreStream(BatchScoreRequest) returns (stream StreamItem)`

**Required Metadata:**
- REST: `X-Policy-Version`, `X-Policy-Checksum` headers
- gRPC: `x-policy-version`, `x-policy-checksum`, `x-trace-id` trailers

### Security Defaults

**Protected:**
- ✅ gRPC reflection: DISABLED by default
- ✅ Models/rules: NOT exposed in APIs
- ✅ Policy: Read-only with CSRF protection

## Development Workflow

### Before Committing

```bash
# 1. Run hardening tests locally
python tests/run_hardening.py

# 2. Check report
cat docs/HARDENING_REPORT.md

# 3. Fix any failures
# ...

# 4. Verify all gates pass
python tests/run_hardening.py && echo "✅ Ready to commit"
```

### Adding New Gates

1. Create test file: `tests/test_hardening_<name>.py`
2. Implement test class with assertions
3. Add metric computation function
4. Update `tests/run_hardening.py` HARDENING_GATES list
5. Update `docs/HARDENING_REPORT.md` template

### Modifying Thresholds

**Environment Variables:**
- `OVERDEFENSE_TARGET` - Default: 1.0 (%)
- (Add more as needed)

**In Code:**
Update `HARDENING_GATES` in `tests/run_hardening.py`

## Troubleshooting

### gRPC Server Not Running
```bash
# Start server manually
PYTHONPATH=src python src/grpc/server.py
```

### Trace ID All Zeros
- Check OpenTelemetry initialization
- Verify interceptor is applied
- Ensure `tracer.start_as_current_span()` is used

### High Over-Defense Rate
- Review safe context detection
- Check threshold values in `policy/policy.yaml`
- Examine false positive prompts

### Low Injection Detection
- Add more injection patterns to guard
- Improve obfuscation detection
- Update policy rules

## Architecture

```
tests/
├── test_hardening_provenance.py   # Provenance coverage
├── test_hardening_traceid.py      # Trace ID validation
├── test_hardening_overdefense.py  # Over-defense metrics
├── test_hardening_injection.py    # Injection detection
├── run_hardening.py               # Test runner & report generator
└── README_HARDENING.md            # This file

docs/
└── HARDENING_REPORT.md            # Auto-generated report

.github/workflows/
└── ci.yml                         # CI with hardening job
```

## Metrics

Each test file exports a `compute_*_metrics()` function that returns:
- Coverage percentages
- Pass/fail counts
- Detailed breakdowns

The test runner aggregates these and generates the final report.

## Exit Codes

- `0` - All gates passed
- `1` - One or more gates failed

Use in scripts:
```bash
python tests/run_hardening.py && ./deploy.sh || echo "Hardening failed, blocking deploy"
```

## Future Gates (Planned)

- **Latency SLO:** P95 < 50ms for /score endpoint
- **Memory Leak:** No growth over 1000 requests
- **Concurrency:** Handle 100 concurrent requests
- **Policy Consistency:** Baseline vs Candidate delta < 5%
- **Multi-Language Parity:** Recall variance < 10% across languages

---

**Last Updated:** 2025-10-09  
**Maintainer:** Safety-Eval Team  
**CI Status:** ![CI](https://github.com/samvardani/safety-eval-mini/workflows/CI/badge.svg)

