"""Provenance middleware for FastAPI governance and audit trails."""

from __future__ import annotations

import logging
import os
from typing import Callable, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from .trace import get_or_create_trace_id

logger = logging.getLogger(__name__)


class ProvenanceMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware that stamps every response with governance headers.
    
    Headers added:
    - X-Policy-Version: Policy version for traceability
    - X-Policy-Checksum: Policy checksum for integrity
    - X-Trace-Id: Request trace ID for distributed tracing
    - X-Provenance-Service: Service name (searei)
    - X-Provenance-Version: Application version
    - X-Provenance-Build: Build ID or git SHA
    
    These headers satisfy SOC2 audit requirements and enable trace correlation.
    """
    
    def __init__(
        self,
        app: ASGIApp,
        service_name: str = "searei",
        version: str = "0.3.1",
        build_id: Optional[str] = None,
    ):
        """Initialize provenance middleware.
        
        Args:
            app: ASGI application
            service_name: Service identifier (default: searei)
            version: Application version
            build_id: Build ID or git SHA
        """
        super().__init__(app)
        self.service_name = service_name
        self.version = version
        self.build_id = build_id or os.getenv("BUILD_ID", "dev")
        
        logger.info(
            f"ProvenanceMiddleware initialized: "
            f"service={service_name}, version={version}, build={self.build_id}"
        )
    
    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """Process request and add provenance headers to response.
        
        Args:
            request: Incoming request
            call_next: Next middleware/handler
            
        Returns:
            Response with provenance headers
        """
        # Get or create trace ID using unified trace module
        # This sets the contextvar for the duration of the request
        trace_id = get_or_create_trace_id(request.headers)
        
        # Get policy metadata from settings
        try:
            from seval.settings import POLICY_VERSION, POLICY_CHECKSUM
        except ImportError:
            POLICY_VERSION = "n/a"
            POLICY_CHECKSUM = "n/a"
        
        # Call next middleware/handler and add headers in finally block
        # This ensures headers are added even if exceptions occur
        response = None
        try:
            response = await call_next(request)
        finally:
            # If response exists, add headers
            if response is not None:
                response.headers["X-Trace-Id"] = trace_id
                response.headers["X-Policy-Version"] = POLICY_VERSION
                response.headers["X-Policy-Checksum"] = POLICY_CHECKSUM
                response.headers["X-Provenance-Service"] = self.service_name
                response.headers["X-Provenance-Version"] = self.version
                response.headers["X-Provenance-Build"] = self.build_id
        
        return response


__all__ = ["ProvenanceMiddleware"]

