"""Google Cloud Storage helpers with optional SDK support."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterable, List, Tuple, Any

try:  # pragma: no cover - optional dependency
    from google.cloud import storage  # type: ignore
except Exception:  # pragma: no cover
    storage = None  # type: ignore

try:  # pragma: no cover
    import httpx  # type: ignore
except Exception:  # pragma: no cover
    httpx = None  # type: ignore


def _parse(uri: str) -> Tuple[str, str]:
    if uri.startswith("gs://"):
        remainder = uri[len("gs://") :]
    elif uri.startswith("gcs://"):
        remainder = uri[len("gcs://") :]
    else:
        raise ValueError(f"Unsupported GCS URI: {uri}")
    if "/" not in remainder:
        raise ValueError("GCS URI must include bucket and object")
    bucket, blob = remainder.split("/", 1)
    return bucket, blob


def _local_base() -> Path:
    base = os.getenv("GCS_FALLBACK_DIR")
    if base:
        return Path(base)
    return Path(".cache/gcs")


def _object_path(bucket: str, blob: str) -> Path:
    return _local_base() / bucket / blob


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _read_lines(content: str) -> List[dict[str, Any]]:
    rows: List[dict[str, Any]] = []
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def _to_content(records: Iterable[dict[str, Any]]) -> str:
    return "\n".join(json.dumps(record, separators=(",", ":")) for record in records) + "\n"


def _storage_client():  # pragma: no cover - sdk path
    if storage is None:
        return None
    return storage.Client()


def read_jsonl(uri: str, encoding: str = "utf-8") -> List[dict[str, Any]]:
    bucket, blob = _parse(uri)
    client = _storage_client()
    if client is not None:  # pragma: no cover
        bucket_obj = client.bucket(bucket)
        blob_obj = bucket_obj.blob(blob)
        data = blob_obj.download_as_text(encoding=encoding)
        return _read_lines(data)

    path = _object_path(bucket, blob)
    if path.exists():
        return _read_lines(path.read_text(encoding=encoding))

    endpoint = os.getenv("GCS_FALLBACK_URL")
    if endpoint and httpx is not None:
        resp = httpx.get(f"{endpoint.rstrip('/')}/{bucket}/{blob}")  # type: ignore[arg-type]
        resp.raise_for_status()
        return _read_lines(resp.text)

    raise FileNotFoundError(f"GCS object {uri} not found")


def write_jsonl(uri: str, records: Iterable[dict[str, Any]], encoding: str = "utf-8") -> None:
    bucket, blob = _parse(uri)
    payload = _to_content(records)
    client = _storage_client()
    if client is not None:  # pragma: no cover
        bucket_obj = client.bucket(bucket)
        blob_obj = bucket_obj.blob(blob)
        blob_obj.upload_from_string(payload, content_type="application/json", client=client)
        return

    path = _object_path(bucket, blob)
    _ensure_parent(path)
    path.write_text(payload, encoding=encoding)

    endpoint = os.getenv("GCS_FALLBACK_URL")
    if endpoint and httpx is not None:
        httpx.put(f"{endpoint.rstrip('/')}/{bucket}/{blob}", content=payload.encode(encoding))  # type: ignore[arg-type]


def exists(uri: str) -> bool:
    bucket, blob = _parse(uri)
    client = _storage_client()
    if client is not None:  # pragma: no cover
        bucket_obj = client.bucket(bucket)
        blob_obj = bucket_obj.blob(blob)
        return blob_obj.exists(client=client)

    path = _object_path(bucket, blob)
    if path.exists():
        return True

    endpoint = os.getenv("GCS_FALLBACK_URL")
    if endpoint and httpx is not None:
        resp = httpx.head(f"{endpoint.rstrip('/')}/{bucket}/{blob}")  # type: ignore[arg-type]
        return resp.status_code < 400

    return False


__all__ = ["read_jsonl", "write_jsonl", "exists"]

