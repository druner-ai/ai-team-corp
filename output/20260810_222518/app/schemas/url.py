"""
Pydantic schemas for URL shortening operations.
"""
from pydantic import BaseModel, HttpUrl, Field, field_validator
from datetime import datetime
from typing import Optional


class ShortenRequest(BaseModel):
    """
    Request schema for creating a short URL.
    
    Attributes:
        url: The original URL to shorten. Must be valid HTTP/HTTPS URL.
    """
    url: HttpUrl = Field(
        ...,
        description="The original URL to shorten",
        max_length=2048,
    )
    
    @field_validator("url")
    @classmethod
    def validate_url_scheme(cls, v: HttpUrl) -> HttpUrl:
        """
        Validate that URL uses only http or https scheme.
        Prevents javascript:, file:, data:, ftp: schemes.
        
        Args:
            v: The URL to validate
            
        Returns:
            HttpUrl: Validated URL
            
        Raises:
            ValueError: If URL scheme is not http or https
        """
        scheme = str(v).split("://")[0].lower() if "://" in str(v) else ""
        if scheme not in ("http", "https"):
            raise ValueError(
                f"URL scheme '{scheme}' is not allowed. Only http and https are supported."
            )
        return v


class ShortenResponse(BaseModel):
    """
    Response schema for created short URL.
    
    Attributes:
        short_id: Generated short identifier
        short_url: Full short URL
        original_url: The original URL that was shortened
        created_at: Timestamp of creation
    """
    short_id: str
    short_url: str
    original_url: str
    created_at: datetime


class StatsResponse(BaseModel):
    """
    Response schema for URL statistics.
    
    Attributes:
        short_id: Short identifier
        original_url: The original URL
        click_count: Number of redirects
        created_at: Timestamp of creation
        is_active: Whether the URL is active
    """
    short_id: str
    original_url: str
    click_count: int
    created_at: datetime
    is_active: bool