# Federated Learning Telemetry

This document describes the privacy-preserving federated learning telemetry system for collaborative model improvement.

## Overview

Federated learning telemetry enables collaborative improvement of safety models across deployments **without sharing sensitive data**. The system collects anonymized evaluation insights to help identify common weaknesses and improve model performance for everyone.

## Privacy-First Design

🔒 **Opt-In Only**: Disabled by default, requires explicit configuration  
🔒 **No PII**: Never collects personally identifiable information  
🔒 **No Raw Content**: Never transmits user prompts or text  
🔒 **Differential Privacy**: Adds calibrated noise to prevent re-identification  
🔒 **Anonymized IDs**: Tenant/deployment IDs are cryptographically hashed  
🔒 **Aggregated Only**: Only statistical summaries, not individual records  
🔒 **Transparent**: Clear documentation of what is collected  

## What is Collected

### Aggregated Statistics (Per Evaluation Run)

✅ **Metrics**:
- False negatives count
- False positives count
- True positives count
- True negatives count
- Precision, recall values
- Average latency (ms)

✅ **Metadata**:
- Anonymized deployment ID (hashed)
- Model version
- Policy version
- Guard name (e.g., "internal", "openai")
- Categories with issues (e.g., ["self-harm", "violence"])

### What is NOT Collected

❌ **Never Collected**:
- Raw text or prompts
- User IDs or emails
- IP addresses
- Session IDs
- Tenant names
- API keys or credentials
- Any personally identifiable information

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `FEDERATED_TELEMETRY_ENABLED` | No | `0` | Enable telemetry (`1` to enable) |
| `FEDERATED_SERVER_URL` | Yes* | None | Central aggregation server URL |
| `DEPLOYMENT_ID` | No | `"default"` | Deployment identifier (will be anonymized) |

*Required only if telemetry is enabled

### Enable Telemetry

```bash
# Enable federated telemetry
export FEDERATED_TELEMETRY_ENABLED=1
export FEDERATED_SERVER_URL=https://telemetry.safety-eval.ai/collect
export DEPLOYMENT_ID=my-deployment-name

# Start service
PYTHONPATH=src uvicorn service.api:app --port 8001
```

### Verify Telemetry Status

Check logs for:
```
INFO: Federated telemetry: enabled=True, server=https://..., dp=True
INFO: Federated telemetry background sender started
```

Or call the health endpoint (if implemented):
```bash
curl http://localhost:8001/telemetry/status
```

## How It Works

### 1. Data Collection

After each evaluation run, anonymized statistics are extracted:

```python
{
  "deployment_id": "a1b2c3d4e5f6",  # Hashed deployment ID
  "model_version": "1.0",
  "policy_version": "v1.2.3",
  "stats": {
    "runs_analyzed": 1,
    "false_negatives": 8,      # With DP noise
    "false_positives": 3,      # With DP noise  
    "true_positives": 87,      # With DP noise
    "true_negatives": 92,      # With DP noise
    "precision": 0.967,
    "recall": 0.916,
    "avg_latency_ms": 150,
    "guard_name": "internal",
    "categories_missed": ["self-harm"]
  },
  "timestamp": 1696780800.0
}
```

### 2. Differential Privacy

Laplace noise is added to counts to prevent re-identification:

```python
# Original count
false_negatives = 5

# With differential privacy (ε = 1.0)
noised_fn = 5 + Laplace(0, 1/ε)
# Result might be: 4, 5, 6, 7, etc.
```

**Privacy Parameter (ε)**:
- ε = 0.1: Very high privacy, more noise
- ε = 1.0: Good balance (default)
- ε = 10.0: Less privacy, less noise

### 3. Batching

Payloads are batched before sending:
- Default batch size: 10 payloads
- Send interval: 5 minutes
- Automatic retry on failure

### 4. Transmission

HTTPS POST to central server:

```http
POST https://telemetry.safety-eval.ai/collect
Content-Type: application/json

{
  "payloads": [
    {
      "deployment_id": "...",
      "model_version": "...",
      "stats": { ... }
    },
    ...
  ]
}
```

### 5. Central Aggregation

The central server aggregates statistics across all deployments to:
- Identify common false negative patterns
- Prioritize categories needing improvement
- Guide policy rule development
- Improve model accuracy for everyone

## Programmatic Usage

### Report Evaluation Run

```python
from telemetry import get_telemetry_client

client = get_telemetry_client()

# After evaluation
run_result = {
    "tp": 90,
    "fp": 5,
    "tn": 95,
    "fn": 10,
    "precision": 0.947,
    "recall": 0.900,
}

await client.report_run(
    run_result=run_result,
    model_version="1.0",
    policy_version="v1.2.3"
)
```

### Manual Payload

```python
from telemetry import TelemetryPayload

payload = TelemetryPayload(
    deployment_id="anon-123",
    model_version="1.0",
    policy_version="v1",
    stats={
        "false_negatives": 5,
        "categories_missed": ["violence"],
    }
)

await client.report(payload)
```

### Flush Immediately

```python
# Send all pending payloads now
await client.flush()
```

## Testing

Run telemetry tests:

```bash
pytest tests/test_federated_telemetry.py -v
```

**22 comprehensive tests** covering:
- ✅ Privacy utilities (hashing, anonymization, DP noise)
- ✅ Payload creation and serialization
- ✅ Telemetry client (enabled/disabled, batching, sending)
- ✅ Configuration from environment
- ✅ Data anonymization (no PII, no raw text)
- ✅ Differential privacy on counts
- ✅ Error handling and retries

### Test with Mock Server

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_telemetry_send():
    with patch("telemetry.federated.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client_class.return_value = mock_client
        
        client = FederatedTelemetry(
            enabled=True,
            server_url="https://test.com"
        )
        
        await client.report(payload)
        await client.flush()
        
        # Verify POST was called
        assert mock_client.post.called
```

## Privacy Guarantees

### Differential Privacy

**Laplace Mechanism**:
```
noised_value = true_value + Laplace(0, 1/ε)
```

**Properties**:
- Individual contributions are hidden
- Cannot determine exact counts from single deployment
- Aggregated trends remain visible
- Adjustable privacy parameter (ε)

### Anonymization

**Tenant ID**:
```
anonymized = SHA256(salt + tenant_id)[:16]
```

**Text Hashing**:
```
hash = SHA256(text)
```

### Data Minimization

Only essential statistics are collected:
- Counts (with noise)
- Metrics (precision, recall)
- Category labels
- Performance metrics

## Security

### HTTPS Required

All telemetry transmissions use HTTPS:
```python
client = FederatedTelemetry(
    server_url="https://telemetry.example.com"  # HTTPS only
)
```

### Authentication (Optional)

For production, add API key authentication:

```python
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}
```

### Rate Limiting

Built-in batching prevents overwhelming the server:
- Batch size: 10 payloads
- Send interval: 5 minutes
- Max batch size: 20 (memory limit)

## Troubleshooting

### Telemetry Not Sending

**Check Configuration**:
```bash
echo $FEDERATED_TELEMETRY_ENABLED  # Should be "1"
echo $FEDERATED_SERVER_URL          # Should be valid HTTPS URL
```

**Check Logs**:
```bash
grep "Federated telemetry" /var/log/service.log
```

Should see:
```
INFO: Federated telemetry: enabled=True, server=https://...
INFO: Federated telemetry background sender started
INFO: Federated telemetry: sent 10 payloads to https://...
```

### Server Unreachable

If server is down, telemetry will:
1. Log error: `Federated telemetry send failed: ...`
2. Re-queue payloads (up to batch limit)
3. Retry on next interval
4. Not affect main evaluation flow

### Verify Privacy

Test that no sensitive data is sent:

```python
from telemetry import TelemetryPayload, anonymize_payload

run_result = {
    "raw_text": "SENSITIVE CONTENT",  # Should be excluded
    "tp": 10,
    "fn": 2,
}

payload = TelemetryPayload.from_run_result(
    run_result=run_result,
    deployment_id="deploy-123",
    model_version="1.0",
    policy_version="v1"
)

payload_dict = payload.to_dict()
anonymized = anonymize_payload(payload_dict)

# Verify no sensitive content
assert "SENSITIVE" not in str(anonymized)
assert "raw_text" not in anonymized
```

## Opt-Out

Telemetry is **opt-in** (disabled by default).

To explicitly disable:

```bash
export FEDERATED_TELEMETRY_ENABLED=0
# or simply don't set it
```

To verify it's disabled, check logs:
```
INFO: Federated telemetry: enabled=False
```

## Central Server (Aggregation)

### Expected Endpoint

The central server should accept:

```http
POST /collect
Content-Type: application/json

{
  "payloads": [
    {
      "deployment_id": "a1b2c3d4",
      "model_version": "1.0",
      "policy_version": "v1.2.3",
      "stats": { ... },
      "timestamp": 1696780800.0
    },
    ...
  ]
}
```

### Aggregation Strategy

The server can:
1. **Sum across deployments**: Total FNs by category
2. **Identify patterns**: Common missed content types
3. **Guide improvements**: Prioritize rule development
4. **Share back**: Improved models to all participants

### Example Aggregation

```python
# Aggregate from 100 deployments
total_fn_violence = sum(p["stats"]["false_negatives"] 
                       for p in payloads 
                       if "violence" in p["stats"].get("categories_missed", []))

# Result: 500 total FNs in violence category
# → Priority: Add more violence detection rules
```

## Best Practices

1. **Transparency**: Document what is collected
2. **Consent**: Make opt-in clear during setup
3. **Minimize**: Only collect what's needed
4. **Anonymize**: Hash all identifiers
5. **Noise**: Apply differential privacy
6. **Secure**: HTTPS only
7. **Monitor**: Log telemetry activity
8. **Audit**: Review collected data periodically

## Compliance

### GDPR

- ✅ **Consent**: Opt-in required
- ✅ **Minimization**: Only aggregated stats
- ✅ **Anonymization**: Hashed identifiers
- ✅ **Transparency**: Clear documentation
- ✅ **Right to Object**: Can disable anytime

### CCPA

- ✅ **Notice**: Clear privacy notice
- ✅ **Opt-Out**: Easy to disable
- ✅ **No Sale**: Data not sold to third parties
- ✅ **Security**: HTTPS encryption

### HIPAA (if applicable)

- ✅ **De-identification**: No PHI collected
- ✅ **Minimum Necessary**: Only required stats
- ✅ **Secure Transmission**: HTTPS

## Related Documentation

- [Privacy Policy](PRIVACY.md)
- [Configuration Guide](CONFIGURATION.md)
- [Security Best Practices](SECURITY.md)
- [Federated Learning Overview](FEDERATED_LEARNING.md)

## Support

For telemetry issues:
1. Check `FEDERATED_TELEMETRY_ENABLED` is set to `1`
2. Verify `FEDERATED_SERVER_URL` is valid HTTPS
3. Check logs for errors
4. Test with mock server
5. Verify httpx is installed: `pip show httpx`

