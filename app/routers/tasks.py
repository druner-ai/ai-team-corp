"""
Task CRUD API router.

Implements all task-related endpoints as specified in the API contracts:
- POST /api/v1/tasks - Create a new task
- GET /api/v1/tasks - List all tasks
- PATCH /api/v1/tasks/{id} - Update task completion status
- DELETE /api/v1/tasks/{id} - Delete a task
"""
import logging
from typing import Sequence

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.task import TaskCreate, TaskResponse, TaskUpdate
from app.services.task_service import TaskService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


@router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new task",
    description="Creates a new TODO task with the provided title.",
)
async def create_task(
    task_data: TaskCreate,
    session: AsyncSession = Depends(get_db),
) -> TaskResponse:
    """
    Create a new task.

    Args:
        task_data: Validated task creation data (title).
        session: Database session (injected).

    Returns:
        The created task with all fields populated.
    """
    logger.info("POST /api/v1/tasks - Creating task")
    task = await TaskService.create_task(session, task_data.title)
    return TaskResponse.model_validate(task)


@router.get(
    "",
    response_model=list[TaskResponse],
    status_code=status.HTTP_200_OK,
    summary="List all tasks",
    description="Returns all tasks ordered by creation time (newest first).",
)
async def get_tasks(
    session: AsyncSession = Depends(get_db),
) -> Sequence[TaskResponse]:
    """
    Retrieve all tasks.

    Args:
        session: Database session (injected).

    Returns:
        List of all tasks sorted by created_at DESC.
    """
    logger.info("GET /api/v1/tasks - Listing all tasks")
    tasks = await TaskService.get_all_tasks(session)
    return [TaskResponse.model_validate(task) for task in tasks]


@router.patch(
    "/{task_id}",
    response_model=TaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Update task completion status",
    description="Marks a task as completed or uncompleted.",
    responses={
        404: {
            "description": "Task not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Task not found"}
                }
            },
        }
    },
)
async def update_task(
    task_id: int,
    task_data: TaskUpdate,
    session: AsyncSession = Depends(get_db),
) -> TaskResponse:
    """
    Update task completion status.

    Args:
        task_id: ID of the task to update.
        task_data: Validated update data (completed flag).
        session: Database session (injected).

    Returns:
        The updated task.

    Raises:
        HTTPException 404: If task with given ID does not exist.
    """
    logger.info("PATCH /api/v1/tasks/%d - Updating task", task_id)
    task = await TaskService.update_task(session, task_id, task_data.completed)
    return TaskResponse.model_validate(task)


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a task",
    description="Permanently removes a task by its ID.",
    responses={
        404: {
            "description": "Task not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Task not found"}
                }
            },
        }
    },
)
async def delete_task(
    task_id: int,
    session: AsyncSession = Depends(get_db),
) -> None:
    """
    Delete a task.

    Args:
        task_id: ID of the task to delete.
        session: Database session (injected).

    Returns:
        None (204 No Content on success).

    Raises:
        HTTPException 404: If task with given ID does not exist.
    """
    logger.info("DELETE /api/v1/tasks/%d - Deleting task", task_id)
    await TaskService.delete_task(session, task_id)