"""Tests for secure metrics endpoint."""

from __future__ import annotations

import os
import pytest
from unittest.mock import MagicMock

from fastapi import Request
from fastapi.testclient import TestClient

from monitoring import MetricsAuthMode, MetricsConfig, verify_metrics_access


class TestMetricsConfig:
    """Test metrics configuration."""
    
    def test_config_default(self):
        """Test default configuration."""
        config = MetricsConfig()
        
        assert config.auth_mode == MetricsAuthMode.TOKEN
        assert config.ip_allowlist == []
    
    def test_config_public_mode(self):
        """Test public mode configuration."""
        config = MetricsConfig(auth_mode=MetricsAuthMode.PUBLIC)
        
        assert config.auth_mode == MetricsAuthMode.PUBLIC
    
    def test_config_token_mode(self):
        """Test token mode configuration."""
        config = MetricsConfig(
            auth_mode=MetricsAuthMode.TOKEN,
            token="secret-metrics-token"
        )
        
        assert config.auth_mode == MetricsAuthMode.TOKEN
        assert config.token == "secret-metrics-token"
    
    def test_config_ip_allowlist_mode(self):
        """Test IP allowlist mode configuration."""
        config = MetricsConfig(
            auth_mode=MetricsAuthMode.IP_ALLOWLIST,
            ip_allowlist=["10.0.0.0/8", "192.168.1.0/24"]
        )
        
        assert config.auth_mode == MetricsAuthMode.IP_ALLOWLIST
        assert len(config.allowed_networks) == 2
    
    def test_is_ip_allowed(self):
        """Test IP allowlist checking."""
        config = MetricsConfig(
            auth_mode=MetricsAuthMode.IP_ALLOWLIST,
            ip_allowlist=["10.0.0.0/8", "192.168.1.0/24"]
        )
        
        # Allowed
        assert config.is_ip_allowed("10.0.0.1") is True
        assert config.is_ip_allowed("10.255.255.255") is True
        assert config.is_ip_allowed("192.168.1.100") is True
        
        # Not allowed
        assert config.is_ip_allowed("11.0.0.1") is False
        assert config.is_ip_allowed("192.168.2.1") is False


class TestTokenAuth:
    """Test token-based authentication."""
    
    def test_token_auth_success(self):
        """Test successful token authentication."""
        config = MetricsConfig(
            auth_mode=MetricsAuthMode.TOKEN,
            token="correct-token"
        )
        
        # Mock request
        request = MagicMock(spec=Request)
        request.headers = {"Authorization": "Bearer correct-token"}
        
        # Should not raise
        verify_metrics_access(request, config)
    
    def test_token_auth_missing_header(self):
        """Test token auth with missing Authorization header."""
        config = MetricsConfig(
            auth_mode=MetricsAuthMode.TOKEN,
            token="correct-token"
        )
        
        request = MagicMock(spec=Request)
        request.headers = {}
        
        # Should raise 401
        with pytest.raises(Exception) as exc_info:
            verify_metrics_access(request, config)
        
        assert exc_info.value.status_code == 401
    
    def test_token_auth_invalid_token(self):
        """Test token auth with invalid token."""
        config = MetricsConfig(
            auth_mode=MetricsAuthMode.TOKEN,
            token="correct-token"
        )
        
        request = MagicMock(spec=Request)
        request.headers = {"Authorization": "Bearer wrong-token"}
        
        # Should raise 401
        with pytest.raises(Exception) as exc_info:
            verify_metrics_access(request, config)
        
        assert exc_info.value.status_code == 401
    
    def test_token_auth_invalid_format(self):
        """Test token auth with invalid format."""
        config = MetricsConfig(
            auth_mode=MetricsAuthMode.TOKEN,
            token="correct-token"
        )
        
        request = MagicMock(spec=Request)
        request.headers = {"Authorization": "InvalidFormat token"}
        
        # Should raise 401
        with pytest.raises(Exception) as exc_info:
            verify_metrics_access(request, config)
        
        assert exc_info.value.status_code == 401


class TestIPAllowlist:
    """Test IP allowlist authentication."""
    
    def test_ip_allowlist_success(self):
        """Test successful IP allowlist check."""
        config = MetricsConfig(
            auth_mode=MetricsAuthMode.IP_ALLOWLIST,
            ip_allowlist=["10.0.0.0/8"]
        )
        
        # Mock request from allowed IP
        request = MagicMock(spec=Request)
        request.headers = {"X-Forwarded-For": "10.0.0.1"}
        request.client = None
        
        # Should not raise
        verify_metrics_access(request, config)
    
    def test_ip_allowlist_denied(self):
        """Test IP allowlist denial."""
        config = MetricsConfig(
            auth_mode=MetricsAuthMode.IP_ALLOWLIST,
            ip_allowlist=["10.0.0.0/8"]
        )
        
        # Mock request from disallowed IP
        request = MagicMock(spec=Request)
        request.headers = {"X-Forwarded-For": "11.0.0.1"}
        request.client = None
        
        # Should raise 403
        with pytest.raises(Exception) as exc_info:
            verify_metrics_access(request, config)
        
        assert exc_info.value.status_code == 403
    
    def test_ip_allowlist_multiple_cidrs(self):
        """Test IP allowlist with multiple CIDR ranges."""
        config = MetricsConfig(
            auth_mode=MetricsAuthMode.IP_ALLOWLIST,
            ip_allowlist=["10.0.0.0/8", "192.168.0.0/16", "172.16.0.0/12"]
        )
        
        # Test various IPs
        request = MagicMock(spec=Request)
        request.client = None
        
        # Allowed IPs
        for ip in ["10.1.2.3", "192.168.100.50", "172.20.0.1"]:
            request.headers = {"X-Forwarded-For": ip}
            verify_metrics_access(request, config)  # Should not raise
        
        # Disallowed IP
        request.headers = {"X-Forwarded-For": "8.8.8.8"}
        with pytest.raises(Exception):
            verify_metrics_access(request, config)


class TestPublicMode:
    """Test public mode (no authentication)."""
    
    def test_public_mode_allows_all(self):
        """Test public mode allows all requests."""
        config = MetricsConfig(auth_mode=MetricsAuthMode.PUBLIC)
        
        # Any request should pass
        request = MagicMock(spec=Request)
        request.headers = {}
        
        # Should not raise
        verify_metrics_access(request, config)


class TestMetricsEndpoint:
    """Test /metrics endpoint."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        from service.api import app
        return TestClient(app)
    
    def test_metrics_endpoint_with_token(self, client, monkeypatch):
        """Test /metrics endpoint with token auth."""
        # Set environment
        monkeypatch.setenv("METRICS_AUTH_MODE", "token")
        monkeypatch.setenv("METRICS_TOKEN", "test-metrics-token")
        
        # Reset config
        import monitoring.auth
        monitoring.auth._global_config = None
        
        # Request without token - should fail
        response = client.get("/metrics")
        assert response.status_code == 401
        
        # Request with correct token - should succeed
        response = client.get(
            "/metrics",
            headers={"Authorization": "Bearer test-metrics-token"}
        )
        assert response.status_code == 200
    
    def test_metrics_endpoint_public_mode(self, client, monkeypatch):
        """Test /metrics endpoint in public mode."""
        # Set environment
        monkeypatch.setenv("METRICS_AUTH_MODE", "public")
        
        # Reset config
        import monitoring.auth
        monitoring.auth._global_config = None
        
        # Request without auth - should succeed
        response = client.get("/metrics")
        assert response.status_code == 200
    
    def test_metrics_endpoint_invalid_token(self, client, monkeypatch):
        """Test /metrics endpoint with invalid token."""
        # Set environment
        monkeypatch.setenv("METRICS_AUTH_MODE", "token")
        monkeypatch.setenv("METRICS_TOKEN", "correct-token")
        
        # Reset config
        import monitoring.auth
        monitoring.auth._global_config = None
        
        # Request with wrong token
        response = client.get(
            "/metrics",
            headers={"Authorization": "Bearer wrong-token"}
        )
        assert response.status_code == 401


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

