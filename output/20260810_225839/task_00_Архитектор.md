# Архитектор

## Задача

        Ты получил задачу от пользователя. Спроектируй полное решение.

        ЗАДАЧА ПОЛЬЗОВАТЕЛЯ:
        Создай микросервис URL Shortener: FastAPI, PostgreSQL, Redis. POST /shorten, GET /{id}, GET /stats/{id}, DELETE /{id}. Rate limiting, валидация URL, тесты pytest, Swagger.

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

## 1. Обзор

Микросервис URL Shortener принимает длинные URL-адреса и возвращает короткие ссылки. При обращении к короткой ссылке сервис выполняет HTTP-редирект на оригинальный URL. Сервис также предоставляет статистику переходов и возможность удаления ссылок.

**Ключевые сценарии использования:**

1. **Сокращение URL** — пользователь отправляет POST-запрос с длинным URL, получает короткий идентификатор (6 символов, base62).
2. **Редирект** — при обращении к `GET /{id}` сервис ищет URL в Redis (кэш), при отсутствии — в PostgreSQL, инкрементирует счётчик переходов и возвращает HTTP 302 с заголовком `Location`.
3. **Просмотр статистики** — `GET /stats/{id}` возвращает оригинальный URL, количество переходов, дату создания, дату последнего перехода.
4. **Удаление ссылки** — `DELETE /{id}` помечает ссылку как удалённую (soft delete), очищает кэш.

---

## 2. Технологический стек

| Компонент | Технология | Обоснование |
|---|---|---|
| Язык | Python 3.12 | Современная экосистема, типизация, быстрый старт |
| Web-фреймворк | FastAPI 0.115+ | Async-native, автогенерация OpenAPI/Swagger, валидация через Pydantic v2 |
| ORM | SQLAlchemy 2.0 (async) | Зрелый ORM с поддержкой async, типизированные сессии |
| БД | PostgreSQL 16 | Реляционная БД с надёжными транзакциями, индексами, расширяемостью |
| Кэш | Redis 7 | In-memory хранилище для кэширования редиректов и rate limiting |
| Миграции | Alembic | Стандарт де-факто для SQLAlchemy-миграций |
| Валидация | Pydantic v2 | Интегрирована в FastAPI, нативная валидация URL |
| Rate Limiting | slowapi (на базе limits) | Простая интеграция с FastAPI, Redis-бэкенд для распределённого лимитирования |
| Тестирование | pytest + httpx (AsyncClient) | Async-тесты, удобные фикстуры |
| Контейнеризация | Docker + docker-compose | Локальная разработка и деплой |
| Линтинг | ruff + mypy | Скорость ruff, строгая типизация mypy |

---

## 3. Архитектура

```
┌──────────────┐     ┌──────────────────────────────────┐     ┌─────────────┐
│   Client     │────▶│         FastAPI Application      │────▶│   Redis     │
│  (Browser/   │     │                                  │     │  (Cache +  │
│   curl)      │◀────│  ┌────────────────────────────┐  │◀────│  RateLimit) │
└──────────────┘     │  │     API Router Layer       │  │     └─────────────┘
                     │  │  (shorten, redirect, stats)│  │
                     │  └────────────┬───────────────┘  │     ┌─────────────┐
                     │               │                    │────▶│ PostgreSQL │
                     │  ┌────────────▼───────────────┐  │     │   (Source  │
                     │  │     Service Layer           │  │◀────│    of     │
                     │  │  (business logic, cache     │  │     │  Truth)   │
                     │  │   orchestration)            │  │     └─────────────┘
                     │  └────────────┬───────────────┘  │
                     │               │                    │
                     │  ┌────────────▼───────────────┐  │
                     │  │   Repository Layer          │  │
                     │  │  (SQLAlchemy + Redis DAO)  │  │
                     │  └────────────────────────────┘  │
                     └──────────────────────────────────┘
```

**Компоненты:**

- **API Router Layer** — определяет HTTP-эндпоинты, вызывает сервисный слой, возвращает HTTP-ответы. Не содержит бизнес-логики.
- **Service Layer** — оркестрирует бизнес-логику: генерация короткого ID, работа с кэшем, инкремент счётчиков, soft delete.
- **Repository Layer** — инкапсулирует доступ к PostgreSQL (через SQLAlchemy) и Redis. Сервисный слой не работает с сессиями БД напрямую.
- **Middleware** — rate limiting (slowapi), обработка исключений, логирование запросов.
- **Schema Layer (Pydantic)** — модели запросов и ответов, валидация.

---

## 4. Модель данных

### Сущность: `urls`

| Поле | Тип | Описание |
|---|---|---|
| `id` | `UUID` (PK, default `gen_random_uuid()`) | Внутренний идентификатор |
| `short_code` | `VARCHAR(6)` (UNIQUE, NOT NULL) | Короткий код, base62 (a-z, A-Z, 0-9) |
| `original_url` | `TEXT` (NOT NULL) | Оригинальный URL |
| `created_at` | `TIMESTAMPTZ` (NOT NULL, default `now()`) | Дата создания |
| `expires_at` | `TIMESTAMPTZ` (NULLABLE) | Дата истечения (опционально) |
| `is_deleted` | `BOOLEAN` (NOT NULL, default `false`) | Soft delete флаг |
| `click_count` | `BIGINT` (NOT NULL, default `0`) | Количество переходов |
| `last_clicked_at` | `TIMESTAMPTZ` (NULLABLE) | Время последнего перехода |

**Индексы:**

- `PK urls_pkey` на `id`
- `UNIQUE INDEX idx_urls_short_code` на `short_code` — основной индекс для поиска при редиректе
- `INDEX idx_urls_created_at` на `created_at` — для аналитики и очистки
- `INDEX idx_urls_expires_at` на `expires_at WHERE expires_at IS NOT NULL` — для джобы очистки истёкших ссылок

**Связи:** нет внешних ключей (одна сущность). При расширении можно добавить таблицу `clicks` для детальной аналитики (IP, user-agent, timestamp).

---

## 5. API-контракты

### POST /shorten

Создаёт короткую ссылку.

**Request:**
```json
{
  "url": "https://example.com/very/long/path?param=value",
  "expires_at": "2025-12-31T23:59:59Z"  // опционально
}
```

**Response 201 Created:**
```json
{
  "short_code": "aB3xQ9",
  "short_url": "http://localhost:8000/aB3xQ9",
  "original_url": "https://example.com/very/long/path?param=value",
  "created_at": "2025-01-15T10:30:00Z",
  "expires_at": "2025-12-31T23:59:59Z"
}
```

**Ошибки:**
- `422 Unprocessable Entity` — невалидный URL (Pydantic валидация)
- `429 Too Many Requests` — превышен rate limit

**Валидация URL:** Pydantic поле типа `HttpUrl` — проверяет схему (http/https), наличие домена. Дополнительно проверяется, что URL не указывает на localhost/приватные IP (защита от SSRF) через кастомный валидатор.

---

### GET /{short_code}

Выполняет редирект.

**Response 302 Found:**
```
Location: https://example.com/very/long/path?param=value
```

**Ошибки:**
- `404 Not Found` — код не существует или удалён
- `410 Gone` — ссылка истекла по `expires_at`
- `429 Too Many Requests` — превышен rate limit

**Логика:**
1. Проверить Redis по ключу `url:{short_code}`. Если найдено и не удалено — инкрементировать счётчик (Redis `HINCRBY`), обновить `last_clicked_at`, вернуть 302.
2. Если в кэше нет — запросить PostgreSQL. Если найдено — записать в Redis (TTL 1 час), инкрементировать счётчик в БД (асинхронно), вернуть 302.
3. Если не найдено — 404.

---

### GET /stats/{short_code}

Возвращает статистику по ссылке.

**Response 200 OK:**
```json
{
  "short_code": "aB3xQ9",
  "original_url": "https://example.com/very/long/path?param=value",
  "created_at": "2025-01-15T10:30:00Z",
  "click_count": 142,
  "last_clicked_at": "2025-01-20T14:22:00Z",
  "is_active": true
}
```

**Ошибки:**
- `404 Not Found` — код не существует
- `429 Too Many Requests`

---

### DELETE /{short_code}

Soft-delete ссылки.

**Response 204 No Content** — успешно удалено.

**Ошибки:**
- `404 Not Found` — код не существует
- `429 Too Many Requests`

**Логика:**
1. Установить `is_deleted = true` в PostgreSQL.
2. Удалить ключ из Redis (`DEL url:{short_code}`).
3. Вернуть 204.

---

### Rate Limiting

- `POST /shorten`: 10 запросов в минуту на IP.
- `GET /{short_code}`: 100 запросов в минуту на IP.
- `GET /stats/{short_code}`: 30 запросов в минуту на IP.
- `DELETE /{short_code}`: 10 запросов в минуту на IP.

Реализовано через slowapi с Redis-бэкендом. При превышении возвращается `429` с заголовком `Retry-After`.

---

### Swagger

Доступен по `GET /docs` (Swagger UI) и `GET /redoc` (ReDoc). FastAPI генерирует автоматически из Pydantic-моделей и type hints.

---

## 6. Нефункциональные требования

### Безопасность

- **SSRF-защита:** при валидации URL отклоняются ссылки на localhost, 127.0.0.0/8, 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 169.254.0.0/16 (AWS metadata).
- **SQL-инъекции:** исключены использованием параметризованных запросов SQLAlchemy.
- **CORS:** настраивается через `CORSMiddleware`, по умолчанию разрешены только GET-методы для редиректов.
- **Секреты:** хранятся в переменных окружения, не в коде. `.env` файл в `.gitignore`.
- **Длина short_code:** 6 символов base62 = 62^6 ≈ 56.8 млрд комбинаций. Достаточно для большинства задач. Генерация через `secrets.token_urlsafe` с обрезкой + проверка уникальности в БД.

### Производительность

- **Кэш Redis:** редиректы обрабатываются из кэша (TTL 1 час). PostgreSQL используется только при cache miss.
- **Асинхронность:** FastAPI + asyncpg/SQLAlchemy async — обработка тысяч конкурентных запросов на одном воркере.
- **Инкремент счётчика:** при cache hit счётчик инкрементируется в Redis (`HINCRBY`), периодически (раз в 5 минут) сбрасывается в PostgreSQL фоновой таской. При cache miss — инкремент напрямую в БД.
- **Connection pooling:** SQLAlchemy async pool (`AsyncAdaptedQueuePool`), размер пула настраивается.

### Масштабирование

- **Stateless:** приложение не хранит состояние — горизонтально масштабируется добавлением реплик.
- **Redis Cluster:** при росте нагрузки Redis можно развернуть в кластерном режиме.
- **PostgreSQL read-реплики:** статистика (GET /stats) может читаться из реплики.
- **Docker:** приложение упаковано в образ, деплой через docker-compose или Kubernetes.

### Надёжность

- **Soft delete:** ссылки не удаляются физически — сохраняется audit trail.
- **Graceful shutdown:** FastAPI обрабатывает `SIGTERM`, дожидаясь завершения активных запросов.
- **Health check:** `GET /health` возвращает `200` если БД и Redis доступны.

---

## 7. Структура проекта

```
url-shortener/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
├── alembic.ini
├── README.md
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 001_initial.py
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app, middleware, routers
│   ├── config.py                  # Settings (pydantic-settings)
│   ├── database.py                # Async engine, session factory
│   ├── redis_client.py            # Redis connection factory
│   ├── dependencies.py            # FastAPI dependencies (db session, redis)
│   ├── models/
│   │   ├── __init__.py
│   │   └── url.py                 # SQLAlchemy model: URLRecord
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── url.py                 # Pydantic: ShortenRequest, ShortenResponse, StatsResponse
│   │   └── common.py              # ErrorResponse, HealthResponse
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── url_repository.py     # CRUD operations (PostgreSQL)
│   │   └── cache_repository.py   # Redis cache operations
│   ├── services/
│   │   ├── __init__.py
│   │   ├── url_service.py        # Business logic: shorten, redirect, stats, delete
│   │   └── short_code_generator.py # Base62 code generation
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── shorten.py             # POST /shorten
│   │   ├── redirect.py           # GET /{short_code}
│   │   ├── stats.py              # GET /stats/{short_code}
│   │   └── health.py            # GET /health
│   ├── middleware/
│   │   ├── __init__.py
│   │   └── rate_limiter.py       # slowapi setup
│   ├── utils/
│   │   ├── __init__.py
│   │   └── url_validator.py      # SSRF protection, URL validation
│   └── exceptions/
│       ├── __init__.py
│       └── handlers.py           # Custom exceptions + FastAPI exception handlers
└── tests/
    ├── __init__.py
    ├── conftest.py               # Fixtures: async db, redis, test client
    ├── test_shorten.py           # POST /shorten tests
    ├── test_redirect.py          # GET /{short_code} tests
    ├── test_stats.py             # GET /stats/{short_code} tests
    ├── test_delete.py            # DELETE /{short_code} tests
    ├── test_rate_limit.py        # Rate limiting tests
    ├── test_validation.py        # URL validation, SSRF tests
    └── test_health.py           # Health check tests
```

### Переменные окружения (.env)

```
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/urlshortener
REDIS_URL=redis://localhost:6379/0
BASE_URL=http://localhost:8000
SHORT_CODE_LENGTH=6
CACHE_TTL_SECONDS=3600
RATE_LIMIT_SHORTEN=10/minute
RATE_LIMIT_REDIRECT=100/minute
RATE_LIMIT_STATS=30/minute
RATE_LIMIT_DELETE=10/minute
```

### Команды запуска

```bash
# Локальная разработка
docker-compose up -d postgres redis
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Тесты
pytest -v --cov=app --cov-report=term-missing

# Продакшн
docker-compose up -d
```

---

**Этот документ — единственный источник правды.** Разработчик реализует код строго по описанным контрактам, моделям и структуре. Любые отклонения согласовываются с архитектором.