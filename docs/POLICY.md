# Declarative Policy DSL

The guard now loads its detection logic from `policy/policy.yaml`, a declarative
format that describes slices, rules, safe-context exclusions, and actions. The
policy is compiled at runtime into efficient structures used by
`src/guards/candidate.py`.

## Structure

```yaml
version: 1
safe_contexts:
  - id: support_terms
    type: regex
    patterns:
      - "\\btherapy\\b"
      - "\\bprevention\\b"
penalties:
  safe_context: 0.8
slices:
  - category: violence
    language: en
    threshold: 0.99
    rules:
      - id: violence_keywords
        weight: 1.0
        action: block
        match:
          regex:
            - "\\bkill\\b"
      - id: violence_substrings
        weight: 1.0
        action: block
        match:
          substrings:
            - makeabomb
```

Key concepts:

- **Slices** are `(category, language)` pairs with independent thresholds and
  rule stacks.
- **Rules** declare regex and/or substring matches with a weight contribution
  and action (currently `block`, with future room for `warn`, `route`, or
  `escalate`).
- **Safe contexts** apply a penalty when matched, reducing the score before the
  threshold comparison.

## Validation

Run the validator before committing changes:

```bash
python -m src.policy.validate
```

The CLI prints a summary of slices and total rule counts. The CI workflow also
runs this validation, failing the build if the policy is malformed.

## Compilation

`src/policy/compiler.py` loads the YAML, validates it, and produces
`CompiledPolicy` objects containing compiled regex patterns and lower-cased
substrings. The candidate guard uses these compiled slices when available,
falling back to legacy in-code patterns if the policy file is missing.

## Migration Notes

- Thresholds in `policy/policy.yaml` mirror `config.yaml` slice thresholds. The
  guard still respects `config.yaml` for backward compatibility, but policy
  thresholds take precedence.
- Existing hard-coded patterns remain as a fallback path to ease incremental
  migration. Update the YAML to adjust weights or add additional rules instead
  of editing the guard directly.
- Policy actions currently map to the guard’s block/allow decision; future work
  can extend `src/policy/actions.py` to integrate warnings or routing hooks.
