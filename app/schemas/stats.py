"""
Pydantic schemas for statistics-related API responses.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class ClickInfo(BaseModel):
    """Schema for a single click event."""

    clicked_at: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    referer: Optional[str] = None


class StatsResponse(BaseModel):
    """Schema for URL statistics response."""

    short_code: str
    clicks_count: int
    last_click_at: Optional[datetime] = None
    created_at: datetime
    recent_clicks: List[ClickInfo] = []
