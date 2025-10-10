# Image Moderation Guide

Optional image moderation for NSFW, violence, and suggestive content detection.

## Overview

The image moderation module provides content safety checks for images via the `/score-image` endpoint. It uses a lightweight HuggingFace model for classification and is disabled by default to minimize dependencies.

## Quick Start

### 1. Install Dependencies

```bash
pip install transformers torch pillow
```

Or use the optional dependency group:

```bash
pip install -e ".[image]"
```

### 2. Enable Image Moderation

```bash
export ENABLE_IMAGE=1
```

### 3. Start Service

```bash
PYTHONPATH=src uvicorn service.api:app --host 0.0.0.0 --port 8001
```

### 4. Score Images

**Upload File**:
```bash
curl -X POST http://localhost:8001/score-image \
  -F "file=@path/to/image.jpg"
```

**From URL**:
```bash
curl -X POST http://localhost:8001/score-image \
  -F "url=https://example.com/image.jpg"
```

## Response Format

```json
{
  "categories": {
    "normal": 0.75,
    "nsfw": 0.15,
    "violence": 0.08,
    "suggestive": 0.02
  },
  "blocked": false,
  "primary_category": "normal",
  "latency_ms": 145,
  "model_name": "Falconsai/nsfw_image_detection",
  "metadata": {
    "primary_score": 0.75,
    "thresholds": {
      "nsfw": 0.5,
      "violence": 0.7,
      "suggestive": 0.6
    }
  }
}
```

## Configuration

Add to `config.yaml`:

```yaml
image_moderation:
  model_name: "Falconsai/nsfw_image_detection"
  cache_dir: "~/.cache/seval-image-models"
  
  thresholds:
    nsfw: 0.5        # Block if NSFW score >= 0.5
    violence: 0.7    # Block if violence score >= 0.7
    suggestive: 0.6  # Block if suggestive score >= 0.6
    normal: 1.0      # Never block normal content
```

## Model Details

**Default Model**: `Falconsai/nsfw_image_detection`
- **Size**: ~500MB (first download)
- **Categories**: normal, nsfw, violence, suggestive
- **Framework**: HuggingFace Transformers + PyTorch
- **Cache**: Models cached locally (`~/.cache/seval-image-models`)

**Lazy Loading**: Model is downloaded and loaded on first request, not at startup.

## Thresholds

Thresholds determine when content is blocked:

- **NSFW**: 0.5 (block if score >= 0.5)
- **Violence**: 0.7 (more permissive)
- **Suggestive**: 0.6 (middle ground)

Lower thresholds = more restrictive (more blocking)
Higher thresholds = more permissive (less blocking)

## Performance

**Hardware Recommendations**:
- **CPU**: Works, ~150-300ms per image
- **GPU**: Recommended for production, ~20-50ms per image
- **Memory**: ~2GB for model + image processing

**First Request**: Slower due to model download/loading (~10-30s depending on network)
**Subsequent Requests**: Fast (~50-300ms depending on hardware)

## API Reference

### POST /score-image

**Content-Type**: `multipart/form-data`

**Parameters**:
- `file` (optional): Image file upload
- `url` (optional): Image URL

**Constraints**:
- Provide either `file` OR `url`, not both
- Max image size: 10MB (configurable)
- Supported formats: PNG, JPEG, GIF, WebP

**Responses**:
- `200`: Success with moderation results
- `400`: Invalid request (missing params, both file and URL provided)
- `404`: Image moderation not enabled (`ENABLE_IMAGE=1` not set)
- `500`: Internal error (model loading failed, etc.)

## Audit Logging

Image moderation events are automatically logged to the audit trail:

```json
{
  "action": "image.score",
  "resource": "image_moderator",
  "context": {
    "image_hash": "abc123def456",
    "primary_category": "normal",
    "blocked": false,
    "source": "file"
  }
}
```

**Privacy**: Only image hash is logged, not the image itself or URL.

## Testing

```bash
# Run image moderation tests (requires ENABLE_IMAGE=1)
ENABLE_IMAGE=1 pytest tests/test_image_moderation*.py -v

# Test with mocked model (no dependencies needed)
pytest tests/test_image_moderation.py::test_is_enabled_default -v
```

## Programmatic Usage

```python
from seval.image_moderation import is_enabled, get_global_moderator
from PIL import Image

# Check if enabled
if is_enabled():
    moderator = get_global_moderator(thresholds={"nsfw": 0.4})
    
    # Moderate image
    img = Image.open("photo.jpg")
    result = moderator.moderate_image(img)
    
    print(f"Blocked: {result.blocked}")
    print(f"Primary: {result.primary_category}")
    print(f"Scores: {result.categories}")
```

## Troubleshooting

**Model download fails**:
- Check internet connection
- Set `HF_HOME` environment variable for custom cache location
- Use `cache_dir` parameter in configuration

**Out of memory**:
- Reduce batch size
- Use CPU instead of GPU
- Resize large images before processing

**Slow inference**:
- Use GPU if available
- Consider model quantization
- Cache results for repeated images

## Production Considerations

1. **Scaling**: Use horizontal scaling with shared model cache
2. **GPU**: Dramatically improves throughput (10x faster)
3. **Caching**: Implement Redis cache for processed image hashes
4. **Rate Limiting**: Add rate limits for /score-image endpoint
5. **File Size**: Enforce max upload size (default: 10MB)
6. **CDN**: For URL-based scoring, use CDN for faster downloads

## Alternative Models

You can use other HuggingFace models:

```yaml
image_moderation:
  model_name: "openai/clip-vit-base-patch32"  # Generic CLIP
  # or
  model_name: "microsoft/resnet-50"  # ResNet-based
```

Adjust thresholds based on model output format.

## Limitations

- **Language**: Model trained primarily on English/Western content
- **Context**: May not understand cultural context
- **Edge Cases**: Artistic content may be misclassified
- **False Positives**: Medical/educational content may trigger NSFW

Use in combination with human review for sensitive applications.

