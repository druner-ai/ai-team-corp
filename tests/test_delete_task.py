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