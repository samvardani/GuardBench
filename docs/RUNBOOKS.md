# Incident Runbooks

This document outlines mitigation guidance for common safety incidents exercised
by `src.incidents.simulator`.

## Jailbreak Flood

1. **Detect:** Monitor runtime telemetry and red-team swarm alerts for a sudden
   spike in jailbreak-style prompts.
2. **Mitigate:**
   - Run `python -m src.incidents.simulator --scenario jailbreak ...` to gauge
     impact.
   - Execute `make autopatch` targeting affected slices (usually `violence/en`).
   - Deploy stricter policy thresholds or immediate block rules if residual risk
     remains above 5%.
3. **Communicate:** Notify on-call safety lead and log incident in response
   tracker.

## PII Burst

1. **Detect:** Check telemetry for `pii` slice recall drops or runtime residual
   risk > 0.05.
2. **Mitigate:**
   - Generate fresh prompts via `src.multilingual.parity` to confirm language
     coverage.
   - Lower thresholds for `pii/en` using AutoPatch, and add specific regexes for
     leaking patterns.
   - Coordinate with legal/compliance if user data exposure suspected.
3. **Post-incident:** Backfill dataset with newly observed prompts and rerun
   obfuscation lab to ensure robustness.

## Obfuscation Swarm

1. **Detect:** Obfuscation hardness chart shows spike in miss rate; incident
   simulator reproduces scenario.
2. **Mitigate:**
   - Extend policy regex/substrings to catch the new obfuscation.
   - Regenerate red-team variants with the adaptive swarm (focus on hardened
     operators).
   - Validate via obfuscation lab and rerun `make validate`.

## General Steps

- Always capture metrics with `report/incident_<scenario>.json` and attach to the
  incident log.
- Rebuild `report/index.html` to confirm detection/mitigation timelines improve
  post-response.
- Update policy and runtime telemetry dashboards accordingly.
