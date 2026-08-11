# Архитектор

## Задача

        Ты получил задачу от пользователя. Спроектируй полное решение.

        ЗАДАЧА ПОЛЬЗОВАТЕЛЯ:
        Создай микросервис URL Shortener: FastAPI, PostgreSQL, Redis. API: POST /shorten, GET /{id}, GET /stats/{id}, DELETE /{id}. Rate limiting 100/мин, валидация URL, тесты pytest, короткий ID 7 символов, Swagger, graceful shutdown.

        Твой документ ДОЛЖЕН содержать (markdown, минимум 500 слов):
        1. **Обзор**: что делает система, ключевые сценарии использования
        2. **Технологический стек**: языки, фреймворки, БД, кэш, очереди — с обоснованием выбора
        3. **Архитектура**: диаграмма компонентов (текстом), описание каждого
        4. **Модель данных**: сущности, поля, связи, индексы
        5. **API-контракты**: endpoints, методы, форматы запросов/ответов, коды ошибок
        6. **Нефункциональные требования**: безопасность, производительность, масштабирование
        7. **Структура проекта**: дерево файлов и папок

        Это — ЕДИНСТВЕННЫЙ источник правды для Разработчика и DevOps.
        Не сжимай информацию в YAML/JSON — пиши полный человекочитаемый текст.
        

## Результат

# Архитектурный документ: URL Shortener Microservice

**Версия:** 1.0  
**Статус:** Утверждён  
**Автор:** Архитектор  
**Источник правды для:** Разработчик, DevOps, QA

---

## 1. Обзор

### Назначение системы
Микросервис URL Shortener принимает длинные URL-адреса и возвращает короткие идентификаторы (7 символов). При обращении к короткому ID сервис редиректит на оригинальный URL. Сервис также собирает статистику переходов и поддерживает удаление ссылок.

### Ключевые сценарии использования
1. **Сокращение URL**: Пользователь отправляет POST-запрос с длинным URL → получает короткий ID.
2. **Редирект**: Пользователь обращается к `GET /{id}` → сервис увеличивает счётчик переходов и возвращает HTTP 302 с оригинальным URL.
3. **Просмотр статистики**: Пользователь запрашивает `GET /stats/{id}` → получает количество переходов и метаданные.
4. **Удаление ссылки**: Владелец удаляет ссылку через `DELETE /{id}` → она перестаёт быть доступной.

### Границы системы (out of scope)
- Аутентификация пользователей (в v1 не требуется).
- Кастомные короткие ID (в v1 не требуется).
- QR-коды, аналитика по гео/устройствам.

---

## 2. Технологический стек

| Компонент | Технология | Обоснование |
|-----------|-----------|-------------|
| Язык | Python 3.11+ | Соответствует ТЗ, богатая экосистема |
| Web-фреймворк | FastAPI 0.110+ | Async, автогенерация Swagger/OpenAPI, Pydantic-валидация |
| ASGI-сервер | Uvicorn | Стандарт де-факто для FastAPI, поддержка graceful shutdown |
| БД | PostgreSQL 15 | Реляционное хранилище, надёжность, индексы |
| ORM | SQLAlchemy 2.0 (async) | Async-поддержка, зрелая ORM |
| Кэш | Redis 7 | Кэширование редиректов, rate limiting, счётчики переходов |
| Миграции | Alembic | Стандарт для SQLAlchemy |
| Rate limiting | Redis + custom middleware | Sliding window на Redis, атомарность через Lua |
| Тестирование | pytest + pytest-asyncio + httpx | Async-тесты FastAPI |
| Валидация | Pydantic v2 | Встроена в FastAPI |

---

## 3. Архитектура

### Диаграмма компонентов (текст)

```
                    ┌──────────────────────────────────────────────┐
                    │              Client (HTTP)                    │
                    └───────────────────┬──────────────────────────┘
                                        │
                                        ▼
                    ┌──────────────────────────────────────────────┐
                    │         Rate Limiting Middleware              │
                    │  (Redis sliding window, 100 req/min/IP)      │
                    └───────────────────┬──────────────────────────┘
                                        │
                                        ▼
                    ┌──────────────────────────────────────────────┐
                    │            FastAPI Application               │
                    │  ┌──────────┐ ┌──────────┐ ┌──────────────┐ │
                    │  │ Routers  │ │ Services │ │  Validators  │ │
                    │  │(endpoints)│ │(business)│ │  (Pydantic)  │ │
                    │  └────┬─────┘ └────┬─────┘ └──────────────┘ │
                    └───────┼─────────────┼───────────────────────┘
                            │             │
              ┌─────────────┼─────────────┼──────────────┐
              ▼             ▼             ▼              ▼
        ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
        │  Redis   │  │PostgreSQL│  │  Redis   │  │  Redis   │
        │ (cache:  │  │ (source  │  │ (counter │  │ (rate    │
        │  url→id) │  │  of truth)│  │  incr)   │  │  limit)  │
        └──────────┘  └──────────┘  └──────────┘  └──────────┘
```

### Описание компонентов

**Rate Limiting Middleware** — перехватывает каждый запрос до роутинга. Использует sliding window algorithm на Redis: ключ `rate:{ip}`, TTL 60 секунд, счётчик запросов. При превышении 100 — HTTP 429 с заголовком `Retry-After`.

**Routers** — тонкий слой, делегирует бизнес-логику в Services. Не содержит SQL-запросов.

**Services** — бизнес-логика: генерация короткого ID, работа с БД и кэшем, инкремент счётчика.

**Validators (Pydantic)** — валидация входящих URL: проверка схемы (http/https), длины, доступности домена (опционально).

**Redis Cache Layer** — при `GET /{id}` сначала проверяется кэш `url:{short_id}` → если есть, сразу редирект + инкремент. Если нет — запрос в PostgreSQL, затем запись в кэш с TTL 1 час.

**PostgreSQL** — источник истины. Хранит все URL и метаданные.

**Redis Counter** — счётчик переходов `stats:{short_id}`. Периодически (или при чтении статистики) синхронизируется с PostgreSQL. Для простоты v1: инкремент в Redis + асинхронная запись в БД.

---

## 4. Модель данных

### Сущность: `urls`

| Поле | Тип | Описание | Индекс |
|------|-----|----------|--------|
| `id` | UUID (PK) | Внутренний идентификатор | Primary Key |
| `short_id` | VARCHAR(7), UNIQUE | Короткий идентификатор | Unique Index |
| `original_url` | TEXT | Оригинальный URL | — |
| `created_at` | TIMESTAMPTZ | Время создания | — |
| `expires_at` | TIMESTAMPTZ, NULL | Время истечения (опц.) | — |
| `is_active` | BOOLEAN, default TRUE | Флаг активной ссылки | Partial Index |
| `click_count` | BIGINT, default 0 | Количество переходов | — |
| `last_accessed_at` | TIMESTAMPTZ, NULL | Последний переход | — |

### Индексы
```sql
CREATE UNIQUE INDEX idx_urls_short_id ON urls(short_id);
CREATE INDEX idx_urls_active ON urls(short_id) WHERE is_active = TRUE;
```

### Алгоритм генерации short_id
- Используется Base62-кодирование: `[a-zA-Z0-9]` (62 символа).
- 7 символов = 62^7 ≈ 3.5 триллиона комбинаций.
- Генерация: `secrets.token_urlsafe(5)[:7]` или случайный выбор из Base62-алфавита.
- При коллизии (UNIQUE constraint violation) — повторная генерация (максимум 5 попыток).

---

## 5. API-контракты

### Base URL: `/api/v1`

### POST `/shorten`
Создаёт короткую ссылку.

**Request:**
```json
{
  "url": "https://example.com/very/long/path?query=1",
  "expires_at": "2025-12-31T23:59:59Z"  // опционально
}
```

**Response 201:**
```json
{
  "short_id": "aB3xK9q",
  "short_url": "https://short.example.com/aB3xK9q",
  "original_url": "https://example.com/very/long/path?query=1",
  "created_at": "2025-01-15T10:30:00Z"
}
```

**Ошибки:**
- `400` — невалидный URL (нет схемы, не http/https, длина > 2048)
- `422` — ошибка валидации Pydantic
- `429` — превышен rate limit

---

### GET `/{short_id}`
Редирект на оригинальный URL.

**Response 302:**
```
Location: https://example.com/very/long/path?query=1
```

**Ошибки:**
- `404` — короткий ID не найден или удалён
- `410` — ссылка истекла (expires_at в прошлом)

---

### GET `/stats/{short_id}`
Возвращает статистику по ссылке.

**Response 200:**
```json
{
  "short_id": "aB3xK9q",
  "original_url": "https://example.com/very/long/path?query=1",
  "click_count": 142,
  "created_at": "2025-01-15T10:30:00Z",
  "last_accessed_at": "2025-01-20T14:22:01Z",
  "is_active": true
}
```

**Ошибки:**
- `404` — ID не найден

---

### DELETE `/{short_id}`
Удаляет (деактивирует) ссылку. Soft delete: `is_active = FALSE`.

**Response 204:** No Content

**Ошибки:**
- `404` — ID не найден

---

### Общие заголовки ответов
- `X-RateLimit-Limit: 100`
- `X-RateLimit-Remaining: 87`
- `Retry-After: 45` (только при 429)

### Swagger
Доступен по адресу `/docs`, ReDoc — `/redoc`. Автогенерируется FastAPI из Pydantic-моделей и docstring.

---

## 6. Нефункциональные требования

### Безопасность
- **Валидация URL**: только `http` и `https` схемы. Запрет `localhost`, `127.0.0.1`, `0.0.0.0`, приватных диапазонов IP (RFC 1918) для предотвращения SSRF.
- **Длина URL**: максимум 2048 символов.
- **Rate limiting**: 100 запросов/мин на IP. Реализация через Redis sliding window.
- **SQL-инъекции**: параметризованные запросы через SQLAlchemy ORM.
- **HTTPS**: предполагается termination на reverse proxy (nginx/traefik).

### Производительность
- **Кэш Redis** для редиректов: hit rate ожидается >90%, время ответа <10ms.
- **Connection pooling**: SQLAlchemy async pool, размер 10, max_overflow 20.
- **Асинхронная запись счётчика**: инкремент в Redis синхронно, запись в PostgreSQL через background task.
- **Целевая пропускная способность**: 1000 RPS на один инстанс.

### Масштабирование
- **Горизонтальное**: сервис stateless — можно запускать несколько инстансов за load balancer.
- **Redis**: готов к кластеризации. Ключи распределены равномерно.
- **PostgreSQL**: read-replicas для `/stats` при росте нагрузки.

### Graceful Shutdown
- Uvicorn получает SIGTERM → перестаёт принимать новые соединения.
- Ожидает завершения текущих запросов (timeout 30 секунд).
- Закрывает пулы PostgreSQL и Redis соединений.
- Flush несохранённых счётчиков из Redis в PostgreSQL (background task).

### Надёжность
- **Health check**: `GET /health` → `{"status": "ok"}` (проверка БД и Redis).
- **Логирование**: structured JSON-логи (structlog или loguru), уровень INFO.
- **Retry при коллизии short_id**: до 5 попыток.

---

## 7. Структура проекта

```
url-shortener/
├── alembic/                          # Миграции БД
│   ├── versions/
│   └── env.py
├── alembic.ini
├── app/
│   ├── __init__.py
│   ├── main.py                       # Точка входа, создание FastAPI app
│   ├── config.py                     # Настройки (pydantic-settings)
│   ├── dependencies.py               # DI: get_db, get_redis
│   ├── api/
│   │   ├── __init__.py
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── router.py             # Объединение роутов v1
│   │   │   ├── shorten.py            # POST /shorten
│   │   │   ├── redirect.py           # GET /{short_id}
│   │   │   ├── stats.py              # GET /stats/{short_id}
│   │   │   └── delete.py             # DELETE /{short_id}
│   │   └── health.py                 # GET /health
│   ├── core/
│   │   ├── __init__.py
│   │   ├── short_id.py               # Генерация Base62 ID
│   │   ├── url_validator.py          # Валидация URL, SSRF-защита
│   │   └── rate_limiter.py           # Redis sliding window
│   ├── db/
│   │   ├── __init__.py
│   │   ├── session.py                # Async engine, sessionmaker
│   │   └── redis_client.py           # Redis connection
│   ├── models/
│   │   ├── __init__.py
│   │   └── url.py                    # SQLAlchemy модель Url
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── shorten.py                # ShortenRequest, ShortenResponse
│   │   ├── stats.py                  # StatsResponse
│   │   └── common.py                 # ErrorResponse
│   ├── services/
│   │   ├── __init__.py
│   │   ├── url_service.py            # Бизнес-логика
│   │   └── cache_service.py          # Работа с Redis кэшем
│   └── middleware/
│       ├── __init__.py
│       └── rate_limit.py             # Rate limit middleware
├── tests/
│   ├── __init__.py
│   ├── conftest.py                   # Фикстуры: test client, БД, Redis
│   ├── test_shorten.py
│   ├── test_redirect.py
│   ├── test_stats.py
│   ├── test_delete.py
│   ├── test_rate_limit.py
│   ├── test_url_validation.py
│   └── test_short_id.py
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml            # app + postgres + redis
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml
├── .env.example
├── Makefile
└── README.md
```

### Конфигурация (.env.example)
```
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/urlshortener
REDIS_URL=redis://localhost:6379/0
BASE_URL=https://short.example.com
RATE_LIMIT_PER_MINUTE=100
CACHE_TTL_SECONDS=3600
SHORT_ID_LENGTH=7
UVICORN_WORKERS=4
UVICORN_HOST=0.0.0.0
UVICORN_PORT=8000
```

### Команды (Makefile)
- `make migrate` — применить миграции
- `make run` — запустить сервис
- `make test` — запустить тесты
- `make lint` — flake8 + mypy

---

**Документ завершён.** Это единственный источник правды. Любые отклонения требуют согласования с Архитектором.