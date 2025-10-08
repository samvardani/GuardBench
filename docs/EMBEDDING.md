# Embedding the Safety Engine (SDK)

Install and use the SDK in-process:

```python
from seval import predict, batch_predict

result = predict("hello", "violence", "en", guard="candidate")
rows = [{"text":"hola","category":"violence","language":"es"}]
results = batch_predict(rows)
```

Determinism: set `SEVAL_SEED` to control random/heuristic paths. Policy and regexes are cached per worker process.



