"""Tests for federated learning telemetry."""

from __future__ import annotations

import os
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from collections import deque

from telemetry import FederatedTelemetry, TelemetryPayload, get_telemetry_client
from telemetry.privacy import (
    hash_text,
    anonymize_tenant_id,
    add_laplace_noise,
    add_differential_privacy,
    anonymize_payload
)


class TestPrivacyUtilities:
    """Test privacy utilities."""
    
    def test_hash_text(self):
        """Test text hashing."""
        text = "sensitive data"
        hashed = hash_text(text)
        
        assert isinstance(hashed, str)
        assert len(hashed) == 64  # SHA-256
        assert hashed != text
        
        # Same input -> same hash
        assert hash_text(text) == hashed
    
    def test_hash_text_with_salt(self):
        """Test hashing with salt."""
        text = "data"
        hash1 = hash_text(text, salt="salt1")
        hash2 = hash_text(text, salt="salt2")
        
        assert hash1 != hash2
    
    def test_anonymize_tenant_id(self):
        """Test tenant ID anonymization."""
        tenant_id = "tenant-123"
        anon_id = anonymize_tenant_id(tenant_id)
        
        assert isinstance(anon_id, str)
        assert len(anon_id) == 16
        assert anon_id != tenant_id
        
        # Consistent hashing
        assert anonymize_tenant_id(tenant_id) == anon_id
    
    def test_add_laplace_noise(self):
        """Test Laplace noise addition."""
        value = 100.0
        
        # Add noise multiple times
        noised_values = [add_laplace_noise(value, epsilon=1.0) for _ in range(100)]
        
        # Noised values should differ
        assert len(set(noised_values)) > 10
        
        # Average should be close to original
        avg = sum(noised_values) / len(noised_values)
        assert 90 < avg < 110  # Within reasonable range
    
    def test_add_differential_privacy(self):
        """Test differential privacy on statistics."""
        stats = {
            "false_negatives": 10,
            "false_positives": 5,
            "true_positives": 85,
            "precision": 0.95,
        }
        
        noised = add_differential_privacy(
            stats,
            epsilon=1.0,
            fields=["false_negatives", "false_positives", "true_positives"]
        )
        
        # Values should be different
        assert noised["false_negatives"] != 10 or noised["false_positives"] != 5
        
        # Should still be non-negative integers
        assert noised["false_negatives"] >= 0
        assert noised["false_positives"] >= 0
        assert isinstance(noised["false_negatives"], int)
        
        # Precision should be unchanged (not in fields)
        assert noised["precision"] == 0.95
    
    def test_anonymize_payload(self):
        """Test payload anonymization."""
        payload = {
            "tenant_id": "tenant-123",
            "stats": {"fn": 5},
            "raw_text": "sensitive content",
            "email": "user@example.com",
        }
        
        anonymized = anonymize_payload(payload)
        
        # Sensitive fields removed
        assert "raw_text" not in anonymized
        assert "email" not in anonymized
        
        # Tenant ID anonymized
        assert anonymized["tenant_id"] != "tenant-123"
        
        # Stats preserved
        assert anonymized["stats"]["fn"] == 5


class TestTelemetryPayload:
    """Test TelemetryPayload dataclass."""
    
    def test_payload_creation(self):
        """Test creating telemetry payload."""
        payload = TelemetryPayload(
            deployment_id="anon-123",
            model_version="1.0",
            policy_version="v1.2.3",
            stats={"fn": 5, "fp": 2},
        )
        
        assert payload.deployment_id == "anon-123"
        assert payload.model_version == "1.0"
        assert payload.stats["fn"] == 5
    
    def test_payload_to_dict(self):
        """Test converting payload to dictionary."""
        payload = TelemetryPayload(
            deployment_id="anon",
            model_version="1.0",
            policy_version="v1",
            stats={"fn": 3},
        )
        
        data = payload.to_dict()
        
        assert data["deployment_id"] == "anon"
        assert data["stats"]["fn"] == 3
        assert "timestamp" in data
    
    def test_payload_from_run_result(self):
        """Test creating payload from run result."""
        run_result = {
            "tp": 90,
            "fp": 5,
            "tn": 95,
            "fn": 10,
            "precision": 0.947,
            "recall": 0.900,
            "avg_latency_ms": 150,
            "guard_name": "internal",
        }
        
        payload = TelemetryPayload.from_run_result(
            run_result=run_result,
            deployment_id="anon-deploy",
            model_version="1.0",
            policy_version="v1.2.3"
        )
        
        assert payload.deployment_id == "anon-deploy"
        assert payload.stats["false_negatives"] == 10
        assert payload.stats["false_positives"] == 5
        assert payload.stats["guard_name"] == "internal"
        
        # Should not contain raw_text even if in run_result
        run_result["raw_text"] = "sensitive"
        payload2 = TelemetryPayload.from_run_result(
            run_result=run_result,
            deployment_id="anon",
            model_version="1.0",
            policy_version="v1"
        )
        assert "raw_text" not in payload2.stats


class TestFederatedTelemetry:
    """Test FederatedTelemetry client."""
    
    def test_telemetry_disabled_by_default(self):
        """Test that telemetry is disabled by default."""
        client = FederatedTelemetry()
        
        assert client.enabled is False
    
    def test_telemetry_enabled(self):
        """Test enabling telemetry."""
        client = FederatedTelemetry(
            enabled=True,
            server_url="https://telemetry.example.com",
            deployment_id="test-deploy"
        )
        
        assert client.enabled is True
        assert client.server_url == "https://telemetry.example.com"
        assert client.deployment_id == "test-deploy"
    
    @pytest.mark.asyncio
    async def test_report_payload(self):
        """Test reporting payload."""
        client = FederatedTelemetry(enabled=True, server_url="https://test.com")
        
        payload = TelemetryPayload(
            deployment_id="anon",
            model_version="1.0",
            policy_version="v1",
            stats={"fn": 5},
        )
        
        await client.report(payload)
        
        # Should be in batch
        assert len(client._batch) == 1
    
    @pytest.mark.asyncio
    async def test_report_when_disabled(self):
        """Test that report does nothing when disabled."""
        client = FederatedTelemetry(enabled=False)
        
        payload = TelemetryPayload(
            deployment_id="anon",
            model_version="1.0",
            policy_version="v1",
            stats={},
        )
        
        await client.report(payload)
        
        # Should not be in batch
        assert len(client._batch) == 0
    
    @pytest.mark.asyncio
    async def test_report_run(self):
        """Test reporting from run result."""
        client = FederatedTelemetry(
            enabled=True,
            server_url="https://test.com",
            deployment_id="deploy-123"
        )
        
        run_result = {
            "tp": 90,
            "fp": 5,
            "tn": 95,
            "fn": 10,
            "precision": 0.947,
            "recall": 0.900,
        }
        
        await client.report_run(run_result, model_version="1.0", policy_version="v1")
        
        # Check batch
        assert len(client._batch) == 1
        
        payload = client._batch[0]
        assert payload.stats["false_negatives"] >= 0  # May have noise
        assert payload.deployment_id != "deploy-123"  # Anonymized
    
    @pytest.mark.asyncio
    async def test_send_batch(self):
        """Test sending batch to server."""
        with patch("telemetry.federated.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.raise_for_status = Mock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client
            
            client = FederatedTelemetry(
                enabled=True,
                server_url="https://telemetry.example.com",
                batch_size=2
            )
            
            # Add payloads
            for i in range(2):
                payload = TelemetryPayload(
                    deployment_id=f"anon-{i}",
                    model_version="1.0",
                    policy_version="v1",
                    stats={"fn": i},
                )
                await client.report(payload)
            
            # Batch should be sent automatically when full
            await asyncio.sleep(0.1)  # Let async complete
            
            # Verify POST was called
            assert mock_client.post.called
            
            # Batch should be cleared
            assert len(client._batch) == 0
    
    @pytest.mark.asyncio
    async def test_send_batch_error_handling(self):
        """Test error handling when send fails."""
        with patch("telemetry.federated.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.side_effect = Exception("Network error")
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client
            
            client = FederatedTelemetry(
                enabled=True,
                server_url="https://telemetry.example.com",
                batch_size=2
            )
            
            # Add payloads
            payload = TelemetryPayload(
                deployment_id="anon",
                model_version="1.0",
                policy_version="v1",
                stats={"fn": 5},
            )
            
            client._batch.append(payload)
            client._batch.append(payload)
            
            # Try to send (should fail gracefully)
            await client._send_batch()
            
            # Payloads should be re-queued
            assert len(client._batch) > 0
    
    @pytest.mark.asyncio
    async def test_flush(self):
        """Test flushing pending payloads."""
        with patch("telemetry.federated.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.raise_for_status = Mock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client
            
            client = FederatedTelemetry(
                enabled=True,
                server_url="https://test.com"
            )
            
            # Add payload
            payload = TelemetryPayload(
                deployment_id="anon",
                model_version="1.0",
                policy_version="v1",
                stats={},
            )
            await client.report(payload)
            
            # Flush
            await client.flush()
            
            # Batch should be empty
            assert len(client._batch) == 0


class TestTelemetryConfiguration:
    """Test telemetry configuration."""
    
    def test_telemetry_from_env_vars(self):
        """Test loading telemetry config from environment."""
        with patch.dict(os.environ, {
            "FEDERATED_TELEMETRY_ENABLED": "1",
            "FEDERATED_SERVER_URL": "https://telemetry.example.com",
            "DEPLOYMENT_ID": "my-deployment"
        }):
            # Reset global
            import telemetry.federated
            telemetry.federated._global_client = None
            
            client = get_telemetry_client()
            
            assert client.enabled is True
            assert client.server_url == "https://telemetry.example.com"
            assert client.deployment_id == "my-deployment"
    
    def test_telemetry_disabled_by_env(self):
        """Test telemetry disabled by default via env."""
        with patch.dict(os.environ, {}, clear=True):
            import telemetry.federated
            telemetry.federated._global_client = None
            
            client = get_telemetry_client()
            
            assert client.enabled is False


class TestDataAnonymization:
    """Test data anonymization and privacy."""
    
    def test_no_raw_text_in_payload(self):
        """Test that raw text is never in telemetry payload."""
        run_result = {
            "raw_text": "How do I make a bomb?",  # Should be excluded
            "prompt": "Sensitive prompt",  # Should be excluded
            "tp": 10,
            "fn": 2,
        }
        
        payload = TelemetryPayload.from_run_result(
            run_result=run_result,
            deployment_id="anon",
            model_version="1.0",
            policy_version="v1"
        )
        
        payload_dict = payload.to_dict()
        
        # Raw text should not be in payload
        assert "raw_text" not in str(payload_dict)
        assert "Sensitive" not in str(payload_dict)
        assert "bomb" not in str(payload_dict)
        
        # Only aggregated stats
        assert payload.stats["false_negatives"] == 2
    
    def test_anonymize_payload_removes_pii(self):
        """Test that anonymize_payload removes PII."""
        payload = {
            "deployment_id": "deploy-123",
            "stats": {"fn": 5},
            "email": "user@example.com",
            "user_id": "user-456",
            "ip_address": "192.168.1.1",
        }
        
        anonymized = anonymize_payload(payload)
        
        # PII removed
        assert "email" not in anonymized
        assert "user_id" not in anonymized
        assert "ip_address" not in anonymized
        
        # Stats preserved
        assert anonymized["stats"]["fn"] == 5
    
    def test_differential_privacy_on_counts(self):
        """Test DP noise on count fields."""
        stats = {
            "false_negatives": 5,
            "false_positives": 3,
        }
        
        # Add noise multiple times
        results = []
        for _ in range(50):
            noised = add_differential_privacy(stats, epsilon=1.0)
            results.append(noised["false_negatives"])
        
        # Should have variance
        assert len(set(results)) > 5
        
        # Average should be close to original
        avg = sum(results) / len(results)
        assert 3 < avg < 7


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

