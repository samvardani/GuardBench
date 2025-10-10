# CI-Safe Image Moderation Testing

This document describes the CI-safe image moderation implementation that avoids downloading large models during testing while maintaining deterministic, reliable test coverage.

## Overview

The image moderation module provides a **provider interface** that allows switching between real HuggingFace models (production) and lightweight stub models (testing/CI).

## Problem

Traditional image moderation tests face several challenges in CI environments:

❌ **Large Model Downloads**: HuggingFace models are 100s of MBs  
❌ **Network Dependency**: Requires internet access  
❌ **Slow Execution**: Model loading takes 10-30 seconds  
❌ **ABI Instability**: PyTorch/transformers version mismatches  
❌ **Non-Deterministic**: Model outputs can vary slightly  

## Solution

✅ **Provider Interface**: Abstract moderation logic  
✅ **Stub Model**: Lightweight, deterministic, no downloads  
✅ **Pinned Dependencies**: Avoid ABI churn  
✅ **Marked Slow Tests**: Skip heavy tests in CI  
✅ **Fast Test Suite**: 10 tests run in <0.1s  

## Architecture

```
                    ImageModerationProvider (interface)
                               |
                +--------------+--------------+
                |                             |
    HuggingFaceImageModerator       StubImageModerator
        (production)                    (testing)
        - Downloads model               - No model
        - Network required              - Offline
        - Real inference                - Fixed logits
        - Slow (10-30s)                 - Fast (<1ms)
```

## Configuration

### Environment Variables

| Variable | Values | Description |
|----------|--------|-------------|
| `ENABLE_IMAGE` | `0`, `1` | Enable image moderation |
| `TEST_MODE` | `0`, `1` | Force stub model |

### Provider Selection Logic

```python
def get_image_moderator() -> ImageModerationProvider:
    if TEST_MODE=1 or ENABLE_IMAGE=0:
        return StubImageModerator()  # Fast, no download
    else:
        return HuggingFaceImageModerator()  # Real model
```

## Stub Model

### Deterministic Logic

The stub uses **filename patterns** for deterministic results:

| Filename Pattern | Result | Categories |
|-----------------|--------|------------|
| `*nsfw*` or `*unsafe*` | Unsafe | `nsfw: 0.95` |
| `*violence*` | Unsafe | `violence: 0.90` |
| Default | Safe | `normal: 0.98` |

### Example

```python
from image_moderation import StubImageModerator

moderator = StubImageModerator()

# Safe image
result = moderator.moderate("photo.png")
# → is_safe=True, normal=0.98

# Unsafe image (filename pattern)
result = moderator.moderate("nsfw_image.png")
# → is_safe=False, nsfw=0.95
```

### Benefits

✅ **No Model Loading**: Instant initialization  
✅ **No Network**: Fully offline  
✅ **Deterministic**: Same input → same output  
✅ **Fast**: <1ms per image  
✅ **CI-Friendly**: No infrastructure required  

## Testing

### Fast Tests (Default)

Run **without** downloading models:

```bash
# Set TEST_MODE to use stub
TEST_MODE=1 pytest tests/test_image_moderation.py -v

# Or skip slow tests
pytest tests/test_image_moderation.py -v -m "not slow"
```

**Results**:
```
10 passed, 3 deselected in 0.05s
```

### Slow Tests (Optional)

Run **with** real HuggingFace models:

```bash
# Install image deps
pip install -e ".[image]"

# Run all tests (including slow)
ENABLE_IMAGE=1 pytest tests/test_image_moderation.py -v
```

**Results**:
```
13 passed in 30.5s  # Model download + inference
```

## Test Coverage

### Fast Tests (10 tests, ~0.05s)

✅ **StubImageModerator** (5 tests):
  - Stub creation
  - Safe image detection
  - NSFW image detection
  - Violence detection
  - Deterministic results

✅ **Factory** (2 tests):
  - TEST_MODE returns stub
  - ENABLE_IMAGE=0 returns stub

✅ **Thresholds** (2 tests):
  - Safe image passes threshold
  - Unsafe image blocked by threshold

✅ **Result** (1 test):
  - ImageModerationResult creation

### Slow Tests (3 tests, ~30s)

🐌 **HuggingFaceImageModerator** (3 tests):
  - Model creation (downloads model)
  - Real moderation (inference)
  - Production mode

**Marked with** `@pytest.mark.slow` and `@pytest.mark.image`

## Dependency Pinning

To avoid ABI churn, dependencies are **pinned** in `pyproject.toml`:

```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.2.0",
    # Image moderation deps (pinned)
    "pillow==10.3.0",
    "torch==2.3.1",
    "torchvision==0.18.1",
    "transformers==4.41.2",
]

image = [
    "pillow==10.3.0",
    "torch==2.3.1",
    "torchvision==0.18.1",
    "transformers==4.41.2",
]
```

### Why Pin?

- ❌ **Unplanned**: `torch>=2.3.0` → CI breaks on 2.4.0 (ABI change)
- ✅ **Pinned**: `torch==2.3.1` → CI stable

## Pytest Configuration

### Markers

```ini
[pytest]
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    image: marks tests requiring image moderation models
```

### Usage

```bash
# Run only fast tests (default)
pytest -m "not slow"

# Run only slow tests
pytest -m "slow"

# Run image tests
pytest -m "image"
```

## CI Integration

### GitHub Actions

```yaml
name: Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -e ".[dev]"
      
      - name: Run fast tests (no model download)
        env:
          TEST_MODE: "1"
        run: |
          pytest tests/test_image_moderation.py -v -m "not slow"
      
      # Optional: Run slow tests (weekly)
      - name: Run slow tests (with model)
        if: github.event_name == 'schedule'
        env:
          ENABLE_IMAGE: "1"
        run: |
          pytest tests/test_image_moderation.py -v -m "slow"
```

### Benefits

✅ **Fast CI**: No model downloads  
✅ **No Network**: Fully offline  
✅ **Predictable**: Deterministic results  
✅ **Optional Slow**: Real model tests on schedule  

## Production Usage

### With HuggingFace Model

```python
import os

# Enable image moderation
os.environ["ENABLE_IMAGE"] = "1"
os.environ["TEST_MODE"] = "0"

from image_moderation import get_image_moderator

# Gets HuggingFaceImageModerator
moderator = get_image_moderator()

# Real inference
result = moderator.moderate("user_upload.png")

if not result.is_safe:
    print(f"Blocked: {result.flagged_categories}")
```

## Best Practices

1. **Always use stub in tests**: Set `TEST_MODE=1` or `ENABLE_IMAGE=0`
2. **Pin dependencies**: Avoid ABI churn with exact versions
3. **Mark slow tests**: Use `@pytest.mark.slow` for model tests
4. **Run fast by default**: Skip slow tests in CI
5. **Test thresholds**: Verify gating logic with deterministic logits

## Troubleshooting

### Test Fails: "transformers not installed"

**Issue**: Slow test tried to import transformers

**Fix**: Skip slow tests or install deps
```bash
pytest -m "not slow"  # Skip
# OR
pip install -e ".[image]"  # Install
```

### CI Downloads Model

**Issue**: `TEST_MODE` not set

**Fix**: Set environment variable
```bash
TEST_MODE=1 pytest tests/test_image_moderation.py
```

### ABI Mismatch

**Issue**: PyTorch version incompatible

**Fix**: Use pinned versions
```bash
pip install -e ".[dev]"  # Installs pinned versions
```

## Performance

| Configuration | Initialization | Per Image | Total (13 tests) |
|--------------|---------------|-----------|------------------|
| **Stub** (TEST_MODE=1) | <1ms | <1ms | **~0.05s** ✅ |
| **HuggingFace** (ENABLE_IMAGE=1) | 10-30s | 100-500ms | **~30s** 🐌 |

**Speedup**: ~600x faster with stub

## Related Documentation

- [Image Moderation Provider Interface](../src/image_moderation/provider.py)
- [Stub Implementation](../src/image_moderation/stub.py)
- [Test Suite](../tests/test_image_moderation.py)

## Summary

The CI-safe image moderation implementation provides:

✅ **Fast Tests**: 10 tests in <0.1s (no model download)  
✅ **Deterministic**: Stub returns fixed logits  
✅ **CI-Friendly**: No network, no large files  
✅ **Production-Ready**: Real HuggingFace model available  
✅ **Flexible**: Switch with environment variables  

This enables reliable, fast testing while maintaining production-grade image moderation capabilities.

