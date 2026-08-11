"""
Common Pydantic schemas for the API.
"""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standard error response."""
    detail: str
    error_code: str | None = None
    extra: dict[str, Any] | None = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "ok"
    database: str = "up"
    redis: str = "up"
    timestamp: datetime = Field(default_factory=datetime.utcnow)