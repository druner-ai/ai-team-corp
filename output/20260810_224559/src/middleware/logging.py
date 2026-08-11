"""
Middleware that adds request logging using structlog.

Generates a unique request_id and logs basic request information.
"""
import uuid

import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

logger = structlog.get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log every request with method, path, status, and duration."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        structlog.contextvars.bind_contextvars(request_id=request_id)

        logger.info(
            "request_started",
            method=request.method,
            path=request.url.path,
            query=request.query_params,
        )

        response = await call_next(request)

        logger.info(
            "request_finished",
            status_code=response.status_code,
        )
        structlog.contextvars.unbind_contextvars("request_id")
        return response