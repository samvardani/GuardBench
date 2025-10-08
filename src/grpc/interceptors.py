"""gRPC server interceptors for metadata injection and tracing."""

from __future__ import annotations

import grpc  # type: ignore
import time
from opentelemetry import trace

from src.seval.settings import POLICY_VERSION, POLICY_CHECKSUM

# Get tracer for this module
tracer = trace.get_tracer(__name__)


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
            with tracer.start_as_current_span("rpc", attributes={
                "rpc.system": "grpc",
                "rpc.service": service_name,
                "rpc.method": method_name,
            }):
                try:
                    return await handler.unary_unary(request, context)
                finally:
                    tid = trace.get_current_span().get_span_context().trace_id
                    context.set_trailing_metadata((
                        ("x-policy-version", POLICY_VERSION),
                        ("x-policy-checksum", POLICY_CHECKSUM),
                        ("x-trace-id", f"{tid:032x}"),
                    ))

        # Handle unary-stream calls
        async def _wrap_unary_stream(request, context):  # type: ignore
            with tracer.start_as_current_span("rpc_stream", attributes={
                "rpc.system": "grpc",
                "rpc.service": service_name,
                "rpc.method": method_name,
            }):
                try:
                    async for resp in handler.unary_stream(request, context):
                        yield resp
                finally:
                    tid = trace.get_current_span().get_span_context().trace_id
                    context.set_trailing_metadata((
                        ("x-policy-version", POLICY_VERSION),
                        ("x-policy-checksum", POLICY_CHECKSUM),
                        ("x-trace-id", f"{tid:032x}"),
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
