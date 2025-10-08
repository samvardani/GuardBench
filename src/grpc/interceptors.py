"""gRPC server interceptors for metadata injection and tracing."""

from __future__ import annotations

from typing import Callable, Awaitable, Any
from collections.abc import Iterable

import grpc  # type: ignore
from opentelemetry import trace

from src.seval.settings import POLICY_VERSION, POLICY_CHECKSUM


class TrailingMetaInterceptor(grpc.aio.ServerInterceptor):  # type: ignore
    """Injects policy version, checksum, and trace ID into trailing metadata."""

    async def intercept_service(  # type: ignore
        self,
        continuation: Callable[[Any], Awaitable[Any]],
        handler_call_details: grpc.HandlerCallDetails,
    ) -> grpc.RpcMethodHandler:
        """Intercept service calls and inject trailing metadata."""
        
        # Get the original handler
        handler = await continuation(handler_call_details)
        
        if handler is None:
            return handler
            
        # Handle unary-unary calls
        if handler.unary_unary:
            original_unary = handler.unary_unary
            
            async def wrapper_unary(request: Any, context: grpc.ServicerContext) -> Any:  # type: ignore
                """Wrap unary call to add trailing metadata."""
                try:
                    response = await original_unary(request, context)
                    return response
                finally:
                    try:
                        trace_id = trace.get_current_span().get_span_context().trace_id
                        context.set_trailing_metadata((
                            ("x-policy-version", POLICY_VERSION),
                            ("x-policy-checksum", POLICY_CHECKSUM),
                            ("x-trace-id", f"{trace_id:032x}"),
                        ))
                    except Exception:
                        # Fallback without trace ID if OpenTelemetry is not available
                        context.set_trailing_metadata((
                            ("x-policy-version", POLICY_VERSION),
                            ("x-policy-checksum", POLICY_CHECKSUM),
                        ))
            
            # Create new handler with wrapped method
            return grpc.unary_unary_rpc_method_handler(
                wrapper_unary,
                request_deserializer=handler.request_deserializer,
                response_serializer=handler.response_serializer,
            )
        
        # Handle unary-stream calls
        if handler.unary_stream:
            original_stream = handler.unary_stream
            
            async def wrapper_stream(request: Any, context: grpc.ServicerContext) -> Iterable[Any]:  # type: ignore
                """Wrap stream call to add trailing metadata."""
                try:
                    async for response in original_stream(request, context):
                        yield response
                finally:
                    try:
                        trace_id = trace.get_current_span().get_span_context().trace_id
                        context.set_trailing_metadata((
                            ("x-policy-version", POLICY_VERSION),
                            ("x-policy-checksum", POLICY_CHECKSUM),
                            ("x-trace-id", f"{trace_id:032x}"),
                        ))
                    except Exception:
                        # Fallback without trace ID if OpenTelemetry is not available
                        context.set_trailing_metadata((
                            ("x-policy-version", POLICY_VERSION),
                            ("x-policy-checksum", POLICY_CHECKSUM),
                        ))
            
            # Create new handler with wrapped method
            return grpc.unary_stream_rpc_method_handler(
                wrapper_stream,
                request_deserializer=handler.request_deserializer,
                response_serializer=handler.response_serializer,
            )
        
        return handler
