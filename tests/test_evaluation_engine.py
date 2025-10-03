from src.evaluation import evaluate


def test_evaluate_produces_metrics_and_risk():
    dataset = [
        {"id": "r1", "text": "benign prompt", "label": "benign", "category": "violence", "language": "en"},
        {"id": "r2", "text": "harmful instruction", "label": "unsafe", "category": "violence", "language": "en"},
        {"id": "r3", "text": "borderline", "label": "borderline", "category": "violence", "language": "en"},
    ]

    def stub_guard(text, category=None, language=None):
        flagged = "harmful" in text
        return {"prediction": "flag" if flagged else "pass", "latency_ms": 10 if flagged else 5}

    summary = evaluate(
        {"guards": {"stub": {"name": "stub-guard", "predict": stub_guard}}},
        dataset,
        policy={"risk_weights": {"violence": 3.0}},
    )

    guard = summary["guards"]["stub"]
    strict = guard["modes"]["strict"]
    lenient = guard["modes"]["lenient"]

    cm_strict = strict["confusion"]
    assert cm_strict["tp"] == 1
    assert cm_strict["fp"] == 0
    assert cm_strict["tn"] == 1
    assert cm_strict["fn"] == 1
    assert cm_strict["precision"] == 1.0
    assert cm_strict["recall"] == 0.5
    assert cm_strict["fnr"] == 0.5
    assert cm_strict["fpr"] == 0.0

    cm_lenient = lenient["confusion"]
    assert cm_lenient["tp"] == 1
    assert cm_lenient["fn"] == 0

    latency = guard["latency"]
    assert latency == {"p50": 5.0, "p90": 10.0, "p99": 10.0}

    strict_slice = strict["slices"][0]
    assert strict_slice["risk_weight"] == 3.0
    assert strict_slice["risk_score"] == 1.5
    assert guard["aggregate_risk"] == 1.5
    assert summary["dataset"]["size"] == len(dataset)
