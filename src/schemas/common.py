"""
Common Pydantic schemas used across the API.
"""

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standard error response schema."""

    detail: str = Field(..., description="Error message describing what went wrong")
