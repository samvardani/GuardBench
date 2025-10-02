# Obfuscation Lab

The obfuscation lab benchmarks the guard against systematic text mutations
(leet, zero-width, homoglyphs, emoji noise, camelCase → snake_case, etc.) and
summarises how well each slice holds up.

## Running the lab

```bash
python -m src.obfuscation.lab --slices "violence/en,self_harm/en,malware/en" --out report/obfuscation.json
```

This command:

1. Collects up to 20 seed prompts per slice from `dataset/sample.csv` and
   `data/rows.yaml`.
2. Applies each obfuscation operator to every seed.
3. Evaluates the mutated prompt with the candidate guard.
4. Writes per-operator detection rates and a "hardness" index to
   `report/obfuscation.json`.

`make validate` loads the JSON (if present) and adds an **Obfuscation Hardness**
chart to the HTML report so you can monitor drift alongside runtime telemetry
and red-team findings.

## Interpreting the metrics

- **operators[op]** – fraction of obfuscated prompts still detected by the
  guard for a given slice. Lower numbers highlight weak spots.
- **hardness.mean** – average miss rate across operators (`1 - mean(recall)`),
  useful for ranking slices that need additional hardening.

Use these insights to prioritise policy updates, red-team generation, or new
runtime mitigations.
