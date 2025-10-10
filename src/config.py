"""Centralized configuration management with runtime immutability."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class FrozenConfigError(Exception):
    """Raised when attempting to modify frozen configuration."""
    pass


@dataclass
class Config:
    """Immutable configuration singleton.
    
    All environment variable reads should go through this config object.
    Config is frozen after initialization to prevent runtime modification.
    """
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8001
    grpc_port: int = 50051
    
    # Logging
    log_level: str = "info"
    log_format: str = "json"
    
    # Features
    enable_image: bool = False
    test_mode: bool = False
    
    # Auth
    oidc_client_id: Optional[str] = None
    oidc_client_secret: Optional[str] = None
    
    saml_sp_entity_id: Optional[str] = None
    saml_idp_entity_id: Optional[str] = None
    saml_idp_cert: Optional[str] = None
    saml_idp_cert_fingerprint: Optional[str] = None
    
    slack_client_id: Optional[str] = None
    slack_client_secret: Optional[str] = None
    slack_signing_secret: Optional[str] = None
    
    # Metrics
    metrics_enabled: bool = True
    metrics_port: int = 8000
    metrics_auth_token: Optional[str] = None
    
    # Database
    database_url: str = "sqlite:///history.db"
    
    # Internal state
    _frozen: bool = field(default=False, init=False, repr=False)
    
    def __post_init__(self):
        """Load config from environment."""
        self._load_from_env()
        self._validate()
    
    def _load_from_env(self):
        """Load configuration from environment variables."""
        # Server
        self.host = os.getenv("HOST", self.host)
        self.port = int(os.getenv("PORT", str(self.port)))
        self.grpc_port = int(os.getenv("GRPC_PORT", str(self.grpc_port)))
        
        # Logging
        self.log_level = os.getenv("LOG_LEVEL", self.log_level).lower()
        self.log_format = os.getenv("LOG_FORMAT", self.log_format).lower()
        
        # Features
        self.enable_image = os.getenv("ENABLE_IMAGE", "0") == "1"
        self.test_mode = os.getenv("TEST_MODE", "0") == "1"
        
        # Auth - OIDC
        self.oidc_client_id = os.getenv("OIDC_CLIENT_ID")
        self.oidc_client_secret = os.getenv("OIDC_CLIENT_SECRET")
        
        # Auth - SAML
        self.saml_sp_entity_id = os.getenv("SAML_SP_ENTITY_ID")
        self.saml_idp_entity_id = os.getenv("SAML_IDP_ENTITY_ID")
        self.saml_idp_cert = os.getenv("SAML_IDP_CERT")
        self.saml_idp_cert_fingerprint = os.getenv("SAML_IDP_CERT_FINGERPRINT")
        
        # Auth - Slack
        self.slack_client_id = os.getenv("SLACK_CLIENT_ID")
        self.slack_client_secret = os.getenv("SLACK_CLIENT_SECRET")
        self.slack_signing_secret = os.getenv("SLACK_SIGNING_SECRET")
        
        # Metrics
        self.metrics_enabled = os.getenv("METRICS_ENABLED", "1") == "1"
        self.metrics_port = int(os.getenv("METRICS_PORT", str(self.metrics_port)))
        self.metrics_auth_token = os.getenv("METRICS_AUTH_TOKEN")
        
        # Database
        self.database_url = os.getenv("DATABASE_URL", self.database_url)
        
        logger.info(f"Configuration loaded: {self._summary()}")
    
    def _validate(self):
        """Validate configuration."""
        # Port ranges
        if not (1 <= self.port <= 65535):
            raise ValueError(f"Invalid port: {self.port}")
        
        if not (1 <= self.grpc_port <= 65535):
            raise ValueError(f"Invalid gRPC port: {self.grpc_port}")
        
        if not (1 <= self.metrics_port <= 65535):
            raise ValueError(f"Invalid metrics port: {self.metrics_port}")
        
        # Log level
        valid_log_levels = ["debug", "info", "warning", "error", "critical"]
        if self.log_level not in valid_log_levels:
            raise ValueError(f"Invalid log level: {self.log_level}")
    
    def _summary(self) -> str:
        """Get config summary (safe for logging)."""
        return (
            f"host={self.host}, port={self.port}, "
            f"log_level={self.log_level}, test_mode={self.test_mode}"
        )
    
    def freeze(self):
        """Freeze configuration to prevent runtime modification.
        
        After freezing, any attempt to set attributes will raise FrozenConfigError.
        """
        object.__setattr__(self, "_frozen", True)
        logger.info("Configuration frozen (immutable)")
    
    def __setattr__(self, name: str, value: Any):
        """Override setattr to enforce immutability when frozen."""
        # Allow setting during initialization
        if name == "_frozen" or not hasattr(self, "_frozen"):
            object.__setattr__(self, name, value)
            return
        
        # Raise error if frozen
        if self._frozen:
            raise FrozenConfigError(
                f"Cannot modify frozen configuration: attempted to set '{name}' = {value}"
            )
        
        object.__setattr__(self, name, value)
    
    def dump(self, redact: bool = True) -> Dict[str, Any]:
        """Dump configuration as dictionary.
        
        Args:
            redact: If True, redact sensitive values
            
        Returns:
            Configuration dictionary
        """
        config_dict = {}
        
        # Sensitive keys (always redacted)
        sensitive_keys = {
            "oidc_client_secret",
            "saml_idp_cert",
            "slack_client_secret",
            "slack_signing_secret",
            "metrics_auth_token",
        }
        
        # Partially redacted (show prefix only)
        partial_redact_keys = {
            "oidc_client_id",
            "saml_idp_cert_fingerprint",
            "slack_client_id",
        }
        
        for key, value in self.__dict__.items():
            # Skip internal attributes
            if key.startswith("_"):
                continue
            
            if redact:
                # Full redaction
                if key in sensitive_keys:
                    config_dict[key] = "***REDACTED***" if value else None
                # Partial redaction (first 8 chars)
                elif key in partial_redact_keys and value:
                    config_dict[key] = f"{str(value)[:8]}..." if len(str(value)) > 8 else value
                else:
                    config_dict[key] = value
            else:
                config_dict[key] = value
        
        return config_dict


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get global configuration instance.
    
    Returns:
        Config singleton
    """
    global _config
    
    if _config is None:
        _config = Config()
        _config.freeze()
    
    return _config


def reset_config():
    """Reset global config (for testing only).
    
    WARNING: This should only be used in tests.
    """
    global _config
    _config = None


__all__ = ["Config", "FrozenConfigError", "get_config", "reset_config"]

