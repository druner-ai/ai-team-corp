"""
Pydantic schemas for stats endpoint.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class StatsResponse(BaseModel):
    short_id: str
    original_url: str
    click_count: int
    created_at: datetime
    last_accessed_at: Optional[datetime]
    is_active: bool

    class Config:
        from_attributes = True