"""
Фикстуры и конфигурация для тестов pytest.
"""

import asyncio
import json
import os
import tempfile
from typing import AsyncGenerator, Generator

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.storage import JSONStorage


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Создание event loop для всей сессии тестов."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def temp_storage() -> AsyncGenerator[JSONStorage, None]:
    """
    Фикстура, создающая временный файл хранилища для тестов.

    Yields:
        Экземпляр JSONStorage, указывающий на временный файл.
    """
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
        tmp.write("[]")
        tmp_path = tmp.name

    storage = JSONStorage(tmp_path)
    await storage.initialize()
    yield storage

    # Очистка
    if os.path.exists(tmp_path):
        os.unlink(tmp_path)


@pytest.fixture
async def client(temp_storage: JSONStorage) -> AsyncGenerator[AsyncClient, None]:
    """
    Фикстура асинхронного HTTP-клиента для тестирования API.

    Переопределяет зависимость хранилища в приложении на тестовое.
    """
    # Подменяем глобальный storage в main на тестовый
    import app.main as main_module

    original_storage = main_module.storage
    main_module.storage = temp_storage

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    # Восстанавливаем оригинальное хранилище
    main_module.storage = original_storage


@pytest.fixture
def sample_note_data() -> dict:
    """Пример данных для создания заметки."""
    return {"title": "Тестовая заметка", "content": "Содержимое тестовой заметки"}
