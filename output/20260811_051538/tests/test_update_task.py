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