from __future__ import annotations

import asyncio
import os
from concurrent import futures
from typing import AsyncIterator

import grpc  # type: ignore

from service.api import _resolve_guard, _wrap_guard_sync, POLICY_VERSION
from policy.compiler import POLICY_PATH
from service.api import _policy_checksum

# Import generated stubs (assumes protoc has been run to generate seval_pb2, seval_pb2_grpc)
try:
    from grpc_generated import score_pb2 as seval_pb2  # type: ignore
    from grpc_generated import score_pb2_grpc as seval_pb2_grpc  # type: ignore
except Exception:  # pragma: no cover - generation may not be present locally
    seval_pb2 = None
    seval_pb2_grpc = None


class ScoreService(seval_pb2_grpc.ScoreServiceServicer):  # type: ignore
    async def Score(self, request, context):  # type: ignore
        guard = request.guard or "candidate"
        spec = _resolve_guard(guard)
        fn = _wrap_guard_sync(guard, spec)
        result = fn(request.text, request.category, request.language)
        score_value = float(result.get("score") or 1.0 if result.get("prediction") else 0.0)
        return seval_pb2.ScoreResponse(
            score=score_value,
            guard_version=spec.get("version", guard) or guard,
            policy_version=POLICY_VERSION,
            policy_checksum=_policy_checksum(POLICY_PATH),
            request_id="",
        )

    async def BatchScore(self, request_iterator, context):  # type: ignore
        async for req in request_iterator:  # type: ignore
            resp = await self.Score(req, context)
            yield resp


async def serve_async(host: str = "0.0.0.0", port: int = 50051):
    if seval_pb2_grpc is None:
        raise RuntimeError("gRPC stubs not generated; run protoc")
    server = grpc.aio.server()
    seval_pb2_grpc.add_ScoreServiceServicer_to_server(ScoreService(), server)
    server.add_insecure_port(f"{host}:{port}")
    await server.start()
    await server.wait_for_termination()


def main():  # pragma: no cover
    loop = asyncio.get_event_loop()
    loop.run_until_complete(serve_async())


if __name__ == "__main__":
    main()



