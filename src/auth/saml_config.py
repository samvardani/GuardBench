"""SAML configuration with security hardening."""

from __future__ import annotations

import hashlib
import logging
import os
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


@dataclass
class SAMLConfig:
    """SAML configuration with security settings."""
    
    # Entity IDs
    sp_entity_id: str
    idp_entity_id: str
    
    # URLs
    acs_url: str  # Assertion Consumer Service
    idp_sso_url: str
    idp_cert: str  # X.509 certificate (PEM format)
    
    # Optional URLs
    slo_url: Optional[str] = None  # Single Logout
    idp_cert_fingerprint: Optional[str] = None  # SHA-256 fingerprint for pinning
    
    # Security settings
    require_signed_assertion: bool = True
    require_signed_response: bool = True
    allow_unsigned: bool = False  # Override (INSECURE)
    max_clock_skew_seconds: int = 180  # ±3 minutes
    
    # SLO security
    allowed_relay_state_origins: list[str] = None  # For RelayState validation
    
    def __post_init__(self):
        """Validate configuration."""
        # Compute fingerprint if not provided
        if not self.idp_cert_fingerprint and self.idp_cert:
            self.idp_cert_fingerprint = self.compute_cert_fingerprint(self.idp_cert)
            logger.info(f"Computed IdP cert fingerprint: {self.idp_cert_fingerprint[:16]}...")
        
        # Default allowed origins to ACS URL origin
        if self.allowed_relay_state_origins is None:
            acs_origin = self._extract_origin(self.acs_url)
            self.allowed_relay_state_origins = [acs_origin] if acs_origin else []
    
    @staticmethod
    def compute_cert_fingerprint(cert_pem: str) -> str:
        """Compute SHA-256 fingerprint of certificate.
        
        Args:
            cert_pem: Certificate in PEM format
            
        Returns:
            SHA-256 fingerprint (hex)
        """
        try:
            # Remove PEM headers/footers and whitespace
            cert_data = cert_pem.replace("-----BEGIN CERTIFICATE-----", "")
            cert_data = cert_data.replace("-----END CERTIFICATE-----", "")
            cert_data = cert_data.replace("\n", "").replace("\r", "").replace(" ", "")
            
            # Decode base64 and hash
            import base64
            cert_bytes = base64.b64decode(cert_data)
            
            return hashlib.sha256(cert_bytes).hexdigest()
        
        except Exception as e:
            # For testing or invalid certs, hash the raw PEM string
            logger.warning(f"Could not decode certificate, using PEM hash: {e}")
            return hashlib.sha256(cert_pem.encode()).hexdigest()
    
    def verify_cert_fingerprint(self, cert_pem: str) -> bool:
        """Verify certificate matches pinned fingerprint.
        
        Args:
            cert_pem: Certificate to verify
            
        Returns:
            True if matches, False otherwise
        """
        if not self.idp_cert_fingerprint:
            # No pinning configured
            return True
        
        actual_fingerprint = self.compute_cert_fingerprint(cert_pem)
        
        if actual_fingerprint != self.idp_cert_fingerprint:
            logger.error(
                f"Certificate fingerprint mismatch! "
                f"Expected: {self.idp_cert_fingerprint[:16]}..., "
                f"got: {actual_fingerprint[:16]}..."
            )
            return False
        
        return True
    
    @staticmethod
    def _extract_origin(url: str) -> str:
        """Extract origin from URL.
        
        Args:
            url: Full URL
            
        Returns:
            Origin (scheme://host:port)
        """
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"
    
    def is_relay_state_allowed(self, relay_state: Optional[str]) -> bool:
        """Check if RelayState URL is allowed.
        
        Args:
            relay_state: RelayState parameter
            
        Returns:
            True if allowed (same-origin or in allowlist)
        """
        if not relay_state:
            return True  # Empty is ok
        
        # Parse RelayState
        try:
            parsed = urlparse(relay_state)
            
            # Relative URLs are ok
            if not parsed.scheme:
                return True
            
            # Check against allowed origins
            relay_origin = f"{parsed.scheme}://{parsed.netloc}"
            
            if relay_origin in self.allowed_relay_state_origins:
                return True
            
            logger.warning(f"RelayState origin not allowed: {relay_origin}")
            return False
        
        except Exception as e:
            logger.error(f"Error parsing RelayState: {e}")
            return False


def get_saml_config() -> Optional[SAMLConfig]:
    """Get SAML configuration from environment.
    
    Returns:
        SAMLConfig or None if not configured
    """
    sp_entity_id = os.getenv("SAML_SP_ENTITY_ID")
    idp_entity_id = os.getenv("SAML_IDP_ENTITY_ID")
    
    if not sp_entity_id or not idp_entity_id:
        return None
    
    return SAMLConfig(
        sp_entity_id=sp_entity_id,
        idp_entity_id=idp_entity_id,
        acs_url=os.getenv("SAML_ACS_URL", "https://localhost:8001/auth/saml/acs"),
        slo_url=os.getenv("SAML_SLO_URL"),
        idp_sso_url=os.getenv("SAML_IDP_SSO_URL", ""),
        idp_cert=os.getenv("SAML_IDP_CERT", ""),
        idp_cert_fingerprint=os.getenv("SAML_IDP_CERT_FINGERPRINT"),
        require_signed_assertion=os.getenv("SAML_REQUIRE_SIGNED_ASSERTION", "true").lower() == "true",
        require_signed_response=os.getenv("SAML_REQUIRE_SIGNED_RESPONSE", "true").lower() == "true",
        allow_unsigned=os.getenv("SAML_ALLOW_UNSIGNED", "false").lower() == "true",
        max_clock_skew_seconds=int(os.getenv("SAML_MAX_CLOCK_SKEW", "180")),
    )


__all__ = ["SAMLConfig", "get_saml_config"]

