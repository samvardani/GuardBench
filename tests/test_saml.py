"""Tests for SAML authentication."""

from __future__ import annotations

import os
import pytest
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock, MagicMock

from fastapi.testclient import TestClient

from auth.saml import SAMLAuth, SAMLUser, validate_saml_config
from auth.saml_config import SAMLConfig, init_saml_config_table, get_saml_config, set_saml_config


# Sample x509 certificate for testing (fake/self-signed)
TEST_CERT = """MIIC4DCCAcigAwIBAgIUXDKqjv0VJ7IxH4vKwLJVQKV0D8swDQYJKoZIhvcNAQEL
BQAwGTEXMBUGA1UEAwwOdGVzdC1pZHAtY2VydDAeFw0yNDAxMDEwMDAwMDBaFw0y
NTAxMDEwMDAwMDBaMBkxFzAVBgNVBAMMDnRlc3QtaWRwLWNlcnQwggEiMA0GCSqG
SIb3DQEBAQUAA4IBDwAwggEKAoIBAQC5v4v4v4v4v4v4v4v4v4v4v4v4v4v4v4v4
v4v4v4v4v4v4v4v4v4v4v4v4v4v4v4v4v4v4v4v4v4v4v4v4v4v4v4v4v4v4v4v4
v4v4v4v4v4v4v4v4v4v4v4v4v4v4v4v4v4v4v4v4v4v4v4v4v4v4v4v4v4v4v4v4
v4v4v4v4v4v4v4v4v4v4v4v4v4v4v4v4v4v4v4v4v4v4v4v4v4v4v4v4v4v4v4v4
v4v4v4v4v4v4v4v4v4v4v4v4v4v4v4v4v4v4v4v4v4v4v4v4AQAB"""


@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db_path = Path(path)
    
    # Initialize schema
    conn = sqlite3.connect(db_path)
    init_saml_config_table(conn)
    conn.close()
    
    yield db_path
    
    # Cleanup
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def saml_config():
    """Create sample SAML configuration."""
    return SAMLConfig(
        tenant_id="test-tenant",
        sp_entity_id="https://sp.example.com",
        sp_acs_url="https://sp.example.com/auth/saml/acs",
        sp_sls_url="https://sp.example.com/auth/saml/sls/test-tenant",
        idp_entity_id="https://idp.example.com",
        idp_sso_url="https://idp.example.com/sso",
        idp_slo_url="https://idp.example.com/slo",
        idp_x509_cert=TEST_CERT,
        name_id_format="urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
        authn_requests_signed=False,
        want_assertions_signed=True,
        attribute_mapping={"email": "emailAddress", "first_name": "givenName"},
        default_role="viewer",
        enabled=True,
    )


class TestSAMLConfig:
    """Test SAML configuration."""
    
    def test_saml_config_to_dict(self, saml_config):
        """Test converting config to dictionary."""
        data = saml_config.to_dict()
        
        assert data["tenant_id"] == "test-tenant"
        assert data["sp_entity_id"] == "https://sp.example.com"
        assert data["idp_entity_id"] == "https://idp.example.com"
        assert data["default_role"] == "viewer"
        assert data["enabled"] is True
    
    def test_saml_config_to_saml_settings(self, saml_config):
        """Test converting config to python3-saml settings."""
        settings = saml_config.to_saml_settings()
        
        assert settings["sp"]["entityId"] == "https://sp.example.com"
        assert settings["sp"]["assertionConsumerService"]["url"] == "https://sp.example.com/auth/saml/acs"
        assert settings["idp"]["entityId"] == "https://idp.example.com"
        assert settings["idp"]["singleSignOnService"]["url"] == "https://idp.example.com/sso"
        assert settings["security"]["wantAssertionsSigned"] is True
    
    def test_store_and_retrieve_config(self, temp_db, saml_config):
        """Test storing and retrieving SAML config."""
        # Store config
        set_saml_config(saml_config, db_path=temp_db)
        
        # Retrieve config
        retrieved = get_saml_config("test-tenant", db_path=temp_db)
        
        assert retrieved is not None
        assert retrieved.tenant_id == "test-tenant"
        assert retrieved.sp_entity_id == "https://sp.example.com"
        assert retrieved.idp_entity_id == "https://idp.example.com"
        assert retrieved.default_role == "viewer"
    
    def test_get_nonexistent_config(self, temp_db):
        """Test retrieving non-existent config."""
        retrieved = get_saml_config("nonexistent", db_path=temp_db)
        assert retrieved is None
    
    def test_update_config(self, temp_db, saml_config):
        """Test updating existing config."""
        # Store initial config
        set_saml_config(saml_config, db_path=temp_db)
        
        # Update config
        saml_config.default_role = "analyst"
        saml_config.enabled = False
        set_saml_config(saml_config, db_path=temp_db)
        
        # Retrieve updated config
        retrieved = get_saml_config("test-tenant", db_path=temp_db)
        
        # Enabled is False, so should return None
        assert retrieved is None
        
        # Enable and try again
        saml_config.enabled = True
        set_saml_config(saml_config, db_path=temp_db)
        retrieved = get_saml_config("test-tenant", db_path=temp_db)
        
        assert retrieved is not None
        assert retrieved.default_role == "analyst"


class TestSAMLValidation:
    """Test SAML configuration validation."""
    
    def test_valid_config(self, saml_config):
        """Test validating valid configuration."""
        is_valid, errors = validate_saml_config(saml_config)
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_missing_sp_entity_id(self, saml_config):
        """Test validation with missing SP entity ID."""
        saml_config.sp_entity_id = ""
        is_valid, errors = validate_saml_config(saml_config)
        
        assert is_valid is False
        assert any("SP entity ID" in e for e in errors)
    
    def test_invalid_acs_url(self, saml_config):
        """Test validation with invalid ACS URL."""
        saml_config.sp_acs_url = "not-a-url"
        is_valid, errors = validate_saml_config(saml_config)
        
        assert is_valid is False
        assert any("ACS URL" in e for e in errors)
    
    def test_missing_idp_cert(self, saml_config):
        """Test validation with missing IdP certificate."""
        saml_config.idp_x509_cert = ""
        is_valid, errors = validate_saml_config(saml_config)
        
        assert is_valid is False
        assert any("certificate" in e for e in errors)


class TestSAMLAuth:
    """Test SAML authentication."""
    
    def test_saml_auth_initialization(self, saml_config):
        """Test initializing SAML auth handler."""
        saml_auth = SAMLAuth(saml_config)
        
        assert saml_auth.config == saml_config
        assert saml_auth.settings is not None
    
    def test_prepare_request_data(self, saml_config):
        """Test preparing request data."""
        saml_auth = SAMLAuth(saml_config)
        
        request_data = {
            "http_host": "sp.example.com",
            "script_name": "/auth/saml/acs",
            "get_data": {},
            "post_data": {},
            "server_port": 443,
            "https": "on",
        }
        
        prepared = saml_auth.prepare_request_data(request_data)
        
        assert prepared["http_host"] == "sp.example.com"
        assert prepared["server_port"] == 443
        assert prepared["https"] == "on"
    
    @patch("auth.saml.OneLogin_Saml2_Auth")
    def test_get_sso_url(self, mock_auth_class, saml_config):
        """Test getting SSO URL."""
        mock_auth = MagicMock()
        mock_auth.login.return_value = "https://idp.example.com/sso?SAMLRequest=..."
        mock_auth_class.return_value = mock_auth
        
        saml_auth = SAMLAuth(saml_config)
        
        request_data = {
            "http_host": "sp.example.com",
            "script_name": "/auth/saml/login",
            "get_data": {},
            "post_data": {},
            "server_port": 443,
            "https": "on",
        }
        
        sso_url = saml_auth.get_sso_url(request_data, relay_state="tenant:test-tenant")
        
        assert "idp.example.com" in sso_url
        mock_auth.login.assert_called_once()
    
    @patch("auth.saml.OneLogin_Saml2_Auth")
    def test_process_saml_response_success(self, mock_auth_class, saml_config):
        """Test processing successful SAML response."""
        mock_auth = MagicMock()
        mock_auth.process_response.return_value = None
        mock_auth.get_errors.return_value = []
        mock_auth.is_authenticated.return_value = True
        mock_auth.get_nameid.return_value = "user@example.com"
        mock_auth.get_attributes.return_value = {
            "emailAddress": ["user@example.com"],
            "givenName": ["John"],
            "surname": ["Doe"],
        }
        mock_auth.get_session_index.return_value = "session_123"
        mock_auth_class.return_value = mock_auth
        
        saml_auth = SAMLAuth(saml_config)
        
        request_data = {
            "http_host": "sp.example.com",
            "script_name": "/auth/saml/acs",
            "post_data": {"SAMLResponse": "base64_encoded_response"},
            "get_data": {},
            "server_port": 443,
            "https": "on",
        }
        
        success, saml_user, errors = saml_auth.process_saml_response(request_data)
        
        assert success is True
        assert saml_user is not None
        assert saml_user.name_id == "user@example.com"
        assert saml_user.email == "user@example.com"
        assert saml_user.first_name == "John"
        assert saml_user.last_name == "Doe"
        assert len(errors) == 0
    
    @patch("auth.saml.OneLogin_Saml2_Auth")
    def test_process_saml_response_failure(self, mock_auth_class, saml_config):
        """Test processing failed SAML response."""
        mock_auth = MagicMock()
        mock_auth.process_response.return_value = None
        mock_auth.get_errors.return_value = ["Invalid signature"]
        mock_auth.is_authenticated.return_value = False
        mock_auth_class.return_value = mock_auth
        
        saml_auth = SAMLAuth(saml_config)
        
        request_data = {
            "http_host": "sp.example.com",
            "script_name": "/auth/saml/acs",
            "post_data": {"SAMLResponse": "invalid_response"},
            "get_data": {},
            "server_port": 443,
            "https": "on",
        }
        
        success, saml_user, errors = saml_auth.process_saml_response(request_data)
        
        assert success is False
        assert saml_user is None
        assert len(errors) > 0
    
    @patch("auth.saml.OneLogin_Saml2_Settings")
    def test_get_sp_metadata(self, mock_settings_class, saml_config):
        """Test getting SP metadata."""
        mock_settings = MagicMock()
        mock_settings.get_sp_metadata.return_value = '<?xml version="1.0"?><EntityDescriptor>...</EntityDescriptor>'
        mock_settings.validate_metadata.return_value = []
        mock_settings_class.return_value = mock_settings
        
        saml_auth = SAMLAuth(saml_config)
        metadata = saml_auth.get_sp_metadata()
        
        assert "EntityDescriptor" in metadata
        mock_settings.get_sp_metadata.assert_called_once()


class TestSAMLUser:
    """Test SAML user dataclass."""
    
    def test_saml_user_to_dict(self):
        """Test converting SAMLUser to dictionary."""
        user = SAMLUser(
            name_id="user@example.com",
            email="user@example.com",
            first_name="John",
            last_name="Doe",
            display_name="John Doe",
            attributes={"role": ["admin"]},
            session_index="session_123",
        )
        
        data = user.to_dict()
        
        assert data["name_id"] == "user@example.com"
        assert data["email"] == "user@example.com"
        assert data["first_name"] == "John"
        assert data["last_name"] == "Doe"
        assert data["session_index"] == "session_123"


class TestSAMLRoutes:
    """Test SAML authentication routes."""
    
    @pytest.fixture
    def mock_db(self, temp_db):
        """Mock database with SAML config."""
        config = SAMLConfig(
            tenant_id="test-tenant",
            sp_entity_id="https://sp.example.com",
            sp_acs_url="https://sp.example.com/auth/saml/acs",
            sp_sls_url="https://sp.example.com/auth/saml/sls/test-tenant",
            idp_entity_id="https://idp.example.com",
            idp_sso_url="https://idp.example.com/sso",
            idp_slo_url="https://idp.example.com/slo",
            idp_x509_cert=TEST_CERT,
            default_role="viewer",
            enabled=True,
        )
        set_saml_config(config, db_path=temp_db)
        
        # Patch get_saml_config to use temp_db
        with patch("auth.saml_routes.get_saml_config") as mock:
            mock.return_value = config
            yield mock
    
    def test_saml_login_redirect(self, mock_db):
        """Test SAML login initiates redirect to IdP."""
        from service.api import app
        client = TestClient(app)
        
        with patch("auth.saml.OneLogin_Saml2_Auth") as mock_auth_class:
            mock_auth = MagicMock()
            mock_auth.login.return_value = "https://idp.example.com/sso?SAMLRequest=..."
            mock_auth_class.return_value = mock_auth
            
            response = client.get("/auth/saml/login/test-tenant", follow_redirects=False)
            
            assert response.status_code == 307  # Redirect
            assert "idp.example.com" in response.headers["location"]
    
    def test_saml_login_no_config(self):
        """Test SAML login with no configuration."""
        from service.api import app
        client = TestClient(app)
        
        with patch("auth.saml_routes.get_saml_config") as mock:
            mock.return_value = None
            
            response = client.get("/auth/saml/login/nonexistent")
            
            assert response.status_code == 404
            assert "not configured" in response.json()["detail"]
    
    def test_saml_metadata_endpoint(self, mock_db):
        """Test SP metadata endpoint."""
        from service.api import app
        client = TestClient(app)
        
        with patch("auth.saml.OneLogin_Saml2_Settings") as mock_settings_class:
            mock_settings = MagicMock()
            mock_settings.get_sp_metadata.return_value = '<?xml version="1.0"?><EntityDescriptor>...</EntityDescriptor>'
            mock_settings.validate_metadata.return_value = []
            mock_settings_class.return_value = mock_settings
            
            response = client.get("/auth/saml/metadata/test-tenant")
            
            assert response.status_code == 200
            assert "application/xml" in response.headers["content-type"]
            assert "EntityDescriptor" in response.text


class TestAttributeMapping:
    """Test SAML attribute mapping."""
    
    def test_extract_attribute_with_mapping(self, saml_config):
        """Test extracting attribute with custom mapping."""
        saml_auth = SAMLAuth(saml_config)
        
        attributes = {
            "emailAddress": ["user@example.com"],
            "givenName": ["John"],
        }
        
        # email maps to emailAddress in config
        email = saml_auth._extract_attribute(attributes, "email", ["email", "mail"])
        assert email == "user@example.com"
        
        # first_name maps to givenName in config
        first_name = saml_auth._extract_attribute(attributes, "first_name", ["firstName"])
        assert first_name == "John"
    
    def test_extract_attribute_without_mapping(self, saml_config):
        """Test extracting attribute without custom mapping."""
        saml_config.attribute_mapping = {}
        saml_auth = SAMLAuth(saml_config)
        
        attributes = {
            "email": ["user@example.com"],
            "firstName": ["John"],
        }
        
        # Falls back to standard keys
        email = saml_auth._extract_attribute(attributes, "email", ["email", "mail"])
        assert email == "user@example.com"
        
        first_name = saml_auth._extract_attribute(attributes, "first_name", ["firstName", "givenName"])
        assert first_name == "John"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

