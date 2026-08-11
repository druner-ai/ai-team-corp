# Pytest Patterns для Разработчика и QA

Машиночитаемые паттерны для тестирования FastAPI + SQLite (без ORM).

## Структура тестов

```
tests/
├── conftest.py          # fixtures, БД-инициализация
├── test_health.py       # smoke tests
├── test_create_url.py   # POST /shorten
├── test_redirect.py     # GET /{code}
├── test_stats.py        # GET /stats/{code}
└── test_url_info.py     # GET/DELETE /urls/{code}
```

## conftest.py — обязательный шаблон

```python
"""Fixtures для FastAPI + SQLite (без ORM) тестов.

Ключевые принципы:
1. In-memory SQLite (:memory:) — быстро, изолированно
2. scope="function" — новая БД на каждый тест
3. dependency_overrides — подмена зависимостей FastAPI
4. pytest-asyncio для async тестов
"""

import pytest
import sqlite3
from pathlib import Path
from httpx import AsyncClient, ASGITransport

# Путь к схеме (относительно tests/)
SCHEMA_PATH = Path(__file__).parent.parent / "sql" / "init.sql"


@pytest.fixture(scope="function")
def db_connection():
    """In-memory SQLite с применённой схемой."""
    # :memory: = in-memory database
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row  # dict-like доступ

    # Применяем схему
    if SCHEMA_PATH.exists():
        with open(SCHEMA_PATH) as f:
            conn.executescript(f.read())
    else:
        # Fallback: inline schema
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS urls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                short_code TEXT UNIQUE NOT NULL,
                original_url TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                visits INTEGER DEFAULT 0
            );
        """)
    conn.commit()

    yield conn

    conn.close()


@pytest.fixture(scope="function")
async def client(db_connection):
    """FastAPI test client с подменённой БД."""
    from app.main import app
    from app.database import get_db  # или как называется dependency

    # Подменяем зависимость
    def override_get_db():
        return db_connection

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac

    # Очищаем overrides
    app.dependency_overrides.clear()
```

## pytest.ini — обязательный файл

```ini
[pytest]
pythonpath = .
testpaths = tests
asyncio_mode = auto
```

> **КРИТИЧНО**: секция `[pytest]`, не `[tool:pytest]`!

## Примеры тестов

### Smoke test (health check)

```python
@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
```

### POST endpoint

```python
@pytest.mark.asyncio
async def test_create_short_url(client: AsyncClient):
    resp = await client.post("/shorten", json={"url": "https://example.com"})
    assert resp.status_code == 201
    data = resp.json()
    assert "short_code" in data
    assert len(data["short_code"]) == 6
```

### GET с редиректом

```python
@pytest.mark.asyncio
async def test_redirect(client: AsyncClient):
    # Создаём ссылку
    create_resp = await client.post("/shorten", json={"url": "https://example.com"})
    short_code = create_resp.json()["short_code"]

    # Переходим
    resp = await client.get(f"/{short_code}", follow_redirects=False)
    assert resp.status_code == 301
    assert resp.headers["location"] == "https://example.com"
```

### 404 handling

```python
@pytest.mark.asyncio
async def test_redirect_not_found(client: AsyncClient):
    resp = await client.get("/nonexistent")
    assert resp.status_code == 404
```

## Anti-patterns

| ❌ Не делай | ✅ Делай |
|:---|:---|
| `scope="module"` для БД | `scope="function"` — изоляция |
| Реальный файл `test.db` | `:memory:` — скорость |
| `TestClient` (sync) | `AsyncClient` + `ASGITransport` |
| `assert resp.status_code == 200` без проверки тела | Проверяй и код, и JSON |
| `print()` в тестах | `assert` с сообщением |
| `time.sleep()` | `await asyncio.sleep()` |

## QA Gate checklist

При ревью кода проверяй:

- [ ] `conftest.py` существует и инициализирует БД
- [ ] `pytest.ini` с `[pytest]` и `pythonpath = .`
- [ ] Тесты используют `AsyncClient`, не `TestClient`
- [ ] Каждый тест получает чистую БД (`scope="function"`)
- [ ] Проверяются не только status codes, но и JSON response
- [ ] Есть тесты на ошибки (404, 422, 400)
- [ ] `requirements-dev.txt` содержит `pytest`, `httpx`, `pytest-asyncio`
