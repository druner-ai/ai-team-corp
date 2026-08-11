import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import settings

# Переопределяем настройки для тестов
settings.database_path = ":memory:"
settings.base_url = "http://testserver"
settings.short_code_length = 6
settings.rate_limit_per_minute = 1000  # отключаем ограничение в тестах


@pytest.fixture
async def client():
    """Создаёт асинхронный HTTP-клиент с тестовым приложением."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        yield ac
