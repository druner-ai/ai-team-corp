"""
Pydantic-модели для контракта API.
"""
from pydantic import BaseModel
from typing import Literal


class HealthResponse(BaseModel):
    """
    Модель ответа для GET /health.
    """
    status: Literal["healthy", "unhealthy"]
    uptime_seconds: float
    version: str
