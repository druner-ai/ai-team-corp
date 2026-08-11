import logging
import time
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("uvicorn.access")


class LoggingMiddleware(BaseHTTPMiddleware):
    """Simple logging middleware that records method, path, status and duration."""

    async def dispatch(self, request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        logger.info(
            "%s %s - %d - %.4fs",
            request.method,
            request.url.path,
            response.status_code,
            process_time,
        )
        return response
