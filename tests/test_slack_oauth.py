"""Tests for Slack OAuth integration with encryption."""

from __future__ import annotations

import os
import pytest
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from security import CryptoBox, TokenRedactor, redact_tokens
from integrations.slack_oauth import SlackOAuthClient, get_slack_oauth_client
from db.slack_installations import (
    init_slack_tables,
    store_installation,
    get_installation,
    get_decrypted_token
)


class TestCryptoBox:
    """Test CryptoBox encryption."""
    
    def test_crypto_box_creation(self):
        """Test creating CryptoBox."""
        from cryptography.fernet import Fernet
        
        key = Fernet.generate_key().decode()
        crypto_box = CryptoBox(key=key)
        
        assert crypto_box is not None
        assert crypto_box.version == "v1"
    
    def test_encrypt_decrypt_roundtrip(self):
        """Test encrypt and decrypt roundtrip."""
        from cryptography.fernet import Fernet
        
        key = Fernet.generate_key().decode()
        crypto_box = CryptoBox(key=key)
        
        plaintext = "xoxb-123456789-abcdefghijk"
        
        # Encrypt
        ciphertext = crypto_box.encrypt(plaintext)
        
        assert ciphertext != plaintext
        assert ":" in ciphertext  # Has version prefix
        
        # Decrypt
        decrypted = crypto_box.decrypt(ciphertext)
        
        assert decrypted == plaintext
    
    def test_encrypt_empty_string(self):
        """Test encrypting empty string."""
        from cryptography.fernet import Fernet
        
        key = Fernet.generate_key().decode()
        crypto_box = CryptoBox(key=key)
        
        encrypted = crypto_box.encrypt("")
        
        assert encrypted == ""
    
    def test_key_rotation(self):
        """Test key rotation."""
        from cryptography.fernet import Fernet
        
        # Old key
        old_key = Fernet.generate_key().decode()
        crypto_box_old = CryptoBox(key=old_key)
        
        plaintext = "secret-token"
        
        # Encrypt with old key
        old_ciphertext = crypto_box_old.encrypt(plaintext)
        
        # New key
        new_key = f"v2:{Fernet.generate_key().decode()}"
        
        # Rotate
        new_ciphertext = crypto_box_old.rotate_key(old_ciphertext, new_key)
        
        # Decrypt with new key
        crypto_box_new = CryptoBox(key=new_key)
        decrypted = crypto_box_new.decrypt(new_ciphertext)
        
        assert decrypted == plaintext
        assert new_ciphertext.startswith("v2:")


class TestTokenRedactor:
    """Test token redaction."""
    
    def test_redact_slack_token(self):
        """Test redacting Slack token."""
        text = "Token: xoxb-123456789-abcdefghijk-XYZ"
        
        redacted = redact_tokens(text)
        
        assert "xoxb-123456789" not in redacted
        assert "xoxb-****" in redacted
    
    def test_redact_bearer_token(self):
        """Test redacting Bearer token."""
        text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        
        redacted = redact_tokens(text)
        
        assert "eyJhbGci" not in redacted
        assert "Bearer ****" in redacted
    
    def test_redact_json_tokens(self):
        """Test redacting tokens in JSON."""
        text = '{"access_token": "xoxb-very-long-secret-token-here"}'
        
        redacted = redact_tokens(text)
        
        assert "very-long-secret" not in redacted
        # Token is redacted (pattern matches xoxb-)
        assert "xoxb-****" in redacted or '"access_token": "****"' in redacted
    
    def test_redact_dict(self):
        """Test redacting dictionary."""
        data = {
            "access_token": "xoxb-123456789-abcdefghijk",
            "name": "test"
        }
        
        redacted = TokenRedactor.redact_dict(data)
        
        assert redacted["access_token"] == "xoxb****hijk"
        assert redacted["name"] == "test"


class TestSlackInstallations:
    """Test Slack installation database operations."""
    
    @pytest.fixture
    def temp_db(self):
        """Create temporary database."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)
        
        # Initialize
        conn = sqlite3.connect(db_path)
        init_slack_tables(conn)
        conn.close()
        
        yield db_path
        
        # Cleanup
        db_path.unlink(missing_ok=True)
    
    def test_store_installation(self, temp_db):
        """Test storing Slack installation."""
        from cryptography.fernet import Fernet
        
        # Encrypt token
        key = Fernet.generate_key().decode()
        crypto_box = CryptoBox(key=key)
        encrypted_token = crypto_box.encrypt("xoxb-test-token")
        
        # Store
        store_installation(
            team_id="T123456",
            team_name="Test Workspace",
            encrypted_access_token=encrypted_token,
            db_path=temp_db
        )
        
        # Verify
        installation = get_installation("T123456", db_path=temp_db)
        
        assert installation is not None
        assert installation["team_id"] == "T123456"
        assert installation["team_name"] == "Test Workspace"
        assert installation["encrypted_access_token"] == encrypted_token
    
    def test_get_installation_not_found(self, temp_db):
        """Test getting non-existent installation."""
        installation = get_installation("T999999", db_path=temp_db)
        
        assert installation is None
    
    def test_get_decrypted_token(self, temp_db):
        """Test getting decrypted token."""
        from cryptography.fernet import Fernet
        from security import get_crypto_box
        
        # Set up encryption key
        key = Fernet.generate_key().decode()
        os.environ["SLACK_TOKEN_KEY"] = key
        
        # Reset global
        import security.crypto
        security.crypto._global_crypto_box = None
        
        crypto_box = get_crypto_box()
        
        # Store encrypted token
        plaintext_token = "xoxb-test-token-12345"
        encrypted_token = crypto_box.encrypt(plaintext_token)
        
        store_installation(
            team_id="T123456",
            team_name="Test",
            encrypted_access_token=encrypted_token,
            db_path=temp_db
        )
        
        # Get decrypted
        decrypted = get_decrypted_token("T123456", db_path=temp_db)
        
        assert decrypted == plaintext_token


class TestSlackOAuthClient:
    """Test Slack OAuth client."""
    
    def test_client_creation(self):
        """Test creating OAuth client."""
        client = SlackOAuthClient(
            client_id="test-id",
            client_secret="test-secret"
        )
        
        assert client.client_id == "test-id"
        assert client.client_secret == "test-secret"
    
    def test_get_authorization_url(self):
        """Test generating authorization URL."""
        client = SlackOAuthClient(
            client_id="test-id",
            client_secret="test-secret"
        )
        
        url = client.get_authorization_url(state="test-state")
        
        assert "slack.com/oauth/v2/authorize" in url
        assert "client_id=test-id" in url
        assert "state=test-state" in url
    
    @pytest.mark.asyncio
    async def test_exchange_code_success(self):
        """Test exchanging code for token (mocked)."""
        with patch("integrations.slack_oauth.httpx.AsyncClient") as mock_client_class:
            # Mock response
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "ok": True,
                "access_token": "xoxb-test-token",
                "team": {"id": "T123", "name": "Test Team"}
            }
            
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client
            
            client = SlackOAuthClient(
                client_id="test-id",
                client_secret="test-secret"
            )
            
            # Exchange code
            result = await client.exchange_code("test-code")
            
            assert result["ok"] is True
            assert result["access_token"] == "xoxb-test-token"
    
    @pytest.mark.asyncio
    async def test_exchange_code_failure(self):
        """Test exchange code failure."""
        with patch("integrations.slack_oauth.httpx.AsyncClient") as mock_client_class:
            # Mock error response
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "ok": False,
                "error": "invalid_code"
            }
            
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client
            
            client = SlackOAuthClient(
                client_id="test-id",
                client_secret="test-secret"
            )
            
            # Should raise
            with pytest.raises(Exception):
                await client.exchange_code("bad-code")
    
    def test_encrypt_decrypt_token(self):
        """Test token encryption and decryption."""
        from cryptography.fernet import Fernet
        
        key = Fernet.generate_key().decode()
        client = SlackOAuthClient(
            client_id="test-id",
            client_secret="test-secret"
        )
        client.crypto_box = CryptoBox(key=key)
        
        token = "xoxb-123456789-test-token"
        
        # Encrypt
        encrypted = client.encrypt_token(token)
        
        assert encrypted != token
        assert "v1:" in encrypted
        
        # Decrypt
        decrypted = client.decrypt_token(encrypted)
        
        assert decrypted == token


class TestOAuthIntegration:
    """Integration tests for OAuth flow."""
    
    @pytest.fixture
    def temp_db(self):
        """Create temporary database."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)
        
        conn = sqlite3.connect(db_path)
        init_slack_tables(conn)
        conn.close()
        
        yield db_path
        
        db_path.unlink(missing_ok=True)
    
    @pytest.mark.asyncio
    async def test_full_oauth_flow(self, temp_db):
        """Test full OAuth flow with encryption."""
        from cryptography.fernet import Fernet
        
        # Set up encryption key
        key = Fernet.generate_key().decode()
        os.environ["SLACK_TOKEN_KEY"] = key
        
        # Reset global
        import security.crypto
        security.crypto._global_crypto_box = None
        
        with patch("integrations.slack_oauth.httpx.AsyncClient") as mock_client_class:
            # Mock OAuth exchange
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "ok": True,
                "access_token": "xoxb-real-token-12345",
                "team": {"id": "T123", "name": "Test Team"}
            }
            
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client
            
            client = SlackOAuthClient(
                client_id="test-id",
                client_secret="test-secret"
            )
            
            # Exchange code
            oauth_response = await client.exchange_code("auth-code")
            
            # Encrypt token
            encrypted_token = client.encrypt_token(oauth_response["access_token"])
            
            # Store
            store_installation(
                team_id="T123",
                team_name="Test Team",
                encrypted_access_token=encrypted_token,
                db_path=temp_db
            )
            
            # Retrieve and decrypt
            decrypted_token = get_decrypted_token("T123", db_path=temp_db)
            
            assert decrypted_token == "xoxb-real-token-12345"


class TestTokenRedaction:
    """Test token redaction in logs."""
    
    def test_no_tokens_in_logs(self, caplog):
        """Test that tokens are redacted from logs."""
        import logging
        from security.redaction import TokenRedactionFilter
        
        # Install filter
        test_logger = logging.getLogger("test_slack")
        test_logger.setLevel(logging.INFO)
        test_logger.addFilter(TokenRedactionFilter())
        
        # Log with token
        test_logger.info("Received token: xoxb-123456789-abcdefghijk")
        
        # Check log output
        assert "xoxb-123456789-abcdefghijk" not in caplog.text
        assert "xoxb-****" in caplog.text
    
    def test_slack_token_patterns(self):
        """Test Slack token pattern matching."""
        tokens = [
            "xoxb-123-456",
            "xoxp-789-012",
            "xoxa-345-678",
        ]
        
        for token in tokens:
            text = f"Token: {token}"
            redacted = redact_tokens(text)
            
            assert token not in redacted
            assert "****" in redacted


class TestFlakeGuard:
    """Tests for deterministic behavior (flake prevention)."""
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("iteration", range(20))
    async def test_oauth_exchange_20x(self, iteration):
        """Run OAuth exchange 20 times - should never fail."""
        with patch("integrations.slack_oauth.httpx.AsyncClient") as mock_client_class:
            # Deterministic mock response
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "ok": True,
                "access_token": f"xoxb-token-{iteration}",
                "team": {"id": f"T{iteration}", "name": f"Team {iteration}"}
            }
            
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client
            
            client = SlackOAuthClient(
                client_id="test-id",
                client_secret="test-secret"
            )
            
            # Exchange - should always succeed
            result = await client.exchange_code(f"code-{iteration}")
            
            assert result["ok"] is True
            assert result["access_token"] == f"xoxb-token-{iteration}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

