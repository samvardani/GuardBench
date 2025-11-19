# SeaRei Python SDK

Official Python client library for [SeaRei AI Safety API](https://github.com/searei/safety-eval-mini).

## Installation

```bash
pip install searei
```

Or install from source:

```bash
git clone https://github.com/searei/searei-python.git
cd searei-python
pip install -e .
```

## Quick Start

```python
from searei import SeaReiClient

# Initialize client
client = SeaReiClient(
    api_key="your_api_key",  # Optional for self-hosted
    base_url="http://localhost:8001"  # Or your API URL
)

# Score a single text
result = client.score("I will kill you")

if result.is_unsafe:
    print(f"⚠️  Flagged: {result.category} (score: {result.score:.2f})")
    print(f"Rationale: {result.rationale}")
else:
    print("✅ Content is safe")

# Batch scoring
texts = ["Hello world", "I will kill you", "Nice weather today"]
batch = client.batch_score(texts)

print(f"Flagged {batch.flagged}/{batch.total} texts")
for i, result in enumerate(batch.results):
    if result.is_unsafe:
        print(f"  [{i}] {result.category}: {texts[i]}")
```

## API Reference

### `SeaReiClient`

Main client class for interacting with the API.

**Constructor:**
```python
SeaReiClient(
    api_key: Optional[str] = None,
    base_url: str = "http://localhost:8001",
    timeout: int = 30,
    max_retries: int = 3
)
```

**Methods:**

#### `score(text, category=None, language=None)`

Score a single text for safety violations.

**Parameters:**
- `text` (str): Text content to score
- `category` (str, optional): Filter by category (violence, harassment, etc.)
- `language` (str, optional): Language code (en, es, ar, etc.)

**Returns:** `ScoreResult`

**Example:**
```python
result = client.score("I hate you", category="harassment")
print(result.prediction)  # "flag" or "pass"
print(result.score)        # 0.0-1.0
print(result.category)     # "harassment"
```

#### `batch_score(texts, category=None, language=None)`

Score multiple texts in a single request.

**Parameters:**
- `texts` (List[str]): List of text contents
- `category` (str, optional): Filter by category
- `language` (str, optional): Language code

**Returns:** `BatchResult`

**Example:**
```python
texts = ["Hello", "I will hurt you", "Good morning"]
batch = client.batch_score(texts)
print(batch.flagged)  # Number of flagged texts
```

#### `health()`

Check API health status.

**Returns:** Dict with status information

### `ScoreResult`

Result object from a score request.

**Attributes:**
- `prediction` (str): "flag" or "pass"
- `score` (float): Confidence score (0.0-1.0)
- `category` (str): Violation category
- `rationale` (str): Explanation
- `method` (str): Detection method used
- `latency_ms` (int): Request latency
- `policy_version` (str): Policy version
- `policy_checksum` (str): Policy checksum

**Properties:**
- `is_safe` (bool): True if prediction == "pass"
- `is_unsafe` (bool): True if prediction == "flag"

### `BatchResult`

Result object from a batch request.

**Attributes:**
- `results` (List[ScoreResult]): Individual results
- `total` (int): Total texts scored
- `flagged` (int): Number flagged
- `safe` (int): Number safe
- `latency_ms` (int): Total latency

## Error Handling

```python
from searei import SeaReiClient, SeaReiError, AuthenticationError, RateLimitError

try:
    result = client.score("some text")
except AuthenticationError:
    print("Invalid API key")
except RateLimitError:
    print("Rate limit exceeded, please retry later")
except SeaReiError as e:
    print(f"API error: {e}")
```

## Advanced Usage

### Context Manager

```python
with SeaReiClient(api_key="...") as client:
    result = client.score("text")
    # Session automatically closed
```

### Quick Score Function

```python
from searei import score

result = score("I will kill you", api_key="...")
print(result.prediction)
```

### Environment Variables

```bash
export SEAREI_API_KEY="your_api_key"
```

```python
# API key automatically loaded from environment
client = SeaReiClient()
```

### Custom Categories

```python
# Filter by specific category
result = client.score("I will hurt you", category="violence")

# Score for self-harm content only
result = client.score("I want to hurt myself", category="self_harm")
```

### Multilingual Support

```python
# Spanish content
result = client.score("Te voy a matar", language="es")

# Arabic content
result = client.score("سأقتلك", language="ar")
```

## CLI Usage

```bash
# Score from command line
python -m searei "I will kill you"

# Or if installed
searei "text to score"
```

## Testing

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/

# With coverage
pytest --cov=searei tests/
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Support

- **Documentation:** https://docs.searei.ai
- **Issues:** https://github.com/searei/searei-python/issues
- **Email:** support@searei.ai












