"""
Service layer for task business logic.

Orchestrates repository calls, handles validation,
and raises appropriate exceptions for error cases.
"""
import logging
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.task_exceptions import TaskNotFoundError
from app.models.task import Task
from app.repositories.task_repository import TaskRepository

logger = logging.getLogger(__name__)


class TaskService:
    """
    Service for task-related business operations.

    All methods are static and accept an AsyncSession,
    following the dependency injection pattern.
    """

    @staticmethod
    async def create_task(session: AsyncSession, title: str) -> Task:
        """
        Create a new task with the given title.

        Args:
            session: Database session.
            title: Task description (validated by Pydantic schema).

        Returns:
            The newly created Task instance.
        """
        logger.info("Creating task with title: '%s'", title)
        task = await TaskRepository.add(session, title)
        logger.info("Task created successfully: id=%d", task.id)
        return task

    @staticmethod
    async def get_all_tasks(session: AsyncSession) -> Sequence[Task]:
        """
        Retrieve all tasks ordered by creation time (newest first).

        Args:
            session: Database session.

        Returns:
            Sequence of all Task instances.
        """
        logger.info("Retrieving all tasks")
        tasks = await TaskRepository.get_all(session)
        logger.info("Retrieved %d tasks", len(tasks))
        return tasks

    @staticmethod
    async def update_task(session: AsyncSession, task_id: int, completed: bool) -> Task:
        """
        Update the completion status of a task.

        Args:
            session: Database session.
            task_id: ID of the task to update.
            completed: New completion status.

        Returns:
            The updated Task instance.

        Raises:
            TaskNotFoundError: If no task exists with the given ID.
        """
        logger.info("Updating task id=%d, completed=%s", task_id, completed)
        task = await TaskRepository.get_by_id(session, task_id)
        if task is None:
            logger.warning("Task not found for update: id=%d", task_id)
            raise TaskNotFoundError(task_id)
        updated_task = await TaskRepository.update(session, task, completed)
        logger.info("Task updated successfully: id=%d", task_id)
        return updated_task

    @staticmethod
    async def delete_task(session: AsyncSession, task_id: int) -> None:
        """
        Delete a task by its ID.

        Args:
            session: Database session.
            task_id: ID of the task to delete.

        Raises:
            TaskNotFoundError: If no task exists with the given ID.
        """
        logger.info("Deleting task id=%d", task_id)
        task = await TaskRepository.get_by_id(session, task_id)
        if task is None:
            logger.warning("Task not found for deletion: id=%d", task_id)
            raise TaskNotFoundError(task_id)
        await TaskRepository.delete(session, task)
        logger.info("Task deleted successfully: id=%d", task_id)