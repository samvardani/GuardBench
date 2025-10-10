#!/bin/bash
# Test script for Helm chart validation
# Requires: helm

set -e

CHART_DIR="charts/safety-eval-mini"

echo "==> Testing Helm Chart: safety-eval-mini"
echo ""

# 1. Lint chart
echo "1. Running helm lint..."
if command -v helm &> /dev/null; then
    helm lint "$CHART_DIR"
    echo "✅ Lint passed"
else
    echo "⚠️  helm not installed, skipping lint"
fi
echo ""

# 2. Template with default values
echo "2. Rendering templates (default values)..."
if command -v helm &> /dev/null; then
    helm template test-release "$CHART_DIR" > /tmp/helm-test-default.yaml
    echo "✅ Default templates rendered"
    echo "   Output: /tmp/helm-test-default.yaml"
else
    echo "⚠️  helm not installed, skipping template"
fi
echo ""

# 3. Template with production values
echo "3. Rendering templates (production values)..."
if command -v helm &> /dev/null; then
    helm template test-release "$CHART_DIR" \
        -f "$CHART_DIR/examples/values-production.yaml" \
        > /tmp/helm-test-production.yaml
    echo "✅ Production templates rendered"
    echo "   Output: /tmp/helm-test-production.yaml"
else
    echo "⚠️  helm not installed, skipping template"
fi
echo ""

# 4. Validate YAML syntax
echo "4. Validating YAML syntax..."
if command -v yamllint &> /dev/null; then
    yamllint "$CHART_DIR/values.yaml"
    yamllint "$CHART_DIR/templates/"*.yaml
    echo "✅ YAML syntax valid"
else
    echo "⚠️  yamllint not installed, skipping"
fi
echo ""

# 5. Check for common issues
echo "5. Checking for common issues..."

# Check health probes exist
if grep -q "livenessProbe" "$CHART_DIR/templates/deployment.yaml" && \
   grep -q "readinessProbe" "$CHART_DIR/templates/deployment.yaml"; then
    echo "✅ Health probes configured"
else
    echo "❌ Health probes not found"
    exit 1
fi

# Check Secret mounting
if grep -q "secretKeyRef" "$CHART_DIR/templates/deployment.yaml"; then
    echo "✅ Secret mounting configured"
else
    echo "❌ Secret mounting not found"
    exit 1
fi

# Check ServiceMonitor auth
if grep -q "bearerTokenSecret" "$CHART_DIR/templates/servicemonitor.yaml"; then
    echo "✅ ServiceMonitor auth configured"
else
    echo "❌ ServiceMonitor auth not found"
    exit 1
fi

echo ""
echo "==> All checks passed! ✅"

