"""SAML SSO handler with security hardening."""

from __future__ import annotations

import base64
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlparse

from .saml_config import SAMLConfig

logger = logging.getLogger(__name__)


class SAMLSecurityError(Exception):
    """SAML security validation error."""
    pass


class SAMLHandler:
    """SAML SSO handler with strict security validation.
    
    Security features:
    - Strict signature verification
    - Certificate pinning (fingerprint validation)
    - Clock skew validation (±3 minutes)
    - Safe RelayState (prevents open redirects)
    """
    
    def __init__(self, config: SAMLConfig):
        """Initialize SAML handler.
        
        Args:
            config: SAML configuration
        """
        self.config = config
        
        logger.info(
            f"SAMLHandler initialized: "
            f"require_signed={config.require_signed_assertion}, "
            f"cert_pinning={bool(config.idp_cert_fingerprint)}, "
            f"clock_skew={config.max_clock_skew_seconds}s"
        )
    
    def validate_assertion(
        self,
        assertion: dict,
        check_signature: bool = True,
        check_cert_fingerprint: bool = True,
        check_clock_skew: bool = True
    ) -> None:
        """Validate SAML assertion with security checks.
        
        Args:
            assertion: Parsed SAML assertion
            check_signature: Verify signature
            check_cert_fingerprint: Verify cert fingerprint
            check_clock_skew: Validate timestamps
            
        Raises:
            SAMLSecurityError: If validation fails
        """
        # 1. Signature verification
        if check_signature and not self.config.allow_unsigned:
            if self.config.require_signed_assertion:
                if not assertion.get("signed", False):
                    raise SAMLSecurityError("Assertion must be signed")
                
                if not assertion.get("signature_valid", False):
                    raise SAMLSecurityError("Invalid assertion signature")
        
        # 2. Certificate fingerprint verification
        if check_cert_fingerprint and self.config.idp_cert_fingerprint:
            cert_in_assertion = assertion.get("certificate", "")
            
            if not cert_in_assertion:
                raise SAMLSecurityError("No certificate in assertion")
            
            if not self.config.verify_cert_fingerprint(cert_in_assertion):
                raise SAMLSecurityError(
                    "Certificate fingerprint mismatch - possible MitM attack"
                )
        
        # 3. Clock skew validation
        if check_clock_skew:
            self._validate_timestamps(assertion)
        
        # 4. Audience validation
        audience = assertion.get("audience")
        if audience and audience != self.config.sp_entity_id:
            raise SAMLSecurityError(
                f"Invalid audience: expected {self.config.sp_entity_id}, "
                f"got {audience}"
            )
        
        logger.info("SAML assertion validated successfully")
    
    def _validate_timestamps(self, assertion: dict) -> None:
        """Validate NotBefore and NotOnOrAfter timestamps.
        
        Args:
            assertion: SAML assertion
            
        Raises:
            SAMLSecurityError: If timestamp validation fails
        """
        now = datetime.now(timezone.utc)
        max_skew = timedelta(seconds=self.config.max_clock_skew_seconds)
        
        # NotBefore check
        not_before_str = assertion.get("not_before")
        if not_before_str:
            not_before = self._parse_timestamp(not_before_str)
            earliest_valid = not_before - max_skew
            
            if now < earliest_valid:
                skew_seconds = (earliest_valid - now).total_seconds()
                raise SAMLSecurityError(
                    f"Assertion not yet valid (clock skew {skew_seconds:.0f}s exceeds "
                    f"max {self.config.max_clock_skew_seconds}s)"
                )
        
        # NotOnOrAfter check
        not_on_or_after_str = assertion.get("not_on_or_after")
        if not_on_or_after_str:
            not_on_or_after = self._parse_timestamp(not_on_or_after_str)
            latest_valid = not_on_or_after + max_skew
            
            if now >= latest_valid:
                skew_seconds = (now - latest_valid).total_seconds()
                raise SAMLSecurityError(
                    f"Assertion expired (clock skew {skew_seconds:.0f}s exceeds "
                    f"max {self.config.max_clock_skew_seconds}s)"
                )
    
    @staticmethod
    def _parse_timestamp(timestamp_str: str) -> datetime:
        """Parse SAML timestamp.
        
        Args:
            timestamp_str: ISO 8601 timestamp
            
        Returns:
            datetime object
        """
        # Handle various formats
        formats = [
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%dT%H:%M:%S%z",
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(timestamp_str, fmt).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
        
        # Fallback to fromisoformat
        try:
            dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            return dt.astimezone(timezone.utc)
        except Exception:
            raise ValueError(f"Cannot parse timestamp: {timestamp_str}")
    
    def validate_relay_state(self, relay_state: Optional[str]) -> None:
        """Validate RelayState parameter to prevent open redirects.
        
        Args:
            relay_state: RelayState parameter from SAML request
            
        Raises:
            SAMLSecurityError: If RelayState points to external domain
        """
        if not relay_state:
            return  # Empty is ok
        
        # Check if allowed
        if not self.config.is_relay_state_allowed(relay_state):
            raise SAMLSecurityError(
                f"RelayState points to disallowed origin: {relay_state}"
            )
        
        logger.debug(f"RelayState validated: {relay_state}")


__all__ = ["SAMLHandler", "SAMLSecurityError"]

