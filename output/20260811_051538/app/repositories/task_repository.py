"""
Repository for Task entity database operations.

Encapsulates all SQLAlchemy queries for the tasks table,
providing a clean interface for CRUD operations.
"""
import logging
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task

logger = logging.getLogger(__name__)


class TaskRepository:
    """
    Repository for Task CRUD operations.

    All methods are static and accept an AsyncSession as the first parameter,
    following the dependency injection pattern used in FastAPI.
    """

    @staticmethod
    async def add(session: AsyncSession, title: str) -> Task:
        """
        Create and persist a new task.

        Args:
            session: Database session.
            title: Task description.

        Returns:
            The newly created Task instance with generated ID and timestamps.
        """
        task = Task(title=title)
        session.add(task)
        await session.commit()
        await session.refresh(task)
        logger.debug("Created task: id=%d, title='%s'", task.id, task.title)
        return task

    @staticmethod
    async def get_all(session: AsyncSession) -> Sequence[Task]:
        """
        Retrieve all tasks ordered by creation time (newest first).

        Args:
            session: Database session.

        Returns:
            Sequence of Task instances sorted by created_at DESC.
        """
        result = await session.execute(
            select(Task).order_by(Task.created_at.desc())
        )
        tasks = result.scalars().all()
        logger.debug("Retrieved %d tasks", len(tasks))
        return tasks

    @staticmethod
    async def get_by_id(session: AsyncSession, task_id: int) -> Task | None:
        """
        Retrieve a single task by its ID.

        Args:
            session: Database session.
            task_id: Task identifier.

        Returns:
            Task instance if found, None otherwise.
        """
        result = await session.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()
        if task:
            logger.debug("Found task: id=%d", task_id)
        else:
            logger.debug("Task not found: id=%d", task_id)
        return task

    @staticmethod
    async def update(session: AsyncSession, task: Task, completed: bool) -> Task:
        """
        Update the completion status of a task.

        Args:
            session: Database session.
            task: Task instance to update.
            completed: New completion status.

        Returns:
            The updated Task instance.
        """
        task.completed = completed
        await session.commit()
        await session.refresh(task)
        logger.debug("Updated task: id=%d, completed=%s", task.id, task.completed)
        return task

    @staticmethod
    async def delete(session: AsyncSession, task: Task) -> None:
        """
        Delete a task from the database.

        Args:
            session: Database session.
            task: Task instance to delete.
        """
        await session.delete(task)
        await session.commit()
        logger.debug("Deleted task: id=%d", task.id)