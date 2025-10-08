from seval import predict, batch_predict


def test_sdk_predict_smoke():
    r = predict("hello", "violence", "en", guard="candidate")
    assert isinstance(r, dict)


def test_sdk_batch_predict_smoke():
    rows = [
        {"text": "hello", "category": "violence", "language": "en"},
        {"text": "hola", "category": "violence", "language": "es"},
    ]
    rs = batch_predict(rows, guard="candidate")
    assert len(rs) == 2


