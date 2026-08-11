"""
Common response models for errors and health check.
"""
from pydantic import BaseModel
from typing import Any, Optional


class ErrorResponse(BaseModel):
    detail: str
    error_code: str = "error"
    status_code: int = 500
    extra: Optional[dict[str, Any]] = None


class HealthResponse(BaseModel):
    status: str
    db_connected: bool
    redis_connected: bool
    version: str = "1.0.0"