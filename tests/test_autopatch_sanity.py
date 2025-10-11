
from autopatch import ab_eval


def test_ab_eval_produces_result_json(tmp_path):
    result_path = tmp_path / "ab_result.json"
    # No-op threshold change should still produce output and fail acceptance
    result = ab_eval.evaluate_threshold_candidate(
        updates={},
        target_slices=["violence/en"],
        result_path=result_path,
        cases=[],
    )

    assert result_path.exists()
    assert "baseline" in result and "patched" in result
    assert not ab_eval.accepts_improvement(result, ["violence/en"])


def test_acceptance_threshold_logic():
    fake_result = {
        "per_slice": {
            "self_harm/en": {
                "delta": {"recall": 0.02, "fpr": 0.004},
            }
        }
    }
    assert ab_eval.accepts_improvement(fake_result, ["self_harm/en"])

    regress_result = {
        "per_slice": {
            "self_harm/en": {
                "delta": {"recall": 0.01, "fpr": 0.01},
            }
        }
    }
    assert not ab_eval.accepts_improvement(regress_result, ["self_harm/en"])
