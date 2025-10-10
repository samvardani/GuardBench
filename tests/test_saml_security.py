"""Tests for SAML security hardening."""

from __future__ import annotations

import base64
import hashlib
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from auth import SAMLHandler, SAMLSecurityError, SAMLConfig


# Sample certificate (for testing)
SAMPLE_CERT_PEM = """-----BEGIN CERTIFICATE-----
MIIDXTCCAkWgAwIBAgIJAKL0UG+mRKSzMA0GCSqGSIb3DQEBCwUAMEUxCzAJBgNV
BAYTAlVTMRMwEQYDVQQIDApTb21lLVN0YXRlMSEwHwYDVQQKDBhJbnRlcm5ldCBX
aWRnaXRzIFB0eSBMdGQwHhcNMjQwMTAxMDAwMDAwWhcNMjUwMTAxMDAwMDAwWjBF
MQswCQYDVQQGEwJVUzETMBEGA1UECAwKU29tZS1TdGF0ZTEhMB8GA1UECgwYSW50
ZXJuZXQgV2lkZ2l0cyBQdHkgTHRkMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIB
CgKCAQEAw==
-----END CERTIFICATE-----"""


class TestSAMLConfig:
    """Test SAML configuration."""
    
    def test_config_creation(self):
        """Test creating SAML config."""
        config = SAMLConfig(
            sp_entity_id="https://sp.example.com",
            idp_entity_id="https://idp.example.com",
            acs_url="https://sp.example.com/saml/acs",
            idp_sso_url="https://idp.example.com/sso",
            idp_cert=SAMPLE_CERT_PEM
        )
        
        assert config.sp_entity_id == "https://sp.example.com"
        assert config.require_signed_assertion is True  # Secure by default
        assert config.max_clock_skew_seconds == 180  # 3 minutes
    
    def test_compute_cert_fingerprint(self):
        """Test computing certificate fingerprint."""
        fingerprint = SAMLConfig.compute_cert_fingerprint(SAMPLE_CERT_PEM)
        
        assert isinstance(fingerprint, str)
        assert len(fingerprint) == 64  # SHA-256
    
    def test_verify_cert_fingerprint_match(self):
        """Test fingerprint verification (match)."""
        config = SAMLConfig(
            sp_entity_id="https://sp.example.com",
            idp_entity_id="https://idp.example.com",
            acs_url="https://sp.example.com/saml/acs",
            idp_sso_url="https://idp.example.com/sso",
            idp_cert=SAMPLE_CERT_PEM
        )
        
        # Should match (same cert)
        assert config.verify_cert_fingerprint(SAMPLE_CERT_PEM) is True
    
    def test_verify_cert_fingerprint_mismatch(self):
        """Test fingerprint verification (mismatch)."""
        different_cert = SAMPLE_CERT_PEM.replace("w==", "x==")
        
        config = SAMLConfig(
            sp_entity_id="https://sp.example.com",
            idp_entity_id="https://idp.example.com",
            acs_url="https://sp.example.com/saml/acs",
            idp_sso_url="https://idp.example.com/sso",
            idp_cert=SAMPLE_CERT_PEM
        )
        
        # Should NOT match (different cert)
        assert config.verify_cert_fingerprint(different_cert) is False
    
    def test_relay_state_same_origin(self):
        """Test RelayState same-origin allowed."""
        config = SAMLConfig(
            sp_entity_id="https://sp.example.com",
            idp_entity_id="https://idp.example.com",
            acs_url="https://sp.example.com/saml/acs",
            idp_sso_url="https://idp.example.com/sso",
            idp_cert="cert"
        )
        
        # Same origin
        assert config.is_relay_state_allowed("https://sp.example.com/dashboard") is True
        
        # Relative URL
        assert config.is_relay_state_allowed("/dashboard") is True
        
        # Empty
        assert config.is_relay_state_allowed(None) is True
    
    def test_relay_state_external_domain(self):
        """Test RelayState external domain blocked."""
        config = SAMLConfig(
            sp_entity_id="https://sp.example.com",
            idp_entity_id="https://idp.example.com",
            acs_url="https://sp.example.com/saml/acs",
            idp_sso_url="https://idp.example.com/sso",
            idp_cert="cert"
        )
        
        # External domain
        assert config.is_relay_state_allowed("https://evil.com/phishing") is False


class TestSAMLHandler:
    """Test SAML handler security validation."""
    
    @pytest.fixture
    def handler(self):
        """Create SAML handler."""
        config = SAMLConfig(
            sp_entity_id="https://sp.example.com",
            idp_entity_id="https://idp.example.com",
            acs_url="https://sp.example.com/saml/acs",
            idp_sso_url="https://idp.example.com/sso",
            idp_cert=SAMPLE_CERT_PEM,
            max_clock_skew_seconds=180
        )
        
        return SAMLHandler(config=config)
    
    def test_handler_creation(self, handler):
        """Test creating handler."""
        assert handler is not None
        assert handler.config.require_signed_assertion is True
    
    def test_validate_assertion_unsigned_rejected(self, handler):
        """Test unsigned assertion rejected."""
        assertion = {
            "signed": False,
            "signature_valid": False
        }
        
        with pytest.raises(SAMLSecurityError) as exc_info:
            handler.validate_assertion(assertion)
        
        assert "must be signed" in str(exc_info.value)
    
    def test_validate_assertion_invalid_signature_rejected(self, handler):
        """Test invalid signature rejected."""
        assertion = {
            "signed": True,
            "signature_valid": False
        }
        
        with pytest.raises(SAMLSecurityError) as exc_info:
            handler.validate_assertion(assertion)
        
        assert "Invalid assertion signature" in str(exc_info.value)
    
    def test_validate_assertion_wrong_fingerprint_rejected(self, handler):
        """Test wrong certificate fingerprint rejected."""
        different_cert = SAMPLE_CERT_PEM.replace("w==", "x==")
        
        assertion = {
            "signed": True,
            "signature_valid": True,
            "certificate": different_cert
        }
        
        with pytest.raises(SAMLSecurityError) as exc_info:
            handler.validate_assertion(assertion)
        
        assert "fingerprint mismatch" in str(exc_info.value).lower()
    
    def test_validate_assertion_clock_skew_future(self, handler):
        """Test clock skew rejection (NotBefore too far in future)."""
        # NotBefore 5 minutes in future (exceeds 3 min max)
        future_time = datetime.now(timezone.utc) + timedelta(minutes=5)
        
        assertion = {
            "signed": True,
            "signature_valid": True,
            "certificate": SAMPLE_CERT_PEM,
            "not_before": future_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        }
        
        with pytest.raises(SAMLSecurityError) as exc_info:
            handler.validate_assertion(assertion)
        
        assert "not yet valid" in str(exc_info.value).lower()
    
    def test_validate_assertion_clock_skew_expired(self, handler):
        """Test clock skew rejection (NotOnOrAfter too far in past)."""
        # Expired 5 minutes ago (exceeds 3 min max)
        past_time = datetime.now(timezone.utc) - timedelta(minutes=5)
        
        assertion = {
            "signed": True,
            "signature_valid": True,
            "certificate": SAMPLE_CERT_PEM,
            "not_on_or_after": past_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        }
        
        with pytest.raises(SAMLSecurityError) as exc_info:
            handler.validate_assertion(assertion)
        
        assert "expired" in str(exc_info.value).lower()
    
    def test_validate_assertion_clock_skew_within_limit(self, handler):
        """Test clock skew within limit is accepted."""
        # 2 minutes in future (within 3 min max)
        future_time = datetime.now(timezone.utc) + timedelta(minutes=2)
        expiry_time = datetime.now(timezone.utc) + timedelta(minutes=10)
        
        assertion = {
            "signed": True,
            "signature_valid": True,
            "certificate": SAMPLE_CERT_PEM,
            "not_before": future_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "not_on_or_after": expiry_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "audience": "https://sp.example.com"
        }
        
        # Should not raise
        handler.validate_assertion(assertion)
    
    def test_validate_relay_state_external_blocked(self, handler):
        """Test RelayState to external domain blocked."""
        relay_state = "https://evil.com/phishing"
        
        with pytest.raises(SAMLSecurityError) as exc_info:
            handler.validate_relay_state(relay_state)
        
        assert "disallowed origin" in str(exc_info.value).lower()
    
    def test_validate_relay_state_same_origin_allowed(self, handler):
        """Test RelayState to same origin allowed."""
        relay_state = "https://sp.example.com/dashboard"
        
        # Should not raise
        handler.validate_relay_state(relay_state)
    
    def test_validate_assertion_invalid_audience(self, handler):
        """Test invalid audience rejected."""
        assertion = {
            "signed": True,
            "signature_valid": True,
            "certificate": SAMPLE_CERT_PEM,
            "audience": "https://wrong-sp.example.com"
        }
        
        with pytest.raises(SAMLSecurityError) as exc_info:
            handler.validate_assertion(assertion, check_clock_skew=False)
        
        assert "Invalid audience" in str(exc_info.value)


class TestSAMLSecurityDefaults:
    """Test that security defaults are strict."""
    
    def test_defaults_are_secure(self):
        """Test that default configuration is secure."""
        config = SAMLConfig(
            sp_entity_id="https://sp.example.com",
            idp_entity_id="https://idp.example.com",
            acs_url="https://sp.example.com/saml/acs",
            idp_sso_url="https://idp.example.com/sso",
            idp_cert="cert"
        )
        
        # Strict by default
        assert config.require_signed_assertion is True
        assert config.require_signed_response is True
        assert config.allow_unsigned is False
        assert config.max_clock_skew_seconds == 180


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

