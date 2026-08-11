"""
Common Pydantic schemas for API responses.
"""
from pydantic import BaseModel
from typing import Optional


class ErrorResponse(BaseModel):
    """
    Standard error response schema.
    
    Attributes:
        detail: Human-readable error message
        error_code: Optional machine-readable error code
    """
    detail: str
    error_code: Optional[str] = None


class HealthResponse(BaseModel):
    """
    Health check response schema.
    
    Attributes:
        status: Service status (e.g., "healthy", "degraded")
        database: Database connection status
        redis: Redis connection status
    """
    status: str
    database: str
    redis: str