"""gRPC server interceptors for metadata injection and tracing."""

from __future__ import annotations

import grpc  # type: ignore
from opentelemetry import trace

import sys
import logging
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).resolve().parents[1]
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from seval.settings import POLICY_VERSION, POLICY_CHECKSUM
from observability.trace import get_or_create_trace_id, clear_trace_id

# Get tracer for this module
tracer = trace.get_tracer(__name__)
logger = logging.getLogger(__name__)


class TrailingMetaInterceptor(grpc.aio.ServerInterceptor):  # type: ignore
    """Injects policy version, checksum, and trace ID into trailing metadata with OpenTelemetry spans."""

    async def intercept_service(self, continuation, handler_call_details):  # type: ignore
        """Intercept service calls and inject trailing metadata with tracing."""
        handler = await continuation(handler_call_details)
        
        if handler is None:
            return handler
        
        # Parse RPC method info
        method_parts = handler_call_details.method.split("/")
        service_name = method_parts[1].rsplit(".", 1)[0] if len(method_parts) > 1 else "unknown"
        method_name = method_parts[-1] if method_parts else "unknown"

        # Handle unary-unary calls
        async def _wrap_unary_unary(request, context):  # type: ignore
            # Clear any existing trace ID from previous requests
            clear_trace_id()
            
            # Extract or generate trace ID from gRPC metadata
            try:
                metadata = context.invocation_metadata()
                metadata_dict = {k: v for k, v in metadata}
            except Exception as e:
                logger.debug(f"Failed to extract gRPC metadata: {e}")
                metadata_dict = {}
            
            trace_id = get_or_create_trace_id(metadata_dict)
            logger.debug(f"Generated trace_id for gRPC unary call: {trace_id}")
            
            with tracer.start_as_current_span("rpc", attributes={
                "rpc.system": "grpc",
                "rpc.service": service_name,
                "rpc.method": method_name,
                "trace.id": trace_id,
            }):
                try:
                    return await handler.unary_unary(request, context)
                finally:
                    context.set_trailing_metadata((
                        ("x-policy-version", POLICY_VERSION),
                        ("x-policy-checksum", POLICY_CHECKSUM),
                        ("x-trace-id", trace_id),
                    ))

        # Handle unary-stream calls
        async def _wrap_unary_stream(request, context):  # type: ignore
            # Clear any existing trace ID from previous requests
            clear_trace_id()
            
            # Extract or generate trace ID from gRPC metadata
            try:
                metadata = context.invocation_metadata()
                metadata_dict = {k: v for k, v in metadata}
            except Exception as e:
                logger.debug(f"Failed to extract gRPC metadata: {e}")
                metadata_dict = {}
            
            trace_id = get_or_create_trace_id(metadata_dict)
            logger.debug(f"Generated trace_id for gRPC stream call: {trace_id}")
            
            with tracer.start_as_current_span("rpc_stream", attributes={
                "rpc.system": "grpc",
                "rpc.service": service_name,
                "rpc.method": method_name,
                "trace.id": trace_id,
            }):
                try:
                    async for resp in handler.unary_stream(request, context):
                        yield resp
                finally:
                    context.set_trailing_metadata((
                        ("x-policy-version", POLICY_VERSION),
                        ("x-policy-checksum", POLICY_CHECKSUM),
                        ("x-trace-id", trace_id),
                    ))

        if handler and handler.unary_unary:
            return grpc.unary_unary_rpc_method_handler(
                _wrap_unary_unary,
                request_deserializer=handler.request_deserializer,
                response_serializer=handler.response_serializer,
            )
        if handler and handler.unary_stream:
            return grpc.unary_stream_rpc_method_handler(
                _wrap_unary_stream,
                request_deserializer=handler.request_deserializer,
                response_serializer=handler.response_serializer,
            )
        return handler
