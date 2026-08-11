from pydantic import BaseModel, HttpUrl, Field
from datetime import datetime


class LinkCreateRequest(BaseModel):
    """Schema for creating a short link (input)."""

    url: HttpUrl = Field(
        ...,
        description="Original URL to shorten",
        max_length=2048,
    )


class LinkResponse(BaseModel):
    """Response after successful short link creation."""

    short_code: str
    short_url: str
    original_url: str
    created_at: datetime


class StatsResponse(BaseModel):
    """Response for link statistics."""

    short_code: str
    original_url: str
    clicks: int
    created_at: datetime


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
