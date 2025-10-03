from pathlib import Path

from src.obfuscation.lab import run_media_lab


def test_image_lab_confusion(tmp_path):
    dataset = tmp_path / "images.csv"
    dataset.write_text(
        "path,label,category\n"
        "nsfw_example.jpg,unsafe,image\n"
        "family_photo.jpg,benign,image\n"
    , encoding="utf-8")
    out_path = tmp_path / "out.json"
    results = run_media_lab(dataset, out_path, mode="image")
    image_metrics = results["image"]
    assert image_metrics["tp"] == 1
    assert image_metrics["tn"] == 1
    assert image_metrics["fp"] == 0
    assert image_metrics["fn"] == 0


def test_audio_lab_confusion(tmp_path):
    dataset = tmp_path / "audio.csv"
    dataset.write_text(
        "path,label,category\n"
        "explicit_track.wav,unsafe,audio\n"
        "storytelling.wav,benign,audio\n"
    , encoding="utf-8")
    out_path = tmp_path / "audio.json"
    results = run_media_lab(dataset, out_path, mode="audio")
    metrics = results["audio"]
    assert metrics["tp"] == 1
    assert metrics["tn"] == 1
    assert metrics["fp"] == 0
    assert metrics["fn"] == 0
