"""
    Global exception handler that formats errors as JSON with request ID.
"""
import logging
from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as exc:
            request_id = getattr(request.state, "request_id", None)
            return self.format_exception(exc, request_id)

    def format_exception(self, exc: Exception, request_id: str | None) -> JSONResponse:
        if isinstance(exc, StarletteHTTPException):
            status_code = exc.status_code
            detail = exc.detail
            code = "HTTP_ERROR"
            if status_code == 404:
                code = "NOT_FOUND"
            elif status_code == 410:
                code = "GONE"
            elif status_code == 400:
                code = "BAD_REQUEST"
            elif status_code == 429:
                code = "RATE_LIMIT_EXCEEDED"
            message = str(detail) if isinstance(detail, str) else detail.get("detail", "Unexpected error")
        elif isinstance(exc, RequestValidationError):
            status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
            code = "VALIDATION_ERROR"
            message = str(exc)
        else:
            logger.exception("Unhandled exception")
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            code = "INTERNAL_ERROR"
            message = "An unexpected error occurred"

        return JSONResponse(
            status_code=status_code,
            content={
                "error": {
                    "code": code,
                    "message": message,
                    "request_id": request_id,
                }
            },
        )