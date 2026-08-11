"""
Pydantic models for statistics responses.
"""
from pydantic import BaseModel
from typing import Optional


class ClickInfo(BaseModel):
    """Information about a single click."""
    clicked_at: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class StatsResponse(BaseModel):
    """Response containing statistics for a short URL."""
    code: str
    original_url: str
    created_at: str
    total_clicks: int
    recent_clicks: list[ClickInfo]
