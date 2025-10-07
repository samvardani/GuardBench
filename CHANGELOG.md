# Changelog

## v0.3.0 — “Telemetry & gRPC”

### Added
- gRPC service (Score, BatchScore) + health checks; optional reflection.
- Prometheus counters for gRPC; surfaced via REST /metrics.
- Privacy-aware prompt logging in runtime exporter.
- New multi-turn conversation harness samples (support, extortion).

### Improved
- Red-team deduper catches zero-width obfuscations (\u200b) reliably.
- NotificationManager robust to non-JSONable errors (logs instead of failing).
- Obfuscation lab, parity JSON feed into dashboard & report.
- Make targets for gRPC (grpc-gen, grpc-serve, grpc-client) and CLI helpers.

### Fixed
- Policy validation drift between guard/runtime; CI runs DSL check before report.
- Headless build stability (switch to non-GUI Matplotlib backend when needed).

### Artifacts
- Evidence pack includes report + obfuscation/parity/incidents + manifest checksums.
