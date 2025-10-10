"""Authentication and authorization for metrics endpoint."""

from __future__ import annotations

import ipaddress
import logging
import os
from enum import Enum
from typing import Optional

from fastapi import HTTPException, Request, status

logger = logging.getLogger(__name__)


class MetricsAuthMode(Enum):
    """Metrics authentication modes."""
    
    PUBLIC = "public"
    TOKEN = "token"
    IP_ALLOWLIST = "ip_allowlist"


class MetricsConfig:
    """Configuration for metrics endpoint security."""
    
    def __init__(
        self,
        auth_mode: MetricsAuthMode = MetricsAuthMode.TOKEN,
        token: Optional[str] = None,
        ip_allowlist: Optional[list[str]] = None
    ):
        """Initialize metrics configuration.
        
        Args:
            auth_mode: Authentication mode
            token: Bearer token (for TOKEN mode)
            ip_allowlist: CIDR ranges (for IP_ALLOWLIST mode)
        """
        self.auth_mode = auth_mode
        self.token = token
        self.ip_allowlist = ip_allowlist or []
        
        # Parse CIDR ranges
        self.allowed_networks = []
        for cidr in self.ip_allowlist:
            try:
                self.allowed_networks.append(ipaddress.ip_network(cidr))
            except ValueError as e:
                logger.error(f"Invalid CIDR range {cidr}: {e}")
        
        logger.info(
            f"MetricsConfig: mode={auth_mode.value}, "
            f"ip_allowlist={len(self.allowed_networks)} networks"
        )
    
    def is_ip_allowed(self, ip_address: str) -> bool:
        """Check if IP address is allowed.
        
        Args:
            ip_address: IP address to check
            
        Returns:
            True if allowed
        """
        if not self.allowed_networks:
            return False
        
        try:
            ip = ipaddress.ip_address(ip_address)
            
            for network in self.allowed_networks:
                if ip in network:
                    return True
            
            return False
        
        except ValueError:
            logger.warning(f"Invalid IP address: {ip_address}")
            return False


# Global config instance
_global_config: Optional[MetricsConfig] = None


def get_metrics_config() -> MetricsConfig:
    """Get metrics configuration from environment.
    
    Returns:
        MetricsConfig instance
    """
    global _global_config
    
    if _global_config is None:
        # Get auth mode
        mode_str = os.getenv("METRICS_AUTH_MODE", "token").lower()
        
        try:
            auth_mode = MetricsAuthMode(mode_str)
        except ValueError:
            logger.warning(f"Invalid METRICS_AUTH_MODE: {mode_str}, defaulting to token")
            auth_mode = MetricsAuthMode.TOKEN
        
        # Get token
        token = os.getenv("METRICS_TOKEN")
        
        # Get IP allowlist
        allowlist_str = os.getenv("METRICS_IP_ALLOWLIST", "")
        ip_allowlist = [ip.strip() for ip in allowlist_str.split(",") if ip.strip()]
        
        _global_config = MetricsConfig(
            auth_mode=auth_mode,
            token=token,
            ip_allowlist=ip_allowlist
        )
    
    return _global_config


def verify_metrics_access(request: Request, config: Optional[MetricsConfig] = None) -> None:
    """Verify access to metrics endpoint.
    
    Args:
        request: FastAPI request
        config: Optional metrics config (uses global if None)
        
    Raises:
        HTTPException: If access denied
    """
    if config is None:
        config = get_metrics_config()
    
    # Public mode - allow all
    if config.auth_mode == MetricsAuthMode.PUBLIC:
        return
    
    # Token mode - check Authorization header
    if config.auth_mode == MetricsAuthMode.TOKEN:
        authorization = request.headers.get("Authorization", "")
        
        if not authorization:
            logger.warning("Metrics access denied: missing Authorization header")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing Authorization header",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        scheme, _, token = authorization.partition(" ")
        
        if scheme.lower() != "bearer" or not token:
            logger.warning("Metrics access denied: invalid Authorization format")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Authorization header format",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        if not config.token or token != config.token:
            logger.warning(f"Metrics access denied: invalid token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid metrics token",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        logger.debug("Metrics access granted via token")
        return
    
    # IP allowlist mode - check client IP
    if config.auth_mode == MetricsAuthMode.IP_ALLOWLIST:
        # Get client IP (handle X-Forwarded-For)
        client_ip = request.headers.get("X-Forwarded-For", "")
        
        if client_ip:
            # Take first IP in chain (original client)
            client_ip = client_ip.split(",")[0].strip()
        else:
            # Fall back to direct connection IP
            client_ip = request.client.host if request.client else ""
        
        if not client_ip:
            logger.warning("Metrics access denied: cannot determine client IP")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot determine client IP"
            )
        
        if not config.is_ip_allowed(client_ip):
            logger.warning(f"Metrics access denied: IP {client_ip} not in allowlist")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"IP address {client_ip} not allowed"
            )
        
        logger.debug(f"Metrics access granted for IP {client_ip}")
        return


__all__ = [
    "MetricsAuthMode",
    "MetricsConfig",
    "get_metrics_config",
    "verify_metrics_access",
]

