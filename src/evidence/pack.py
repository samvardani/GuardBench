"""Generate regulator/client evidence packs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tarfile
from pathlib import Path
from typing import Dict, List

from src.utils.io_utils import git_commit

INCLUDE_PATHS = [
    Path("report/index.html"),
    Path("report/ci_slices.json"),
    Path("report/obfuscation.json"),
    Path("report/parity.json"),
    Path("tuned_thresholds.yaml"),
    Path("policy/policy.yaml"),
    Path("runs.jsonl"),
]

DIST_DIR = Path("dist")
MANIFEST_NAME = "MANIFEST.json"


def _file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def build_manifest(paths: List[Path], commit: str) -> Dict[str, object]:
    entries = []
    for path in paths:
        if path.exists():
            entries.append(
                {
                    "path": str(path),
                    "sha256": _file_hash(path),
                    "size": path.stat().st_size,
                }
            )
    manifest = {
        "commit": commit,
        "files": entries,
    }
    manifest_path = MANIFEST_NAME
    Path(manifest_path).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    manifest_hash = _file_hash(Path(manifest_path))
    manifest["manifest_sha256"] = manifest_hash
    Path(manifest_path).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def build_evidence_pack(paths: List[Path] | None = None) -> Path:
    commit = git_commit()
    paths = paths or INCLUDE_PATHS
    manifest = build_manifest(paths, commit)

    DIST_DIR.mkdir(exist_ok=True)
    archive_path = DIST_DIR / f"evidence_pack_{commit}.tar.gz"

    with tarfile.open(archive_path, "w:gz") as tar:
        for path in paths:
            if path.exists():
                tar.add(path, arcname=path.name)
        tar.add(MANIFEST_NAME)

    # Print summary
    print("Evidence pack contents:")
    for entry in manifest["files"]:
        print(f" - {entry['path']} (sha256={entry['sha256']})")
    print(f"Manifest sha256: {manifest['manifest_sha256']}")
    print(f"Archive: {archive_path}")
    return archive_path


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build evidence pack")
    parser.parse_args(argv)
    build_evidence_pack()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
