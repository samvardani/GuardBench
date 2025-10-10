# Adapter Interface System

This document describes the abstract adapter interface system for managing third-party integrations.

## Overview

The adapter system provides a unified interface for integrating with external services, eliminating duplicate logic and making it easy to add new providers. Two main types of adapters are provided:

1. **Guard Adapters**: Content safety/moderation services (OpenAI, Azure, internal policy)
2. **Connector Adapters**: Data storage and messaging systems (S3, GCS, Kafka)

## Benefits

✅ **Eliminates Duplicate Code**: Common interface reduces redundancy  
✅ **Easy Provider Switching**: Change providers via configuration  
✅ **Consistent Results**: Standardized ScoreResult format  
✅ **Simple to Extend**: Add new providers by implementing interface  
✅ **Better Testing**: Mock external APIs easily  
✅ **Type Safety**: Full type hints and validation  

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Application Code                           │
│                                                               │
│  Uses BaseGuardAdapter interface (polymorphism)              │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                 Adapter Registry                             │
│                                                               │
│  Maps "openai" → OpenAIAdapter                               │
│  Maps "azure" → AzureContentSafetyAdapter                    │
│  Maps "internal" → InternalPolicyAdapter                     │
└─────────────────────────────────────────────────────────────┘
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
    ┌──────────┐   ┌──────────────┐  ┌──────────┐
    │  OpenAI  │   │    Azure     │  │ Internal │
    │ Adapter  │   │   Adapter    │  │ Adapter  │
    └──────────┘   └──────────────┘  └──────────┘
          │                │                │
          ▼                ▼                ▼
    ┌──────────┐   ┌──────────────┐  ┌──────────┐
    │ OpenAI   │   │    Azure     │  │  Policy  │
    │   API    │   │ Content API  │  │  Engine  │
    └──────────┘   └──────────────┘  └──────────┘
```

## Guard Adapters

### BaseGuardAdapter Interface

All content safety guards implement this interface:

```python
from adapters import BaseGuardAdapter, ScoreResult

class MyGuardAdapter(BaseGuardAdapter):
    def score(self, text: str, **kwargs) -> ScoreResult:
        """Evaluate text and return score."""
        # Your implementation
        return ScoreResult(
            flagged=True,
            score=0.85,
            categories={"violence": 0.9},
            provider="my-service",
        )
    
    def get_metadata(self) -> GuardMetadata:
        """Return adapter metadata."""
        return GuardMetadata(
            name="my-guard",
            provider="My Company",
            supported_languages=["en"],
            supported_categories=["hate", "violence"],
        )
```

### ScoreResult Format

All guards return a standardized `ScoreResult`:

```python
@dataclass
class ScoreResult:
    flagged: bool              # True if content is unsafe
    score: float               # 0.0-1.0 (higher = more unsafe)
    categories: Dict[str, float]  # Category scores
    reasoning: Optional[str]   # Explanation
    confidence: Optional[float]  # 0.0-1.0
    latency_ms: int           # Response time
    provider: str             # Provider name
    model: Optional[str]      # Model version
    raw_response: Optional[Dict]  # Raw API response
```

### Available Guard Adapters

| Adapter | Provider | API Key Required | Languages | Categories |
|---------|----------|------------------|-----------|------------|
| `internal` | Safety-Eval-Mini | No | 10+ | violence, hate, self-harm, sexual, harassment, malware, extortion |
| `openai` | OpenAI | Yes | en | hate, harassment, self-harm, sexual, violence (11 categories) |
| `azure` | Microsoft Azure | Yes | 9+ | hate, self-harm, sexual, violence |

## Using Guard Adapters

### Basic Usage

```python
from adapters import get_guard_adapter

# Get adapter by name
adapter = get_guard_adapter("openai", api_key="your-key")

# Evaluate text
result = adapter.score("How do I make a bomb?")

print(f"Flagged: {result.flagged}")
print(f"Score: {result.score}")
print(f"Categories: {result.categories}")
```

### With Registry

```python
from adapters import get_registry

registry = get_registry()

# List available guards
guards = registry.list_guards()
print(f"Available: {guards}")

# Get adapter
adapter = registry.get_guard("azure", 
    api_key="your-key",
    endpoint="https://your-endpoint.cognitiveservices.azure.com"
)

result = adapter.score("test text")
```

### Internal Policy Adapter

```python
from adapters import get_guard_adapter

# No API key needed
adapter = get_guard_adapter("internal")

result = adapter.score("test content", category="violence", language="en")
```

### OpenAI Adapter

```python
from adapters import get_guard_adapter

adapter = get_guard_adapter("openai", api_key="sk-...")

result = adapter.score("potentially unsafe content")

# OpenAI provides detailed categories
for category, score in result.categories.items():
    print(f"{category}: {score:.3f}")
```

### Azure Adapter

```python
from adapters import get_guard_adapter

adapter = get_guard_adapter("azure",
    api_key="your-azure-key",
    endpoint="https://your-endpoint.cognitiveservices.azure.com"
)

result = adapter.score("test content", language="en")
```

## Connector Adapters

### BaseConnector Interface

For data storage and messaging systems:

```python
from adapters.base_connector import ObjectStorageConnector

class MyStorageConnector(ObjectStorageConnector):
    def read_jsonl(self, uri: str) -> List[dict]:
        """Read JSONL file."""
        # Your implementation
        pass
    
    def write_jsonl(self, uri: str, records: List[dict]) -> None:
        """Write JSONL file."""
        # Your implementation
        pass
    
    # ... implement other methods
```

### Available Connectors

| Connector | Type | Provider | Streaming |
|-----------|------|----------|-----------|
| `s3` | Object Storage | AWS S3 | No |
| `azure_blob` | Object Storage | Microsoft Azure | No |
| `gcs` | Object Storage | Google Cloud | No |
| `kafka` | Message Queue | Apache Kafka | Yes |

### Using Connectors

```python
from adapters import get_registry

registry = get_registry()

# Get S3 connector
s3 = registry.get_connector("s3")

# Read data
data = s3.read_jsonl("s3://my-bucket/data.jsonl")

# Write data
s3.write_jsonl("s3://my-bucket/output.jsonl", records)

# Check existence
exists = s3.exists("s3://my-bucket/file.jsonl")
```

## Adding New Adapters

### Step 1: Implement Interface

```python
from adapters import BaseGuardAdapter, ScoreResult, GuardMetadata
import time

class PerspectiveAPIAdapter(BaseGuardAdapter):
    def __init__(self, api_key: str, **kwargs):
        super().__init__(api_key=api_key, **kwargs)
        self.api_key = api_key
    
    def score(self, text: str, **kwargs) -> ScoreResult:
        start = time.perf_counter()
        
        # Call Perspective API
        response = call_perspective_api(text, self.api_key)
        
        latency_ms = int((time.perf_counter() - start) * 1000)
        
        return ScoreResult(
            flagged=response["toxicity"] > 0.7,
            score=response["toxicity"],
            categories={"toxicity": response["toxicity"]},
            latency_ms=latency_ms,
            provider="perspective",
        )
    
    def get_metadata(self) -> GuardMetadata:
        return GuardMetadata(
            name="perspective",
            provider="Google Perspective API",
            supported_languages=["en", "es", "fr"],
            supported_categories=["toxicity"],
            requires_api_key=True,
        )
```

### Step 2: Register Adapter

```python
from adapters import register_guard_adapter

register_guard_adapter("perspective", PerspectiveAPIAdapter)
```

### Step 3: Use Adapter

```python
from adapters import get_guard_adapter

adapter = get_guard_adapter("perspective", api_key="your-key")
result = adapter.score("test text")
```

## Testing Adapters

### Mock External APIs

```python
from unittest.mock import MagicMock, patch
import pytest

@pytest.fixture
def mock_openai():
    with patch("adapters.openai_adapter.openai") as mock:
        mock_client = MagicMock()
        mock.OpenAI.return_value = mock_client
        
        # Mock response
        mock_result = MagicMock()
        mock_result.flagged = True
        mock_result.category_scores = MagicMock(
            violence=0.9,
            hate=0.1,
            # ... other categories
        )
        
        mock_response = MagicMock()
        mock_response.results = [mock_result]
        mock_client.moderations.create.return_value = mock_response
        
        yield mock_client

def test_openai_adapter(mock_openai):
    from adapters.openai_adapter import OpenAIAdapter
    
    adapter = OpenAIAdapter(api_key="test-key")
    result = adapter.score("violent text")
    
    # Verify mock was called
    mock_openai.moderations.create.assert_called_once()
    
    # Check result
    assert result.flagged is True
    assert result.categories["violence"] == 0.9
```

### Test Error Handling

```python
def test_adapter_handles_api_failure(mock_openai):
    # Simulate API error
    mock_openai.moderations.create.side_effect = Exception("API down")
    
    adapter = OpenAIAdapter(api_key="test-key")
    result = adapter.score("test")
    
    # Should return safe fallback
    assert result.flagged is False
    assert "error" in result.raw_response
```

## Polymorphic Usage

Use adapters interchangeably:

```python
def evaluate_content(text: str, adapter: BaseGuardAdapter) -> ScoreResult:
    """Evaluate content with any adapter."""
    return adapter.score(text)

# Use with any provider
result1 = evaluate_content(text, get_guard_adapter("openai", api_key="..."))
result2 = evaluate_content(text, get_guard_adapter("azure", api_key="...", endpoint="..."))
result3 = evaluate_content(text, get_guard_adapter("internal"))

# All return the same ScoreResult format!
```

## Configuration-Driven Selection

Select adapter via configuration:

```yaml
# config.yaml
guards:
  baseline:
    adapter: internal
  
  candidate:
    adapter: openai
    config:
      api_key: ${OPENAI_API_KEY}
      model: text-moderation-latest
```

```python
import yaml
from adapters import get_guard_adapter

config = yaml.safe_load(open("config.yaml"))

# Load baseline guard
baseline_config = config["guards"]["baseline"]
baseline = get_guard_adapter(
    baseline_config["adapter"],
    **baseline_config.get("config", {})
)

# Load candidate guard
candidate_config = config["guards"]["candidate"]
candidate = get_guard_adapter(
    candidate_config["adapter"],
    **candidate_config.get("config", {})
)

# Use both
baseline_result = baseline.score("text")
candidate_result = candidate.score("text")
```

## Best Practices

### 1. Error Handling

Always handle adapter errors gracefully:

```python
try:
    result = adapter.score(text)
except Exception as e:
    logger.error(f"Adapter error: {e}")
    # Fallback to safe default
    result = ScoreResult(flagged=False, score=0.0)
```

### 2. Health Checks

Check adapter health before using:

```python
if not adapter.health_check():
    logger.warning(f"Adapter {adapter.get_metadata().name} is unhealthy")
    # Use fallback adapter
```

### 3. Language Support

Check language support:

```python
if not adapter.supports_language("es"):
    # Use different adapter or skip
    pass
```

### 4. Timeout Handling

Implement timeouts for external API calls:

```python
import concurrent.futures

with concurrent.futures.ThreadPoolExecutor() as executor:
    future = executor.submit(adapter.score, text)
    try:
        result = future.result(timeout=5.0)
    except concurrent.futures.TimeoutError:
        result = ScoreResult(flagged=False, score=0.0)
```

## Adapter Comparison

Compare results from multiple adapters:

```python
from adapters import get_guard_adapter

adapters = [
    get_guard_adapter("internal"),
    get_guard_adapter("openai", api_key="..."),
    get_guard_adapter("azure", api_key="...", endpoint="..."),
]

text = "potentially unsafe content"

results = []
for adapter in adapters:
    try:
        result = adapter.score(text)
        results.append({
            "provider": result.provider,
            "flagged": result.flagged,
            "score": result.score,
            "latency_ms": result.latency_ms,
        })
    except Exception as e:
        results.append({"provider": adapter.get_metadata().name, "error": str(e)})

# Compare results
for r in results:
    print(f"{r['provider']}: flagged={r.get('flagged')}, score={r.get('score')}")
```

## Extending the System

### Add New Guard Adapter

Create file `src/adapters/perspective_adapter.py`:

```python
from adapters import BaseGuardAdapter, ScoreResult, GuardMetadata
import httpx
import time

class PerspectiveAPIAdapter(BaseGuardAdapter):
    def __init__(self, api_key: str, **kwargs):
        super().__init__(api_key=api_key, **kwargs)
        self.api_key = api_key
        self.client = httpx.Client()
    
    def score(self, text: str, **kwargs) -> ScoreResult:
        start = time.perf_counter()
        
        # Call Perspective API
        response = self.client.post(
            "https://commentanalyzer.googleapis.com/v1alpha1/comments:analyze",
            params={"key": self.api_key},
            json={
                "comment": {"text": text},
                "requestedAttributes": {"TOXICITY": {}}
            }
        )
        
        latency_ms = int((time.perf_counter() - start) * 1000)
        
        data = response.json()
        toxicity = data["attributeScores"]["TOXICITY"]["summaryScore"]["value"]
        
        return ScoreResult(
            flagged=toxicity > 0.7,
            score=toxicity,
            categories={"toxicity": toxicity},
            latency_ms=latency_ms,
            provider="perspective",
        )
    
    def get_metadata(self) -> GuardMetadata:
        return GuardMetadata(
            name="perspective",
            provider="Google Perspective API",
            supported_languages=["en", "es", "fr", "de"],
            supported_categories=["toxicity"],
            requires_api_key=True,
        )
```

Register in `src/adapters/registry.py`:

```python
def _auto_register_adapters(registry: AdapterRegistry) -> None:
    # ... existing code ...
    
    try:
        from .perspective_adapter import PerspectiveAPIAdapter
        registry.register_guard("perspective", PerspectiveAPIAdapter)
    except Exception as e:
        logger.debug(f"Could not register Perspective adapter: {e}")
```

### Add New Connector

Similar pattern for connectors:

```python
from adapters import ObjectStorageConnector, ConnectorMetadata, ConnectorType

class MinIOConnector(ObjectStorageConnector):
    def __init__(self, endpoint: str, access_key: str, secret_key: str, **kwargs):
        super().__init__(**kwargs)
        # Initialize MinIO client
    
    def read_jsonl(self, uri: str) -> List[dict]:
        # Implementation
        pass
    
    def write_jsonl(self, uri: str, records: List[dict]) -> None:
        # Implementation
        pass
    
    # ... other methods
    
    def get_metadata(self) -> ConnectorMetadata:
        return ConnectorMetadata(
            name="minio",
            connector_type=ConnectorType.OBJECT_STORAGE,
            provider="MinIO",
        )
```

## Advanced Usage

### Adapter Chain

Combine multiple adapters:

```python
class EnsembleAdapter(BaseGuardAdapter):
    """Combine multiple adapters using voting."""
    
    def __init__(self, adapters: List[BaseGuardAdapter], threshold: int = 2):
        self.adapters = adapters
        self.threshold = threshold
    
    def score(self, text: str, **kwargs) -> ScoreResult:
        results = [adapter.score(text, **kwargs) for adapter in self.adapters]
        
        # Count how many flagged
        flagged_count = sum(1 for r in results if r.flagged)
        
        # Average score
        avg_score = sum(r.score for r in results) / len(results)
        
        return ScoreResult(
            flagged=flagged_count >= self.threshold,
            score=avg_score,
            categories={},
            provider="ensemble",
        )
```

### Fallback Adapter

Use fallback if primary fails:

```python
def score_with_fallback(text: str, primary: BaseGuardAdapter, fallback: BaseGuardAdapter) -> ScoreResult:
    try:
        return primary.score(text)
    except Exception as e:
        logger.warning(f"Primary adapter failed ({e}), using fallback")
        return fallback.score(text)

# Usage
openai = get_guard_adapter("openai", api_key="...")
internal = get_guard_adapter("internal")

result = score_with_fallback(text, primary=openai, fallback=internal)
```

## Testing

Run adapter tests:

```bash
pytest tests/test_adapters*.py -v
```

**34 comprehensive tests** covering:
- ✅ ScoreResult creation and serialization
- ✅ GuardMetadata
- ✅ BaseGuardAdapter interface
- ✅ InternalPolicyAdapter
- ✅ OpenAIAdapter (with mocked API)
- ✅ AzureContentSafetyAdapter (with mocked API)
- ✅ AdapterRegistry (registration, lookup, singleton)
- ✅ Connector adapters (S3, Kafka)
- ✅ Error handling
- ✅ Health checks

## Performance

Adapter overhead is minimal (<1ms):
- Interface calls are direct method invocations
- No serialization/deserialization overhead
- Latency dominated by external API calls

## Security

- **API Keys**: Stored in adapter config, not logged
- **Validation**: Input validation in adapter
- **Error Handling**: Exceptions don't leak sensitive data
- **Timeouts**: Prevent hanging on slow APIs

## Related Documentation

- [Configuration Guide](CONFIGURATION.md)
- [API Documentation](API.md)
- [Development Guide](DEVELOPMENT.md)
- [Adding New Providers](CONTRIBUTING.md)

## Support

For adapter issues:
1. Check adapter health: `adapter.health_check()`
2. Enable debug logging: `logging.getLogger("adapters").setLevel(logging.DEBUG)`
3. Check provider API status
4. Review error in `result.raw_response`

