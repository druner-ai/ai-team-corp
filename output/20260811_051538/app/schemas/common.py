"""
Common Pydantic schemas used across the application.
"""
from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """
    Standard error response schema.

    Attributes:
        detail: Human-readable error message.
    """
    detail: str

    model_config = {
        "json_schema_extra": {
            "example": {"detail": "Task not found"}
        }
    }