# Safety-Eval-Mini Helm Chart

Deploy Safety-Eval-Mini to Kubernetes with this production-ready Helm chart.

## Prerequisites

- Kubernetes 1.20+
- Helm 3.0+
- (Optional) Prometheus Operator for ServiceMonitor

## Quick Start

### 1. Add Repository (when published)

```bash
helm repo add safety-eval https://samvardani.github.io/safety-eval-mini
helm repo update
```

### 2. Install from Local Chart

```bash
# From repository root
helm install my-safety-eval ./charts/safety-eval-mini

# With custom values
helm install my-safety-eval ./charts/safety-eval-mini -f my-values.yaml

# In specific namespace
helm install my-safety-eval ./charts/safety-eval-mini --namespace safety-eval --create-namespace
```

### 3. Verify Installation

```bash
# Check pods
kubectl get pods -l app.kubernetes.io/name=safety-eval-mini

# Check service
kubectl get svc -l app.kubernetes.io/name=safety-eval-mini

# Test health endpoint
kubectl port-forward svc/my-safety-eval-safety-eval-mini 8001:8001
curl http://localhost:8001/healthz
```

## Configuration

### Basic Configuration

```yaml
# values.yaml
replicaCount: 3

resources:
  requests:
    cpu: 500m
    memory: 512Mi
  limits:
    cpu: 1000m
    memory: 1Gi

config:
  logLevel: "INFO"
  corsAllowOrigins: "https://your-domain.com"
```

### Ingress Configuration

```yaml
ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
  hosts:
    - host: safety-eval.your-domain.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: safety-eval-tls
      hosts:
        - safety-eval.your-domain.com
```

### Secrets Configuration

⚠️ **Never commit secrets to values.yaml**. Use one of these methods:

**Option 1: Kubernetes Secret (Recommended)**
```bash
kubectl create secret generic safety-eval-secrets \
  --from-literal=openai-api-key="sk-..." \
  --from-literal=session-secret="random-secret-here"

# Then reference in values:
envFrom:
  - secretRef:
      name: safety-eval-secrets
```

**Option 2: values.yaml Override (for testing only)**
```yaml
secrets:
  sessionSecret: "dev-secret-not-for-production"
  openaiApiKey: "sk-..."
  slackWebhookUrl: "https://hooks.slack.com/..."
```

**Option 3: Helm --set flags**
```bash
helm install my-safety-eval ./charts/safety-eval-mini \
  --set secrets.sessionSecret="..." \
  --set secrets.openaiApiKey="..."
```

### Custom Policy

**Option 1: Inline in values.yaml**
```yaml
policy:
  data: |
    version: 1
    metadata:
      name: production-policy
    slices:
      - id: violence_strict
        category: violence
        language: en
        threshold: 0.5
        rules:
          - id: violence_keywords
            weight: 1.0
            action: block
            match:
              regex:
                - "\\bkill\\b"
```

**Option 2: Existing ConfigMap**
```yaml
policy:
  existingConfigMap: "my-policy-configmap"
```

### Autoscaling

```yaml
autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80
```

### Prometheus Monitoring

```yaml
serviceMonitor:
  enabled: true
  interval: 30s
  scrapeTimeout: 10s
  labels:
    prometheus: kube-prometheus
```

## Values Reference

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `replicaCount` | int | `2` | Number of replicas |
| `image.repository` | string | `safety-eval-mini` | Image repository |
| `image.tag` | string | `latest` | Image tag (default: chart appVersion) |
| `image.pullPolicy` | string | `IfNotPresent` | Image pull policy |
| `service.type` | string | `ClusterIP` | Kubernetes service type |
| `service.port` | int | `8001` | Service port |
| `grpcService.enabled` | bool | `true` | Enable gRPC service |
| `grpcService.port` | int | `50051` | gRPC service port |
| `ingress.enabled` | bool | `false` | Enable ingress |
| `resources.requests.cpu` | string | `500m` | CPU request |
| `resources.requests.memory` | string | `512Mi` | Memory request |
| `resources.limits.cpu` | string | `1000m` | CPU limit |
| `resources.limits.memory` | string | `1Gi` | Memory limit |
| `autoscaling.enabled` | bool | `false` | Enable HPA |
| `serviceMonitor.enabled` | bool | `false` | Enable Prometheus ServiceMonitor |
| `config.logLevel` | string | `INFO` | Log level (DEBUG, INFO, WARNING, ERROR) |
| `config.privacyMode` | string | `off` | Privacy mode (on/off) |
| `config.corsAllowOrigins` | string | `*` | CORS allowed origins |

For a complete list of values, see `values.yaml`.

## Health Checks

The chart includes liveness and readiness probes:

**Liveness Probe**:
- Endpoint: `GET /healthz`
- Initial delay: 10s
- Period: 30s
- Timeout: 5s
- Failure threshold: 3

**Readiness Probe**:
- Endpoint: `GET /healthz`
- Initial delay: 5s
- Period: 10s
- Timeout: 3s
- Failure threshold: 3

## Upgrade

```bash
# Upgrade with new values
helm upgrade my-safety-eval ./charts/safety-eval-mini -f new-values.yaml

# Force recreate pods
helm upgrade my-safety-eval ./charts/safety-eval-mini --recreate-pods
```

## Uninstall

```bash
helm uninstall my-safety-eval
```

## Testing

```bash
# Lint the chart
helm lint ./charts/safety-eval-mini

# Render templates (dry-run)
helm template my-safety-eval ./charts/safety-eval-mini

# Install in dry-run mode
helm install my-safety-eval ./charts/safety-eval-mini --dry-run --debug

# Test on kind cluster
kind create cluster
helm install test ./charts/safety-eval-mini
kubectl get pods -w
```

## Troubleshooting

**Pods not starting**:
```bash
kubectl describe pod -l app.kubernetes.io/name=safety-eval-mini
kubectl logs -l app.kubernetes.io/name=safety-eval-mini
```

**Health check failing**:
```bash
kubectl port-forward svc/my-safety-eval-safety-eval-mini 8001:8001
curl http://localhost:8001/healthz
```

**Image pull errors**:
- Ensure image exists and is accessible
- Check `imagePullSecrets` if using private registry

## Production Considerations

### Resource Sizing

**Small (Dev/Test)**:
```yaml
resources:
  requests:
    cpu: 250m
    memory: 256Mi
  limits:
    cpu: 500m
    memory: 512Mi
replicaCount: 1
```

**Medium (Production)**:
```yaml
resources:
  requests:
    cpu: 500m
    memory: 512Mi
  limits:
    cpu: 1000m
    memory: 1Gi
replicaCount: 3
autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 10
```

**Large (High Traffic)**:
```yaml
resources:
  requests:
    cpu: 1000m
    memory: 1Gi
  limits:
    cpu: 2000m
    memory: 2Gi
replicaCount: 5
autoscaling:
  enabled: true
  minReplicas: 5
  maxReplicas: 20
```

### Security Best Practices

1. **Run as non-root** (already configured)
2. **Read-only root filesystem** (partially configured)
3. **Use network policies** to restrict traffic
4. **Enable Pod Security Standards**
5. **Use separate namespaces** for different environments
6. **Rotate secrets regularly**

### High Availability

```yaml
replicaCount: 3

affinity:
  podAntiAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      - labelSelector:
          matchExpressions:
            - key: app.kubernetes.io/name
              operator: In
              values:
                - safety-eval-mini
        topologyKey: kubernetes.io/hostname

# Spread across availability zones
topologySpreadConstraints:
  - maxSkew: 1
    topologyKey: topology.kubernetes.io/zone
    whenUnsatisfiable: DoNotSchedule
    labelSelector:
      matchLabels:
        app.kubernetes.io/name: safety-eval-mini
```

### Monitoring Setup

```yaml
serviceMonitor:
  enabled: true
  interval: 30s
  labels:
    prometheus: kube-prometheus

# Add Grafana dashboards
# See docs/grafana-dashboard.json
```

## License

MIT License - See LICENSE file in repository root

