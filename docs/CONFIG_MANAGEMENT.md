# Configuration Management

This document describes the centralized configuration management system with runtime immutability and static environment read scanning.

## Overview

The configuration system ensures:

✅ **Centralized Configuration**: All env reads through `get_config()`  
✅ **Runtime Immutability**: Config frozen after initialization  
✅ **Static Scanning**: Detect stray `os.getenv()` calls  
✅ **Admin Support**: Debug endpoint with redaction  

## Problem Solved

**Before**: Scattered environment reads
- Direct `os.getenv()` calls throughout codebase
- No validation
- Runtime mutation possible
- Hard to debug configuration issues

**After**: Centralized, immutable config
- Single source of truth (`config.py`)
- Frozen after initialization
- **Static scanner** detects stray calls
- Admin dump endpoint for support

## Configuration Class

### Basic Usage

\`\`\`python
from config import get_config

# Get global config singleton
config = get_config()

# Access configuration
port = config.port
log_level = config.log_level
slack_secret = config.slack_client_secret

# Config is frozen (immutable)
# config.port = 9999  # → Raises FrozenConfigError!
\`\`\`

### Configuration Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| \`host\` | str | "0.0.0.0" | Server host |
| \`port\` | int | 8001 | Server port |
| \`grpc_port\` | int | 50051 | gRPC port |
| \`log_level\` | str | "info" | Log level |
| \`log_format\` | str | "json" | Log format |
| \`enable_image\` | bool | False | Enable image moderation |
| \`test_mode\` | bool | False | Test mode |
| \`oidc_client_id\` | Optional[str] | None | OIDC client ID |
| \`oidc_client_secret\` | Optional[str] | None | OIDC client secret |
| \`saml_*\` | Optional[str] | None | SAML configuration |
| \`slack_*\` | Optional[str] | None | Slack OAuth |
| \`metrics_*\` | - | - | Metrics configuration |
| \`database_url\` | str | "sqlite:///history.db" | Database URL |

### Environment Variables

Config automatically loads from environment:

\`\`\`bash
export PORT=9000
export LOG_LEVEL=debug
export ENABLE_IMAGE=1
export SLACK_CLIENT_SECRET=secret123
\`\`\`

## Runtime Immutability

### Freezing

Config is automatically frozen after initialization:

\`\`\`python
from config import get_config

config = get_config()

# Already frozen
# config.port = 9999  # → FrozenConfigError!
\`\`\`

### Manual Freeze

For testing, you can manually freeze:

\`\`\`python
from config import Config

config = Config()

# Modify before freeze (ok)
config.port = 9000

# Freeze
config.freeze()

# Mutation fails
# config.port = 9001  # → FrozenConfigError!
\`\`\`

### Why Immutability?

- ✅ **Prevents Bugs**: No accidental runtime mutation
- ✅ **Predictable**: Config stays consistent
- ✅ **Thread-Safe**: No concurrent modification issues
- ✅ **Debugging**: Config same as initialization

## Static Scanning

### Scanner Tool

Detect stray `os.getenv()` calls:

\`\`\`bash
# Scan src/ directory
python scripts/scan_env_reads.py src --allow-config

# Scan specific directory
python scripts/scan_env_reads.py src/service

# Scan with custom exclusions
python scripts/scan_env_reads.py src --exclude "*/legacy/*"
\`\`\`

### Example Output

\`\`\`
Scanning src for os.getenv() calls...

❌ Found 15 file(s) with stray os.getenv() calls:

src/service/api.py:
  Line 175: os.getenv('BUILD_ID')
  Line 200: os.getenv('SESSION_SECRET')
  Line 571: os.getenv('POLICY_ADMIN_TOKEN')

Total violations: 58

⚠️  All environment reads should use config.get_config() instead!
\`\`\`

### Fixing Violations

**Before** (bad):
\`\`\`python
import os

def get_port():
    return int(os.getenv("PORT", "8001"))
\`\`\`

**After** (good):
\`\`\`python
from config import get_config

def get_port():
    config = get_config()
    return config.port
\`\`\`

## Config Dump Endpoint

### Admin Support

Dump configuration for debugging:

\`\`\`bash
# With redaction (default)
curl -H "Authorization: Bearer ADMIN_TOKEN" \\
  http://localhost:8001/admin/config/dump

# Without redaction (sensitive!)
curl -H "Authorization: Bearer ADMIN_TOKEN" \\
  http://localhost:8001/admin/config/dump?redact=false
\`\`\`

### Response Format

\`\`\`json
{
  "config": {
    "host": "0.0.0.0",
    "port": 8001,
    "log_level": "info",
    "slack_client_secret": "***REDACTED***",
    "slack_client_id": "U0123456...",
    "metrics_auth_token": "***REDACTED***"
  },
  "redacted": true,
  "frozen": true
}
\`\`\`

### Redaction

**Full redaction** (sensitive):
- `oidc_client_secret`
- `saml_idp_cert`
- `slack_client_secret`
- `slack_signing_secret`
- `metrics_auth_token`

**Partial redaction** (IDs):
- `oidc_client_id` → "client_i..."
- `slack_client_id` → "U012345..."
- `saml_idp_cert_fingerprint` → "a1b2c3d4..."

**No redaction**:
- `port`, `host`, `log_level`, etc.

## Testing

### Config Tests

\`\`\`bash
pytest tests/test_config_sweep.py -v
\`\`\`

**17 tests**:

✅ **Config** (4 tests):
  - Config creation
  - Load from environment
  - Validation (port, log level)

✅ **Frozen Config** (3 tests):
  - Freeze prevents modification
  - Multiple attributes frozen
  - Modification before freeze

✅ **Config Dump** (3 tests):
  - Dump with redaction
  - Dump without redaction
  - Partial redaction

✅ **Singleton** (3 tests):
  - get_config() returns singleton
  - Singleton is frozen
  - reset_config() for testing

✅ **Scanner** (3 tests):
  - Scanner finds os.getenv()
  - Scanner returns empty for clean code
  - Scanner finds multiple calls

✅ **Sweep** (1 test):
  - No stray getenv in src/

### Frozen Config Test

\`\`\`python
def test_freeze_prevents_modification():
    config = Config()
    config.freeze()
    
    with pytest.raises(FrozenConfigError):
        config.port = 9999
\`\`\`

### Scanner Test

\`\`\`python
def test_no_stray_getenv_in_src():
    violations = scan_directory("src/", exclude_patterns=["*/config.py"])
    
    assert len(violations) == 0, "Found stray os.getenv() calls"
\`\`\`

## Migration Guide

### Step 1: Add to Config

Add new fields to `config.py`:

\`\`\`python
@dataclass
class Config:
    # Add your field
    my_api_key: Optional[str] = None
    
    def _load_from_env(self):
        # Load from environment
        self.my_api_key = os.getenv("MY_API_KEY")
\`\`\`

### Step 2: Replace os.getenv()

Replace direct calls:

\`\`\`python
# Before
import os
api_key = os.getenv("MY_API_KEY")

# After
from config import get_config
config = get_config()
api_key = config.my_api_key
\`\`\`

### Step 3: Run Scanner

Verify no stray calls:

\`\`\`bash
python scripts/scan_env_reads.py src --allow-config
\`\`\`

### Step 4: Add to Redaction

If sensitive, add to redaction list:

\`\`\`python
def dump(self, redact: bool = True):
    sensitive_keys = {
        "my_api_key",  # Add here
    }
\`\`\`

## Current Status

**Scanner results** (as of implementation):

\`\`\`
Found: 58 stray os.getenv() calls
Files: 15 files

Top violators:
- src/service/api.py: 13 calls
- src/connectors/azure.py: 7 calls
- src/grpc_service/server.py: 7 calls
- src/connectors/s3.py: 6 calls
\`\`\`

**Recommended**: Migrate these files to use `get_config()`.

## Best Practices

1. **Always use get_config()**: Never use `os.getenv()` directly
2. **Add validation**: Validate in `_validate()`
3. **Test with env**: Use `monkeypatch.setenv()` in tests
4. **Freeze in production**: Config auto-frozen via `get_config()`
5. **Redact sensitive**: Add to `sensitive_keys` in `dump()`
6. **Run scanner**: Check for stray calls before merging

## Troubleshooting

### FrozenConfigError

**Issue**: Trying to modify config after freeze

\`\`\`python
config = get_config()
config.port = 9999  # → FrozenConfigError!
\`\`\`

**Fix**: Config is immutable by design. Set environment variables instead:

\`\`\`bash
export PORT=9999
\`\`\`

### Stray os.getenv() Calls

**Issue**: Scanner finds violations

\`\`\`
src/service/api.py:
  Line 200: os.getenv('SESSION_SECRET')
\`\`\`

**Fix**: Migrate to config:

\`\`\`python
# Add to config.py
session_secret: Optional[str] = None

# In _load_from_env():
self.session_secret = os.getenv("SESSION_SECRET")

# Use in code:
from config import get_config
config = get_config()
secret = config.session_secret
\`\`\`

### Config Dump 403

**Issue**: Unauthorized when calling `/admin/config/dump`

**Fix**: Provide admin token:

\`\`\`bash
export ADMIN_TOKEN=your_secure_token
curl -H "Authorization: Bearer your_secure_token" \\
  http://localhost:8001/admin/config/dump
\`\`\`

## Related Documentation

- [Environment Variables](./ENV_VARS.md)
- [Testing Guide](./TESTING.md)
- [Admin API](./ADMIN_API.md)

## Summary

The configuration management system provides:

✅ **Centralized**: Single source of truth via `get_config()`  
✅ **Immutable**: Frozen after initialization  
✅ **Validated**: Port ranges, log levels checked  
✅ **Scannable**: Static analysis finds violations  
✅ **Debuggable**: Admin dump endpoint with redaction  
✅ **Tested**: 17 comprehensive tests  

This ensures consistent, predictable configuration throughout the application lifecycle.

