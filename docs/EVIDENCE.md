# Evidence Pack Workflow

Use the evidence pack generator to bundle regulator/client-ready artefacts for a
release.

```bash
python -m src.evidence.pack
```

This command collects:

- `report/index.html`
- `report/ci_slices.json`
- `report/obfuscation.json`
- `report/parity.json`
- `tuned_thresholds.yaml`
- `policy/policy.yaml`
- current git commit hash

A `MANIFEST.json` is created with per-file SHA256 hashes and signed with a
manifest-level hash. Everything is archived in
`dist/evidence_pack_<commit>.tar.gz` and the contents are printed to stdout for
quick verification.

Include the tarball in release artifacts or share with stakeholders requiring a
compliance evidence trail.
