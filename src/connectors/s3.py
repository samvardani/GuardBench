"""Lightweight S3 helpers with optional SDK support."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterable, List, Tuple

try:  # pragma: no cover - optional dependency
    import boto3  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    boto3 = None  # type: ignore

try:  # pragma: no cover - optional dependency
    import botocore.session  # type: ignore
except Exception:  # pragma: no cover
    botocore = None  # type: ignore

try:  # pragma: no cover - optional dependency
    import httpx  # type: ignore
except Exception:  # pragma: no cover
    httpx = None  # type: ignore


def _parse(uri: str) -> Tuple[str, str]:
    if not uri.startswith("s3://"):
        raise ValueError(f"Unsupported S3 URI: {uri}")
    bucket_and_key = uri[len("s3://") :]
    if "/" not in bucket_and_key:
        raise ValueError("S3 URI must include bucket and key")
    bucket, key = bucket_and_key.split("/", 1)
    return bucket, key


def _local_base() -> Path:
    base = os.getenv("S3_FALLBACK_DIR")
    if base:
        return Path(base)
    return Path(".cache/s3")


def _object_path(bucket: str, key: str) -> Path:
    base = _local_base()
    return base / bucket / key


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _read_lines(content: str) -> List[dict[str, Any]]:
    lines: List[dict[str, Any]] = []
    for raw_line in content.splitlines():
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        lines.append(json.loads(raw_line))
    return lines


def _to_content(records: Iterable[dict]) -> str:
    return "\n".join(json.dumps(record, separators=(",", ":")) for record in records) + "\n"


def _boto3_client():  # pragma: no cover - only exercised when boto3 present
    if boto3 is None:
        return None
    endpoint = os.getenv("S3_ENDPOINT_URL")
    return boto3.client("s3", endpoint_url=endpoint)


def _botocore_client():  # pragma: no cover - only exercised when botocore present
    if botocore is None:
        return None
    session = botocore.session.get_session()
    endpoint = os.getenv("S3_ENDPOINT_URL")
    return session.create_client("s3", endpoint_url=endpoint)


def read_jsonl(uri: str, encoding: str = "utf-8") -> List[dict[str, Any]]:
    bucket, key = _parse(uri)
    client = _boto3_client()
    if client is not None:  # pragma: no cover - boto3 path
        obj = client.get_object(Bucket=bucket, Key=key)
        body = obj["Body"].read().decode(encoding)
        return _read_lines(body)

    client = _botocore_client()
    if client is not None:  # pragma: no cover - botocore path
        obj = client.get_object(Bucket=bucket, Key=key)
        body = obj["Body"].read().decode(encoding)
        return _read_lines(body)

    fallback_path = _object_path(bucket, key)
    if fallback_path.exists():
        return _read_lines(fallback_path.read_text(encoding=encoding))

    endpoint = os.getenv("S3_FALLBACK_URL")
    if endpoint and httpx is not None:
        resp = httpx.get(f"{endpoint.rstrip('/')}/{bucket}/{key}")  # type: ignore[arg-type]
        resp.raise_for_status()
        return _read_lines(resp.text)

    raise FileNotFoundError(f"S3 object {uri} not found")


def write_jsonl(uri: str, records: Iterable[dict], encoding: str = "utf-8") -> None:
    bucket, key = _parse(uri)
    payload = _to_content(records)
    client = _boto3_client()
    if client is not None:  # pragma: no cover - boto3 path
        client.put_object(Bucket=bucket, Key=key, Body=payload.encode(encoding))
        return

    client = _botocore_client()
    if client is not None:  # pragma: no cover - botocore path
        client.put_object(Bucket=bucket, Key=key, Body=payload.encode(encoding))
        return

    fallback_path = _object_path(bucket, key)
    _ensure_parent(fallback_path)
    fallback_path.write_text(payload, encoding=encoding)

    endpoint = os.getenv("S3_FALLBACK_URL")
    if endpoint and httpx is not None:
        httpx.put(f"{endpoint.rstrip('/')}/{bucket}/{key}", content=payload.encode(encoding))  # type: ignore[arg-type]


def exists(uri: str) -> bool:
    bucket, key = _parse(uri)
    client = _boto3_client()
    if client is not None:  # pragma: no cover
        try:
            client.head_object(Bucket=bucket, Key=key)
            return True
        except Exception:
            return False

    client = _botocore_client()
    if client is not None:  # pragma: no cover
        try:
            client.head_object(Bucket=bucket, Key=key)
            return True
        except Exception:
            return False

    fallback_path = _object_path(bucket, key)
    if fallback_path.exists():
        return True

    endpoint = os.getenv("S3_FALLBACK_URL")
    if endpoint and httpx is not None:
        resp = httpx.head(f"{endpoint.rstrip('/')}/{bucket}/{key}")  # type: ignore[arg-type]
        return resp.status_code < 400

    return False


__all__ = ["read_jsonl", "write_jsonl", "exists"]

