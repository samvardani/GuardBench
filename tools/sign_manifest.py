from __future__ import annotations

import json
import os
from pathlib import Path


def main() -> int:
    key_hex = os.getenv("EVIDENCE_SIGN_KEY")
    if not key_hex:
        print("EVIDENCE_SIGN_KEY not set; skipping")
        return 0
    try:
        from nacl.signing import SigningKey  # type: ignore
    except Exception:
        print("PyNaCl not installed; cannot sign")
        return 2
    manifest = Path("MANIFEST.json")
    if not manifest.exists():
        print("MANIFEST.json not found")
        return 1
    payload = json.dumps(json.loads(manifest.read_text(encoding="utf-8")), separators=(",", ":")).encode("utf-8")
    key = SigningKey(bytes.fromhex(key_hex))
    sig = key.sign(payload).signature.hex()
    Path("manifest.sig").write_text(sig, encoding="utf-8")
    print("manifest.sig written")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())



