from src.utils.scrub import scrub_text, scrub_record


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
