from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class StatsResponse(BaseModel):
    """Response schema for URL statistics."""
    code: str
    original_url: str
    clicks: int
    created_at: datetime
    last_clicked_at: Optional[datetime] = None
