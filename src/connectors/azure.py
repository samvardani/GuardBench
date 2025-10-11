"""Azure Blob Storage helpers with optional SDK support."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterable, List, Tuple, Any

try:  # pragma: no cover - optional dependency
    from azure.storage.blob import BlobServiceClient  # type: ignore
except Exception:  # pragma: no cover
    BlobServiceClient = None  # type: ignore

try:  # pragma: no cover
    import httpx  # type: ignore
except Exception:  # pragma: no cover
    httpx = None  # type: ignore


def _parse(uri: str) -> Tuple[str, str]:
    prefix = None
    for option in ("azure://", "az://", "wasbs://"):
        if uri.startswith(option):
            prefix = option
            break
    if prefix is None:
        raise ValueError(f"Unsupported Azure blob URI: {uri}")
    remainder = uri[len(prefix) :]
    if "/" not in remainder:
        raise ValueError("Azure URI must include container and blob path")
    container, blob = remainder.split("/", 1)
    return container, blob


def _local_base() -> Path:
    base = os.getenv("AZURE_FALLBACK_DIR")
    if base:
        return Path(base)
    return Path(".cache/azure")


def _blob_path(container: str, blob: str) -> Path:
    return _local_base() / container / blob


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


def _to_content(records: Iterable[dict]) -> str:
    return "\n".join(json.dumps(record, separators=(",", ":")) for record in records) + "\n"


def _client():  # pragma: no cover - sdk path
    if BlobServiceClient is None:
        return None
    conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    account_url = os.getenv("AZURE_STORAGE_ACCOUNT_URL")
    if conn_str:
        return BlobServiceClient.from_connection_string(conn_str)
    if account_url:
        credential = os.getenv("AZURE_STORAGE_SAS_TOKEN")
        return BlobServiceClient(account_url=account_url, credential=credential)
    return None


def read_jsonl(uri: str, encoding: str = "utf-8") -> List[dict[str, Any]]:
    container, blob = _parse(uri)
    client = _client()
    if client is not None:  # pragma: no cover
        blob_client = client.get_blob_client(container, blob)
        data = blob_client.download_blob().content_as_text(encoding=encoding)
        return _read_lines(data)

    path = _blob_path(container, blob)
    if path.exists():
        return _read_lines(path.read_text(encoding=encoding))

    endpoint = os.getenv("AZURE_FALLBACK_URL")
    if endpoint and httpx is not None:
        resp = httpx.get(f"{endpoint.rstrip('/')}/{container}/{blob}")  # type: ignore[arg-type]
        resp.raise_for_status()
        return _read_lines(resp.text)

    raise FileNotFoundError(f"Azure blob {uri} not found")


def write_jsonl(uri: str, records: Iterable[dict], encoding: str = "utf-8") -> None:
    container, blob = _parse(uri)
    payload = _to_content(records)
    client = _client()
    if client is not None:  # pragma: no cover
        blob_client = client.get_blob_client(container, blob)
        blob_client.upload_blob(payload.encode(encoding), overwrite=True)
        return

    path = _blob_path(container, blob)
    _ensure_parent(path)
    path.write_text(payload, encoding=encoding)

    endpoint = os.getenv("AZURE_FALLBACK_URL")
    if endpoint and httpx is not None:
        httpx.put(f"{endpoint.rstrip('/')}/{container}/{blob}", content=payload.encode(encoding))  # type: ignore[arg-type]


def exists(uri: str) -> bool:
    container, blob = _parse(uri)
    client = _client()
    if client is not None:  # pragma: no cover
        blob_client = client.get_blob_client(container, blob)
        return blob_client.exists()

    path = _blob_path(container, blob)
    if path.exists():
        return True

    endpoint = os.getenv("AZURE_FALLBACK_URL")
    if endpoint and httpx is not None:
        resp = httpx.head(f"{endpoint.rstrip('/')}/{container}/{blob}")  # type: ignore[arg-type]
        return resp.status_code < 400

    return False


__all__ = ["read_jsonl", "write_jsonl", "exists"]

