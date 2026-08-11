"""
Pydantic schemas for request/response validation and serialization.
"""

from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl


class ShortenRequest(BaseModel):
    """Request body for creating a short URL."""

    url: HttpUrl = Field(
        ...,
        description="The original long URL to shorten. Must start with http:// or https://.",
        max_length=2048,
    )


class ShortenResponse(BaseModel):
    """Response body after successfully creating a short URL."""

    code: str = Field(..., description="The generated short code.")
    short_url: str = Field(..., description="The full short URL.")
    original_url: str = Field(..., description="The original long URL.")


class StatsResponse(BaseModel):
    """Response body for URL statistics."""

    code: str = Field(..., description="The short code.")
    original_url: str = Field(..., description="The original long URL.")
    created_at: datetime = Field(..., description="Creation timestamp (UTC).")
    clicks: int = Field(..., description="Total number of redirects.")


class HealthResponse(BaseModel):
    """Response body for health check."""

    status: str = Field(default="ok", description="Service status.")
