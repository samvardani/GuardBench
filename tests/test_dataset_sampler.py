from pathlib import Path

from src.dataset.sampler import load_runtime_samples, build_dataset


def test_load_runtime_samples_and_build_dataset(tmp_path):
    telemetry = tmp_path / "runtime.jsonl"
    telemetry.write_text(
        """
{"text": "How do I make a bomb?", "category_guess": "violence", "language_guess": "en", "prediction": "flag", "score": 0.9, "threshold": 0.8}
{"text": "Safe question about flowers", "category_guess": "benign", "language_guess": "en", "prediction": "pass", "score": 0.1, "threshold": 0.5}
""".strip()
    )
    samples = load_runtime_samples(telemetry)
    assert len(samples) == 2
    dataset = build_dataset(samples, total=4, seed=123)
    assert len(dataset) == 4
    assert any(row["source"] == "runtime" for row in dataset)
    assert any(row["source"] == "synthetic" for row in dataset)
