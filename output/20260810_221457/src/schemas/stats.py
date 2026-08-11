"""
    Schemas for /stats/{id} endpoint.
"""
from datetime import datetime
from pydantic import BaseModel

class StatsResponse(BaseModel):
    short_id: str
    original_url: str
    click_count: int
    created_at: datetime
    expires_at: datetime | None = None
    is_active: bool