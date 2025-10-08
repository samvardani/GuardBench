from __future__ import annotations

import os
import hashlib
import pathlib
import subprocess

from pydantic_settings import BaseSettings, SettingsConfigDict


class SDKSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    default_guard: str = "candidate"
    seed_env: str = "SEVAL_SEED"


def get_sdk_settings() -> SDKSettings:
    return SDKSettings()  # type: ignore[call-arg]


# Policy version from git tags or environment
POLICY_VERSION = os.getenv("POLICY_VERSION") or (
    subprocess.run(["git", "describe", "--tags", "--always"], capture_output=True, text=True).stdout.strip() or "dev"
)


# Canonical checksum: policy file + ruleset + repo sha
def policy_checksum() -> str:
    try:
        policy_path = pathlib.Path(os.getenv("POLICY_PATH", "policy/policy.yaml"))
        h = hashlib.sha256()
        if policy_path.exists():
            h.update(policy_path.read_bytes())
        # include repo HEAD sha for supply-chain provenance
        sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        h.update(sha.encode())
        return h.hexdigest()[:12]
    except Exception:
        return "unknown"


POLICY_CHECKSUM = os.getenv("POLICY_CHECKSUM") or policy_checksum()



