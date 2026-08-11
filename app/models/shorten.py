from pydantic import BaseModel, HttpUrl, Field


class ShortenRequest(BaseModel):
    """Request schema for URL shortening."""
    url: HttpUrl = Field(..., description="The long URL to shorten")


class ShortenResponse(BaseModel):
    """Response schema after successful shortening."""
    code: str
    short_url: str
    original_url: str
