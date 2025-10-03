# Quick Start Tutorial

This guided flow walks through the most common evaluation tasks:

1. authoring a policy,
2. running the obfuscation stress lab,
3. executing the adaptive red-team swarm,
4. triggering a chaos drill, and
5. bundling an evidence pack for stakeholders.

Each step assumes you have already created and activated a virtual environment and installed the project requirements.

```bash
python -m venv .venv && source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 1. Create or update the policy

Edit `policy/policy.yaml` to declare slices, thresholds, and rule sets. Validate the structure before compiling:

```bash
python -m src.policy.validate
```

If validation fails, adjust the YAML until it reports the slice summary. The candidate guard will hot-reload the compiled policy when it changes.

---

## 2. Run the obfuscation lab

Generate obfuscation hardness metrics for the slices you care about:

```bash
python -m src.obfuscation.lab --slices "violence/en,self_harm/en,malware/en" --out report/obfuscation.json
```

The results surface detection rates per operator. Open `dashboard/index.html` to visualise the hardness card.

---

## 3. Execute a red-team swarm

Launch the multi-agent swarm to probe for fresh false negatives. The example below budgets five attempts for English violence prompts:

```bash
python -m src.redteam.swarm --max-iters 100 --budget '{"violence/en": 5}'
```

New failures are written to `report/redteam_cases.jsonl` and candidate threshold suggestions are appended to `tuned_thresholds.yaml`.

---

## 4. Trigger an incident drill

Simulate a short chaos exercise (jailbreak scenario, 10 seconds at five requests/second):

```bash
python -m src.incidents.simulator --scenario jailbreak --duration 10 --rate 5
```

The drill writes `report/incident_jailbreak.json`. The dashboard incident panel reads this file automatically.

---

## 5. Build an evidence pack

Finally, create a regulator/client bundle containing the latest report, parity and obfuscation summaries, tuned thresholds, and lineage metadata:

```bash
python -m src.evidence.pack
```

The command prints the archive path (under `dist/`) along with file hashes. Share this tarball along with the `runs.jsonl` lineage log for audit trails.

---

## What next?

- Review the interactive dashboards at `dashboard/index.html` (metrics) and `dashboard/upload.html` (ad-hoc evaluations).
- Explore [Policy DSL](POLICY.md) for advanced rule writing, [Red-Team Swarm docs](../docs/REDTEAM.md) for budgeting, and [Incident Runbooks](RUNBOOKS.md) to practice mitigation steps.
