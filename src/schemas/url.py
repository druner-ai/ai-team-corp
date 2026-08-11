"""
Pydantic schemas for URL shortening API requests and responses.
"""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from src.utils.url_validator import validate_url


class ShortenRequest(BaseModel):
    """Request schema for creating a short URL."""

    url: str = Field(
        ...,
        max_length=2048,
        description="The original URL to shorten. Must use http or https scheme.",
        examples=["https://example.com/very/long/path?query=1"],
    )

    @field_validator("url")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        """
        Validate that the URL uses http or https scheme and is well-formed.

        Args:
            v: The URL string to validate.

        Returns:
            The validated URL string.

        Raises:
            ValueError: If the URL is invalid or uses a disallowed scheme.
        """
        return validate_url(v)


class ShortenResponse(BaseModel):
    """Response schema for a created short URL."""

    short_code: str = Field(..., description="The generated short code")
    short_url: str = Field(..., description="The full short URL")
    original_url: str = Field(..., description="The original URL that was shortened")


class StatsResponse(BaseModel):
    """Response schema for short URL statistics."""

    short_code: str = Field(..., description="The short code")
    original_url: str = Field(..., description="The original URL")
    clicks: int = Field(..., description="Number of clicks/redirects")
    created_at: str = Field(..., description="ISO 8601 timestamp of creation")
