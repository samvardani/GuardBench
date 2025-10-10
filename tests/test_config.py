"""Tests for centralized configuration module."""

from __future__ import annotations

import os
import pytest
import logging
from unittest.mock import patch
from pathlib import Path

from config import AppConfig, get_config, reload_config


class TestAppConfig:
    """Test AppConfig class."""
    
    def test_default_values(self):
        """Test that default values are set correctly."""
        config = AppConfig()
        
        # Application
        assert config.app_name == "Safety-Eval-Mini"
        assert config.environment == "development"
        
        # Server
        assert config.uvicorn_host == "127.0.0.1"
        assert config.uvicorn_port == 8000
        assert config.uvicorn_workers == 1
        
        # gRPC
        assert config.grpc_host == "0.0.0.0"
        assert config.grpc_port == 50051
        assert config.grpc_tls_enabled is False
        
        # Service
        assert config.predict_max_workers == 8
        assert config.predict_timeout_seconds == 2.0
        assert config.safety_max_rows == 5000
        
        # Rate Limiting
        assert config.rate_limit_enabled is True
        assert config.token_rate_limit == 60
        
        # Circuit Breaker
        assert config.cb_failure_threshold == 3
        assert config.cb_latency_threshold_ms == 750
        assert config.cb_recovery_seconds == 30.0
        
        # Logging
        assert config.log_level == "INFO"
    
    def test_env_var_override(self):
        """Test that environment variables override defaults."""
        with patch.dict(os.environ, {
            "UVICORN_PORT": "9000",
            "GRPC_PORT": "60060",
            "PREDICT_MAX_WORKERS": "16",
            "LOG_LEVEL": "DEBUG",
            "RATE_LIMIT_ENABLED": "false",
        }):
            config = AppConfig()
            
            assert config.uvicorn_port == 9000
            assert config.grpc_port == 60060
            assert config.predict_max_workers == 16
            assert config.log_level == "DEBUG"
            assert config.rate_limit_enabled is False
    
    def test_boolean_parsing(self):
        """Test boolean environment variable parsing."""
        # Test True values
        for true_val in ["true", "1", "yes", "on"]:
            with patch.dict(os.environ, {"RATE_LIMIT_ENABLED": true_val}):
                config = AppConfig()
                assert config.rate_limit_enabled is True
        
        # Test False values
        for false_val in ["false", "0", "no", "off"]:
            with patch.dict(os.environ, {"RATE_LIMIT_ENABLED": false_val}):
                config = AppConfig()
                assert config.rate_limit_enabled is False
    
    def test_integer_validation(self):
        """Test integer field validation."""
        # Valid port
        with patch.dict(os.environ, {"UVICORN_PORT": "8080"}):
            config = AppConfig()
            assert config.uvicorn_port == 8080
        
        # Invalid port (too high)
        with patch.dict(os.environ, {"UVICORN_PORT": "99999"}):
            with pytest.raises(Exception):  # Pydantic validation error
                AppConfig()
    
    def test_float_validation(self):
        """Test float field validation."""
        with patch.dict(os.environ, {"PREDICT_TIMEOUT_SECONDS": "5.5"}):
            config = AppConfig()
            assert config.predict_timeout_seconds == 5.5
    
    def test_secret_str_fields(self):
        """Test SecretStr fields."""
        with patch.dict(os.environ, {
            "SESSION_SECRET": "my-secret-key",
            "SLACK_BOT_TOKEN": "xoxb-123-456",
            "AWS_SECRET_ACCESS_KEY": "secret123",
        }):
            config = AppConfig()
            
            # SecretStr values are hidden
            assert str(config.session_secret) != "my-secret-key"
            assert ("SecretStr" in str(config.session_secret) or 
                    "**********" in str(config.session_secret))
            
            # Can get actual value
            assert config.session_secret.get_secret_value() == "my-secret-key"
            assert config.slack_bot_token.get_secret_value() == "xoxb-123-456"
            assert config.aws_secret_access_key.get_secret_value() == "secret123"
    
    def test_optional_fields(self):
        """Test optional fields default to None."""
        config = AppConfig()
        
        assert config.redis_url is None
        assert config.kafka_brokers is None
        assert config.otel_exporter_otlp_endpoint is None
        assert config.s3_bucket is None
        assert config.policy_admin_token is None
    
    def test_log_level_validation(self):
        """Test log level validation."""
        # Valid log levels
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            with patch.dict(os.environ, {"LOG_LEVEL": level}):
                config = AppConfig()
                assert config.log_level == level
        
        # Invalid log level should default to INFO
        with patch.dict(os.environ, {"LOG_LEVEL": "INVALID"}):
            config = AppConfig()
            assert config.log_level == "INFO"
        
        # Case insensitive
        with patch.dict(os.environ, {"LOG_LEVEL": "debug"}):
            config = AppConfig()
            assert config.log_level == "DEBUG"
    
    def test_environment_validation(self):
        """Test environment validation."""
        # Valid environments
        for env in ["development", "staging", "production", "test"]:
            with patch.dict(os.environ, {"ENVIRONMENT": env}):
                config = AppConfig()
                assert config.environment == env
        
        # Invalid environment should default to development
        with patch.dict(os.environ, {"ENVIRONMENT": "invalid"}):
            config = AppConfig()
            assert config.environment == "development"
        
        # Case insensitive
        with patch.dict(os.environ, {"ENVIRONMENT": "PRODUCTION"}):
            config = AppConfig()
            assert config.environment == "production"
    
    def test_cloud_storage_config(self):
        """Test cloud storage configuration."""
        with patch.dict(os.environ, {
            "S3_BUCKET": "my-bucket",
            "AWS_REGION": "us-west-2",
            "AZURE_CONTAINER": "my-container",
            "GCS_BUCKET": "my-gcs-bucket",
        }):
            config = AppConfig()
            
            assert config.s3_bucket == "my-bucket"
            assert config.aws_region == "us-west-2"
            assert config.azure_container == "my-container"
            assert config.gcs_bucket == "my-gcs-bucket"
    
    def test_grpc_tls_config(self):
        """Test gRPC TLS configuration."""
        with patch.dict(os.environ, {
            "GRPC_TLS_ENABLED": "true",
            "GRPC_TLS_PORT": "5443",
            "GRPC_TLS_CERT": "/path/to/cert.pem",
            "GRPC_TLS_KEY": "/path/to/key.pem",
        }):
            config = AppConfig()
            
            assert config.grpc_tls_enabled is True
            assert config.grpc_tls_port == 5443
            assert config.grpc_tls_cert == "/path/to/cert.pem"
            assert config.grpc_tls_key == "/path/to/key.pem"
    
    def test_kafka_config(self):
        """Test Kafka configuration."""
        with patch.dict(os.environ, {
            "KAFKA_BROKERS": "localhost:9092,localhost:9093",
            "KAFKA_TOPIC": "safety-events",
        }):
            config = AppConfig()
            
            assert config.kafka_brokers == "localhost:9092,localhost:9093"
            assert config.kafka_topic == "safety-events"
    
    def test_get_policy_version(self):
        """Test policy version getter."""
        # With env var
        with patch.dict(os.environ, {"POLICY_VERSION": "v1.2.3"}):
            config = AppConfig()
            assert config.get_policy_version() == "v1.2.3"
        
        # Without env var (auto-detect)
        with patch.dict(os.environ, {}, clear=True):
            config = AppConfig()
            version = config.get_policy_version()
            assert isinstance(version, str)
            assert len(version) > 0
    
    def test_get_build_id(self):
        """Test build ID getter."""
        # With env var
        with patch.dict(os.environ, {"BUILD_ID": "abc123"}):
            config = AppConfig()
            assert config.get_build_id() == "abc123"
        
        # Without env var (auto-detect)
        with patch.dict(os.environ, {}, clear=True):
            config = AppConfig()
            build_id = config.get_build_id()
            assert isinstance(build_id, str)
            assert len(build_id) > 0


class TestConfigToDict:
    """Test configuration serialization."""
    
    def test_to_dict_without_secrets(self):
        """Test to_dict() without secrets."""
        with patch.dict(os.environ, {
            "SESSION_SECRET": "my-secret",
            "SLACK_BOT_TOKEN": "xoxb-123",
            "UVICORN_PORT": "8080",
        }):
            config = AppConfig()
            data = config.to_dict(include_secrets=False)
            
            assert data["uvicorn_port"] == 8080
            assert data["session_secret"] == "***REDACTED***"
            assert data["slack_bot_token"] == "***REDACTED***"
    
    def test_to_dict_with_secrets(self):
        """Test to_dict() with secrets (use with caution!)."""
        with patch.dict(os.environ, {
            "SESSION_SECRET": "my-secret",
            "SLACK_BOT_TOKEN": "xoxb-123",
        }):
            config = AppConfig()
            data = config.to_dict(include_secrets=True)
            
            assert data["session_secret"] == "my-secret"
            assert data["slack_bot_token"] == "xoxb-123"
    
    def test_log_config(self, caplog):
        """Test config logging."""
        with caplog.at_level(logging.INFO):
            config = AppConfig()
            config.log_config()
            
            # Check that config was logged
            assert "Application Configuration" in caplog.text
            assert "uvicorn_port" in caplog.text
            
            # Secrets should be redacted
            assert "***REDACTED***" in caplog.text or "session_secret" not in caplog.text


class TestSingletonPattern:
    """Test singleton pattern for get_config()."""
    
    def test_get_config_returns_same_instance(self):
        """Test that get_config() returns the same instance."""
        config1 = get_config()
        config2 = get_config()
        
        assert config1 is config2
    
    def test_reload_config_creates_new_instance(self):
        """Test that reload_config() creates a new instance."""
        config1 = get_config()
        
        with patch.dict(os.environ, {"UVICORN_PORT": "9999"}):
            config2 = reload_config()
            
            assert config1 is not config2
            assert config2.uvicorn_port == 9999
    
    def test_reload_config_updates_singleton(self):
        """Test that reload_config() updates the singleton."""
        get_config()  # Initialize
        
        with patch.dict(os.environ, {"UVICORN_PORT": "7777"}):
            reload_config()
            config = get_config()
            
            assert config.uvicorn_port == 7777


class TestRealWorldScenarios:
    """Test real-world configuration scenarios."""
    
    def test_production_config(self):
        """Test production-like configuration."""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "UVICORN_HOST": "0.0.0.0",
            "UVICORN_PORT": "8000",
            "UVICORN_WORKERS": "4",
            "LOG_LEVEL": "WARNING",
            "RATE_LIMIT_ENABLED": "true",
            "REDIS_URL": "redis://redis:6379/0",
            "OTEL_EXPORTER_OTLP_ENDPOINT": "http://jaeger:4318",
            "SESSION_SECRET": "production-secret-key-change-me",
        }):
            config = AppConfig()
            
            assert config.environment == "production"
            assert config.uvicorn_host == "0.0.0.0"
            assert config.uvicorn_workers == 4
            assert config.log_level == "WARNING"
            assert config.redis_url == "redis://redis:6379/0"
            assert config.otel_exporter_otlp_endpoint == "http://jaeger:4318"
    
    def test_development_config(self):
        """Test development-like configuration."""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "development",
            "LOG_LEVEL": "DEBUG",
            "RATE_LIMIT_ENABLED": "false",
        }):
            config = AppConfig()
            
            assert config.environment == "development"
            assert config.log_level == "DEBUG"
            assert config.rate_limit_enabled is False
    
    def test_testing_config(self):
        """Test testing-like configuration."""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "test",
            "DATABASE_PATH": ":memory:",
            "RATE_LIMIT_ENABLED": "false",
            "LOG_LEVEL": "ERROR",
        }):
            config = AppConfig()
            
            assert config.environment == "test"
            assert config.database_path == ":memory:"
            assert config.rate_limit_enabled is False
            assert config.log_level == "ERROR"
    
    def test_cloud_deployment_config(self):
        """Test cloud deployment configuration."""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "S3_BUCKET": "my-app-bucket",
            "AWS_REGION": "us-east-1",
            "REDIS_URL": "redis://elasticache:6379",
            "KAFKA_BROKERS": "kafka1:9092,kafka2:9092",
            "OTEL_EXPORTER_OTLP_ENDPOINT": "https://otlp-collector:4318",
        }):
            config = AppConfig()
            
            assert config.s3_bucket == "my-app-bucket"
            assert config.aws_region == "us-east-1"
            assert config.redis_url == "redis://elasticache:6379"
            assert config.kafka_brokers == "kafka1:9092,kafka2:9092"


class TestBackwardCompatibility:
    """Test backward compatibility with existing code."""
    
    def test_settings_compatibility(self):
        """Test that old Settings class still works."""
        from service.settings import get_settings, get_config as get_service_config
        
        # Old way (deprecated but should work)
        settings = get_settings()
        assert isinstance(settings.uvicorn_port, int)
        assert settings.uvicorn_port > 0
        
        # New way (recommended)
        config = get_service_config()
        assert isinstance(config.uvicorn_port, int)
        assert config.uvicorn_port > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

