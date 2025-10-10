#!/bin/bash
# Test script for Helm chart validation

set -e

CHART_DIR="$(dirname "$0")"

echo "=== Helm Chart Tests ==="
echo

echo "1. Linting chart..."
helm lint "$CHART_DIR"
echo "✓ Lint passed"
echo

echo "2. Rendering templates..."
helm template test "$CHART_DIR" > /dev/null
echo "✓ Template rendering passed"
echo

echo "3. Rendering with debug..."
helm template test "$CHART_DIR" --debug 2>&1 | grep -q "NOTES.txt"
echo "✓ NOTES.txt generated"
echo

echo "4. Testing with custom values..."
cat > /tmp/test-values.yaml <<EOF
replicaCount: 3
resources:
  requests:
    cpu: 250m
    memory: 256Mi
ingress:
  enabled: true
  hosts:
    - host: test.example.com
      paths:
        - path: /
          pathType: Prefix
EOF

helm template test "$CHART_DIR" -f /tmp/test-values.yaml > /dev/null
echo "✓ Custom values rendering passed"
echo

echo "5. Validating manifest count..."
MANIFEST_COUNT=$(helm template test "$CHART_DIR" | grep -c "^kind:")
echo "   Generated $MANIFEST_COUNT manifests"
[[ $MANIFEST_COUNT -ge 5 ]] || (echo "❌ Expected at least 5 manifests"; exit 1)
echo "✓ Manifest count OK"
echo

echo "=== All tests passed! ==="
echo
echo "To install on a cluster:"
echo "  helm install my-safety-eval $CHART_DIR"
echo
echo "To install on kind/minikube:"
echo "  kind create cluster"
echo "  kubectl cluster-info"
echo "  helm install test $CHART_DIR"
echo "  kubectl get pods -w"

