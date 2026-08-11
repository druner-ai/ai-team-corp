"""
Pydantic schema for URL stats response.
"""
from pydantic import BaseModel
from datetime import datetime


class StatsResponse(BaseModel):
    """Response containing click statistics for a short URL."""
    id: str
    original_url: str
    clicks: int
    created_at: datetime

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "aB3x9Kq",
                "original_url": "https://example.com/very/long/path?query=1",
                "clicks": 142,
                "created_at": "2025-01-15T10:30:00Z",
            }
        }
    }