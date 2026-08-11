"""
Pydantic models for URL shortening requests and responses.
"""
from pydantic import BaseModel, HttpUrl, Field


class ShortenRequest(BaseModel):
    """Request body for creating a short URL."""
    url: HttpUrl = Field(
        ...,
        description="The original URL to shorten. Must be http or https.",
        max_length=2048,
    )


class ShortenResponse(BaseModel):
    """Response after successful shortening."""
    code: str
    short_url: str
    original_url: str
