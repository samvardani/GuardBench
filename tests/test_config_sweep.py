"""Tests for configuration management and environment read sweeps."""

from __future__ import annotations

import os
import pytest
from pathlib import Path

from config import Config, FrozenConfigError, get_config, reset_config


class TestConfig:
    """Test Config class."""
    
    def test_config_creation(self):
        """Test creating config."""
        config = Config()
        
        assert config.host == "0.0.0.0"
        assert config.port == 8001
        assert config.log_level == "info"
    
    def test_config_from_env(self, monkeypatch):
        """Test loading config from environment."""
        monkeypatch.setenv("PORT", "9000")
        monkeypatch.setenv("LOG_LEVEL", "debug")
        monkeypatch.setenv("ENABLE_IMAGE", "1")
        
        config = Config()
        
        assert config.port == 9000
        assert config.log_level == "debug"
        assert config.enable_image is True
    
    def test_config_validation_invalid_port(self):
        """Test config validation rejects invalid port."""
        config = Config()
        config.port = 99999
        
        with pytest.raises(ValueError) as exc_info:
            config._validate()
        
        assert "Invalid port" in str(exc_info.value)
    
    def test_config_validation_invalid_log_level(self):
        """Test config validation rejects invalid log level."""
        config = Config()
        config.log_level = "invalid"
        
        with pytest.raises(ValueError) as exc_info:
            config._validate()
        
        assert "Invalid log level" in str(exc_info.value)


class TestFrozenConfig:
    """Test frozen configuration."""
    
    def test_freeze_prevents_modification(self):
        """Test that freezing prevents modification."""
        config = Config()
        config.freeze()
        
        with pytest.raises(FrozenConfigError) as exc_info:
            config.port = 9999
        
        assert "Cannot modify frozen configuration" in str(exc_info.value)
        assert "port" in str(exc_info.value)
    
    def test_freeze_multiple_attributes(self):
        """Test that all attributes are frozen."""
        config = Config()
        config.freeze()
        
        # Try to modify various attributes
        with pytest.raises(FrozenConfigError):
            config.host = "localhost"
        
        with pytest.raises(FrozenConfigError):
            config.log_level = "error"
        
        with pytest.raises(FrozenConfigError):
            config.enable_image = True
    
    def test_modification_before_freeze(self):
        """Test that modification works before freeze."""
        config = Config()
        
        # Should work (not frozen yet)
        config.port = 9000
        assert config.port == 9000
        
        # Freeze
        config.freeze()
        
        # Should fail now
        with pytest.raises(FrozenConfigError):
            config.port = 9001


class TestConfigDump:
    """Test config dump functionality."""
    
    def test_dump_with_redaction(self, monkeypatch):
        """Test dump redacts sensitive values."""
        monkeypatch.setenv("OIDC_CLIENT_SECRET", "secret123")
        monkeypatch.setenv("SLACK_SIGNING_SECRET", "slack_secret")
        monkeypatch.setenv("METRICS_AUTH_TOKEN", "token123")
        
        config = Config()
        dumped = config.dump(redact=True)
        
        # Sensitive values redacted
        assert dumped["oidc_client_secret"] == "***REDACTED***"
        assert dumped["slack_signing_secret"] == "***REDACTED***"
        assert dumped["metrics_auth_token"] == "***REDACTED***"
        
        # Non-sensitive values visible
        assert dumped["port"] == 8001
        assert dumped["log_level"] == "info"
    
    def test_dump_without_redaction(self, monkeypatch):
        """Test dump without redaction shows all values."""
        monkeypatch.setenv("OIDC_CLIENT_SECRET", "secret123")
        
        config = Config()
        dumped = config.dump(redact=False)
        
        # All values visible
        assert dumped["oidc_client_secret"] == "secret123"
    
    def test_dump_partial_redaction(self, monkeypatch):
        """Test partial redaction of IDs."""
        monkeypatch.setenv("OIDC_CLIENT_ID", "very_long_client_id_12345")
        
        config = Config()
        dumped = config.dump(redact=True)
        
        # Partially redacted (first 8 chars)
        assert dumped["oidc_client_id"] == "very_lon..."


class TestGetConfig:
    """Test global config singleton."""
    
    def teardown_method(self):
        """Reset config after each test."""
        reset_config()
    
    def test_get_config_singleton(self):
        """Test get_config returns singleton."""
        config1 = get_config()
        config2 = get_config()
        
        assert config1 is config2
    
    def test_get_config_frozen(self):
        """Test get_config returns frozen config."""
        config = get_config()
        
        with pytest.raises(FrozenConfigError):
            config.port = 9999
    
    def test_reset_config(self):
        """Test reset_config clears singleton."""
        config1 = get_config()
        
        reset_config()
        
        config2 = get_config()
        
        # Different instances
        assert config1 is not config2


class TestEnvScan:
    """Test environment variable scanning."""
    
    def test_scan_finds_getenv(self, tmp_path):
        """Test scanner finds os.getenv() calls."""
        from scripts.scan_env_reads import scan_file
        
        # Create test file with os.getenv()
        test_file = tmp_path / "test.py"
        test_file.write_text("""
import os

def bad_function():
    api_key = os.getenv("API_KEY")
    return api_key
""")
        
        violations = scan_file(test_file)
        
        assert len(violations) == 1
        line, key = violations[0]
        assert key == "API_KEY"
    
    def test_scan_no_violations(self, tmp_path):
        """Test scanner returns empty for clean code."""
        from scripts.scan_env_reads import scan_file
        
        # Create test file without os.getenv()
        test_file = tmp_path / "test.py"
        test_file.write_text("""
from config import get_config

def good_function():
    config = get_config()
    return config.port
""")
        
        violations = scan_file(test_file)
        
        assert len(violations) == 0
    
    def test_scan_multiple_calls(self, tmp_path):
        """Test scanner finds multiple os.getenv() calls."""
        from scripts.scan_env_reads import scan_file
        
        # Create test file with multiple calls
        test_file = tmp_path / "test.py"
        test_file.write_text("""
import os

api_key = os.getenv("API_KEY")
db_url = os.getenv("DATABASE_URL")
port = os.getenv("PORT", "8000")
""")
        
        violations = scan_file(test_file)
        
        assert len(violations) == 3
        keys = [key for _, key in violations]
        assert "API_KEY" in keys
        assert "DATABASE_URL" in keys
        assert "PORT" in keys


class TestConfigSweep:
    """Integration tests for config sweep."""
    
    def test_no_stray_getenv_in_src(self):
        """Test that src/ has no stray os.getenv() calls."""
        from scripts.scan_env_reads import scan_directory
        
        src_path = Path("src")
        
        if not src_path.exists():
            pytest.skip("src/ directory not found")
        
        # Scan src/ excluding config.py
        violations = scan_directory(
            src_path,
            exclude_patterns=["*/config.py", "*/test_*"]
        )
        
        if violations:
            # Build error message
            msg = "Found stray os.getenv() calls:\n"
            for file_path, file_violations in violations.items():
                msg += f"\n{file_path}:\n"
                for line, key in file_violations:
                    msg += f"  Line {line}: os.getenv({key!r})\n"
            
            pytest.fail(msg)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

