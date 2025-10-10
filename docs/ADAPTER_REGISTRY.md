# Unified Adapter Registry

This document describes the unified adapter registry system for managing content moderation providers with a single source of truth for provider routing.

## Overview

The adapter registry provides a centralized, consistent way to register and use different content moderation providers (OpenAI, Azure, local policy, etc.) through a common interface.

## Key Principles

🎯 **Single Registry**: One `AdapterRegistry` for all providers  
🎯 **Canonical Model**: One `ScoreResult` model used everywhere  
🎯 **Abstract Interface**: `BaseGuardAdapter` for all implementations  
🎯 **Auto-Registration**: Built-in adapters registered automatically  
🎯 **No Duplicates**: Eliminates duplicate provider routing logic  

## Architecture

```
AdapterRegistry (single source of truth)
        ↓
    register(name, class)
        ↓
   ┌──────────┬──────────┬──────────┐
   │  local   │  openai  │  azure   │
   │(internal)│          │          │
   └──────────┴──────────┴──────────┘
        ↓
BaseGuardAdapter.score(text)
        ↓
    ScoreResult (canonical)
```

## Base Adapter Interface

### BaseGuardAdapter

All adapters must implement:

```python
from adapters import BaseGuardAdapter, ScoreResult

class MyCustomAdapter(BaseGuardAdapter):
    def score(self, text: str, context: dict = None) -> ScoreResult:
        # Evaluate content
        is_safe = analyze(text)
        
        return ScoreResult(
            is_safe=is_safe,
            confidence=0.95,
            categories={"violence": 0.1},
            flagged_categories=[],
            provider="mycustom"
        )
```

### Canonical ScoreResult

**Single source of truth** for all score results:

```python
@dataclass
class ScoreResult:
    is_safe: bool              # Safety decision
    confidence: float          # 0.0 - 1.0
    categories: Dict[str, float]  # Category scores
    flagged_categories: List[str]  # Above threshold
    provider: str              # Provider name
    latency_ms: int           # Response time
    reason: Optional[str]      # Optional explanation
    metadata: Dict[str, Any]   # Additional data
```

## Usage

### Register Custom Adapter

```python
from adapters import get_adapter_registry, BaseGuardAdapter, ScoreResult

class MyAdapter(BaseGuardAdapter):
    def score(self, text, context=None):
        return ScoreResult(
            is_safe=True,
            confidence=0.9,
            provider="my_adapter"
        )

# Register
registry = get_adapter_registry()
registry.register("my_adapter", MyAdapter)
```

### Use Adapter

```python
from adapters import get_adapter_registry

registry = get_adapter_registry()

# Get adapter instance
adapter = registry.get("openai", config={"api_key": "..."})

# Score content
result = adapter.score("test content")

print(f"Safe: {result.is_safe}")
print(f"Confidence: {result.confidence}")
print(f"Flagged: {result.flagged_categories}")
```

### List Available Adapters

```python
registry = get_adapter_registry()

adapters = registry.list_adapters()
# Returns: ['local', 'internal', 'openai', 'azure']
```

## Built-in Adapters

### LocalPolicyAdapter

Uses system's built-in policy rules:

```python
from adapters import LocalPolicyAdapter

adapter = LocalPolicyAdapter(name="local")

result = adapter.score("test content")
# Uses local policy engine
```

**Auto-registered as**:
- `local`
- `internal` (alias)

### OpenAIAdapter

Uses OpenAI Moderation API:

```python
from adapters import OpenAIAdapter

adapter = OpenAIAdapter(
    name="openai",
    config={"api_key": "sk-..."}
)

result = adapter.score("test content")
# Calls OpenAI API
```

**Configuration**:
- `api_key`: From config or `OPENAI_API_KEY` env
- Timeout: 10 seconds
- Fail open on errors

**Auto-registered as**:
- `openai`

### AzureContentSafetyAdapter

Uses Azure Content Safety API:

```python
from adapters import AzureContentSafetyAdapter

adapter = AzureContentSafetyAdapter(
    name="azure",
    config={
        "api_key": "...",
        "endpoint": "https://..."
    }
)

result = adapter.score("test content")
# Calls Azure API
```

**Configuration**:
- `api_key`: From config or `AZURE_CONTENT_SAFETY_KEY`
- `endpoint`: From config or `AZURE_CONTENT_SAFETY_ENDPOINT`

**Auto-registered as**:
- `azure`

## Adding New Provider

### Step 1: Implement Adapter

```python
# src/adapters/myprovider.py

from adapters import BaseGuardAdapter, ScoreResult

class MyProviderAdapter(BaseGuardAdapter):
    def score(self, text, context=None):
        # Call provider API
        response = call_my_provider_api(text)
        
        # Convert to ScoreResult
        return ScoreResult(
            is_safe=response.safe,
            confidence=response.confidence,
            categories=response.categories,
            flagged_categories=response.flagged,
            provider="myprovider"
        )
```

### Step 2: Register

```python
# In __init__.py or startup

from adapters import get_adapter_registry
from adapters.myprovider import MyProviderAdapter

registry = get_adapter_registry()
registry.register("myprovider", MyProviderAdapter)
```

### Step 3: Use

```python
adapter = registry.get("myprovider")
result = adapter.score("test")
```

## Testing

Run adapter registry tests:

```bash
pytest tests/test_adapter_registry.py -v
```

**14 comprehensive tests** covering:
- ✅ ScoreResult model (2 tests)
- ✅ AdapterRegistry (7 tests)
- ✅ Built-in adapters (3 tests)
- ✅ Backward compatibility (2 tests)

## Best Practices

1. **One Registry**: Use `get_adapter_registry()` everywhere
2. **Canonical Model**: Always return `ScoreResult`
3. **Fail Open**: Return safe on errors (don't block content)
4. **Log Errors**: Log API failures for debugging
5. **Cache Instances**: Registry caches adapter instances
6. **Health Checks**: Implement `health_check()` method

## Migration Guide

### From Old Registry

**Before** (duplicate registries):
```python
from old_module import OldRegistry

registry1 = OldRegistry()
registry2 = AnotherRegistry()
```

**After** (unified):
```python
from adapters import get_adapter_registry

registry = get_adapter_registry()  # Single source of truth
```

## Related Documentation

- [Adding Providers](ADDING_PROVIDERS.md)
- [Adapter Development](ADAPTER_DEVELOPMENT.md)
- [Security Best Practices](SECURITY.md)

## Support

For adapter registry issues:
1. Check `get_adapter_registry().list_adapters()`
2. Verify adapter is registered
3. Test with `registry.get(name)`
4. Review adapter implementation
5. Check configuration (API keys, endpoints)

