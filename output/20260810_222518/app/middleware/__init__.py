"""
Middleware package initialization.
"""
from app.middleware.rate_limit import RateLimitMiddleware

__all__ = ["RateLimitMiddleware"]