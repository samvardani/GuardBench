"""Centralized configuration management for Safety-Eval-Mini.

This module consolidates all configuration settings from environment variables,
providing validation, defaults, and type safety using Pydantic.
"""

from __future__ import annotations

import hashlib
import logging
import os
import pathlib
import subprocess
from typing import Any, Optional

from pydantic import Field, field_validator, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class AppConfig(BaseSettings):
    """Centralized application configuration.
    
    All configuration values are loaded from environment variables with sensible defaults.
    Use this class instead of os.getenv() throughout the codebase.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra env vars
    )
    
    # ===== Application Info =====
    app_name: str = Field(default="Safety-Eval-Mini", description="Application name")
    app_version: str = Field(default="1.0.0", description="Application version")
    environment: str = Field(default="development", description="Environment (development/staging/production)")
    
    # ===== Server Configuration =====
    uvicorn_host: str = Field(default="127.0.0.1", description="Uvicorn bind host")
    uvicorn_port: int = Field(default=8000, description="Uvicorn port", ge=1, le=65535)
    uvicorn_workers: int = Field(default=1, description="Number of Uvicorn workers", ge=1)
    uvicorn_log_level: str = Field(default="info", description="Uvicorn log level")
    uvicorn_timeout_keep_alive: int = Field(default=5, description="Uvicorn keep-alive timeout (seconds)")
    
    # ===== gRPC Configuration =====
    grpc_host: str = Field(default="0.0.0.0", description="gRPC server bind host")
    grpc_port: int = Field(default=50051, description="gRPC server port", ge=1, le=65535)
    grpc_tls_enabled: bool = Field(default=False, description="Enable gRPC TLS")
    grpc_tls_port: int = Field(default=5443, description="gRPC TLS port", ge=1, le=65535)
    grpc_tls_cert: Optional[str] = Field(default=None, description="Path to gRPC TLS certificate")
    grpc_tls_key: Optional[str] = Field(default=None, description="Path to gRPC TLS private key")
    grpc_cert_file: Optional[str] = Field(default=None, description="gRPC certificate file (alternative naming)")
    grpc_key_file: Optional[str] = Field(default=None, description="gRPC key file (alternative naming)")
    grpc_addr: str = Field(default="127.0.0.1:50051", description="gRPC client address")
    enable_grpc_reflection: bool = Field(default=False, description="Enable gRPC reflection")
    
    # ===== Database Configuration =====
    database_path: str = Field(default="history.db", description="SQLite database path")
    db_url: Optional[str] = Field(default=None, description="Database URL (if using PostgreSQL/MySQL)")
    
    # ===== Service Configuration =====
    predict_max_workers: int = Field(default=8, description="Max worker threads for predictions", ge=1)
    predict_timeout_seconds: float = Field(default=2.0, description="Prediction timeout (seconds)", gt=0)
    max_json_body_bytes: int = Field(default=1_048_576, description="Max JSON body size (bytes)")
    safety_max_rows: int = Field(default=5000, description="Max rows per safety evaluation run", ge=1)
    
    # ===== Rate Limiting =====
    rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
    token_rate_limit: int = Field(default=60, description="Rate limit per token", ge=1)
    token_rate_window_seconds: int = Field(default=60, description="Rate limit window (seconds)", ge=1)
    
    # ===== Circuit Breaker =====
    cb_failure_threshold: int = Field(default=3, description="Circuit breaker failure threshold", ge=1)
    cb_latency_threshold_ms: int = Field(default=750, description="Circuit breaker latency threshold (ms)", ge=0)
    cb_recovery_seconds: float = Field(default=30.0, description="Circuit breaker recovery time (seconds)", ge=0)
    
    # ===== Logging =====
    log_level: str = Field(default="INFO", description="Application log level")
    
    # ===== CORS Configuration =====
    cors_allow_origins: Optional[str] = Field(
        default=None,
        description="CORS allowed origins (comma-separated or * for all)"
    )
    
    # ===== Redis Configuration =====
    redis_url: Optional[str] = Field(default=None, description="Redis connection URL")
    
    # ===== Kafka Configuration =====
    kafka_brokers: Optional[str] = Field(default=None, description="Kafka broker addresses (comma-separated)")
    kafka_rest_proxy: Optional[str] = Field(default=None, description="Kafka REST proxy URL")
    kafka_topic: Optional[str] = Field(default=None, description="Kafka topic name")
    
    # ===== Cloud Storage Configuration =====
    # S3
    aws_access_key_id: Optional[SecretStr] = Field(default=None, description="AWS access key ID")
    aws_secret_access_key: Optional[SecretStr] = Field(default=None, description="AWS secret access key")
    aws_region: str = Field(default="us-east-1", description="AWS region")
    s3_bucket: Optional[str] = Field(default=None, description="S3 bucket name")
    s3_prefix: str = Field(default="safety-eval", description="S3 key prefix")
    
    # Azure
    azure_storage_account: Optional[str] = Field(default=None, description="Azure storage account name")
    azure_storage_key: Optional[SecretStr] = Field(default=None, description="Azure storage account key")
    azure_container: Optional[str] = Field(default=None, description="Azure Blob container name")
    azure_connection_string: Optional[SecretStr] = Field(default=None, description="Azure storage connection string")
    
    # GCS
    gcs_bucket: Optional[str] = Field(default=None, description="GCS bucket name")
    gcs_project: Optional[str] = Field(default=None, description="GCP project ID")
    google_application_credentials: Optional[str] = Field(
        default=None,
        description="Path to GCP service account key JSON"
    )
    
    # ===== Observability =====
    otel_exporter_otlp_endpoint: Optional[str] = Field(
        default=None,
        description="OpenTelemetry OTLP exporter endpoint"
    )
    otel_exporter_otlp_insecure: bool = Field(
        default=True,
        description="Use insecure connection for OTLP exporter"
    )
    
    # ===== Policy Configuration =====
    policy_path: str = Field(default="policy/policy.yaml", description="Path to policy YAML file")
    policy_version: Optional[str] = Field(default=None, description="Policy version (auto-detected from git if not set)")
    policy_checksum: Optional[str] = Field(default=None, description="Policy checksum (auto-computed if not set)")
    
    # ===== Build Information =====
    build_id: Optional[str] = Field(default=None, description="Build ID or git commit hash")
    
    # ===== Security & Authentication =====
    session_secret: SecretStr = Field(
        default=SecretStr("dev-not-secret-change-in-production"),
        description="Session middleware secret key"
    )
    policy_admin_token: Optional[SecretStr] = Field(
        default=None,
        description="Admin token for policy management"
    )
    
    # ===== Slack Integration =====
    slack_bot_token: Optional[SecretStr] = Field(default=None, description="Slack bot OAuth token")
    slack_signing_secret: Optional[SecretStr] = Field(default=None, description="Slack signing secret")
    slack_app_token: Optional[SecretStr] = Field(default=None, description="Slack app-level token")
    
    # ===== SAML Configuration =====
    slack_client_id: Optional[str] = Field(default=None, description="Slack OAuth client ID")
    slack_client_secret: Optional[SecretStr] = Field(default=None, description="Slack OAuth client secret")
    slack_redirect_uri: str = Field(
        default="http://localhost:8001/slack/oauth_callback",
        description="Slack OAuth redirect URI"
    )
    
    # ===== Usage Quotas =====
    enforce_usage_quota: bool = Field(
        default=False,
        description="Enforce hard usage quota limits (blocks over-quota requests)"
    )
    
    # ===== Federation =====
    federation_tenant_secret: SecretStr = Field(
        default=SecretStr("default-secret-change-in-production"),
        description="Federation tenant shared secret"
    )
    
    # ===== Feed Configuration =====
    feed_refresh_seconds: float = Field(
        default=3600.0,
        description="Feed refresh interval (seconds)",
        ge=0
    )
    
    # ===== SDK Configuration =====
    default_guard: str = Field(default="candidate", description="Default safety guard to use")
    seval_seed: Optional[str] = Field(default=None, description="Environment variable name for random seed")
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            logger.warning(f"Invalid log level '{v}', defaulting to INFO")
            return "INFO"
        return v_upper
    
    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment."""
        valid_envs = ["development", "staging", "production", "test"]
        v_lower = v.lower()
        if v_lower not in valid_envs:
            logger.warning(f"Invalid environment '{v}', defaulting to development")
            return "development"
        return v_lower
    
    def get_policy_version(self) -> str:
        """Get policy version (auto-detect from git if not set)."""
        if self.policy_version:
            return self.policy_version
        
        try:
            result = subprocess.run(
                ["git", "describe", "--tags", "--always"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.stdout.strip() or "dev"
        except Exception:
            return "dev"
    
    def get_policy_checksum(self) -> str:
        """Get policy checksum (auto-compute if not set)."""
        if self.policy_checksum:
            return self.policy_checksum
        
        try:
            policy_path = pathlib.Path(self.policy_path)
            h = hashlib.sha256()
            
            if policy_path.exists():
                h.update(policy_path.read_bytes())
            
            # Include repo HEAD sha for provenance
            try:
                result = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                sha = result.stdout.strip()
                h.update(sha.encode())
            except Exception:
                pass
            
            return h.hexdigest()[:12]
        except Exception:
            return "unknown"
    
    def get_build_id(self) -> str:
        """Get build ID (auto-detect from git if not set)."""
        if self.build_id:
            return self.build_id
        
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.stdout.strip() or "n/a"
        except Exception:
            return "n/a"
    
    def to_dict(self, include_secrets: bool = False) -> dict[str, Any]:
        """Convert config to dictionary.
        
        Args:
            include_secrets: If True, include secret values (use with caution!)
            
        Returns:
            Configuration dictionary
        """
        data = {}
        for field_name in self.model_fields.keys():
            value = getattr(self, field_name)
            
            # Handle SecretStr
            if isinstance(value, SecretStr):
                if include_secrets:
                    data[field_name] = value.get_secret_value()
                else:
                    data[field_name] = "***REDACTED***"
            else:
                data[field_name] = value
        
        return data
    
    def log_config(self, logger_instance: Optional[logging.Logger] = None) -> None:
        """Log configuration (with secrets redacted).
        
        Args:
            logger_instance: Logger to use (defaults to module logger)
        """
        log = logger_instance or logger
        
        log.info("=" * 60)
        log.info("Application Configuration")
        log.info("=" * 60)
        
        config_dict = self.to_dict(include_secrets=False)
        
        # Group by category
        categories = {
            "Application": ["app_name", "app_version", "environment", "build_id"],
            "Server": ["uvicorn_host", "uvicorn_port", "uvicorn_workers", "uvicorn_log_level"],
            "gRPC": ["grpc_host", "grpc_port", "grpc_tls_enabled", "enable_grpc_reflection"],
            "Database": ["database_path", "db_url"],
            "Service": ["predict_max_workers", "predict_timeout_seconds", "safety_max_rows"],
            "Rate Limiting": ["rate_limit_enabled", "token_rate_limit", "token_rate_window_seconds"],
            "Circuit Breaker": ["cb_failure_threshold", "cb_latency_threshold_ms", "cb_recovery_seconds"],
            "Logging": ["log_level"],
            "CORS": ["cors_allow_origins"],
            "Redis": ["redis_url"],
            "Kafka": ["kafka_brokers", "kafka_topic"],
            "Cloud Storage": ["s3_bucket", "azure_container", "gcs_bucket"],
            "Observability": ["otel_exporter_otlp_endpoint"],
            "Policy": ["policy_path", "policy_version", "policy_checksum"],
            "Security": ["session_secret", "policy_admin_token", "federation_tenant_secret"],
            "Slack": ["slack_bot_token", "slack_signing_secret"],
            "Usage Quotas": ["enforce_usage_quota"],
        }
        
        for category, fields in categories.items():
            category_values = {k: config_dict[k] for k in fields if k in config_dict and config_dict[k] is not None}
            if category_values:
                log.info(f"\n[{category}]")
                for key, value in category_values.items():
                    log.info(f"  {key}: {value}")
        
        log.info("=" * 60)


# Global config instance
_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """Get global configuration instance (singleton).
    
    Returns:
        AppConfig instance
    """
    global _config
    if _config is None:
        _config = AppConfig()
    return _config


def reload_config() -> AppConfig:
    """Reload configuration from environment (useful for testing).
    
    Returns:
        Newly created AppConfig instance
    """
    global _config
    _config = AppConfig()
    return _config


__all__ = ["AppConfig", "get_config", "reload_config"]

