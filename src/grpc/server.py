from __future__ import annotations

import asyncio
import os
import signal
from typing import List

import grpc  # type: ignore

from src.seval import sdk
from grpc_health.v1 import health, health_pb2, health_pb2_grpc  # type: ignore
from grpc_reflection.v1alpha import reflection  # type: ignore
from src.grpc_generated import score_pb2, score_pb2_grpc  # type: ignore
from src.seval.settings import POLICY_VERSION, POLICY_CHECKSUM
from src.policy.compiler import POLICY_PATH
from src.grpc.interceptors import TrailingMetaInterceptor
import logging
from src.grpc import metrics as grpc_metrics


class ScoreService(score_pb2_grpc.ScoreServiceServicer):  # type: ignore
    async def Score(self, request, context):  # type: ignore
        guard = request.guard or "candidate"
        result = sdk.predict(request.text, request.category, request.language, guard=guard)
        score_val = float(result.get("score") or (1.0 if result.get("prediction") else 0.0))
        slices = [str(s) for s in (result.get("slices") or [])]
        return score_pb2.ScoreResponse(
            score=score_val,
            slices=slices,
            policy_version=POLICY_VERSION,
            guard_version=str(result.get("guard_version") or guard),
            latency_ms=int(result.get("latency_ms") or 0),
            request_id=str(result.get("request_id") or ""),
        )

    async def BatchScore(self, request, context):  # type: ignore
        items = []
        for req in request.items:
            r = await self.Score(req, context)
            items.append(r)
        return score_pb2.BatchScoreResponse(items=items)
    
    async def BatchScoreStream(self, request, context):  # type: ignore
        """Stream batch scores one item at a time."""
        for idx, req in enumerate(request.items):
            guard = req.guard or "candidate"
            result = sdk.predict(req.text, req.category, req.language, guard=guard)
            score_val = float(result.get("score") or (1.0 if result.get("prediction") else 0.0))
            slices = [str(s) for s in (result.get("slices") or [])]
            
            resp = score_pb2.ScoreResponse(
                score=score_val,
                slices=slices,
                policy_version=POLICY_VERSION,
                guard_version=str(result.get("guard_version") or guard),
                latency_ms=int(result.get("latency_ms") or 0),
                request_id=str(result.get("request_id") or ""),
            )
            
            yield score_pb2.StreamItem(index=idx, resp=resp)


async def serve_async():
    # Build interceptor chain
    interceptors = [TrailingMetaInterceptor()]
    prometheus_interceptor = grpc_metrics.get_prometheus_interceptor()
    if prometheus_interceptor is not None:
        interceptors.append(prometheus_interceptor)
    
    # Create server with interceptors and message size limits (32MB)
    server = grpc.aio.server(
        interceptors=interceptors,
        options=[
            ("grpc.max_send_message_length", 32 * 1024 * 1024),
            ("grpc.max_receive_message_length", 32 * 1024 * 1024),
        ]
    )
    score_pb2_grpc.add_ScoreServiceServicer_to_server(ScoreService(), server)
    # Register gRPC Health Checking service and set status to SERVING
    try:
        health_servicer = health.aio.HealthServicer()  # type: ignore[attr-defined]
        is_aio_health = True
    except AttributeError:  # fallback if aio variant not available
        health_servicer = health.HealthServicer()  # type: ignore
        is_aio_health = False
    health_pb2_grpc.add_HealthServicer_to_server(health_servicer, server)
    host = os.getenv("GRPC_HOST", "0.0.0.0")
    # TLS settings
    tls_enabled = os.getenv("GRPC_TLS_ENABLED", "false").lower() in {"1", "true", "yes"}
    if tls_enabled:
        port = int(os.getenv("GRPC_TLS_PORT", "5443"))
        cert = os.getenv("GRPC_TLS_CERT")
        key = os.getenv("GRPC_TLS_KEY")
        if not cert or not key:
            raise RuntimeError("GRPC_TLS_ENABLED=true but GRPC_TLS_CERT/GRPC_TLS_KEY not set")
        with open(cert, "rb") as c, open(key, "rb") as k:
            creds = grpc.ssl_server_credentials(((k.read(), c.read()),))
        server.add_secure_port(f"{host}:{port}", creds)
        logging.getLogger("grpc_server").info("gRPC listening with TLS on %s:%s", host, port)
    else:
        port = int(os.getenv("GRPC_PORT", "50051"))
        server.add_insecure_port(f"{host}:{port}")
        logging.getLogger("grpc_server").info("gRPC listening plaintext on %s:%s", host, port)
    # Set health status for overall server and specific service
    service_name = 'seval.ScoreService'
    serving = health_pb2.HealthCheckResponse.SERVING  # type: ignore[attr-defined]
    if is_aio_health:
        try:
            await health_servicer.set('', serving)  # type: ignore[attr-defined]
            await health_servicer.set(service_name, serving)  # type: ignore[attr-defined]
        except Exception:
            pass
    else:
        try:
            health_servicer.set('', serving)  # type: ignore[attr-defined]
            health_servicer.set(service_name, serving)  # type: ignore[attr-defined]
        except Exception:
            pass

    # Conditionally enable server reflection for grpcurl and tooling
    logger = logging.getLogger("grpc_server")
    enable_reflection = os.getenv("ENABLE_GRPC_REFLECTION", "false").lower() in {"1", "true", "yes"}
    if enable_reflection:
        try:
            service_names = (
                score_pb2.DESCRIPTOR.services_by_name['ScoreService'].full_name,
                health_pb2.DESCRIPTOR.services_by_name['Health'].full_name,
                reflection.SERVICE_NAME,
            )
            reflection.enable_server_reflection(service_names, server)
            logger.info("gRPC reflection: enabled")
        except Exception as e:
            logger.warning("gRPC reflection: failed to enable (%s)", e)
    else:
        logger.info("gRPC reflection: disabled")

    await server.start()
    
    # Graceful shutdown on SIGINT/SIGTERM
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    
    def handle_shutdown(sig: signal.Signals) -> None:
        logger.info("Received signal %s, initiating graceful shutdown", sig.name)
        stop_event.set()
    
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda s=sig: handle_shutdown(s))
    
    # Wait for shutdown signal
    await stop_event.wait()
    
    # Stop server gracefully, allowing inflight RPCs to drain
    logger.info("Stopping gRPC server...")
    await server.stop(grace=5.0)  # 5 second grace period
    logger.info("gRPC server stopped cleanly")


def main():  # pragma: no cover
    asyncio.run(serve_async())


if __name__ == "__main__":
    main()



