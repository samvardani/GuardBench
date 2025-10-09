from __future__ import annotations

import os
import asyncio
import grpc  # type: ignore

from grpc_generated import score_pb2, score_pb2_grpc  # type: ignore


async def main():
    addr = os.getenv("GRPC_ADDR", "127.0.0.1:50051")
    async with grpc.aio.insecure_channel(addr) as channel:
        stub = score_pb2_grpc.ScoreServiceStub(channel)
        req = score_pb2.ScoreRequest(text="hello", category="violence", language="en", guard="candidate")
        resp = await stub.Score(req)
        print("score=", resp.score)


if __name__ == "__main__":  # pragma: no cover
    asyncio.run(main())


