"""
Интеграционные тесты для API заметок.

Проверяют все CRUD-операции через HTTP-клиент.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_note(client: AsyncClient, sample_note_data: dict) -> None:
    """Тест создания заметки: POST /notes -> 201 Created."""
    response = await client.post("/notes", json=sample_note_data)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == sample_note_data["title"]
    assert data["content"] == sample_note_data["content"]
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data
    assert data["created_at"] == data["updated_at"]


@pytest.mark.asyncio
async def test_create_note_validation_error(client: AsyncClient) -> None:
    """Тест валидации при создании: пустой заголовок -> 422."""
    response = await client.post("/notes", json={"title": "", "content": "Текст"})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_all_notes_empty(client: AsyncClient) -> None:
    """Тест получения пустого списка заметок: GET /notes -> 200, []."""
    response = await client.get("/notes")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_all_notes_with_data(client: AsyncClient, sample_note_data: dict) -> None:
    """Тест получения списка заметок после создания одной."""
    await client.post("/notes", json=sample_note_data)
    response = await client.get("/notes")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == sample_note_data["title"]


@pytest.mark.asyncio
async def test_get_note_by_id(client: AsyncClient, sample_note_data: dict) -> None:
    """Тест получения заметки по ID: GET /notes/{id} -> 200."""
    create_resp = await client.post("/notes", json=sample_note_data)
    note_id = create_resp.json()["id"]

    response = await client.get(f"/notes/{note_id}")
    assert response.status_code == 200
    assert response.json()["id"] == note_id


@pytest.mark.asyncio
async def test_get_note_not_found(client: AsyncClient) -> None:
    """Тест получения несуществующей заметки: GET /notes/999 -> 404."""
    response = await client.get("/notes/999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_note(client: AsyncClient, sample_note_data: dict) -> None:
    """Тест обновления заметки: PUT /notes/{id} -> 200."""
    create_resp = await client.post("/notes", json=sample_note_data)
    note_id = create_resp.json()["id"]
    original_updated_at = create_resp.json()["updated_at"]

    update_data = {"title": "Обновленный заголовок", "content": "Обновленный текст"}
    response = await client.put(f"/notes/{note_id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == update_data["title"]
    assert data["content"] == update_data["content"]
    assert data["updated_at"] != original_updated_at


@pytest.mark.asyncio
async def test_update_note_partial(client: AsyncClient, sample_note_data: dict) -> None:
    """Тест частичного обновления: PUT /notes/{id} только с title -> 200."""
    create_resp = await client.post("/notes", json=sample_note_data)
    note_id = create_resp.json()["id"]

    update_data = {"title": "Только заголовок"}
    response = await client.put(f"/notes/{note_id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == update_data["title"]
    assert data["content"] == sample_note_data["content"]  # Не изменился


@pytest.mark.asyncio
async def test_update_note_not_found(client: AsyncClient) -> None:
    """Тест обновления несуществующей заметки: PUT /notes/999 -> 404."""
    response = await client.put("/notes/999", json={"title": "Неважно"})
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_note(client: AsyncClient, sample_note_data: dict) -> None:
    """Тест удаления заметки: DELETE /notes/{id} -> 204."""
    create_resp = await client.post("/notes", json=sample_note_data)
    note_id = create_resp.json()["id"]

    response = await client.delete(f"/notes/{note_id}")
    assert response.status_code == 204

    # Проверяем, что заметка действительно удалена
    get_resp = await client.get(f"/notes/{note_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_note_not_found(client: AsyncClient) -> None:
    """Тест удаления несуществующей заметки: DELETE /notes/999 -> 404."""
    response = await client.delete("/notes/999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_multiple_notes_ids_increment(client: AsyncClient, sample_note_data: dict) -> None:
    """Тест, что ID заметок увеличиваются последовательно."""
    resp1 = await client.post("/notes", json=sample_note_data)
    resp2 = await client.post("/notes", json=sample_note_data)
    resp3 = await client.post("/notes", json=sample_note_data)

    id1 = resp1.json()["id"]
    id2 = resp2.json()["id"]
    id3 = resp3.json()["id"]

    assert id2 == id1 + 1
    assert id3 == id2 + 1
