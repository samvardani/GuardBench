from pathlib import Path

from multimodal.adapters import ImageInput, AudioInput, score_image, score_audio, TELEMETRY_PATH


def test_image_adapter_logs_and_validates(tmp_path, monkeypatch):
    monkeypatch.setenv("PYTHONHASHSEED", "0")
    monkeypatch.chdir(tmp_path)
    data = b"\x89PNG\r\n\x1a\n..."
    out = score_image(ImageInput(content_type="image/png", bytes=data))
    assert out["modality"] == "image"
    assert out["category_guess"] == "image/*"
    assert out["threshold"] == 1.0
    assert TELEMETRY_PATH.exists()
    content = TELEMETRY_PATH.read_text(encoding="utf-8").strip()
    assert content and "\"modality\": \"image\"" in content


def test_audio_adapter_logs_and_validates(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    data = b"ID3\x03\x00\x00\x00\x00\x00\x21..."
    out = score_audio(AudioInput(content_type="audio/mpeg", bytes=data))
    assert out["modality"] == "audio"
    assert out["category_guess"] == "audio/*"
    assert out["threshold"] == 1.0
    content = TELEMETRY_PATH.read_text(encoding="utf-8")
    assert "\"modality\": \"audio\"" in content


