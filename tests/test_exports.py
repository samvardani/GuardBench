"""Tests for export streaming and secret redaction."""

from __future__ import annotations

import json
import pytest

from exports.redaction import SecretRedactor, redact_secrets
from exports.report_builder import ReportBuilder, StreamingReportBuilder
from exports.routes import add_security_headers

from fastapi import Response
from fastapi.testclient import TestClient
from fastapi import FastAPI


class TestSecretRedactor:
    """Test deep secret redaction."""
    
    def test_redactor_creation(self):
        """Test creating redactor."""
        redactor = SecretRedactor()
        
        assert redactor is not None
        assert len(redactor.compiled_patterns) > 0
    
    def test_is_sensitive_key(self):
        """Test sensitive key detection."""
        redactor = SecretRedactor()
        
        # Sensitive keys
        assert redactor.is_sensitive_key("api_key") is True
        assert redactor.is_sensitive_key("SECRET") is True  # Case insensitive
        assert redactor.is_sensitive_key("password") is True
        assert redactor.is_sensitive_key("client_secret") is True
        
        # Non-sensitive keys
        assert redactor.is_sensitive_key("username") is False
        assert redactor.is_sensitive_key("email") is False
        assert redactor.is_sensitive_key("score") is False
    
    def test_redact_flat_dict(self):
        """Test redacting flat dictionary."""
        redactor = SecretRedactor()
        
        data = {
            "username": "alice",
            "password": "secret123",
            "email": "alice@example.com",
            "api_key": "key_abc"
        }
        
        redacted = redactor.redact(data)
        
        # Non-sensitive preserved
        assert redacted["username"] == "alice"
        assert redacted["email"] == "alice@example.com"
        
        # Sensitive redacted
        assert redacted["password"] == "***REDACTED***"
        assert redacted["api_key"] == "***REDACTED***"
    
    def test_redact_nested_dict(self):
        """Test redacting nested dictionary."""
        redactor = SecretRedactor()
        
        data = {
            "user": {
                "name": "alice",
                "password": "secret123"
            },
            "config": {
                "database_url": "postgres://localhost",
                "api_token": "token_xyz"
            }
        }
        
        redacted = redactor.redact(data)
        
        # Nested non-sensitive preserved
        assert redacted["user"]["name"] == "alice"
        assert redacted["config"]["database_url"] == "postgres://localhost"
        
        # Nested sensitive redacted
        assert redacted["user"]["password"] == "***REDACTED***"
        assert redacted["config"]["api_token"] == "***REDACTED***"
    
    def test_redact_list_of_dicts(self):
        """Test redacting list of dictionaries."""
        redactor = SecretRedactor()
        
        data = {
            "users": [
                {"name": "alice", "password": "pass1"},
                {"name": "bob", "secret": "secret2"}
            ]
        }
        
        redacted = redactor.redact(data)
        
        # Names preserved
        assert redacted["users"][0]["name"] == "alice"
        assert redacted["users"][1]["name"] == "bob"
        
        # Secrets redacted
        assert redacted["users"][0]["password"] == "***REDACTED***"
        assert redacted["users"][1]["secret"] == "***REDACTED***"
    
    def test_redact_deeply_nested(self):
        """Test redacting deeply nested structures."""
        redactor = SecretRedactor()
        
        data = {
            "level1": {
                "level2": {
                    "level3": {
                        "api_key": "deep_secret"
                    }
                }
            }
        }
        
        redacted = redactor.redact(data)
        
        # Deep secret redacted
        assert redacted["level1"]["level2"]["level3"]["api_key"] == "***REDACTED***"
    
    def test_redact_mixed_structures(self):
        """Test redacting mixed data structures."""
        redactor = SecretRedactor()
        
        data = {
            "metadata": {
                "version": "1.0",
                "auth_token": "token123"
            },
            "items": [
                {"id": 1, "password": "pass1"},
                {"id": 2, "key": "value"}
            ],
            "nested": {
                "array": [
                    {"secret": "s1"},
                    {"secret": "s2"}
                ]
            }
        }
        
        redacted = redactor.redact(data)
        
        # Verify structure preserved
        assert redacted["metadata"]["version"] == "1.0"
        assert redacted["items"][0]["id"] == 1
        assert redacted["items"][1]["id"] == 2
        
        # Verify secrets redacted
        assert redacted["metadata"]["auth_token"] == "***REDACTED***"
        assert redacted["items"][0]["password"] == "***REDACTED***"
        assert redacted["nested"]["array"][0]["secret"] == "***REDACTED***"
        assert redacted["nested"]["array"][1]["secret"] == "***REDACTED***"
    
    def test_get_redacted_keys(self):
        """Test tracking redacted keys."""
        redactor = SecretRedactor()
        
        data = {
            "password": "pass1",
            "api_key": "key1",
            "username": "alice",
            "secret": "secret1"
        }
        
        redactor.redact(data)
        
        redacted_keys = redactor.get_redacted_keys()
        
        assert "password" in redacted_keys
        assert "api_key" in redacted_keys
        assert "secret" in redacted_keys
        assert "username" not in redacted_keys


class TestRedactSecretsFunction:
    """Test convenience function."""
    
    def test_redact_secrets_basic(self):
        """Test basic redaction."""
        data = {
            "name": "test",
            "password": "secret"
        }
        
        redacted = redact_secrets(data)
        
        assert redacted["name"] == "test"
        assert redacted["password"] == "***REDACTED***"
    
    def test_redact_secrets_custom_patterns(self):
        """Test custom patterns."""
        data = {
            "username": "alice",
            "custom_field": "sensitive"
        }
        
        # Only redact "custom_field"
        redacted = redact_secrets(data, patterns=["custom"])
        
        assert redacted["username"] == "alice"
        assert redacted["custom_field"] == "***REDACTED***"


class TestReportBuilder:
    """Test report building."""
    
    def test_builder_creation(self):
        """Test creating builder."""
        data = {"test": "value"}
        builder = ReportBuilder(data)
        
        assert builder.data == data
        assert builder.redact is True
    
    def test_build_json(self):
        """Test building JSON."""
        data = {
            "name": "test",
            "password": "secret"
        }
        
        builder = ReportBuilder(data, redact=True)
        json_str = builder.build_json()
        
        # Parse to verify
        parsed = json.loads(json_str)
        assert parsed["name"] == "test"
        assert parsed["password"] == "***REDACTED***"
    
    def test_build_json_no_redact(self):
        """Test building JSON without redaction."""
        data = {
            "name": "test",
            "password": "secret"
        }
        
        builder = ReportBuilder(data, redact=False)
        json_str = builder.build_json()
        
        parsed = json.loads(json_str)
        assert parsed["password"] == "secret"  # Not redacted
    
    def test_build_markdown(self):
        """Test building Markdown."""
        data = {
            "metadata": {"version": "1.0"},
            "results": ["test1", "test2"]
        }
        
        builder = ReportBuilder(data, redact=False)
        md_str = builder.build_markdown()
        
        assert "# Safety Evaluation Report" in md_str
        assert "## Metadata" in md_str
        assert "version" in md_str
    
    def test_estimate_size(self):
        """Test size estimation."""
        data = {"key": "value" * 1000}  # Somewhat large
        
        builder = ReportBuilder(data)
        size = builder.estimate_size()
        
        assert size > 0
    
    def test_compute_etag(self):
        """Test ETag computation."""
        data = {"key": "value"}
        
        builder = ReportBuilder(data)
        etag = builder.compute_etag()
        
        assert len(etag) == 16  # 16 character hash


class TestStreamingReportBuilder:
    """Test streaming report builder."""
    
    def test_stream_json(self):
        """Test JSON streaming."""
        data = {
            "test": "value",
            "password": "secret"
        }
        
        builder = StreamingReportBuilder(data, redact=True)
        
        # Collect chunks
        chunks = list(builder.stream_json())
        
        assert len(chunks) > 0
        
        # Reconstruct JSON
        full_json = "".join(chunks)
        parsed = json.loads(full_json)
        
        assert parsed["test"] == "value"
        assert parsed["password"] == "***REDACTED***"
    
    def test_stream_markdown(self):
        """Test Markdown streaming."""
        data = {
            "metadata": {"version": "1.0"}
        }
        
        builder = StreamingReportBuilder(data, redact=False)
        
        # Collect chunks
        chunks = list(builder.stream_markdown())
        
        assert len(chunks) > 0
        
        # Verify content
        full_md = "".join(chunks)
        assert "# Safety Evaluation Report" in full_md
    
    def test_stream_memory_bounded(self):
        """Test that streaming is memory bounded."""
        # Create large data
        data = {
            "items": [{"id": i, "data": "x" * 100} for i in range(1000)]
        }
        
        builder = StreamingReportBuilder(data)
        
        # Stream should yield chunks, not load all at once
        chunks = list(builder.stream_json())
        
        # Multiple chunks
        assert len(chunks) > 1


class TestSecurityHeaders:
    """Test security header addition."""
    
    def test_add_security_headers_basic(self):
        """Test adding basic security headers."""
        response = Response(content="test")
        
        add_security_headers(response)
        
        # Cache control
        assert "no-store" in response.headers["Cache-Control"]
        assert "no-cache" in response.headers["Cache-Control"]
        
        # Download protection
        assert response.headers["X-Download-Options"] == "noopen"
        assert response.headers["X-Content-Type-Options"] == "nosniff"
    
    def test_add_security_headers_with_etag(self):
        """Test adding ETag."""
        response = Response(content="test")
        
        add_security_headers(response, etag="abc123")
        
        assert response.headers["ETag"] == '"abc123"'


class TestExportRoutes:
    """Test export API routes."""
    
    @pytest.fixture
    def app(self):
        """Create test app."""
        from exports.routes import router
        
        app = FastAPI()
        app.include_router(router)
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)
    
    def test_export_json_endpoint(self, client):
        """Test JSON export endpoint."""
        response = client.get("/exports/report.json?sample_data=true")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        
        # Verify security headers
        assert "no-store" in response.headers["Cache-Control"]
        assert response.headers["X-Download-Options"] == "noopen"
        
        # Verify redaction
        data = response.json()
        assert data["metadata"]["api_key"] == "***REDACTED***"
        assert data["config"]["slack_client_secret"] == "***REDACTED***"
    
    def test_export_json_no_redact(self, client):
        """Test JSON export without redaction."""
        response = client.get("/exports/report.json?sample_data=true&redact=false")
        
        data = response.json()
        
        # Secrets NOT redacted
        assert data["metadata"]["api_key"] != "***REDACTED***"
    
    def test_export_markdown_endpoint(self, client):
        """Test Markdown export endpoint."""
        response = client.get("/exports/report.md?sample_data=true")
        
        assert response.status_code == 200
        assert "text/markdown" in response.headers["content-type"]
        
        # Verify content
        content = response.text
        assert "# Safety Evaluation Report" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

