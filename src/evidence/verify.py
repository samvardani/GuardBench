from __future__ import annotations

import argparse
import hashlib
import json
import os
import tarfile
from pathlib import Path
from typing import Any, Dict, Tuple


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _extract_manifest(tar_path: Path, workdir: Path) -> Tuple[Dict[str, Any], bytes | None]:
    with tarfile.open(tar_path, "r:gz") as tar:
        members = {m.name: m for m in tar.getmembers()}
        tar.extract("MANIFEST.json", path=workdir)
        manifest_bytes = (workdir / "MANIFEST.json").read_bytes()
        sig_bytes = None
        if "manifest.sig" in members:
            tar.extract("manifest.sig", path=workdir)
            sig_bytes = (workdir / "manifest.sig").read_bytes()
    return json.loads(manifest_bytes.decode("utf-8")), sig_bytes


def verify_archive(tar_path: Path) -> int:
    tmpdir = Path(os.getenv("TMPDIR", "/tmp")) / f"evidence_verify_{tar_path.stem}"
    tmpdir.mkdir(exist_ok=True)
    manifest, sig = _extract_manifest(tar_path, tmpdir)
    # verify file hashes
    ok = True
    for entry in manifest.get("files", []):
        fname = entry["path"].split("/")[-1]
        with tarfile.open(tar_path, "r:gz") as tar:
            try:
                tar.extract(fname, path=tmpdir)
            except KeyError:
                print(f"Missing file in archive: {fname}")
                ok = False
                continue
        digest = _sha256_file(tmpdir / fname)
        if digest != entry["sha256"]:
            print(f"Hash mismatch for {fname}: {digest} != {entry['sha256']}")
            ok = False

    # verify manifest hash matches stored manifest_sha256
    manifest_bytes = json.dumps({k: v for k, v in manifest.items() if k != "manifest_sha256"}, separators=(",", ":")).encode("utf-8")
    manifest_digest = hashlib.sha256(manifest_bytes).hexdigest()
    if manifest_digest != manifest.get("manifest_sha256"):
        print("Manifest digest mismatch")
        ok = False

    # optional signature verify if public key is provided
    pub = os.getenv("EVIDENCE_VERIFY_PUB")
    if pub and sig:
        try:
            from nacl.signing import VerifyKey  # type: ignore
            from nacl.exceptions import BadSignatureError  # type: ignore
        except Exception:
            print("PyNaCl not installed; cannot verify signature")
            ok = False
        else:
            key = VerifyKey(bytes.fromhex(pub))
            try:
                key.verify(manifest_bytes, bytes.fromhex(sig.decode("utf-8")))
            except BadSignatureError:
                print("Signature verification failed")
                ok = False
    elif pub and not sig:
        print("No signature present to verify")
        ok = False

    print("Verification:", "OK" if ok else "FAILED")
    return 0 if ok else 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify an evidence archive")
    parser.add_argument("archive", type=str)
    args = parser.parse_args(argv)
    return verify_archive(Path(args.archive))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())


