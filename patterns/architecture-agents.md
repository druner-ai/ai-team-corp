# Architecture Patterns для Архитектора

Машиночитаемые паттерны для проектирования FastAPI приложений.

## Структура проекта (domain-driven)

```
app/
├── {domain}/           # например: urls/, stats/, health/
│   ├── router.py       # API endpoints (@router.post("/shorten"))
│   ├── schemas.py      # Pydantic models (UrlCreate, UrlResponse)
│   ├── service.py      # Бизнес-логика (create_short_url())
│   ├── repository.py   # Работа с БД (save_url(), get_by_code())
│   ├── models.py       # SQLite table definitions (если нужно)
│   ├── exceptions.py   # Domain exceptions (UrlNotFound, InvalidUrl)
│   └── utils.py        # Helpers (generate_code(), validate_url())
├── config.py           # Settings (pydantic-settings)
├── database.py         # SQLite connection + get_db dependency
├── exceptions.py       # Global exceptions (AppException)
├── main.py             # FastAPI app + lifespan + routers include
└── middleware/         # Rate limiting, logging, CORS
    └── rate_limit.py

tests/
├── conftest.py         # Fixtures (db, client)
├── test_health.py
├── test_create_url.py
├── test_redirect.py
└── test_stats.py

sql/
└── init.sql            # Schema (CREATE TABLE ...)

Dockerfile
docker-compose.yml
pytest.ini
requirements.txt
requirements-dev.txt
.github/workflows/ci.yml
```

## Принципы

### 1. Domain-driven, не file-type

❌ Плохо (по типам файлов):
```
app/
├── routers/
│   ├── urls.py
│   └── stats.py
├── models/
│   ├── url.py
│   └── stats.py
└── services/
    ├── url_service.py
    └── stats_service.py
```

✅ Хорошо (по доменам):
```
app/
├── urls/
│   ├── router.py
│   ├── schemas.py
│   ├── service.py
│   └── repository.py
└── stats/
    ├── router.py
    ├── schemas.py
    ├── service.py
    └── repository.py
```

### 2. Слои (layers)

| Слой | Файл | Ответственность |
|:---|:---|:---|
| Router | `router.py` | HTTP, валидация, serialization |
| Service | `service.py` | Бизнес-логика, координация |
| Repository | `repository.py` | SQL-запросы, БД |
| Schema | `schemas.py` | Pydantic models (request/response) |

**Правило:** Router → Service → Repository. Не пропускай слои.

### 3. SQLite без ORM

```python
# app/database.py
import sqlite3
from contextlib import contextmanager

DATABASE_URL = "sqlite:///./data.db"

def get_db():
    """Dependency для FastAPI."""
    conn = sqlite3.connect(DATABASE_URL, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# app/urls/repository.py
from typing import Optional
from app.database import get_db

class UrlRepository:
    def __init__(self, db):
        self.db = db

    def save(self, short_code: str, original_url: str) -> int:
        cursor = self.db.execute(
            "INSERT INTO urls (short_code, original_url) VALUES (?, ?)",
            (short_code, original_url)
        )
        self.db.commit()
        return cursor.lastrowid

    def get_by_code(self, short_code: str) -> Optional[dict]:
        row = self.db.execute(
            "SELECT * FROM urls WHERE short_code = ?",
            (short_code,)
        ).fetchone()
        return dict(row) if row else None
```

### 4. Pydantic v2

```python
# app/urls/schemas.py
from pydantic import BaseModel, AnyUrl, Field

class UrlCreate(BaseModel):
    url: AnyUrl  # автоматическая валидация URL

class UrlResponse(BaseModel):
    short_code: str
    original_url: str
    created_at: str
    visits: int

class StatsResponse(BaseModel):
    short_code: str
    visits: int
    last_visited: str | None
```

### 5. FastAPI app assembly

```python
# app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.urls.router import router as urls_router
from app.stats.router import router as stats_router
from app.health import router as health_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: init DB, etc.
    from app.database import init_db
    init_db()
    yield
    # Shutdown: cleanup

app = FastAPI(
    title="URL Shortener API",
    lifespan=lifespan,
)

app.include_router(health_router, tags=["health"])
app.include_router(urls_router, prefix="/api", tags=["urls"])
app.include_router(stats_router, prefix="/api", tags=["stats"])
```

## API Design

### RESTful endpoints

| Метод | Путь | Описание | Response |
|:---|:---|:---|:---|
| POST | `/api/shorten` | Создать короткую ссылку | 201 + UrlResponse |
| GET | `/{short_code}` | Редирект на оригинал | 301 redirect |
| GET | `/api/stats/{short_code}` | Статистика переходов | 200 + StatsResponse |
| GET | `/api/urls/{short_code}` | Информация о ссылке | 200 + UrlResponse |
| DELETE | `/api/urls/{short_code}` | Удалить ссылку | 204 |
| GET | `/health` | Health check | 200 + {"status": "ok"} |

### Status codes

| Код | Когда |
|:---|:---|
| 200 | Успешный GET |
| 201 | Успешный POST (создано) |
| 204 | Успешный DELETE |
| 301 | Редирект |
| 400 | Невалидный ввод (client error) |
| 404 | Не найдено |
| 409 | Конфликт (duplicate) |
| 422 | Валидация Pydantic failed |
| 500 | Server error |

## Anti-patterns

| ❌ Не делай | ✅ Делай |
|:---|:---|
| Вся логика в `main.py` | Разделение по доменам |
| Прямой SQL в router | Repository pattern |
| `dict` вместо Pydantic | `UrlResponse(BaseModel)` |
| `print()` для логов | `logging` module |
| Глобальные переменные | `pydantic-settings` |
| Sync DB driver в async | `aiosqlite` или threadpool |

## Checklist для Архитектора

При проектировании убедись:

- [ ] Структура по доменам, не по типам файлов
- [ ] Каждый домен имеет router/service/repository/schemas
- [ ] SQLite без ORM — через `sqlite3` module
- [ ] Pydantic v2 для валидации (AnyUrl, Field)
- [ ] FastAPI lifespan для startup/shutdown
- [ ] Health endpoint обязателен
- [ ] Правильные HTTP status codes
- [ ] dependency injection для БД (get_db)
