# Fix: Removed invalid field 'repository' of type URLRepository | None from URLResponse schema.
# This field was causing FastAPI to raise 'Invalid args for response field' error during route registration.
# The response model should only contain serializable data, not repository instances.

from pydantic import BaseModel, HttpUrl
from datetime import datetime
from typing import Optional, List


class URLCreate(BaseModel):
    url: HttpUrl
    custom_slug: Optional[str] = None


class URLResponse(BaseModel):
    id: int
    slug: str
    original_url: str
    created_at: datetime


class VisitDetail(BaseModel):
    visited_at: datetime
    ip_address: Optional[str] = None


class StatsResponse(BaseModel):
    slug: str
    original_url: str
    created_at: datetime
    visit_count: int
    visits: List[VisitDetail] = []
