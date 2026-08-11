"""
Pydantic schemas for Task entity validation and serialization.

Defines request/response schemas for all task-related API endpoints.
"""
from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict


class TaskCreate(BaseModel):
    """
    Schema for creating a new task.

    Attributes:
        title: Task description, must be 1-500 characters.
    """
    title: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Task description",
        examples=["Купить хлеб"],
    )


class TaskUpdate(BaseModel):
    """
    Schema for updating an existing task.

    Only the completed status can be updated via PATCH.

    Attributes:
        completed: New completion status.
    """
    completed: bool = Field(
        ...,
        description="Whether the task is completed",
        examples=[True],
    )


class TaskResponse(BaseModel):
    """
    Schema for task data returned in API responses.

    Includes all fields of the Task entity with UTC timestamps.

    Attributes:
        id: Unique task identifier.
        title: Task description.
        completed: Completion status.
        created_at: Creation timestamp (UTC).
        updated_at: Last update timestamp (UTC).
    """
    id: int
    title: str
    completed: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "title": "Купить хлеб",
                "completed": False,
                "created_at": "2025-01-15T10:30:00Z",
                "updated_at": "2025-01-15T10:30:00Z",
            }
        },
    )