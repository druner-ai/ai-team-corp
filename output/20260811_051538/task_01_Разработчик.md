# Разработчик

## Задача

        Напиши код строго по архитектурному документу, который создал Архитектор.

        ТРЕБОВАНИЯ:
        - Весь код в одном ответе (не по частям)
        - Каждый файл в markdown-блоке с указанием пути: ```python path/to/file.py
        - Включай requirements.txt или pyproject.toml
        - Включай тесты (pytest)
        - Включай .env.example
        - Если в архитектурном документе есть неясности — отметь в комментариях кода

        КАЧЕСТВО:
        - Типизация (type hints) на всех публичных функциях
        - Документирующие комментарии к классам и сложным функциям
        - Обработка ошибок (не голые try/except)
        - Валидация входных данных
        

## Результат

```python requirements.txt
# Core
fastapi==0.110.0
uvicorn[standard]==0.27.1
sqlalchemy[asyncio]==2.0.25
aiosqlite==0.19.0
alembic==1.13.1
pydantic==2.5.3
pydantic-settings==2.1.0

# Dev
pytest==8.0.0
pytest-asyncio==0.23.3
httpx==0.26.0
ruff==0.1.14
black==24.1.1
```

```python .env.example
DATABASE_URL=sqlite+aiosqlite:///./data/tasks.db
LOG_LEVEL=INFO
APP_ENV=development
```

```python app/__init__.py
"""
TODO REST API application package.
"""
```

```python app/config.py
"""
Application configuration using Pydantic Settings.

Reads configuration from environment variables with sensible defaults.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Attributes:
        DATABASE_URL: SQLAlchemy database connection string.
        LOG_LEVEL: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        APP_ENV: Application environment (development, production).
    """

    DATABASE_URL: str = "sqlite+aiosqlite:///./data/tasks.db"
    LOG_LEVEL: str = "INFO"
    APP_ENV: str = "development"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


settings = Settings()
```

```python app/database.py
"""
Database initialization and session management.

Creates the async SQLAlchemy engine, session factory, and provides
a FastAPI dependency for obtaining database sessions.
"""
import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings

logger = logging.getLogger(__name__)

# Create async engine with SQLite-specific configuration
# StaticPool ensures a single connection is reused (required for SQLite with WAL mode)
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.APP_ENV == "development",
    poolclass=StaticPool,
    connect_args={"check_same_thread": False},
)

# Async session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides an async database session.

    Yields an AsyncSession and ensures it is closed after the request completes.

    Yields:
        AsyncSession: SQLAlchemy async session for database operations.
    """
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Initialize database: enable WAL mode and create all tables.

    Should be called once at application startup.
    WAL mode allows concurrent reads without blocking writers.
    """
    async with engine.begin() as conn:
        # Enable WAL mode for better concurrent read performance
        await conn.exec_driver_sql("PRAGMA journal_mode=WAL;")
        # Enable foreign keys (good practice, though not strictly needed here)
        await conn.exec_driver_sql("PRAGMA foreign_keys=ON;")

    # Create all tables defined in models
    from app.models.task import Base  # noqa: F401 - imported for table registration

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database initialized successfully with WAL mode enabled.")
```

```python app/models/__init__.py
"""
SQLAlchemy ORM models package.
"""
from app.models.task import Task  # noqa: F401

```

```python app/models/task.py
"""
SQLAlchemy ORM model for the Task entity.

Defines the tasks table schema with all columns and constraints
as specified in the architecture document.
"""
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


class Task(Base):
    """
    Task entity representing a single TODO item.

    Attributes:
        id: Auto-incrementing primary key.
        title: Task description (1-500 characters).
        completed: Whether the task is done (default False).
        created_at: UTC timestamp of creation.
        updated_at: UTC timestamp of last update.
    """

    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Index for efficient ordering by creation time (newest first)
    __table_args__ = (
        Index("idx_tasks_created_at", created_at.desc()),
    )

    def __repr__(self) -> str:
        return f"<Task(id={self.id}, title='{self.title[:30]}...', completed={self.completed})>"
```

```python app/schemas/__init__.py
"""
Pydantic schemas package for request/response validation.
"""
from app.schemas.task import TaskCreate, TaskUpdate, TaskResponse  # noqa: F401
from app.schemas.common import ErrorResponse  # noqa: F401

```

```python app/schemas/common.py
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
```

```python app/schemas/task.py
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
```

```python app/exceptions/__init__.py
"""
Custom exceptions package.
"""
from app.exceptions.task_exceptions import TaskNotFoundError  # noqa: F401

```

```python app/exceptions/task_exceptions.py
"""
Custom exceptions for task-related operations.

These exceptions are caught by FastAPI exception handlers
and converted to appropriate HTTP responses.
"""


class TaskNotFoundError(Exception):
    """
    Raised when a requested task does not exist in the database.

    Attributes:
        task_id: The ID of the task that was not found.
    """

    def __init__(self, task_id: int) -> None:
        self.task_id = task_id
        super().__init__(f"Task with id={task_id} not found")
```

```python app/repositories/__init__.py
"""
Repository layer package.

Repositories encapsulate database queries and provide
a clean interface for data access operations.
"""
from app.repositories.task_repository import TaskRepository  # noqa: F401

```

```python app/repositories/task_repository.py
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
```

```python app/services/__init__.py
"""
Service layer package.

Services contain business logic and orchestrate
repository calls with proper error handling.
"""
from app.services.task_service import TaskService  # noqa: F401

```

```python app/services/task_service.py
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
```

```python app/routers/__init__.py
"""
API routers package.

Contains FastAPI routers for all API endpoints.
"""
from app.routers.tasks import router as tasks_router  # noqa: F401
from app.routers.health import router as health_router  # noqa: F401

```

```python app/routers/health.py
"""
Health check endpoint router.

Provides a simple endpoint for monitoring application availability.
"""
import logging

from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    """
    Health check endpoint.

    Returns a simple status indicator to confirm the API is running.

    Returns:
        dict with status "ok".
    """
    logger.debug("Health check requested")
    return {"status": "ok"}
```

```python app/routers/tasks.py
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
```

```python app/main.py
"""
FastAPI application entry point.

Creates the FastAPI app instance, registers routers,
configures exception handlers, and sets up startup/shutdown events.
"""
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import init_db
from app.exceptions.task_exceptions import TaskNotFoundError
from app.routers.health import router as health_router
from app.routers.tasks import router as tasks_router

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="TODO REST API",
    description="Minimalist REST API for managing a TODO list",
    version="1.0.0",
    docs_url="/docs",
    redoc_url=None,  # Disable ReDoc for simplicity
)

# Register routers
app.include_router(tasks_router)
app.include_router(health_router)


# Exception handlers
@app.exception_handler(TaskNotFoundError)
async def task_not_found_handler(request: Request, exc: TaskNotFoundError) -> JSONResponse:
    """
    Convert TaskNotFoundError to HTTP 404 response.

    Args:
        request: The incoming request.
        exc: The caught exception.

    Returns:
        JSON response with 404 status and error detail.
    """
    logger.warning("TaskNotFoundError handled: %s", exc)
    return JSONResponse(
        status_code=404,
        content={"detail": "Task not found"},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catch-all handler for unexpected exceptions.

    Args:
        request: The incoming request.
        exc: The caught exception.

    Returns:
        JSON response with 500 status and generic error message.
    """
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# Startup event
@app.on_event("startup")
async def startup_event() -> None:
    """
    Initialize database on application startup.

    Enables WAL mode and creates tables if they don't exist.
    """
    logger.info("Starting TODO REST API in %s mode", settings.APP_ENV)
    await init_db()
    logger.info("Application startup complete")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Clean up resources on application shutdown."""
    logger.info("Application shutting down")
```

```python tests/__init__.py
"""
Test package for TODO REST API.
"""
```

```python tests/conftest.py
"""
Pytest fixtures for testing the TODO REST API.

Provides an async test client and a fresh test database
for each test session.
"""
import asyncio
import os
import tempfile
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

# Set test environment before importing app modules
os.environ["APP_ENV"] = "testing"
os.environ["LOG_LEVEL"] = "DEBUG"

from app.database import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models.task import Base  # noqa: E402


@pytest_asyncio.fixture(scope="session")
def event_loop():
    """Create a single event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """
    Create a temporary SQLite database for testing.

    Uses an in-memory database with StaticPool for isolation.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Clean up
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_session_factory(test_engine):
    """Create a session factory bound to the test engine."""
    factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    return factory


@pytest_asyncio.fixture(scope="function")
async def test_session(test_session_factory) -> AsyncGenerator[AsyncSession, None]:
    """Provide a test database session."""
    async with test_session_factory() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client(test_session_factory) -> AsyncGenerator[AsyncClient, None]:
    """
    Create an async HTTP test client.

    Overrides the get_db dependency to use the test database session.
    """

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with test_session_factory() as session:
            try:
                yield session
            finally:
                await session.close()

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
```

```python tests/test_create_task.py
"""
Tests for POST /api/v1/tasks endpoint.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_task_success(client: AsyncClient):
    """Test successful task creation."""
    response = await client.post(
        "/api/v1/tasks",
        json={"title": "Купить хлеб"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Купить хлеб"
    assert data["completed"] is False
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data
    assert data["created_at"] == data["updated_at"]


@pytest.mark.asyncio
async def test_create_task_empty_title(client: AsyncClient):
    """Test task creation with empty title returns 422."""
    response = await client.post(
        "/api/v1/tasks",
        json={"title": ""},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_task_title_too_long(client: AsyncClient):
    """Test task creation with title exceeding 500 characters returns 422."""
    response = await client.post(
        "/api/v1/tasks",
        json={"title": "A" * 501},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_task_missing_title(client: AsyncClient):
    """Test task creation without title field returns 422."""
    response = await client.post(
        "/api/v1/tasks",
        json={},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_task_increments_id(client: AsyncClient):
    """Test that task IDs auto-increment."""
    response1 = await client.post("/api/v1/tasks", json={"title": "Task 1"})
    response2 = await client.post("/api/v1/tasks", json={"title": "Task 2"})

    assert response1.status_code == 201
    assert response2.status_code == 201
    assert response2.json()["id"] == response1.json()["id"] + 1
```

```python tests/test_get_tasks.py
"""
Tests for GET /api/v1/tasks endpoint.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_tasks_empty(client: AsyncClient):
    """Test retrieving tasks when none exist returns empty list."""
    response = await client.get("/api/v1/tasks")

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_tasks_with_data(client: AsyncClient):
    """Test retrieving tasks returns all created tasks."""
    # Create some tasks
    await client.post("/api/v1/tasks", json={"title": "Task 1"})
    await client.post("/api/v1/tasks", json={"title": "Task 2"})
    await client.post("/api/v1/tasks", json={"title": "Task 3"})

    response = await client.get("/api/v1/tasks")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    assert all("id" in task for task in data)
    assert all("title" in task for task in data)
    assert all("completed" in task for task in data)
    assert all("created_at" in task for task in data)
    assert all("updated_at" in task for task in data)


@pytest.mark.asyncio
async def test_get_tasks_ordered_by_newest(client: AsyncClient):
    """Test that tasks are returned in descending order by created_at."""
    await client.post("/api/v1/tasks", json={"title": "Oldest"})
    await client.post("/api/v1/tasks", json={"title": "Middle"})
    await client.post("/api/v1/tasks", json={"title": "Newest"})

    response = await client.get("/api/v1/tasks")
    data = response.json()

    assert data[0]["title"] == "Newest"
    assert data[1]["title"] == "Middle"
    assert data[2]["title"] == "Oldest"
```

```python tests/test_update_task.py
"""
Tests for PATCH /api/v1/tasks/{id} endpoint.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_update_task_success(client: AsyncClient):
    """Test successful task completion update."""
    # Create a task first
    create_response = await client.post("/api/v1/tasks", json={"title": "Test task"})
    task_id = create_response.json()["id"]

    # Mark as completed
    response = await client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"completed": True},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == task_id
    assert data["completed"] is True
    assert data["title"] == "Test task"
    # updated_at should be different from created_at after update
    assert data["updated_at"] != data["created_at"]


@pytest.mark.asyncio
async def test_update_task_uncomplete(client: AsyncClient):
    """Test marking a completed task as uncompleted."""
    # Create and complete a task
    create_response = await client.post("/api/v1/tasks", json={"title": "Test task"})
    task_id = create_response.json()["id"]
    await client.patch(f"/api/v1/tasks/{task_id}", json={"completed": True})

    # Mark as uncompleted
    response = await client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"completed": False},
    )

    assert response.status_code == 200
    assert response.json()["completed"] is False


@pytest.mark.asyncio
async def test_update_task_not_found(client: AsyncClient):
    """Test updating a non-existent task returns 404."""
    response = await client.patch(
        "/api/v1/tasks/99999",
        json={"completed": True},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"


@pytest.mark.asyncio
async def test_update_task_invalid_id(client: AsyncClient):
    """Test updating with non-integer ID returns 422."""
    response = await client.patch(
        "/api/v1/tasks/abc",
        json={"completed": True},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_task_invalid_body(client: AsyncClient):
    """Test updating with invalid body returns 422."""
    create_response = await client.post("/api/v1/tasks", json={"title": "Test task"})
    task_id = create_response.json()["id"]

    response = await client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"completed": "not_a_boolean"},
    )

    assert response.status_code == 422
```

```python tests/test_delete_task.py
"""
Tests for DELETE /api/v1/tasks/{id} endpoint.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_delete_task_success(client: AsyncClient):
    """Test successful task deletion."""
    # Create a task first
    create_response = await client.post("/api/v1/tasks", json={"title": "Test task"})
    task_id = create_response.json()["id"]

    # Delete it
    response = await client.delete(f"/api/v1/tasks/{task_id}")

    assert response.status_code == 204
    assert response.content == b""

    # Verify it's gone
    get_response = await client.get("/api/v1/tasks")
    tasks = get_response.json()
    assert len(tasks) == 0


@pytest.mark.asyncio
async def test_delete_task_not_found(client: AsyncClient):
    """Test deleting a non-existent task returns 404."""
    response = await client.delete("/api/v1/tasks/99999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"


@pytest.mark.asyncio
async def test_delete_task_invalid_id(client: AsyncClient):
    """Test deleting with non-integer ID returns 422."""
    response = await client.delete("/api/v1/tasks/abc")

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_delete_task_twice(client: AsyncClient):
    """Test deleting the same task twice returns 404 on second attempt."""
    create_response = await client.post("/api/v1/tasks", json={"title": "Test task"})
    task_id = create_response.json()["id"]

    # First delete
    response1 = await client.delete(f"/api/v1/tasks/{task_id}")
    assert response1.status_code == 204

    # Second delete
    response2 = await client.delete(f"/api/v1/tasks/{task_id}")
    assert response2.status_code == 404
```

```python tests/test_health.py
"""
Tests for GET /health endpoint.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Test health check endpoint returns ok status."""
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

```python pyproject.toml
[project]
name = "todo-api"
version = "1.0.0"
description = "Minimalist REST API for managing a TODO list"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.110.0",
    "uvicorn[standard]>=0.27.1",
    "sqlalchemy[asyncio]>=2.0.25",
    "aiosqlite>=0.19.0",
    "alembic>=1.13.1",
    "pydantic>=2.5.3",
    "pydantic-settings>=2.1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.3",
    "httpx>=0.26.0",
    "ruff>=0.1.14",
    "black>=24.1.1",
]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]

[tool.black]
line-length = 100
target-version = ["py311"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

```python Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY alembic.ini .
COPY alembic/ ./alembic/

# Create data directory for SQLite database
RUN mkdir -p /app/data

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml docker-compose.yml
version: "3.8"

services:
  api:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
    environment:
      - DATABASE_URL=sqlite+aiosqlite:///./data/tasks.db
      - LOG_LEVEL=INFO
      - APP_ENV=production
    restart: unless-stopped
```

```python alembic.ini
[alembic]
script_location = alembic
sqlalchemy.url = sqlite+aiosqlite:///./data/tasks.db

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

```python alembic/env.py
"""
Alembic environment configuration for async SQLAlchemy migrations.
"""
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.models.task import Base  # noqa: F401 - Import for model registration

# Alembic Config object
config = context.config

# Set up logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# MetaData for autogenerate support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    Configures the context with just a URL and not an Engine.
    Calls to context.execute() emit the given string to the script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Execute migrations in a synchronous context."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """
    Run migrations in 'online' mode with async engine.
    """
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

```python alembic/script.py.mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
```

```python alembic/versions/0001_initial.py
"""Initial migration - create tasks table

Revision ID: 0001
Revises: 
Create Date: 2025-01-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the tasks table with all columns and indexes."""
    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("completed", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_tasks_created_at",
        "tasks",
        [sa.text("created_at DESC")],
    )


def downgrade() -> None:
    """Remove the tasks table and its index."""
    op.drop_index("idx_tasks_created_at", table_name="tasks")
    op.drop_table("tasks")
```

```python .gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
.venv/
*.egg-info/
dist/
build/

# Environment
.env
*.env.local

# Database
data/
*.db
*.db-journal
*.db-wal

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Testing
.pytest_cache/
.coverage
htmlcov/

# Alembic
alembic/versions/*.pyc
```

```markdown README.md
# TODO REST API

Минималистичный REST API для управления списком задач (TODO).

## Возможности

- Создание задачи
- Получение списка всех задач (от новых к старым)
- Отметка задачи как выполненной/невыполненной
- Удаление задачи
- Health check эндпоинт

## Технологии

- Python 3.11+
- FastAPI
- SQLAlchemy 2.0 (async)
- SQLite (WAL mode)
- Pydantic v2
- Alembic (миграции)

## Быстрый старт

### Локальный запуск

1. Клонируйте репозиторий:
   ```bash
   git clone <repo-url>
   cd todo-api
   ```

2. Создайте виртуальное окружение и установите зависимости:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   # .venv\Scripts\activate  # Windows
   pip install -r requirements.txt
   ```

3. Скопируйте `.env.example` в `.env`:
   ```bash
   cp .env.example .env
   ```

4. Запустите приложение:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

5. Откройте http://localhost:8000/docs для Swagger UI.

### Docker

```bash
docker-compose up --build
```

## API Endpoints

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/api/v1/tasks` | Создать задачу |
| GET | `/api/v1/tasks` | Получить все задачи |
| PATCH | `/api/v1/tasks/{id}` | Обновить статус задачи |
| DELETE | `/api/v1/tasks/{id}` | Удалить задачу |
| GET | `/health` | Проверка работоспособности |

## Тестирование

```bash
pytest
```

## Переменные окружения

| Переменная | По умолчанию | Описание |
|------------|-------------|----------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./data/tasks.db` | Строка подключения к БД |
| `LOG_LEVEL` | `INFO` | Уровень логирования |
| `APP_ENV` | `development` | Окружение |
```