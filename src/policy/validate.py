"""CLI to validate policy.yaml and emit summary statistics."""

from __future__ import annotations

import argparse
from pathlib import Path

from .compiler import load_compiled_policy, POLICY_PATH


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate policy.yaml")
    parser.add_argument("--path", type=str, default=str(POLICY_PATH))
    args = parser.parse_args(argv)

    policy_path = Path(args.path)
    compiled = load_compiled_policy(policy_path)

    print(f"Policy path: {policy_path}")
    print(f"Safe context patterns: {len(compiled.safe_context_patterns)} (penalty={compiled.safe_context_penalty})")
    print("Slices:")
    for (category, language), slice_ in sorted(compiled.slices.items()):
        print(f"  - {category}/{language}: threshold={slice_.threshold:.2f}, rules={len(slice_.rules)}")
    print(f"Total slices: {len(compiled.slices)}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
