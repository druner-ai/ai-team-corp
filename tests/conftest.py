import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import init_db, close_db, get_connection


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    # Инициализируем тестовую БД перед каждым тестом
    await init_db()
    yield
    # Закрываем соединение после теста
    await close_db()


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
