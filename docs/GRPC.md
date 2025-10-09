# gRPC Guide

## Generate Python stubs

```bash
python -m grpc_tools.protoc -I src/grpc_service --python_out=src/grpc_generated --grpc_python_out=src/grpc_generated src/grpc_service/score.proto
```

## Run the server

```bash
PYTHONPATH=src python -m src.grpc.server
# Configure port via GRPC_PORT (default 50051)
```

## Python client example

```python
import asyncio
import grpc
from src.grpc_generated import score_pb2, score_pb2_grpc

async def main():
    async with grpc.aio.insecure_channel("127.0.0.1:50051") as channel:
        stub = score_pb2_grpc.ScoreServiceStub(channel)
        req = score_pb2.ScoreRequest(text="hello", category="violence", language="en", guard="candidate")
        resp = await stub.Score(req)
        print(resp)

if __name__ == "__main__":
    asyncio.run(main())
```

