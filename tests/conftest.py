import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.urls.repository import URLRepository


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    repo = URLRepository(db_path=":memory:")
    await repo.init_db()
    # Переопределяем репозиторий в приложении для использования in-memory БД
    app.dependency_overrides[get_repository] = lambda: repo
    yield
    app.dependency_overrides.clear()


from app.urls.router import get_repository
