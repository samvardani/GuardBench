from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    root = Path(os.getcwd())
    entries = []
    for p in root.rglob("*"):
        if p.is_file() and ".venv" not in p.parts and ".git" not in p.parts:
            try:
                entries.append({"path": str(p.relative_to(root)), "sha256": sha256_file(p), "size": p.stat().st_size})
            except Exception:
                continue
    dist = root / "dist"
    dist.mkdir(exist_ok=True)
    out = dist / "sbom.json"
    out.write_text(json.dumps({"files": entries}, indent=2), encoding="utf-8")
    print(str(out))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())



