# Secure Metrics Endpoint

This document describes the secure metrics endpoint with authentication and authorization for Prometheus monitoring.

## Overview

The `/metrics` endpoint exposes Prometheus metrics for monitoring. This implementation provides three authentication modes to secure access to sensitive operational data.

## Authentication Modes

### 1. Token Mode (Default, Recommended)

Requires Bearer token authentication.

**Configuration**:
```bash
export METRICS_AUTH_MODE=token
export METRICS_TOKEN=your-secret-metrics-token
```

**Usage**:
```bash
curl -H "Authorization: Bearer your-secret-metrics-token" \\
     http://localhost:8001/metrics
```

**Prometheus scrape_config**:
```yaml
scrape_configs:
  - job_name: 'safety-eval-mini'
    authorization:
      type: Bearer
      credentials: your-secret-metrics-token
    static_configs:
      - targets: ['localhost:8001']
```

### 2. IP Allowlist Mode

Allows access only from specific CIDR ranges.

**Configuration**:
```bash
export METRICS_AUTH_MODE=ip_allowlist
export METRICS_IP_ALLOWLIST=10.0.0.0/8,192.168.1.0/24,172.16.0.0/12
```

**Usage**:
```bash
# From allowed IP (10.0.0.1)
curl http://localhost:8001/metrics  # ✅ Allowed

# From disallowed IP (8.8.8.8)
curl http://localhost:8001/metrics  # ❌ 403 Forbidden
```

**Prometheus scrape_config**:
```yaml
scrape_configs:
  - job_name: 'safety-eval-mini'
    static_configs:
      - targets: ['10.0.0.100:8001']  # Internal IP
```

### 3. Public Mode (Not Recommended)

No authentication required - use only for development.

**Configuration**:
```bash
export METRICS_AUTH_MODE=public
```

**Usage**:
```bash
curl http://localhost:8001/metrics  # ✅ No auth needed
```

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `METRICS_AUTH_MODE` | No | `token` | Auth mode: `public`, `token`, `ip_allowlist` |
| `METRICS_TOKEN` | Yes* | None | Bearer token for metrics access |
| `METRICS_IP_ALLOWLIST` | Yes** | None | Comma-separated CIDR ranges |

*Required if `METRICS_AUTH_MODE=token`  
**Required if `METRICS_AUTH_MODE=ip_allowlist`

### Examples

**Token Mode** (Production):
```bash
# Generate secure token
export METRICS_TOKEN=$(openssl rand -base64 32)

# Set mode
export METRICS_AUTH_MODE=token

# Start service
PYTHONPATH=src uvicorn service.api:app --port 8001
```

**IP Allowlist Mode** (Internal Network):
```bash
# Private network ranges
export METRICS_AUTH_MODE=ip_allowlist
export METRICS_IP_ALLOWLIST=10.0.0.0/8,172.16.0.0/12,192.168.0.0/16

# Start service
PYTHONPATH=src uvicorn service.api:app --port 8001
```

**Public Mode** (Development Only):
```bash
export METRICS_AUTH_MODE=public

# Start service (INSECURE - development only)
PYTHONPATH=src uvicorn service.api:app --port 8001
```

## Prometheus Integration

### Token Mode

**prometheus.yml**:
```yaml
scrape_configs:
  - job_name: 'safety-eval-mini'
    scheme: https
    authorization:
      type: Bearer
      credentials: YOUR_METRICS_TOKEN_HERE
    static_configs:
      - targets:
        - 'api.example.com:8001'
    scrape_interval: 30s
```

### IP Allowlist Mode

**prometheus.yml**:
```yaml
scrape_configs:
  - job_name: 'safety-eval-mini'
    static_configs:
      - targets:
        - '10.0.0.100:8001'  # Internal IP
    scrape_interval: 30s
```

## Kubernetes/Helm Integration

### ServiceMonitor (Prometheus Operator)

**values.yaml**:
```yaml
metrics:
  enabled: true
  authMode: token
  token: "YOUR_METRICS_TOKEN"
  
  # Or for IP allowlist
  # authMode: ip_allowlist
  # ipAllowlist:
  #   - 10.0.0.0/8
  #   - 192.168.0.0/16
```

**ServiceMonitor Template**:
```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: {{ include "safety-eval-mini.fullname" . }}
spec:
  selector:
    matchLabels:
      {{- include "safety-eval-mini.selectorLabels" . | nindent 6 }}
  endpoints:
    - port: http
      path: /metrics
      interval: 30s
      {{- if eq .Values.metrics.authMode "token" }}
      authorization:
        type: Bearer
        credentials:
          name: {{ .Values.metrics.secretName | default "metrics-token" }}
          key: token
      {{- end }}
```

**Secret for Token**:
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: metrics-token
type: Opaque
stringData:
  token: YOUR_METRICS_TOKEN_HERE
```

## Security Best Practices

1. **Use Token Mode**: Most secure for production
2. **Rotate Tokens**: Change `METRICS_TOKEN` quarterly
3. **Secure Storage**: Store tokens in secrets manager
4. **HTTPS Only**: Always use HTTPS in production
5. **Least Privilege**: Minimize CIDR ranges in allowlist
6. **Monitor Access**: Log all metrics endpoint access
7. **Strong Tokens**: Use cryptographically secure tokens (32+ bytes)

## Testing

Run secure metrics tests:

```bash
pytest tests/test_secure_metrics.py -v
```

**16 comprehensive tests** covering:
- ✅ MetricsConfig (5 tests)
- ✅ Token auth (4 tests)
- ✅ IP allowlist (3 tests)
- ✅ Public mode (1 test)
- ✅ Metrics endpoint (3 tests)

### Test Examples

**Token Auth**:
```python
def test_token_auth():
    config = MetricsConfig(
        auth_mode=MetricsAuthMode.TOKEN,
        token="correct-token"
    )
    
    # With correct token
    request.headers = {"Authorization": "Bearer correct-token"}
    verify_metrics_access(request, config)  # ✅ Success
    
    # With wrong token
    request.headers = {"Authorization": "Bearer wrong-token"}
    verify_metrics_access(request, config)  # ❌ 401
```

**IP Allowlist**:
```python
def test_ip_allowlist():
    config = MetricsConfig(
        auth_mode=MetricsAuthMode.IP_ALLOWLIST,
        ip_allowlist=["10.0.0.0/8"]
    )
    
    # From allowed IP
    request.headers = {"X-Forwarded-For": "10.0.0.1"}
    verify_metrics_access(request, config)  # ✅ Success
    
    # From disallowed IP
    request.headers = {"X-Forwarded-For": "8.8.8.8"}
    verify_metrics_access(request, config)  # ❌ 403
```

## Troubleshooting

### 401 Unauthorized

**Issue**: Missing or invalid token

**Fix**:
```bash
# Check token is set
echo $METRICS_TOKEN

# Test with correct token
curl -H "Authorization: Bearer $METRICS_TOKEN" http://localhost:8001/metrics
```

### 403 Forbidden

**Issue**: IP not in allowlist

**Fix**:
```bash
# Check allowlist
echo $METRICS_IP_ALLOWLIST

# Add your IP
export METRICS_IP_ALLOWLIST=$METRICS_IP_ALLOWLIST,YOUR_IP/32

# Restart service
```

### Prometheus Can't Scrape

**Check endpoint**:
```bash
curl -H "Authorization: Bearer $METRICS_TOKEN" http://localhost:8001/metrics
```

**Check Prometheus logs**:
```bash
kubectl logs -n monitoring prometheus-xxx | grep safety-eval-mini
```

**Verify ServiceMonitor**:
```bash
kubectl get servicemonitor -n default safety-eval-mini -o yaml
```

## Migration

### From Unsecured to Token Mode

**Step 1**: Generate token
```bash
export METRICS_TOKEN=$(openssl rand -base64 32)
```

**Step 2**: Update configuration
```bash
export METRICS_AUTH_MODE=token
```

**Step 3**: Update Prometheus
```yaml
# Add to prometheus.yml
authorization:
  type: Bearer
  credentials: YOUR_TOKEN
```

**Step 4**: Restart service

**Step 5**: Verify
```bash
# Should succeed
curl -H "Authorization: Bearer $METRICS_TOKEN" http://localhost:8001/metrics

# Should fail
curl http://localhost:8001/metrics
```

## Related Documentation

- [Prometheus Configuration](https://prometheus.io/docs/prometheus/latest/configuration/configuration/)
- [ServiceMonitor Reference](https://github.com/prometheus-operator/prometheus-operator/blob/main/Documentation/api.md)
- [Security Best Practices](SECURITY.md)

## Support

For secure metrics issues:
1. Check `METRICS_AUTH_MODE` is set correctly
2. Verify `METRICS_TOKEN` or `METRICS_IP_ALLOWLIST` configured
3. Test with curl and correct credentials
4. Check Prometheus scrape_config
5. Review ServiceMonitor YAML

