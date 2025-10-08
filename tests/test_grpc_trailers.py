"""Test that gRPC responses include policy metadata in trailing metadata."""

from __future__ import annotations

import pytest
import grpc

from src.grpc_generated import score_pb2, score_pb2_grpc


@pytest.mark.asyncio
async def test_trailing_metadata(grpc_address: str = "127.0.0.1:50051") -> None:
    """Test that Score endpoint includes policy version and checksum in trailing metadata."""
    async with grpc.aio.insecure_channel(grpc_address) as ch:
        stub = score_pb2_grpc.ScoreServiceStub(ch)
        req = score_pb2.ScoreRequest(text="hi", category="violence", language="en")
        
        # Make the call - this returns a Call object
        call = stub.Score(req)
        
        # Get the response
        resp = await call
        
        # Get trailing metadata from the call object
        trailers = await call.trailing_metadata()
        d = {k: v for k, v in trailers}
        
        # Verify policy version is present and not default
        assert "x-policy-version" in d, "x-policy-version not in trailing metadata"
        assert d["x-policy-version"] != "n/a", "x-policy-version should not be 'n/a'"
        
        # Verify policy checksum is present and has expected length (12 chars)
        assert "x-policy-checksum" in d, "x-policy-checksum not in trailing metadata"
        assert len(d["x-policy-checksum"]) >= 8, "x-policy-checksum should be at least 8 chars"


@pytest.mark.asyncio
async def test_batch_trailing_metadata(grpc_address: str = "127.0.0.1:50051") -> None:
    """Test that BatchScore endpoint includes policy metadata in trailing metadata."""
    async with grpc.aio.insecure_channel(grpc_address) as ch:
        stub = score_pb2_grpc.ScoreServiceStub(ch)
        
        items = [
            score_pb2.ScoreRequest(text="hello", category="violence", language="en"),
            score_pb2.ScoreRequest(text="test", category="crime", language="en"),
        ]
        req = score_pb2.BatchScoreRequest(items=items)
        
        # Make the call - this returns a Call object
        call = stub.BatchScore(req)
        
        # Get the response
        resp = await call
        
        # Get trailing metadata from the call object
        trailers = await call.trailing_metadata()
        d = {k: v for k, v in trailers}
        
        # Verify policy version is present
        assert "x-policy-version" in d, "x-policy-version not in trailing metadata"
        assert d["x-policy-version"] != "n/a", "x-policy-version should not be 'n/a'"
        
        # Verify policy checksum is present
        assert "x-policy-checksum" in d, "x-policy-checksum not in trailing metadata"
        assert len(d["x-policy-checksum"]) >= 8, "x-policy-checksum should be at least 8 chars"


@pytest.mark.asyncio
async def test_stream_trailing_metadata(grpc_address: str = "127.0.0.1:50051") -> None:
    """Test that BatchScoreStream endpoint includes policy metadata in trailing metadata."""
    async with grpc.aio.insecure_channel(grpc_address) as ch:
        stub = score_pb2_grpc.ScoreServiceStub(ch)
        
        items = [
            score_pb2.ScoreRequest(text="hello", category="violence", language="en"),
            score_pb2.ScoreRequest(text="test", category="crime", language="en"),
            score_pb2.ScoreRequest(text="benign", category="benign", language="en"),
        ]
        req = score_pb2.BatchScoreRequest(items=items)
        
        # Make the streaming call
        call = stub.BatchScoreStream(req)
        
        # Consume the stream
        responses = []
        async for item in call:
            responses.append(item)
        
        # Verify we got all items
        assert len(responses) == 3, f"Expected 3 items, got {len(responses)}"
        
        # Verify indices are correct
        for i, item in enumerate(responses):
            assert item.index == i, f"Expected index {i}, got {item.index}"
            assert item.resp.policy_version != "n/a", "policy_version should not be 'n/a'"
        
        # Get trailing metadata from the call object
        trailers = await call.trailing_metadata()
        d = {k: v for k, v in trailers}
        
        # Verify policy version is present
        assert "x-policy-version" in d, "x-policy-version not in trailing metadata"
        assert d["x-policy-version"] != "n/a", "x-policy-version should not be 'n/a'"
        
        # Verify policy checksum is present
        assert "x-policy-checksum" in d, "x-policy-checksum not in trailing metadata"
        assert len(d["x-policy-checksum"]) >= 8, "x-policy-checksum should be at least 8 chars"

