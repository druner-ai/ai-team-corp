"""
Rate limiting middleware using Redis sliding window.
Limits requests per IP address based on configuration.
"""
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import time
import logging

from app.services.cache_service import CacheService
from app.config import settings

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware for rate limiting based on client IP.
    
    Uses Redis sliding window algorithm to track request counts per IP.
    Returns 429 Too Many Requests when limit is exceeded.
    
    Attributes:
        app: The ASGI application
        cache_service: Cache service for Redis operations
        limit: Maximum requests per window
        window: Time window in seconds
    """
    
    def __init__(
        self,
        app: ASGIApp,
        cache_service: CacheService,
        limit: int | None = None,
        window: int = 60
    ):
        """
        Initialize rate limit middleware.
        
        Args:
            app: The ASGI application
            cache_service: Cache service instance
            limit: Max requests per window (uses settings if not provided)
            window: Time window in seconds (default: 60)
        """
        super().__init__(app)
        self.cache_service = cache_service
        self.limit = limit or settings.RATE_LIMIT_PER_MINUTE
        self.window = window
    
    def _get_client_ip(self, request: Request) -> str:
        """
        Extract client IP from request.
        
        Checks X-Forwarded-For header for proxied requests,
        falls back to direct client IP.
        
        Args:
            request: FastAPI request object
            
        Returns:
            str: Client IP address
        """
        # Check X-Forwarded-For header (for reverse proxy setups)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Take the first IP in the chain
            return forwarded.split(",")[0].strip()
        
        # Fall back to direct client
        if request.client:
            return request.client.host
        
        return "unknown"
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Process request through rate limit check.
        
        Args:
            request: Incoming request
            call_next: Next middleware/endpoint handler
            
        Returns:
            Response: Either rate limit error or normal response
        """
        client_ip = self._get_client_ip(request)
        
        # Check rate limit
        is_allowed, remaining, reset_time = await self.cache_service.check_rate_limit(
            client_ip,
            limit=self.limit,
            window=self.window
        )
        
        if not is_allowed:
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            
            # Calculate retry-after in seconds
            retry_after = max(1, reset_time)
            
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Too many requests. Please try again later.",
                    "error_code": "RATE_LIMIT_EXCEEDED"
                },
                headers={
                    "X-RateLimit-Limit": str(self.limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time()) + reset_time),
                    "Retry-After": str(retry_after),
                }
            )
        
        # Process the request
        response = await call_next(request)
        
        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(self.limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + reset_time)
        
        return response