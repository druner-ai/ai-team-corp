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

## 1. Обзор

Микросервис URL Shortener предназначен для создания коротких ссылок на длинные URL-адреса, обеспечения редиректа по короткому идентификатору и сбора базовой статистики переходов. Система работает как автономный микросервис с REST API.

**Ключевые сценарии использования:**

1. **Сокращение URL** — клиент отправляет длинный URL, получает короткий идентификатор (7 символов) и полную короткую ссылку.
2. **Редирект** — при обращении к короткой ссылке сервис находит оригинальный URL и возвращает HTTP 302 redirect. Параллельно инкрементируется счётчик переходов.
3. **Просмотр статистики** — клиент запрашивает количество переходов по конкретному короткому идентификатору.
4. **Удаление ссылки** — клиент удаляет сокращённую ссылку, после чего редирект перестаёт работать.

Сервис рассчитан на высокую нагрузку на чтение (GET /{id}), поэтому использует кэширование в Redis. Запись (POST /shorten) происходит реже и работает напрямую с PostgreSQL.

---

## 2. Технологический стек

| Компонент | Технология | Обоснование |
|---|---|---|
| Язык | Python 3.11+ | Современная типизация, async/await, широкая экосистема |
| Web-фреймворк | FastAPI 0.110+ | Нативная async-поддержка, автогенерация OpenAPI/Swagger, валидация через Pydantic |
| ASGI-сервер | Uvicorn | Стандартный высокопроизводительный ASGI-сервер для FastAPI |
| БД (постоянное хранилище) | PostgreSQL 15 | Реляционная БД с надёжными транзакциями, индексами, поддержкой UUID и генерации |
| ORM | SQLAlchemy 2.0 (async) | Async-поддержка, типизированные модели, совместимость с FastAPI |
| Миграции | Alembic | Стандарт миграций для SQLAlchemy |
| Кэш | Redis 7 | In-memory хранилище для кэширования редиректов и счётчиков, низкая задержка |
| Rate Limiting | Redis + custom middleware | Redis используется как shared store для подсчёта запросов per IP |
| Валидация | Pydantic v2 | Интегрирована в FastAPI, валидация URL через `HttpUrl` |
| Тестирование | pytest + pytest-asyncio + httpx | Async-тесты через TestClient/httpx |
| Контейнеризация | Docker + docker-compose | Изоляция, воспроизводимость окружения |

---

## 3. Архитектура

### Диаграмма компонентов (текстом)

```
                    ┌──────────────────────────┐
                    │       Клиент / Браузер    │
                    └────────────┬─────────────┘
                                 │ HTTP
                                 ▼
                    ┌──────────────────────────┐
                    │      Uvicorn (ASGI)      │
                    │   ┌──────────────────┐   │
                    │   │  FastAPI App     │   │
                    │   │                  │   │
                    │   │ ┌──────────────┐ │   │
                    │   │ │RateLimit MW  │◄┼───┼── Redis (rate limit counters)
                    │   │ └──────┬───────┘ │   │
                    │   │        ▼         │   │
                    │   │ ┌──────────────┐ │   │
                    │   │ │  Routers     │ │   │
                    │   │ │ /shorten     │ │   │
                    │   │ │ /{id}        │ │   │
                    │   │ │ /stats/{id}  │ │   │
                    │   │ │ DELETE /{id} │ │   │
                    │   │ └──────┬───────┘ │   │
                    │   │        ▼         │   │
                    │   │ ┌──────────────┐ │   │
                    │   │ │  Service     │ │   │
                    │   │ │  Layer       │ │   │
                    │   │ └──┬───────┬───┘ │   │
                    │   │    │       │     │   │
                    │   └────┼───────┼─────┘   │
                    └────────┼───────┼─────────┘
                             │       │
                    ┌────────▼──┐ ┌──▼──────────┐
                    │  Redis    │ │ PostgreSQL  │
                    │  (cache)  │ │ (source of  │
                    │           │ │  truth)     │
                    └───────────┘ └─────────────┘
```

### Описание компонентов

- **Uvicorn (ASGI-сервер)** — принимает HTTP-соединения, управляет event loop, поддерживает graceful shutdown через SIGTERM/SIGINT.
- **FastAPI App** — ядро приложения. Регистрирует middleware, роутеры, обработчики жизненного цикла (startup/shutdown).
- **RateLimit Middleware** — перехватывает каждый запрос, проверяет IP клиента в Redis. Если лимит 100 запросов/мин превышен — возвращает 429. Использует паттерн sliding window через `INCR` + `EXPIRE`.
- **Routers** — четыре эндпоинта. Делегируют бизнес-логику в Service Layer.
- **Service Layer** — содержит бизнес-логику: генерацию короткого ID, кэширование, работу с БД, обновление статистики. Изолирует роутеры от деталей хранения.
- **Redis (cache)** — хранит: (1) кэш редиректов `url:{short_id}` → original_url с TTL 1 час; (2) счётчики переходов `stats:{short_id}` для буферизованной записи; (3) rate-limit счётчики `rl:{ip}`.
- **PostgreSQL** — источник истины. Хранит все сокращённые URL и метаданные. Статистика переходов периодически синхронизируется из Redis (или обновляется при каждом переходе через буфер).

### Поток редиректа (GET /{id})

1. Запрос попадает в RateLimit Middleware → проверка лимита.
2. Router передаёт `short_id` в `RedirectService.get(short_id)`.
3. Service проверяет Redis (`url:{short_id}`). Если есть — инкрементирует счётчик `stats:{short_id}` в Redis, возвращает URL.
4. Если в кэше нет — Service делает запрос в PostgreSQL. Если найдено — кладёт в Redis, инкрементирует счётчик, возвращает URL. Если не найдено — возвращает 404.
5. Router возвращает HTTP 302 с заголовком `Location: {original_url}`.

### Генерация короткого ID

Используется `base62`-кодирование (символы `[a-zA-Z0-9]`) случайного числа, либо хеш-функция. 7 символов в base62 дают 62^7 ≈ 3.5 триллиона комбинаций — достаточно для исключения коллизий при разумном объёме. Для гарантии уникальности после генерации проверяется отсутствие в БД; при коллизии генерируется новый ID (до 3 попыток).

---

## 4. Модель данных

### Сущность: `url_mapping`

Таблица в PostgreSQL: `url_mappings`

| Поле | Тип | Ограничения | Описание |
|---|---|---|---|
| `id` | `BIGSERIAL` | PK | Внутренний числовой ID |
| `short_id` | `VARCHAR(7)` | UNIQUE, NOT NULL, INDEX | Короткий идентификатор |
| `original_url` | `TEXT` | NOT NULL | Оригинальный URL |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT now() | Время создания |
| `expires_at` | `TIMESTAMPTZ` | NULLABLE | Время истечения (опционально) |
| `is_active` | `BOOLEAN` | NOT NULL, DEFAULT true | Флаг активной ссылки (для soft delete) |
| `click_count` | `BIGINT` | NOT NULL, DEFAULT 0 | Количество переходов |

**Индексы:**
- `PRIMARY KEY (id)`
- `UNIQUE INDEX idx_url_mappings_short_id ON (short_id)` — быстрый поиск по короткому ID
- `INDEX idx_url_mappings_created_at ON (created_at)` — для аналитики/очистки

### Redis-структуры

| Ключ | Тип | TTL | Описание |
|---|---|---|---|
| `url:{short_id}` | String | 3600s | Кэш: оригинальный URL |
| `stats:{short_id}` | String (integer) | без TTL (или 86400s) | Буферизованный счётчик переходов |
| `rl:{client_ip}` | String (integer) | 60s | Rate-limit счётчик |

### Синхронизация статистики

При каждом редиректе `stats:{short_id}` инкрементируется в Redis. Фоновая задача (или триггер при достижении порога, например каждые 10 переходов) обновляет `click_count` в PostgreSQL. Это снижает нагрузку на БД при высоком трафике.

---

## 5. API-контракты

### POST /shorten

Создаёт короткую ссылку.

**Request:**
```json
{
  "url": "https://example.com/very/long/path?query=1"
}
```

Валидация: поле `url` должно быть валидным HTTP/HTTPS URL (Pydantic `HttpUrl`). Максимальная длина — 2048 символов.

**Response 201 Created:**
```json
{
  "short_id": "aB3x9Qk",
  "short_url": "http://localhost:8000/aB3x9Qk",
  "original_url": "https://example.com/very/long/path?query=1",
  "created_at": "2025-01-15T12:00:00Z"
}
```

**Ошибки:**
- `400 Bad Request` — невалидный URL
- `422 Unprocessable Entity` — нарушение схемы Pydantic
- `429 Too Many Requests` — превышен rate limit
- `500 Internal Server Error` — внутренняя ошибка

---

### GET /{id}

Редирект на оригинальный URL.

**Path параметр:** `id` — короткий идентификатор (строго 7 символов, `[a-zA-Z0-9]`).

**Response 302 Found:**
```
Location: https://example.com/very/long/path?query=1
```
Тело ответа: пустое или минимальный JSON.

**Ошибки:**
- `404 Not Found` — короткий ID не существует или деактивирован
- `429 Too Many Requests` — превышен rate limit

---

### GET /stats/{id}

Возвращает статистику по короткой ссылке.

**Response 200 OK:**
```json
{
  "short_id": "aB3x9Qk",
  "original_url": "https://example.com/very/long/path?query=1",
  "click_count": 142,
  "created_at": "2025-01-15T12:00:00Z",
  "is_active": true
}
```

**Ошибки:**
- `404 Not Found` — ID не найден
- `429 Too Many Requests` — превышен rate limit

---

### DELETE /{id}

Удаляет (soft delete) короткую ссылку.

**Response 204 No Content:** пустое тело.

**Ошибки:**
- `404 Not Found` — ID не найден
- `429 Too Many Requests` — превышен rate limit

При удалении: `is_active = false`, кэш `url:{short_id}` удаляется из Redis. Последующие GET /{id} возвращают 404.

---

### Общие заголовки ответов

- `X-RateLimit-Limit: 100`
- `X-RateLimit-Remaining: 87`
- `X-RateLimit-Reset: 1737000000`

---

## 6. Нефункциональные требования

### Безопасность

- **Валидация URL**: только `http` и `https` схемы. Запрещены `file://`, `ftp://`, `javascript:`, `data:`. Реализуется через Pydantic `HttpUrl` с дополнительной проверкой схемы.
- **SSRF-защита**: опционально — проверка, что URL не указывает на внутренние адреса (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 127.0.0.0/8, localhost).
- **Rate Limiting**: 100 запросов/мин на IP. Реализовано через Redis sliding window. При превышении — HTTP 429 с заголовком `Retry-After`.
- **SQL-инъекции**: предотвращаются через параметризованные запросы SQLAlchemy ORM.
- **Логи**: не логируются полные URL в production (могут содержать чувствительные параметры). Логируется только `short_id` и метаданные.

### Производительность

- **Кэширование редиректов**: Redis обеспечивает <1ms ответ для горячего кэша. TTL — 1 час.
- **Connection pooling**: SQLAlchemy async engine с пулом соединений (размер 10, max overflow 20).
- **Redis pooling**: `redis.asyncio` с connection pool (размер 10).
- **Целевая производительность**: GET /{id} — <50ms на p99 при кэш-хите; POST /shorten — <100ms на p99.

### Масштабирование

- **Горизонтальное масштабирование**: сервис stateless — несколько инстансов за load balancer. Redis и PostgreSQL — shared.
- **Read replicas**: PostgreSQL read replica для GET /stats при высокой нагрузке.
- **Redis Cluster**: при росте — переход на Redis Cluster для шардирования кэша.
- **Асинхронная запись статистики**: буферизация в Redis снижает write-нагрузку на PostgreSQL.

### Graceful Shutdown

- Uvicorn обрабатывает `SIGTERM`/`SIGINT`.
- При получении сигнала: прекращается приём новых соединений, ожидаются завершения текущих запросов (timeout 30s), закрываются пулы Redis и PostgreSQL.
- Реализуется через FastAPI `lifespan` context manager: при shutdown вызываются `engine.dispose()`, `redis.close()`.

### Надёжность

- **Health check**: `GET /health` — возвращает 200, проверяет соединение с PostgreSQL и Redis.
- **Idempotency**: повторный POST /shorten с тем же URL может возвращать существующий `short_id` (опциональное поведение, configurable).
- **Резервное копирование**: PostgreSQL — регулярные pg_dump / WAL archiving.

---

## 7. Структура проекта

```
url-shortener/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── alembic.ini
├── .env.example
├── README.md
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 001_initial.py
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app, lifespan, middleware registration
│   ├── config.py                  # Settings (pydantic-settings), env vars
│   ├── dependencies.py            # FastAPI dependencies (db session, redis)
│   ├── models/
│   │   ├── __init__.py
│   │   └── url_mapping.py         # SQLAlchemy model
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── url.py                  # Pydantic schemas: ShortenRequest, ShortenResponse, StatsResponse
│   │   └── common.py               # ErrorResponse, HealthResponse
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── shorten.py              # POST /shorten
│   │   ├── redirect.py             # GET /{id}
│   │   ├── stats.py                # GET /stats/{id}
│   │   ├── delete.py               # DELETE /{id}
│   │   └── health.py               # GET /health
│   ├── services/
│   │   ├── __init__.py
│   │   ├── url_service.py          # create_short_url, get_original_url, get_stats, delete_url
│   │   ├── cache_service.py        # Redis get/set/delete wrappers
│   │   └── stats_service.py        # Increment, sync to PostgreSQL
│   ├── middleware/
│   │   ├── __init__.py
│   │   └── rate_limit.py           # RateLimitMiddleware (Redis-based)
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── short_id.py             # base62 generation, validation
│   │   └── url_validator.py        # URL scheme validation, SSRF checks
│   └── db/
│       ├── __init__.py
│       ├── session.py              # async engine, sessionmaker
│       └── redis_client.py         # Redis connection pool
└── tests/
    ├── __init__.py
    ├── conftest.py                 # pytest fixtures: test client, test db, redis mock
    ├── test_shorten.py
    ├── test_redirect.py
    ├── test_stats.py
    ├── test_delete.py
    ├── test_rate_limit.py
    ├── test_validation.py
    └── test_health.py
```

### Ключевые конфигурационные переменные (.env)

```
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/urlshortener
REDIS_URL=redis://localhost:6379/0
RATE_LIMIT_PER_MINUTE=100
SHORT_ID_LENGTH=7
CACHE_TTL_SECONDS=3600
BASE_URL=http://localhost:8000
MAX_URL_LENGTH=2048
STATS_SYNC_THRESHOLD=10
SHUTDOWN_TIMEOUT_SECONDS=30
```

### Команды запуска

```bash
# Локальная разработка
docker-compose up -d postgres redis
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Тесты
pytest -v --cov=app

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

**Этот документ — единственный источник правды.** Разработчик реализует код строго по описанным контрактам, моделям и структуре. DevOps разворачивает согласно указанным технологиям и конфигурации. Любые отклонения согласовываются через обновление данного документа.