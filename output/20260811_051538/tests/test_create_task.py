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