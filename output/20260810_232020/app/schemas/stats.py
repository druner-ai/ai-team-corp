"""
Schemas for the statistics endpoint.
"""

from datetime import datetime
from pydantic import BaseModel, Field


class StatsResponse(BaseModel):
    """
    Response schema for GET /stats/{short_code} endpoint.

    Attributes:
        short_code: The short code.
        original_url: The original long URL.
        clicks: Number of clicks/redirects.
        created_at: Creation timestamp.
    """

    short_code: str = Field(..., description="The short code")
    original_url: str = Field(..., description="The original long URL")
    clicks: int = Field(..., description="Number of clicks", ge=0)
    created_at: datetime = Field(..., description="Creation timestamp")

    model_config = {
        "json_schema_extra": {
            "example": {
                "short_code": "aB3x9Q",
                "original_url": "https://example.com/very/long/path?query=1",
                "clicks": 42,
                "created_at": "2025-01-15T10:30:00Z",
            }
        }
    }