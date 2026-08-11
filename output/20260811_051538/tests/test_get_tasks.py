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