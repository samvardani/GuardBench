import importlib
from unittest import mock

from src.utils import scrub
from src.utils.scrub import scrub_text, scrub_record, privacy_mode_for


def test_scrub_off_redacts_pii():
    text = "Contact me at alice@example.com or 555-123-4567 or SSN 123-45-6789"
    cleaned = scrub_text(text, mode="off")
    assert "example.com" not in cleaned
    assert "[REDACTED_EMAIL]" in cleaned
    assert "[REDACTED_PHONE]" in cleaned
    assert "[REDACTED_SSN]" in cleaned


def test_scrub_off_preserves_normal_text():
    text = "Discuss standard operating procedures"
    assert scrub_text(text, mode="off") == text


def test_scrub_strict_hash():
    text = "Highly confidential prompt"
    hashed = scrub_text(text, mode="strict")
    assert hashed.startswith("[HASH:")
    assert hashed.endswith("]")
    assert len(hashed) == len("[HASH:") + 16 + 1


def test_scrub_record_applies_keys():
    record = {"text": "foo@example.com", "other": "value"}
    scrubbed = scrub_record(record, keys=["text"], mode="off")
    assert scrubbed["text"] == "[REDACTED_EMAIL]"
    assert scrubbed["other"] == "value"


def test_custom_patterns(monkeypatch):
    monkeypatch.setattr(
        scrub,
        "load_config",
        lambda: {"privacy": {"default_mode": "off", "custom_patterns": [r"secret\d+"]}},
    )
    monkeypatch.setattr(
        "src.utils.io_utils.load_config",
        lambda: {"privacy": {"default_mode": "off", "custom_patterns": [r"secret\d+"]}},
    )
    assert "[REDACTED_CUSTOM]" in scrub._apply_custom_patterns("the code is secret42")
    cleaned = scrub_text("the code is secret42", mode=None)
    assert "[REDACTED_CUSTOM]" in cleaned


def test_entropy_redaction():
    token = "a1B2c3D4e5F6g7H8"
    cleaned = scrub_text(f"token {token}", mode="off")
    assert "[REDACTED_TOKEN]" in cleaned


def test_privacy_mode_for_endpoint(monkeypatch):
    monkeypatch.setattr(
        scrub,
        "load_config",
        lambda: {"privacy_mode": "off", "privacy": {"default_mode": "off", "endpoints": {"score": "strict"}}},
    )
    assert privacy_mode_for("score") == "strict"
    assert privacy_mode_for("upload") == "off"
