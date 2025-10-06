import os
import json
from pathlib import Path

from src.connectors import s3 as s3c, gcs as gcsc, azure as azc
from src.connectors.kafka import Producer


def test_s3_local_fallback_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("S3_FALLBACK_DIR", str(tmp_path / "s3"))
    uri = "s3://bucket/path/to/file.jsonl"
    records = [{"a": 1}, {"b": 2}]
    s3c.write_jsonl(uri, records)
    assert s3c.exists(uri)
    out = s3c.read_jsonl(uri)
    assert out == records


def test_gcs_local_fallback_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("GCS_FALLBACK_DIR", str(tmp_path / "gcs"))
    uri = "gs://bucket/obj.jsonl"
    records = [{"x": "y"}]
    gcsc.write_jsonl(uri, records)
    assert gcsc.exists(uri)
    out = gcsc.read_jsonl(uri)
    assert out == records


def test_azure_local_fallback_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("AZURE_FALLBACK_DIR", str(tmp_path / "az"))
    uri = "azure://container/obj.jsonl"
    records = [{"k": "v"}]
    azc.write_jsonl(uri, records)
    assert azc.exists(uri)
    out = azc.read_jsonl(uri)
    assert out == records


def test_kafka_filesystem_fallback(tmp_path, monkeypatch):
    monkeypatch.delenv("KAFKA_REST_PROXY", raising=False)
    monkeypatch.setenv("KAFKA_FALLBACK_DIR", str(tmp_path / "kafka"))
    p = Producer(brokers="invalid:9092", retries=1, backoff_seconds=0.01)
    topic = "test-topic"
    payload = {"hello": "world"}
    p.send_json(topic, payload)
    files = list((tmp_path / "kafka" / topic).glob("*.json"))
    assert files, "Expected a json file to be written for fallback"
    content = json.loads(Path(files[0]).read_text(encoding="utf-8"))
    assert content == payload


