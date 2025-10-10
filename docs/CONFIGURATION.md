# Configuration Guide

This guide describes the centralized configuration system for Safety-Eval-Mini.

## Overview

All configuration settings are managed through a centralized `AppConfig` class in `src/config.py`. This replaces scattered `os.getenv()` calls throughout the codebase, providing:

- ✅ **Type Safety**: Pydantic validation ensures correct types
- ✅ **Defaults**: Sensible defaults for all settings
- ✅ **Documentation**: All settings documented inline
- ✅ **Secret Management**: SecretStr for sensitive values
- ✅ **Validation**: Automatic validation of values
- ✅ **Single Source of Truth**: All configuration in one place

## Quick Start

### Using Configuration

```python
from config import get_config

# Get configuration (singleton)
config = get_config()

# Access settings
port = config.uvicorn_port
host = config.uvicorn_host
log_level = config.log_level

# Access secrets (use .get_secret_value())
session_key = config.session_secret.get_secret_value()
```

### Setting Environment Variables

```bash
# Development
export ENVIRONMENT=development
export LOG_LEVEL=DEBUG
export UVICORN_PORT=8000

# Production
export ENVIRONMENT=production
export UVICORN_HOST=0.0.0.0
export UVICORN_WORKERS=4
export SESSION_SECRET=your-secret-key-here
```

### Using .env File

Create `.env` in the project root:

```ini
# Application
ENVIRONMENT=development
LOG_LEVEL=DEBUG

# Server
UVICORN_HOST=127.0.0.1
UVICORN_PORT=8000
UVICORN_WORKERS=1

# Database
DATABASE_PATH=history.db

# Security
SESSION_SECRET=dev-secret-change-in-production

# Features
RATE_LIMIT_ENABLED=true
```

## Configuration Reference

### Application Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `app_name` | str | "Safety-Eval-Mini" | Application name |
| `app_version` | str | "1.0.0" | Application version |
| `environment` | str | "development" | Environment (development/staging/production/test) |

### Server Configuration

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `uvicorn_host` | str | "127.0.0.1" | Uvicorn bind host |
| `uvicorn_port` | int | 8000 | Uvicorn port (1-65535) |
| `uvicorn_workers` | int | 1 | Number of worker processes |
| `uvicorn_log_level` | str | "info" | Uvicorn log level |
| `uvicorn_timeout_keep_alive` | int | 5 | Keep-alive timeout (seconds) |

### gRPC Configuration

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `grpc_host` | str | "0.0.0.0" | gRPC server bind host |
| `grpc_port` | int | 50051 | gRPC server port |
| `grpc_tls_enabled` | bool | False | Enable TLS for gRPC |
| `grpc_tls_port` | int | 5443 | gRPC TLS port |
| `grpc_tls_cert` | str? | None | Path to TLS certificate |
| `grpc_tls_key` | str? | None | Path to TLS private key |
| `enable_grpc_reflection` | bool | False | Enable gRPC reflection |

### Service Configuration

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `predict_max_workers` | int | 8 | Max worker threads for predictions |
| `predict_timeout_seconds` | float | 2.0 | Prediction timeout |
| `max_json_body_bytes` | int | 1_048_576 | Max JSON body size (1MB) |
| `safety_max_rows` | int | 5000 | Max rows per evaluation run |

### Rate Limiting

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `rate_limit_enabled` | bool | True | Enable rate limiting |
| `token_rate_limit` | int | 60 | Requests per token per window |
| `token_rate_window_seconds` | int | 60 | Rate limit window (seconds) |

### Circuit Breaker

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `cb_failure_threshold` | int | 3 | Failures before opening circuit |
| `cb_latency_threshold_ms` | int | 750 | Latency threshold (ms) |
| `cb_recovery_seconds` | float | 30.0 | Recovery time (seconds) |

### Logging

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `log_level` | str | "INFO" | Log level (DEBUG/INFO/WARNING/ERROR/CRITICAL) |

### CORS

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `cors_allow_origins` | str? | None | Allowed origins (comma-separated or * for all) |

### Redis

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `redis_url` | str? | None | Redis connection URL |

### Kafka

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `kafka_brokers` | str? | None | Kafka broker addresses (comma-separated) |
| `kafka_rest_proxy` | str? | None | Kafka REST proxy URL |
| `kafka_topic` | str? | None | Kafka topic name |

### Cloud Storage (S3)

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `aws_access_key_id` | SecretStr? | None | AWS access key ID |
| `aws_secret_access_key` | SecretStr? | None | AWS secret access key |
| `aws_region` | str | "us-east-1" | AWS region |
| `s3_bucket` | str? | None | S3 bucket name |
| `s3_prefix` | str | "safety-eval" | S3 key prefix |

### Cloud Storage (Azure)

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `azure_storage_account` | str? | None | Azure storage account name |
| `azure_storage_key` | SecretStr? | None | Azure storage key |
| `azure_container` | str? | None | Azure Blob container name |
| `azure_connection_string` | SecretStr? | None | Azure storage connection string |

### Cloud Storage (GCS)

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `gcs_bucket` | str? | None | GCS bucket name |
| `gcs_project` | str? | None | GCP project ID |
| `google_application_credentials` | str? | None | Path to service account key JSON |

### Observability

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `otel_exporter_otlp_endpoint` | str? | None | OpenTelemetry OTLP endpoint |
| `otel_exporter_otlp_insecure` | bool | True | Use insecure OTLP connection |

### Policy

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `policy_path` | str | "policy/policy.yaml" | Path to policy YAML file |
| `policy_version` | str? | None | Policy version (auto-detected from git) |
| `policy_checksum` | str? | None | Policy checksum (auto-computed) |

### Security

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `session_secret` | SecretStr | "dev-not-secret..." | Session middleware secret key |
| `policy_admin_token` | SecretStr? | None | Admin token for policy management |
| `federation_tenant_secret` | SecretStr | "default-secret..." | Federation tenant shared secret |

### Slack Integration

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `slack_bot_token` | SecretStr? | None | Slack bot OAuth token |
| `slack_signing_secret` | SecretStr? | None | Slack signing secret |
| `slack_app_token` | SecretStr? | None | Slack app-level token |
| `slack_client_id` | str? | None | Slack OAuth client ID |
| `slack_client_secret` | SecretStr? | None | Slack OAuth client secret |

### Usage Quotas

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `enforce_usage_quota` | bool | False | Enforce hard usage quota limits |

### Other

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `build_id` | str? | None | Build ID or git commit hash |
| `feed_refresh_seconds` | float | 3600.0 | Feed refresh interval (seconds) |
| `default_guard` | str | "candidate" | Default safety guard |

## Usage Patterns

### Application Startup

```python
from config import get_config

# Initialize config early
config = get_config()

# Log configuration (secrets redacted)
config.log_config()

# Use throughout application
app_host = config.uvicorn_host
app_port = config.uvicorn_port
```

### In Functions/Classes

```python
from config import get_config

def my_function():
    config = get_config()
    
    # Use config values
    timeout = config.predict_timeout_seconds
    max_workers = config.predict_max_workers
    
    # Access secrets
    if config.policy_admin_token:
        admin_token = config.policy_admin_token.get_secret_value()
```

### Dependency Injection

```python
from config import get_config, AppConfig

class MyService:
    def __init__(self, config: AppConfig):
        self.config = config
        self.timeout = config.predict_timeout_seconds
    
    def process(self):
        # Use self.config...
        pass

# Usage
config = get_config()
service = MyService(config)
```

### Testing

```python
import os
from unittest.mock import patch
from config import AppConfig, reload_config

def test_with_custom_config():
    # Override env vars
    with patch.dict(os.environ, {
        "UVICORN_PORT": "9000",
        "LOG_LEVEL": "DEBUG"
    }):
        config = AppConfig()  # Create new instance
        assert config.uvicorn_port == 9000
        assert config.log_level == "DEBUG"

def test_singleton_reload():
    # Reload singleton with new env vars
    with patch.dict(os.environ, {"UVICORN_PORT": "7777"}):
        config = reload_config()
        assert config.uvicorn_port == 7777
```

## Secret Management

### SecretStr Fields

SecretStr fields hide their values in logs and string representations:

```python
config = get_config()

# Value is hidden
print(config.session_secret)  # Output: **********

# Get actual value
secret_value = config.session_secret.get_secret_value()
```

### In Production

**Never commit secrets to version control!**

Use environment variables or a secret management service:

```bash
# Environment variables
export SESSION_SECRET=$(openssl rand -hex 32)
export AWS_SECRET_ACCESS_KEY=your-key-here

# Or use a secrets manager
export SESSION_SECRET=$(aws secretsmanager get-secret-value --secret-id app/session_secret --query SecretString --output text)
```

## Logging Configuration

Log effective configuration on startup (with secrets redacted):

```python
from config import get_config
import logging

logger = logging.getLogger(__name__)

config = get_config()
config.log_config(logger)
```

Output:
```
============================================================
Application Configuration
============================================================

[Application]
  app_name: Safety-Eval-Mini
  environment: development
  
[Server]
  uvicorn_host: 127.0.0.1
  uvicorn_port: 8000
  
[Security]
  session_secret: ***REDACTED***
  
============================================================
```

## Environment-Specific Configuration

### Development

```bash
export ENVIRONMENT=development
export LOG_LEVEL=DEBUG
export RATE_LIMIT_ENABLED=false
export UVICORN_HOST=127.0.0.1
```

### Production

```bash
export ENVIRONMENT=production
export LOG_LEVEL=WARNING
export UVICORN_HOST=0.0.0.0
export UVICORN_WORKERS=4
export RATE_LIMIT_ENABLED=true
export REDIS_URL=redis://redis:6379/0
export SESSION_SECRET=<generate-secure-key>
```

### Testing

```bash
export ENVIRONMENT=test
export DATABASE_PATH=:memory:
export LOG_LEVEL=ERROR
export RATE_LIMIT_ENABLED=false
```

## Migration from os.getenv()

### Before (Old Way)

```python
import os

port = int(os.getenv("GRPC_PORT", "50051"))
host = os.getenv("GRPC_HOST", "0.0.0.0")
tls_enabled = os.getenv("GRPC_TLS_ENABLED", "false").lower() in {"1", "true", "yes"}
```

### After (New Way)

```python
from config import get_config

config = get_config()

port = config.grpc_port
host = config.grpc_host
tls_enabled = config.grpc_tls_enabled
```

### Benefits

- ✅ **Type safety**: No manual int() conversion or boolean parsing
- ✅ **Validation**: Invalid values caught at startup
- ✅ **Documentation**: All settings documented in one place
- ✅ **Testing**: Easier to mock and test
- ✅ **IDE support**: Autocomplete and type hints

## Troubleshooting

### Invalid Configuration

If configuration is invalid, Pydantic will raise a validation error at startup:

```
ValidationError: 1 validation error for AppConfig
uvicorn_port
  Input should be less than or equal to 65535 [type=less_than_equal, input_value=99999]
```

Fix by setting a valid value:
```bash
export UVICORN_PORT=8000
```

### Missing Required Settings

Optional settings default to None. If your code requires a setting, check it:

```python
config = get_config()

if not config.redis_url:
    raise ValueError("REDIS_URL environment variable is required")
```

### Secret Values

Remember to use `.get_secret_value()` for SecretStr fields:

```python
# Wrong ❌
token = config.slack_bot_token  # SecretStr object

# Right ✅
token = config.slack_bot_token.get_secret_value()  # str
```

## Best Practices

1. **Initialize Early**: Call `get_config()` at application startup
2. **Log Configuration**: Use `config.log_config()` to verify settings
3. **Use .env Files**: For local development convenience
4. **Validate Secrets**: Check required secrets exist at startup
5. **Document Changes**: Update this guide when adding new settings
6. **Test Configuration**: Write tests for configuration logic
7. **Never Commit Secrets**: Use environment variables or secret managers

## Related Documentation

- [Deployment Guide](DEPLOYMENT.md)
- [Security Best Practices](SECURITY.md)
- [Development Setup](DEVELOPMENT.md)

