# Helm Chart: Safety Eval Mini

This document describes how to deploy **safety-eval-mini** to Kubernetes using Helm with secure secret management and health probe configuration.

## Overview

The Helm chart provides:

✅ **Secure Secret Management**: Mount SSO/Slack credentials from K8s Secrets  
✅ **Public Health Probes**: `/healthz` endpoint bypasses auth middleware  
✅ **Metrics Auth**: Token-based authentication for Prometheus  
✅ **Production-Ready**: Autoscaling, ingress, security contexts  

## Quick Start

### 1. Create Secrets

Create Kubernetes Secrets for sensitive credentials:

\`\`\`bash
# Apply example secrets
kubectl apply -f charts/safety-eval-mini/examples/secrets.yaml

# Or create from files
kubectl create secret generic safety-eval-oidc \\
  --from-literal=client-id="YOUR_CLIENT_ID" \\
  --from-literal=client-secret="YOUR_CLIENT_SECRET"

kubectl create secret generic safety-eval-slack \\
  --from-literal=client-id="YOUR_SLACK_CLIENT_ID" \\
  --from-literal=client-secret="YOUR_SLACK_CLIENT_SECRET" \\
  --from-literal=signing-secret="YOUR_SLACK_SIGNING_SECRET"

kubectl create secret generic safety-eval-metrics-auth \\
  --from-literal=token="YOUR_PROMETHEUS_TOKEN"
\`\`\`

### 2. Install Chart

\`\`\`bash
# Install with default values
helm install safety-eval charts/safety-eval-mini

# Or with production values
helm install safety-eval charts/safety-eval-mini \\
  -f charts/safety-eval-mini/examples/values-production.yaml

# Or override specific values
helm install safety-eval charts/safety-eval-mini \\
  --set secrets.oidc.enabled=true \\
  --set secrets.slack.enabled=true \\
  --set metrics.auth.enabled=true
\`\`\`

### 3. Verify Deployment

\`\`\`bash
# Check pods
kubectl get pods -l app.kubernetes.io/name=safety-eval-mini

# Check health
kubectl port-forward svc/safety-eval-safety-eval-mini 8001:8001
curl http://localhost:8001/healthz
# Should return 200 OK (no auth required)

# Check metrics (with auth)
curl -H "Authorization: Bearer YOUR_TOKEN" \\
  http://localhost:8000/metrics
\`\`\`

## Configuration

### Secret Management

#### OIDC/OAuth

\`\`\`yaml
secrets:
  oidc:
    enabled: true
    secretName: "safety-eval-oidc"
    clientIdKey: "client-id"
    clientSecretKey: "client-secret"
\`\`\`

**Secret format**:
\`\`\`yaml
apiVersion: v1
kind: Secret
metadata:
  name: safety-eval-oidc
type: Opaque
stringData:
  client-id: "your-client-id"
  client-secret: "your-client-secret"
\`\`\`

#### SAML

\`\`\`yaml
secrets:
  saml:
    enabled: true
    secretName: "safety-eval-saml"
    idpCertKey: "idp-cert"
    idpCertFingerprintKey: "idp-cert-fingerprint"
\`\`\`

**Secret format**:
\`\`\`yaml
apiVersion: v1
kind: Secret
metadata:
  name: safety-eval-saml
type: Opaque
stringData:
  idp-cert: |
    -----BEGIN CERTIFICATE-----
    ...
    -----END CERTIFICATE-----
  idp-cert-fingerprint: "a1b2c3d4..."
\`\`\`

#### Slack OAuth

\`\`\`yaml
secrets:
  slack:
    enabled: true
    secretName: "safety-eval-slack"
    clientIdKey: "client-id"
    clientSecretKey: "client-secret"
    signingSecretKey: "signing-secret"
\`\`\`

**Secret format**:
\`\`\`yaml
apiVersion: v1
kind: Secret
metadata:
  name: safety-eval-slack
type: Opaque
stringData:
  client-id: "slack-client-id"
  client-secret: "slack-client-secret"
  signing-secret: "slack-signing-secret"
\`\`\`

### Health Probes

Health probes are **public** and do not require authentication:

\`\`\`yaml
healthCheck:
  liveness:
    enabled: true
    path: /healthz  # Public endpoint
    initialDelaySeconds: 10
    periodSeconds: 10
  readiness:
    enabled: true
    path: /healthz  # Public endpoint
    initialDelaySeconds: 5
    periodSeconds: 10
\`\`\`

**Important**: The `/healthz` endpoint **must bypass** auth middleware in your application.

### Metrics Authentication

#### Token-Based (Recommended)

\`\`\`yaml
metrics:
  enabled: true
  port: 8000
  path: /metrics
  
  auth:
    enabled: true
    type: "token"
    secretName: "safety-eval-metrics-auth"
    tokenKey: "token"
  
  serviceMonitor:
    enabled: true
\`\`\`

**ServiceMonitor with bearer token**:
\`\`\`yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
spec:
  endpoints:
  - port: metrics
    path: /metrics
    bearerTokenSecret:
      name: safety-eval-metrics-auth
      key: token
\`\`\`

#### No Authentication

\`\`\`yaml
metrics:
  auth:
    enabled: false
\`\`\`

## Deployment Modes

### Development

\`\`\`bash
helm install safety-eval charts/safety-eval-mini \\
  --set replicaCount=1 \\
  --set secrets.oidc.enabled=false \\
  --set secrets.slack.enabled=false \\
  --set metrics.auth.enabled=false
\`\`\`

### Staging

\`\`\`bash
helm install safety-eval charts/safety-eval-mini \\
  --set replicaCount=2 \\
  --set secrets.oidc.enabled=true \\
  --set secrets.slack.enabled=true \\
  --set metrics.auth.enabled=true \\
  --set ingress.enabled=true \\
  --set ingress.hosts[0].host=staging.example.com
\`\`\`

### Production

\`\`\`bash
helm install safety-eval charts/safety-eval-mini \\
  -f charts/safety-eval-mini/examples/values-production.yaml
\`\`\`

## Testing

### Helm Lint

\`\`\`bash
helm lint charts/safety-eval-mini
\`\`\`

**Expected output**:
\`\`\`
==> Linting charts/safety-eval-mini
[INFO] Chart.yaml: icon is recommended
1 chart(s) linted, 0 chart(s) failed
\`\`\`

### Helm Template

\`\`\`bash
# Render templates with default values
helm template safety-eval charts/safety-eval-mini

# Render with production values
helm template safety-eval charts/safety-eval-mini \\
  -f charts/safety-eval-mini/examples/values-production.yaml

# Check specific resource
helm template safety-eval charts/safety-eval-mini \\
  -s templates/deployment.yaml
\`\`\`

### Dry Run

\`\`\`bash
helm install safety-eval charts/safety-eval-mini --dry-run --debug
\`\`\`

## Security Best Practices

### 1. Never Store Secrets in values.yaml

❌ **Bad**:
\`\`\`yaml
# values.yaml
oidc:
  clientSecret: "hardcoded-secret"  # NEVER DO THIS
\`\`\`

✅ **Good**:
\`\`\`yaml
# values.yaml
secrets:
  oidc:
    enabled: true
    secretName: "safety-eval-oidc"  # Reference external Secret
\`\`\`

### 2. Use Sealed Secrets or External Secrets

\`\`\`bash
# With Sealed Secrets
kubeseal --format=yaml < secrets.yaml > sealed-secrets.yaml
kubectl apply -f sealed-secrets.yaml

# With External Secrets Operator
kubectl apply -f external-secret.yaml
\`\`\`

### 3. Restrict RBAC

\`\`\`yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: safety-eval-secrets-reader
rules:
- apiGroups: [""]
  resources: ["secrets"]
  resourceNames:
    - safety-eval-oidc
    - safety-eval-slack
    - safety-eval-metrics-auth
  verbs: ["get"]
\`\`\`

### 4. Enable Pod Security Standards

\`\`\`yaml
podSecurityContext:
  runAsNonRoot: true
  runAsUser: 1000
  fsGroup: 1000
  seccompProfile:
    type: RuntimeDefault

securityContext:
  allowPrivilegeEscalation: false
  capabilities:
    drop:
    - ALL
  readOnlyRootFilesystem: true
\`\`\`

## Troubleshooting

### Pods Not Starting

\`\`\`bash
# Check pod status
kubectl describe pod -l app.kubernetes.io/name=safety-eval-mini

# Check logs
kubectl logs -l app.kubernetes.io/name=safety-eval-mini

# Common issue: Missing secrets
# Verify secrets exist
kubectl get secrets
\`\`\`

### Health Probes Failing

\`\`\`bash
# Test health endpoint manually
kubectl port-forward svc/safety-eval-safety-eval-mini 8001:8001
curl http://localhost:8001/healthz

# Should return 200 OK without auth
# If 401, ensure /healthz bypasses auth middleware
\`\`\`

### Metrics Not Scraped

\`\`\`bash
# Check ServiceMonitor
kubectl get servicemonitor

# Verify bearer token secret exists
kubectl get secret safety-eval-metrics-auth

# Test metrics endpoint
kubectl port-forward svc/safety-eval-safety-eval-mini 8000:8000
curl -H "Authorization: Bearer YOUR_TOKEN" \\
  http://localhost:8000/metrics
\`\`\`

## Upgrading

\`\`\`bash
# Upgrade release
helm upgrade safety-eval charts/safety-eval-mini

# Upgrade with new values
helm upgrade safety-eval charts/safety-eval-mini \\
  -f charts/safety-eval-mini/examples/values-production.yaml

# Rollback
helm rollback safety-eval
\`\`\`

## Uninstalling

\`\`\`bash
# Delete release
helm uninstall safety-eval

# Delete secrets (if needed)
kubectl delete secret safety-eval-oidc
kubectl delete secret safety-eval-slack
kubectl delete secret safety-eval-metrics-auth
\`\`\`

## Values Reference

| Parameter | Description | Default |
|-----------|-------------|---------|
| \`replicaCount\` | Number of replicas | \`2\` |
| \`image.repository\` | Image repository | \`safety-eval-mini\` |
| \`image.tag\` | Image tag | \`0.3.1\` |
| \`secrets.oidc.enabled\` | Enable OIDC secrets | \`false\` |
| \`secrets.saml.enabled\` | Enable SAML secrets | \`false\` |
| \`secrets.slack.enabled\` | Enable Slack secrets | \`false\` |
| \`metrics.enabled\` | Enable metrics | \`true\` |
| \`metrics.auth.enabled\` | Enable metrics auth | \`false\` |
| \`metrics.serviceMonitor.enabled\` | Create ServiceMonitor | \`false\` |
| \`healthCheck.liveness.path\` | Liveness probe path | \`/healthz\` |
| \`healthCheck.readiness.path\` | Readiness probe path | \`/healthz\` |
| \`ingress.enabled\` | Enable ingress | \`false\` |
| \`autoscaling.enabled\` | Enable HPA | \`false\` |

See \`values.yaml\` for complete reference.

## Examples

### Example 1: Minimal (No Secrets)

\`\`\`bash
helm install safety-eval charts/safety-eval-mini \\
  --set replicaCount=1
\`\`\`

### Example 2: With OIDC

\`\`\`bash
kubectl create secret generic safety-eval-oidc \\
  --from-literal=client-id="my-client-id" \\
  --from-literal=client-secret="my-client-secret"

helm install safety-eval charts/safety-eval-mini \\
  --set secrets.oidc.enabled=true
\`\`\`

### Example 3: Full Production

\`\`\`bash
# Create all secrets
kubectl apply -f charts/safety-eval-mini/examples/secrets.yaml

# Install with production values
helm install safety-eval charts/safety-eval-mini \\
  -f charts/safety-eval-mini/examples/values-production.yaml
\`\`\`

## Related Documentation

- [Kubernetes Secrets](https://kubernetes.io/docs/concepts/configuration/secret/)
- [Sealed Secrets](https://github.com/bitnami-labs/sealed-secrets)
- [External Secrets Operator](https://external-secrets.io/)
- [Prometheus ServiceMonitor](https://prometheus-operator.dev/docs/operator/api/#servicemonitor)

## Support

For issues or questions:
1. Check pod logs: \`kubectl logs -l app.kubernetes.io/name=safety-eval-mini\`
2. Verify secrets: \`kubectl get secrets\`
3. Test health probe: \`curl http://POD_IP:8001/healthz\`
4. Review chart templates: \`helm template safety-eval charts/safety-eval-mini\`

