"""Tests for Helm chart structure and validity."""

from __future__ import annotations

import yaml
from pathlib import Path


CHART_DIR = Path(__file__).parent.parent / "charts" / "safety-eval-mini"


def test_chart_yaml_exists():
    """Test Chart.yaml exists."""
    chart_file = CHART_DIR / "Chart.yaml"
    assert chart_file.exists()


def test_chart_yaml_valid():
    """Test Chart.yaml is valid YAML."""
    chart_file = CHART_DIR / "Chart.yaml"
    
    with open(chart_file) as f:
        chart_data = yaml.safe_load(f)
    
    assert chart_data["apiVersion"] == "v2"
    assert chart_data["name"] == "safety-eval-mini"
    assert "version" in chart_data
    assert "appVersion" in chart_data


def test_values_yaml_exists():
    """Test values.yaml exists."""
    values_file = CHART_DIR / "values.yaml"
    assert values_file.exists()


def test_values_yaml_valid():
    """Test values.yaml is valid YAML."""
    values_file = CHART_DIR / "values.yaml"
    
    with open(values_file) as f:
        values_data = yaml.safe_load(f)
    
    assert "replicaCount" in values_data
    assert "image" in values_data
    assert "service" in values_data
    assert "resources" in values_data


def test_required_templates_exist():
    """Test required template files exist."""
    templates_dir = CHART_DIR / "templates"
    
    required_templates = [
        "_helpers.tpl",
        "deployment.yaml",
        "service.yaml",
        "configmap.yaml",
        "serviceaccount.yaml",
        "NOTES.txt",
    ]
    
    for template in required_templates:
        template_file = templates_dir / template
        assert template_file.exists(), f"Missing template: {template}"


def test_deployment_template_valid():
    """Test deployment.yaml is valid YAML structure."""
    deployment_file = CHART_DIR / "templates" / "deployment.yaml"
    
    with open(deployment_file) as f:
        content = f.read()
    
    # Check for required fields (template syntax)
    assert "apiVersion: apps/v1" in content
    assert "kind: Deployment" in content
    assert "livenessProbe:" in content
    assert "readinessProbe:" in content
    # Probes are templated from values
    assert ".Values.livenessProbe" in content or ".Values.readinessProbe" in content


def test_service_template_valid():
    """Test service.yaml has required structure."""
    service_file = CHART_DIR / "templates" / "service.yaml"
    
    with open(service_file) as f:
        content = f.read()
    
    assert "apiVersion: v1" in content
    assert "kind: Service" in content
    assert "type:" in content
    assert "port:" in content


def test_configmap_template_valid():
    """Test configmap.yaml has required structure."""
    configmap_file = CHART_DIR / "templates" / "configmap.yaml"
    
    with open(configmap_file) as f:
        content = f.read()
    
    assert "apiVersion: v1" in content
    assert "kind: ConfigMap" in content
    assert "config.yaml:" in content


def test_policy_configmap_exists():
    """Test policy ConfigMap template exists."""
    policy_cm_file = CHART_DIR / "templates" / "policy-configmap.yaml"
    assert policy_cm_file.exists()


def test_ingress_template_exists():
    """Test ingress template exists."""
    ingress_file = CHART_DIR / "templates" / "ingress.yaml"
    assert ingress_file.exists()


def test_servicemonitor_template_exists():
    """Test ServiceMonitor template exists."""
    sm_file = CHART_DIR / "templates" / "servicemonitor.yaml"
    assert sm_file.exists()


def test_hpa_template_exists():
    """Test HPA template exists."""
    hpa_file = CHART_DIR / "templates" / "hpa.yaml"
    assert hpa_file.exists()


def test_chart_readme_exists():
    """Test chart README exists."""
    readme_file = CHART_DIR / "README.md"
    assert readme_file.exists()


def test_chart_readme_has_content():
    """Test chart README has installation instructions."""
    readme_file = CHART_DIR / "README.md"
    
    with open(readme_file) as f:
        content = f.read()
    
    assert "helm install" in content
    assert "Prerequisites" in content
    assert "Configuration" in content


def test_values_has_security_context():
    """Test values.yaml includes security context."""
    values_file = CHART_DIR / "values.yaml"
    
    with open(values_file) as f:
        values_data = yaml.safe_load(f)
    
    assert "securityContext" in values_data
    assert "podSecurityContext" in values_data


def test_values_has_probes():
    """Test values.yaml includes health probes."""
    values_file = CHART_DIR / "values.yaml"
    
    with open(values_file) as f:
        values_data = yaml.safe_load(f)
    
    assert "livenessProbe" in values_data
    assert "readinessProbe" in values_data
    assert values_data["livenessProbe"]["httpGet"]["path"] == "/healthz"
    assert values_data["readinessProbe"]["httpGet"]["path"] == "/healthz"


def test_values_has_resources():
    """Test values.yaml includes resource requests/limits."""
    values_file = CHART_DIR / "values.yaml"
    
    with open(values_file) as f:
        values_data = yaml.safe_load(f)
    
    assert "resources" in values_data
    assert "requests" in values_data["resources"]
    assert "limits" in values_data["resources"]


def test_values_has_affinity():
    """Test values.yaml includes pod anti-affinity."""
    values_file = CHART_DIR / "values.yaml"
    
    with open(values_file) as f:
        values_data = yaml.safe_load(f)
    
    assert "affinity" in values_data
    assert "podAntiAffinity" in values_data["affinity"]


def test_helmignore_exists():
    """Test .helmignore exists."""
    helmignore_file = CHART_DIR / ".helmignore"
    assert helmignore_file.exists()


def test_test_script_exists():
    """Test chart test script exists."""
    test_script = CHART_DIR / "test-chart.sh"
    assert test_script.exists()

