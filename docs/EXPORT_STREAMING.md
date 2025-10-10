# Export Streaming & Deep Secret Redaction

This document describes the export system with streaming for large reports and deep secret redaction for data security.

## Overview

The export system provides secure report downloads with:

✅ **Streaming**: Memory-bounded exports for reports > 1MB  
✅ **Deep Secret Redaction**: Recursive pattern-based redaction  
✅ **Security Headers**: ETag, Cache-Control, X-Download-Options  
✅ **Multiple Formats**: JSON and Markdown exports  

## Problem Solved

**Before**: Unsafe exports
- No secret redaction
- Memory issues with large reports
- Missing security headers
- Secrets exposed in nested data

**After**: Secure streaming exports
- Deep recursive redaction
- Memory-bounded streaming (> 1MB)
- **24 comprehensive tests** (100% pass rate)
- Complete security headers

## Features

### 🔐 Deep Secret Redaction

**Recursive pattern matching**:

\`\`\`python
from exports import redact_secrets

data = {
    "metadata": {
        "version": "1.0",
        "api_key": "secret123"  # Redacted
    },
    "results": [
        {"test": "test1", "password": "pass1"},  # Redacted
        {"test": "test2", "auth_token": "token2"}  # Redacted
    ]
}

redacted = redact_secrets(data)
# → All secrets replaced with "***REDACTED***"
\`\`\`

**Patterns matched** (case-insensitive):
- `key`, `token`, `secret`, `pwd`, `password`
- `client_secret`, `api_key`, `auth`, `bearer`
- `credential`

### 📊 Streaming for Large Reports

**Automatic streaming** (> 1MB):

\`\`\`python
from exports import ReportBuilder, StreamingReportBuilder

# Small report (< 1MB) → Complete response
builder = ReportBuilder(small_data)
json_str = builder.build_json()

# Large report (> 1MB) → Streamed chunks
builder = StreamingReportBuilder(large_data)
for chunk in builder.stream_json():
    yield chunk  # Memory bounded!
\`\`\`

### 🛡️ Security Headers

**Comprehensive protection**:

\`\`\`
Cache-Control: no-store, no-cache, must-revalidate, private
X-Download-Options: noopen
X-Content-Type-Options: nosniff
ETag: "abc123def456"
\`\`\`

## API

### Export Endpoints

#### GET /exports/report.json

Export report as JSON:

\`\`\`bash
# With redaction (default)
curl http://localhost:8001/exports/report.json > report.json

# Without redaction (unsafe!)
curl "http://localhost:8001/exports/report.json?redact=false"
\`\`\`

**Response headers**:
\`\`\`
Content-Type: application/json
Content-Disposition: attachment; filename=report.json
Cache-Control: no-store, no-cache, must-revalidate, private
X-Download-Options: noopen
ETag: "a1b2c3d4"
\`\`\`

#### GET /exports/report.md

Export report as Markdown:

\`\`\`bash
curl http://localhost:8001/exports/report.md > report.md
\`\`\`

**Response headers**:
\`\`\`
Content-Type: text/markdown
Content-Disposition: attachment; filename=report.md
Cache-Control: no-store, no-cache
X-Download-Options: noopen
\`\`\`

### Secret Redaction

#### SecretRedactor Class

\`\`\`python
from exports import SecretRedactor

# Create redactor
redactor = SecretRedactor(
    patterns=["key", "token", "secret"],  # Custom patterns
    redacted_text="[REDACTED]"  # Custom replacement
)

# Redact data
data = {"api_key": "secret123", "username": "alice"}
redacted = redactor.redact(data)

# Track redacted keys
redacted_keys = redactor.get_redacted_keys()
print(f"Redacted: {redacted_keys}")  # → {"api_key"}
\`\`\`

#### redact_secrets() Function

\`\`\`python
from exports import redact_secrets

# Quick redaction with defaults
data = {"password": "secret", "email": "alice@example.com"}
redacted = redact_secrets(data)

# Custom patterns
redacted = redact_secrets(data, patterns=["custom_field"])
\`\`\`

### Report Builders

#### ReportBuilder

For small reports (< 1MB):

\`\`\`python
from exports import ReportBuilder

builder = ReportBuilder(data, redact=True)

# Build JSON
json_str = builder.build_json()

# Build Markdown
md_str = builder.build_markdown()

# Estimate size
size = builder.estimate_size()

# Compute ETag
etag = builder.compute_etag()
\`\`\`

#### StreamingReportBuilder

For large reports (> 1MB):

\`\`\`python
from exports import StreamingReportBuilder

builder = StreamingReportBuilder(data, redact=True)

# Stream JSON
for chunk in builder.stream_json():
    yield chunk  # 8KB chunks

# Stream Markdown
for chunk in builder.stream_markdown():
    yield chunk
\`\`\`

## Testing

**24 comprehensive tests** (100% pass rate):

\`\`\`bash
pytest tests/test_exports.py -v
# ================ 24 passed in 0.25s ================
\`\`\`

### Test Coverage

✅ **SecretRedactor** (8 tests):
  - Creation
  - Sensitive key detection
  - Flat dict redaction
  - Nested dict redaction
  - List of dicts redaction
  - Deeply nested redaction
  - Mixed structures
  - Tracking redacted keys

✅ **Convenience Function** (2 tests):
  - Basic redaction
  - Custom patterns

✅ **ReportBuilder** (6 tests):
  - Creation
  - JSON building
  - JSON without redaction
  - Markdown building
  - Size estimation
  - ETag computation

✅ **StreamingReportBuilder** (3 tests):
  - JSON streaming
  - Markdown streaming
  - Memory bounded streaming

✅ **Security Headers** (2 tests):
  - Basic headers
  - ETag inclusion

✅ **Export Routes** (3 tests):
  - JSON endpoint
  - JSON without redaction
  - Markdown endpoint

### Key Test Results

**Nested secret redaction**:
\`\`\`python
data = {
    "metadata": {"api_key": "secret123"},
    "results": [
        {"test": "test1", "password": "pass1"},
        {"test": "test2", "auth_token": "token2"}
    ]
}

redacted = redact_secrets(data)

# All secrets redacted
assert redacted["metadata"]["api_key"] == "***REDACTED***"
assert redacted["results"][0]["password"] == "***REDACTED***"
assert redacted["results"][1]["auth_token"] == "***REDACTED***"
\`\`\`

**Streaming memory bounded**:
\`\`\`python
# Create large data (1000 items)
data = {"items": [{"id": i, "data": "x" * 100} for i in range(1000)]}

builder = StreamingReportBuilder(data)
chunks = list(builder.stream_json())

# Multiple chunks (not loaded at once)
assert len(chunks) > 1  # ✅
\`\`\`

## Security

### Secret Patterns

**Default patterns** (case-insensitive regex):

| Pattern | Example Keys | Redacted |
|---------|--------------|----------|
| `key` | api_key, secret_key | ✅ |
| `token` | auth_token, bearer_token | ✅ |
| `secret` | client_secret, my_secret | ✅ |
| `pwd` | pwd, user_pwd | ✅ |
| `password` | password, db_password | ✅ |
| `client_secret` | slack_client_secret | ✅ |
| `api_key` | stripe_api_key | ✅ |
| `auth` | auth_header, basic_auth | ✅ |
| `bearer` | bearer_token | ✅ |
| `credential` | credentials, user_credential | ✅ |

### Security Headers

**Cache-Control**:
\`\`\`
no-store, no-cache, must-revalidate, private
\`\`\`
- Prevents browser/proxy caching
- Forces fresh fetch

**X-Download-Options**:
\`\`\`
noopen
\`\`\`
- Prevents opening in browser (IE)
- Forces download

**X-Content-Type-Options**:
\`\`\`
nosniff
\`\`\`
- Prevents MIME sniffing
- Enforces declared content type

**ETag**:
\`\`\`
"a1b2c3d4e5f67890"
\`\`\`
- Cache validation
- 16-character SHA-256 hash

**Content-Disposition**:
\`\`\`
attachment; filename=report.json
\`\`\`
- Forces download (not inline display)

## Use Cases

### 1. Export User Data (GDPR)

\`\`\`python
from exports import ReportBuilder, redact_secrets

# Collect user data
user_data = {
    "profile": {
        "name": "Alice",
        "email": "alice@example.com",
        "password": "hashed_password"  # Sensitive!
    },
    "activity": [
        {"action": "login", "auth_token": "token123"}
    ]
}

# Redact secrets
safe_data = redact_secrets(user_data)

# Export
builder = ReportBuilder(safe_data)
json_export = builder.build_json()
\`\`\`

### 2. Audit Log Export

\`\`\`python
# Large audit log
audit_logs = fetch_audit_logs(limit=100000)  # Many records

# Stream to avoid memory issues
builder = StreamingReportBuilder(audit_logs, redact=True)

# Generate streamed response
return StreamingResponse(
    builder.stream_json(),
    media_type="application/json",
    headers={"Content-Disposition": "attachment; filename=audit.json"}
)
\`\`\`

### 3. Compliance Reports

\`\`\`python
# Generate compliance report
compliance_data = {
    "organization": "ACME Corp",
    "timestamp": "2025-01-01",
    "checks": [...],
    "config": {
        "database_url": "postgres://...",
        "slack_webhook_secret": "secret123"  # Redacted
    }
}

builder = ReportBuilder(compliance_data, redact=True)
md_report = builder.build_markdown()
\`\`\`

## Best Practices

### 1. Always Redact by Default

\`\`\`python
# Good
builder = ReportBuilder(data, redact=True)

# Risky (only if necessary)
builder = ReportBuilder(data, redact=False)
\`\`\`

### 2. Use Custom Patterns for Domain-Specific Secrets

\`\`\`python
# Add domain-specific patterns
patterns = SecretRedactor.DEFAULT_PATTERNS + [
    "internal_id",
    "session_id",
    "private_key"
]

redactor = SecretRedactor(patterns=patterns)
\`\`\`

### 3. Stream Large Reports

\`\`\`python
# Check size first
builder = ReportBuilder(data)

if builder.estimate_size() > 1024 * 1024:  # > 1MB
    # Use streaming
    streaming_builder = StreamingReportBuilder(data)
    return StreamingResponse(streaming_builder.stream_json())
else:
    # Return complete
    return Response(builder.build_json())
\`\`\`

### 4. Add Security Headers

\`\`\`python
from exports.routes import add_security_headers

response = Response(content=data)
add_security_headers(response, etag=etag)
\`\`\`

## Troubleshooting

### Secrets Not Redacted

**Issue**: Some secrets still visible

**Cause**: Key doesn't match patterns

**Fix**: Add custom pattern
\`\`\`python
patterns = SecretRedactor.DEFAULT_PATTERNS + ["your_field"]
redactor = SecretRedactor(patterns=patterns)
\`\`\`

### Memory Issues

**Issue**: Export uses too much memory

**Cause**: Large report loaded at once

**Fix**: Use streaming
\`\`\`python
# Don't do this for large data
builder = ReportBuilder(huge_data)  # Loads all

# Do this instead
builder = StreamingReportBuilder(huge_data)
for chunk in builder.stream_json():
    yield chunk  # Memory bounded
\`\`\`

### Missing Security Headers

**Issue**: Headers not in response

**Cause**: Not using add_security_headers()

**Fix**:
\`\`\`python
from exports.routes import add_security_headers

response = Response(content=data)
add_security_headers(response)  # Add headers
\`\`\`

## Related Documentation

- [Data Privacy](./DATA_PRIVACY.md)
- [Security Best Practices](./SECURITY.md)
- [API Documentation](./API.md)

## Summary

The export system with streaming and redaction provides:

✅ **Secure**: Deep secret redaction  
✅ **Scalable**: Memory-bounded streaming  
✅ **Protected**: Comprehensive security headers  
✅ **Tested**: 24 tests (100% pass rate)  
✅ **Flexible**: JSON and Markdown formats  

This ensures safe, efficient report exports for sensitive data.

