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
    Path("dist/sbom.json"),
]

DIST_DIR = Path("dist")
MANIFEST_NAME = "MANIFEST.json"
SIGNATURE_NAME = "manifest.sig"


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
    # compute digest over canonical json (excluding manifest_sha256 itself)
    canonical = json.dumps(manifest, separators=(",", ":")).encode("utf-8")
    manifest_hash = hashlib.sha256(canonical).hexdigest()
    manifest["manifest_sha256"] = manifest_hash
    Path(manifest_path).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def build_evidence_pack(paths: List[Path] | None = None) -> Path:
    commit = git_commit()
    paths = paths or INCLUDE_PATHS
    manifest = build_manifest(paths, commit)

    # Optional ed25519 signature using PyNaCl or libsodium-compatible
    sign_key = os.getenv("EVIDENCE_SIGN_KEY")
    signature_hex: str | None = None
    if sign_key:
        try:
            from nacl.signing import SigningKey  # type: ignore
        except Exception:
            print("PyNaCl not installed; skipping signing")
        else:
            try:
                key = SigningKey(bytes.fromhex(sign_key))
                payload = json.dumps(
                    {k: v for k, v in manifest.items() if k != "manifest_sha256"},
                    separators=(",", ":"),
                ).encode("utf-8")
                sig = key.sign(payload).signature
                signature_hex = sig.hex()
                Path(SIGNATURE_NAME).write_text(signature_hex, encoding="utf-8")
            except Exception as e:
                print(f"Signing failed: {e}")

    DIST_DIR.mkdir(exist_ok=True)
    archive_path = DIST_DIR / f"evidence_pack_{commit}.tar.gz"

    with tarfile.open(archive_path, "w:gz") as tar:
        for path in paths:
            if path.exists():
                tar.add(path, arcname=path.name)
        tar.add(MANIFEST_NAME)
        if Path("manifest.sig").exists():
            tar.add("manifest.sig")
        if Path(SIGNATURE_NAME).exists():
            tar.add(SIGNATURE_NAME)

    # Print summary
    print("Evidence pack contents:")
    for entry in manifest["files"]:
        print(f" - {entry['path']} (sha256={entry['sha256']})")
    print(f"Manifest sha256: {manifest['manifest_sha256']}")
    if Path(SIGNATURE_NAME).exists():
        print(f"Signature: {Path(SIGNATURE_NAME).read_text(encoding='utf-8')[:16]}... (hex)")
    print(f"Archive: {archive_path}")
    return archive_path


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build evidence pack")
    parser.parse_args(argv)
    build_evidence_pack()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
