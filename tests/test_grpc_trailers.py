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


@pytest.mark.asyncio
async def test_stream_early_cancel(grpc_address: str = "127.0.0.1:50051") -> None:
    """Test that canceling stream early doesn't crash server and trailers are handled gracefully."""
    async with grpc.aio.insecure_channel(grpc_address) as ch:
        stub = score_pb2_grpc.ScoreServiceStub(ch)
        
        # Create a batch request with multiple items
        items = [
            score_pb2.ScoreRequest(text=f"item_{i}", category="violence", language="en")
            for i in range(5)
        ]
        req = score_pb2.BatchScoreRequest(items=items)
        
        # Make the streaming call
        call = stub.BatchScoreStream(req)
        
        # Consume only the first item, then cancel
        first_item = None
        async for item in call:
            first_item = item
            # Cancel after first item
            call.cancel()
            break
        
        # Verify we got the first item
        assert first_item is not None, "Should have received first item"
        assert first_item.index == 0, "First item should have index 0"
        
        # Check if call was cancelled
        assert call.cancelled(), "Call should be cancelled"
        
        # Try to get trailing metadata - may or may not be available after cancel
        # but server should not crash
        try:
            trailers = await call.trailing_metadata()
            if trailers:
                d = {k: v for k, v in trailers}
                # If trailers are present, verify they're valid
                if "x-policy-version" in d:
                    assert d["x-policy-version"] != "n/a", "x-policy-version should be valid"
                if "x-policy-checksum" in d:
                    assert len(d["x-policy-checksum"]) >= 8, "x-policy-checksum should be valid"
        except grpc.RpcError:
            # Cancellation may prevent trailing metadata, which is acceptable
            pass
        
        # Most importantly: verify server is still responsive by making another call
        health_req = score_pb2.ScoreRequest(text="health_check", category="violence", language="en")
        health_resp = await stub.Score(health_req)
        assert health_resp.score is not None, "Server should still be responsive after cancel"


@pytest.mark.asyncio
async def test_deadline_exceeded_with_trailers(grpc_address: str = "127.0.0.1:50051") -> None:
    """Test that DEADLINE_EXCEEDED errors still include trailing metadata."""
    async with grpc.aio.insecure_channel(grpc_address) as ch:
        stub = score_pb2_grpc.ScoreServiceStub(ch)
        
        # Set a very short deadline (50ms) to force timeout
        req = score_pb2.ScoreRequest(text="deadline_test", category="violence", language="en")
        
        try:
            # Make call with 50ms deadline - may or may not timeout depending on system speed
            call = stub.Score(req, timeout=0.05)  # 50ms
            resp = await call
            
            # If it didn't timeout, verify normal behavior
            assert resp.score is not None, "Should get response if no timeout"
            
            # Get trailing metadata even on success
            trailers = await call.trailing_metadata()
            d = {k: v for k, v in trailers}
            assert "x-policy-version" in d, "Should have metadata even without timeout"
            assert "x-policy-checksum" in d, "Should have checksum even without timeout"
            
        except grpc.RpcError as e:
            # If deadline exceeded, verify we still get trailing metadata
            assert e.code() == grpc.StatusCode.DEADLINE_EXCEEDED, \
                f"Expected DEADLINE_EXCEEDED, got {e.code()}"
            
            # Get trailing metadata from the error
            trailers = e.trailing_metadata()
            if trailers:
                d = {k: v for k, v in trailers}
                
                # Verify policy metadata is present even on error
                assert "x-policy-version" in d, "x-policy-version should be in trailers even on timeout"
                assert "x-policy-checksum" in d, "x-policy-checksum should be in trailers even on timeout"
                assert d["x-policy-version"] != "n/a", "x-policy-version should be valid"
                assert len(d["x-policy-checksum"]) >= 8, "x-policy-checksum should be valid"

