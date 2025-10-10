"""Federated learning telemetry client."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .privacy import anonymize_payload, add_differential_privacy

logger = logging.getLogger(__name__)

try:
    import httpx
except ImportError:
    httpx = None


@dataclass
class TelemetryPayload:
    """Anonymized telemetry payload for federated learning."""
    
    deployment_id: str  # Anonymized deployment identifier
    model_version: str
    policy_version: str
    
    # Aggregated statistics (no raw data)
    stats: Dict[str, Any] = field(default_factory=dict)
    
    # Timestamp
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "deployment_id": self.deployment_id,
            "model_version": self.model_version,
            "policy_version": self.policy_version,
            "stats": self.stats,
            "timestamp": self.timestamp,
        }
    
    @classmethod
    def from_run_result(
        cls,
        run_result: Dict[str, Any],
        deployment_id: str,
        model_version: str,
        policy_version: str
    ) -> TelemetryPayload:
        """Create payload from evaluation run result.
        
        Args:
            run_result: Evaluation run result
            deployment_id: Anonymized deployment ID
            model_version: Model version
            policy_version: Policy version
            
        Returns:
            TelemetryPayload
        """
        # Extract anonymized statistics
        stats = {
            "runs_analyzed": 1,
            "false_negatives": run_result.get("fn", 0),
            "false_positives": run_result.get("fp", 0),
            "true_positives": run_result.get("tp", 0),
            "true_negatives": run_result.get("tn", 0),
            "precision": run_result.get("precision", 0.0),
            "recall": run_result.get("recall", 0.0),
            "avg_latency_ms": run_result.get("avg_latency_ms", 0),
        }
        
        # Extract categories with issues (no text)
        if "categories_missed" in run_result:
            stats["categories_missed"] = run_result["categories_missed"]
        
        # Extract guard name (if present)
        if "guard_name" in run_result:
            stats["guard_name"] = run_result["guard_name"]
        
        return cls(
            deployment_id=deployment_id,
            model_version=model_version,
            policy_version=policy_version,
            stats=stats,
        )


class FederatedTelemetry:
    """Client for federated learning telemetry.
    
    Collects and transmits anonymized evaluation insights to a central server
    for collaborative model improvement.
    """
    
    def __init__(
        self,
        enabled: bool = False,
        server_url: Optional[str] = None,
        deployment_id: Optional[str] = None,
        batch_size: int = 10,
        send_interval_seconds: float = 300.0,  # 5 minutes
        use_differential_privacy: bool = True,
        epsilon: float = 1.0,
    ):
        """Initialize federated telemetry client.
        
        Args:
            enabled: Enable telemetry
            server_url: Central server URL
            deployment_id: Deployment identifier (will be anonymized)
            batch_size: Number of payloads to batch before sending
            send_interval_seconds: Interval between sends
            use_differential_privacy: Add DP noise
            epsilon: Privacy parameter for DP
        """
        self.enabled = enabled
        self.server_url = server_url
        self.deployment_id = deployment_id or "unknown"
        self.batch_size = batch_size
        self.send_interval_seconds = send_interval_seconds
        self.use_differential_privacy = use_differential_privacy
        self.epsilon = epsilon
        
        # Batch queue
        self._batch: deque = deque(maxlen=batch_size * 2)  # Limit memory
        self._lock = asyncio.Lock()
        
        # Background task
        self._send_task: Optional[asyncio.Task] = None
        
        if httpx is None and enabled:
            logger.warning("httpx not installed - federated telemetry will not send data")
            self.enabled = False
        
        logger.info(
            f"Federated telemetry: enabled={enabled}, "
            f"server={server_url}, dp={use_differential_privacy}"
        )
    
    async def report(self, payload: TelemetryPayload) -> None:
        """Report telemetry payload.
        
        Args:
            payload: Telemetry payload
        """
        if not self.enabled:
            return
        
        async with self._lock:
            self._batch.append(payload)
            
            logger.debug(f"Telemetry: queued payload (batch size: {len(self._batch)})")
            
            # Send if batch is full
            if len(self._batch) >= self.batch_size:
                await self._send_batch()
    
    async def report_run(
        self,
        run_result: Dict[str, Any],
        model_version: str,
        policy_version: str
    ) -> None:
        """Report evaluation run result.
        
        Args:
            run_result: Evaluation run result
            model_version: Model version
            policy_version: Policy version
        """
        if not self.enabled:
            return
        
        from .privacy import anonymize_tenant_id
        
        # Anonymize deployment ID
        anon_deployment_id = anonymize_tenant_id(self.deployment_id)
        
        # Create payload
        payload = TelemetryPayload.from_run_result(
            run_result=run_result,
            deployment_id=anon_deployment_id,
            model_version=model_version,
            policy_version=policy_version
        )
        
        # Apply differential privacy if enabled
        if self.use_differential_privacy:
            payload.stats = add_differential_privacy(
                payload.stats,
                epsilon=self.epsilon,
                fields=["false_negatives", "false_positives", "true_positives", "true_negatives"]
            )
        
        # Anonymize payload
        payload_dict = payload.to_dict()
        payload_dict = anonymize_payload(payload_dict)
        
        # Re-create payload from anonymized dict
        payload = TelemetryPayload(
            deployment_id=payload_dict["deployment_id"],
            model_version=payload_dict["model_version"],
            policy_version=payload_dict["policy_version"],
            stats=payload_dict["stats"],
            timestamp=payload_dict["timestamp"],
        )
        
        await self.report(payload)
    
    async def _send_batch(self) -> None:
        """Send batched payloads to server."""
        if not self.enabled or not self.server_url:
            return
        
        if len(self._batch) == 0:
            return
        
        # Get batch to send
        batch_to_send = list(self._batch)
        self._batch.clear()
        
        try:
            # Send to server
            payloads = [p.to_dict() for p in batch_to_send]
            
            if httpx is None:
                logger.warning("httpx not available - cannot send telemetry")
                return
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.server_url,
                    json={"payloads": payloads},
                    headers={"Content-Type": "application/json"}
                )
                
                response.raise_for_status()
                
                logger.info(f"Federated telemetry: sent {len(payloads)} payloads to {self.server_url}")
        
        except Exception as e:
            logger.error(f"Federated telemetry send failed: {e}")
            
            # Re-queue failed payloads (up to limit)
            for payload in batch_to_send[:self.batch_size]:
                self._batch.append(payload)
    
    async def start_background_sender(self) -> None:
        """Start background task to send telemetry periodically."""
        if not self.enabled or self._send_task is not None:
            return
        
        self._send_task = asyncio.create_task(self._background_sender())
        logger.info("Federated telemetry background sender started")
    
    async def _background_sender(self) -> None:
        """Background task that sends telemetry periodically."""
        while True:
            try:
                await asyncio.sleep(self.send_interval_seconds)
                
                async with self._lock:
                    await self._send_batch()
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Background sender error: {e}")
    
    async def stop_background_sender(self) -> None:
        """Stop background sender."""
        if self._send_task is not None:
            self._send_task.cancel()
            try:
                await self._send_task
            except asyncio.CancelledError:
                pass
            self._send_task = None
            logger.info("Federated telemetry background sender stopped")
    
    async def flush(self) -> None:
        """Flush pending payloads immediately."""
        if not self.enabled:
            return
        
        async with self._lock:
            await self._send_batch()


# Global telemetry client
_global_client: Optional[FederatedTelemetry] = None


def get_telemetry_client(
    enabled: Optional[bool] = None,
    server_url: Optional[str] = None,
    deployment_id: Optional[str] = None
) -> FederatedTelemetry:
    """Get global telemetry client.
    
    Args:
        enabled: Override enabled flag
        server_url: Override server URL
        deployment_id: Override deployment ID
        
    Returns:
        FederatedTelemetry instance
    """
    global _global_client
    
    if _global_client is None:
        import os
        
        enabled = enabled if enabled is not None else os.getenv("FEDERATED_TELEMETRY_ENABLED", "0") == "1"
        server_url = server_url or os.getenv("FEDERATED_SERVER_URL")
        deployment_id = deployment_id or os.getenv("DEPLOYMENT_ID", "default")
        
        _global_client = FederatedTelemetry(
            enabled=enabled,
            server_url=server_url,
            deployment_id=deployment_id,
        )
    
    return _global_client


__all__ = ["FederatedTelemetry", "TelemetryPayload", "get_telemetry_client"]

