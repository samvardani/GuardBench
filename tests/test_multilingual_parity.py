from multilingual.parity import _variance, ParityResult


def test_variance_calculation():
    values = [0.9, 0.8, 0.85]
    var = _variance(values)
    assert round(var, 5) == round(sum((v - sum(values) / 3) ** 2 for v in values) / 3, 5)


def test_parity_result_dict():
    result = ParityResult(
        category="violence",
        language_metrics={"en": {"total": 3, "flagged": 3, "recall": 1.0}},
        max_delta=0.0,
        variance=0.0,
    )
    payload = result.to_dict()
    assert payload["category"] == "violence"
    assert "en" in payload["languages"]
    assert payload["target_delta"] == result.target_delta
