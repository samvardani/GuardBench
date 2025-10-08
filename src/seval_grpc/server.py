from __future__ import annotations

import asyncio
import os

import grpc  # type: ignore

from seval import sdk
from src.grpc_generated import score_pb2, score_pb2_grpc  # type: ignore
from src.service.api import POLICY_VERSION


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


async def serve_async():
    server = grpc.aio.server()
    score_pb2_grpc.add_ScoreServiceServicer_to_server(ScoreService(), server)
    port = int(os.getenv("GRPC_PORT", "50051"))
    host = os.getenv("GRPC_HOST", "0.0.0.0")
    use_tls = os.getenv("GRPC_TLS", "false").lower() in {"1", "true", "yes"}
    if use_tls:
        cert = os.getenv("GRPC_CERT_FILE")
        key = os.getenv("GRPC_KEY_FILE")
        if not cert or not key:
            raise RuntimeError("GRPC_TLS enabled but GRPC_CERT_FILE/GRPC_KEY_FILE not set")
        with open(cert, "rb") as c, open(key, "rb") as k:
            creds = grpc.ssl_server_credentials(((k.read(), c.read()),))
        server.add_secure_port(f"{host}:{port}", creds)
    else:
        server.add_insecure_port(f"{host}:{port}")
    await server.start()
    await server.wait_for_termination()


def main():  # pragma: no cover
    asyncio.run(serve_async())


if __name__ == "__main__":
    main()



