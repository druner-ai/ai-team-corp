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

**Версия:** 1.0.0  
**Статус:** Утверждён  
**Автор:** Архитектор  
**Дата:** 2025

---

## 1. Обзор

### 1.1 Назначение системы

Микросервис URL Shortener — это сервис сокращения длинных URL-адресов в короткие ссылки с возможностью отслеживания статистики переходов. Сервис принимает длинный URL, генерирует уникальный короткий идентификатор, сохраняет соответствие в базу данных и кэш, а затем при обращении к короткой ссылке выполняет редирект на оригинальный URL с одновременным учётом статистики.

### 1.2 Ключевые сценарии использования

1. **Сокращение URL:** Пользователь отправляет POST-запрос с длинным URL. Система валидирует URL, генерирует короткий идентификатор (7 символов, base62), сохраняет в PostgreSQL и кэширует в Redis. Возвращает короткую ссылку.

2. **Редирект:** Пользователь обращается к `GET /{short_id}`. Система сначала проверяет Redis (кэш), при промахе — PostgreSQL. Увеличивает счётчик переходов (асинхронно через Redis-счётчик с периодическим сбросом в БД). Выполняет HTTP 302 редирект на оригинальный URL.

3. **Просмотр статистики:** Пользователь запрашивает `GET /stats/{short_id}`. Система возвращает оригинальный URL, количество переходов, дату создания и дату последнего перехода.

4. **Удаление ссылки:** Пользователь отправляет `DELETE /{short_id}`. Система помечает запись как удалённую (soft delete), инвалидирует кэш в Redis. Последующие обращения возвращают 404.

5. **Rate limiting:** Все эндпоинты защищены rate limiter на основе Redis (token bucket / sliding window). Превышение лимита возвращает 429.

---

## 2. Технологический стек

| Компонент | Технология | Обоснование |
|-----------|-----------|-------------|
| Язык | Python 3.11+ | Требование задачи; async/await для высокой производительности I/O |
| Web-фреймворк | FastAPI 0.110+ | Нативная async-поддержка, автогенерация OpenAPI/Swagger, валидация через Pydantic v2 |
| База данных | PostgreSQL 15+ | Реляционное хранилище, надёжность, индексы, ACID-транзакции для постоянного хранения соответствий URL |
| ORM | SQLAlchemy 2.0 (async) | Зрелая ORM с async-поддержкой, совместимость с Pydantic |
| Миграции | Alembic | Стандарт де-факто для SQLAlchemy, версионирование схемы |
| Кэш | Redis 7+ | Кэширование коротких ссылок для O(1) редиректов; счётчики переходов; rate limiting |
| Валидация | Pydantic v2 | Интегрирована с FastAPI, быстрая валидация URL через `HttpUrl` |
| Rate limiting | redis-py + custom middleware | Redis как backing store для sliding window; middleware на уровне приложения |
| Тестирование | pytest 8+ + pytest-asyncio + httpx (ASGI client) | Стандарт для Python, async-тесты, интеграционные тесты через TestClient |
| Линтинг | ruff + mypy | Скорость ruff, статическая типизация mypy |
| Контейнеризация | Docker + docker-compose | Изоляция, воспроизводимость окружения |
| Логирование | structlog (JSON) | Структурированные логи для production |

---

## 3. Архитектура

### 3.1 Диаграмма компонентов

```
                    ┌─────────────────────────────────────────────┐
                    │              Клиент (Browser/cURL)           │
                    └──────────────────────┬──────────────────────┘
                                           │ HTTP
                                           ▼
                    ┌─────────────────────────────────────────────┐
                    │           FastAPI Application (ASGI)        │
                    │  ┌───────────────────────────────────────┐  │
                    │  │         Middleware Pipeline            │  │
                    │  │  ┌─────────┐  ┌──────────────────┐   │  │
                    │  │  │ Logging │→ │ RateLimitMiddleware│  │  │
                    │  │  └─────────┘  └────────┬─────────┘   │  │
                    │  └────────────────────────┼────────────┘  │
                    │                           ▼                 │
                    │  ┌───────────────────────────────────────┐  │
                    │  │            API Routers                │  │
                    │  │  /shorten  /{id}  /stats/{id}  DELETE │  │
                    │  └───────────────────────┬───────────────┘  │
                    │                          ▼                   │
                    │  ┌───────────────────────────────────────┐  │
                    │  │           Service Layer               │  │
                    │  │  UrlService  StatsService  CacheService│  │
                    │  └──────┬──────────────────┬─────────────┘  │
                    │         │                  │                 │
                    │  ┌──────▼──────┐  ┌────────▼────────┐       │
                    │  │ Repository  │  │  Redis Client   │       │
                    │  │  (SQLAlchemy)│ │  (aioredis)     │       │
                    │  └──────┬──────┘  └────────┬────────┘       │
                    └─────────┼───────────────────┼───────────────┘
                              │                   │
                    ┌─────────▼─────┐    ┌────────▼────────┐
                    │  PostgreSQL   │    │     Redis       │
                    │  (urls table) │    │ cache + counters│
                    └───────────────┘    └─────────────────┘
```

### 3.2 Описание компонентов

- **Middleware Pipeline:** Перехватывает каждый запрос. Сначала логирование (request_id, method, path, timestamp). Затем RateLimitMiddleware проверяет лимит по IP-адресу клиента через Redis (sliding window). При превышении — немедленный ответ 429 без передачи в роутеры.

- **API Routers:** Тонкий слой маршрутизации. Принимает HTTP-запрос, валидирует через Pydantic-схемы, делегирует в Service Layer, формирует HTTP-ответ. Не содержит бизнес-логики.

- **Service Layer:** Бизнес-логика. `UrlService` — генерация short_id (base62, 7 символов), проверка коллизий (retry до 3 раз), сохранение. `StatsService` — инкремент счётчика в Redis, периодический flush в PostgreSQL. `CacheService` — обёртка над Redis: get/set/delete с TTL 24 часа.

- **Repository (SQLAlchemy):** Доступ к PostgreSQL. Методы: `create`, `get_by_short_id`, `soft_delete`, `increment_clicks`, `get_stats`. Использует async session.

- **Redis Client:** Два назначения: (1) кэш `short_id → {original_url, created_at}` с TTL 24h; (2) счётчик переходов `counter:{short_id}` (Redis INCR) с периодическим сбросом в БД через фоновую задачу (каждые 60 секунд или по порогу 100 переходов).

- **Background Task (StatsFlusher):** Запускается при старте приложения через `lifespan`. Каждые 60 секунд читает все ключи `counter:*` из Redis, обновляет `click_count` и `last_clicked_at` в PostgreSQL, сбрасывает Redis-счётчики.

---

## 4. Модель данных

### 4.1 Сущность: `urls`

| Поле | Тип | Ограничения | Описание |
|------|-----|-------------|----------|
| `id` | `UUID` (PK) | `DEFAULT gen_random_uuid()` | Внутренний идентификатор |
| `short_id` | `VARCHAR(7)` | `UNIQUE NOT NULL` | Короткий идентификатор (base62) |
| `original_url` | `TEXT` | `NOT NULL` | Оригинальный URL |
| `click_count` | `BIGINT` | `NOT NULL DEFAULT 0` | Количество переходов |
| `last_clicked_at` | `TIMESTAMPTZ` | `NULL` | Время последнего перехода |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL DEFAULT NOW()` | Время создания |
| `deleted_at` | `TIMESTAMPTZ` | `NULL` | Soft delete: если не NULL — ссылка удалена |

### 4.2 Индексы

| Имя | Колонки | Тип | Назначение |
|-----|---------|-----|-----------|
| `idx_urls_short_id` | `short_id` | UNIQUE B-TREE | Быстрый lookup по short_id, гарантия уникальности |
| `idx_urls_created_at` | `created_at` | B-TREE | Аналитические запросы по дате |
| `idx_urls_deleted_at` | `deleted_at` | Partial index `WHERE deleted_at IS NULL` | Фильтрация активных ссылок |

### 4.3 Redis-структуры

| Ключ | Тип | TTL | Описание |
|------|-----|-----|----------|
| `cache:{short_id}` | String (JSON) | 24h | Кэш: `{"original_url": "...", "created_at": "..."}` |
| `counter:{short_id}` | String (integer) | нет TTL | Счётчик переходов с момента последнего flush |
| `ratelimit:{ip}` | Sorted Set | 60s | Sliding window rate limiter |

---

## 5. API-контракты

### 5.1 POST /shorten

**Запрос:**
```json
{
  "url": "https://example.com/very/long/path?query=1"
}
```

**Валидация:** Поле `url` обязательно, должно быть валидным HTTP/HTTPS URL (Pydantic `HttpUrl`). Максимальная длина — 2048 символов.

**Успешный ответ (201 Created):**
```json
{
  "short_id": "aB3x9Qk",
  "short_url": "http://localhost:8000/aB3x9Qk",
  "original_url": "https://example.com/very/long/path?query=1",
  "created_at": "2025-01-15T10:30:00Z"
}
```

**Ошибки:**
| Код | Сценарий |
|-----|----------|
| 422 | URL отсутствует или невалиден |
| 429 | Rate limit превышен |
| 500 | Внутренняя ошибка (коллизия short_id после 3 ретраев) |

### 5.2 GET /{short_id}

**Редирект (302 Found):**
- Заголовок `Location: {original_url}`
- Тело: пустое

**Ошибки:**
| Код | Сценарий |
|-----|----------|
| 404 | Short ID не найден или удалён |
| 429 | Rate limit превышен |

### 5.3 GET /stats/{short_id}

**Успешный ответ (200 OK):**
```json
{
  "short_id": "aB3x9Qk",
  "original_url": "https://example.com/very/long/path?query=1",
  "click_count": 142,
  "created_at": "2025-01-15T10:30:00Z",
  "last_clicked_at": "2025-01-16T08:45:00Z"
}
```

**Ошибки:**
| Код | Сценарий |
|-----|----------|
| 404 | Short ID не найден или удалён |
| 429 | Rate limit превышен |

### 5.4 DELETE /{short_id}

**Успешный ответ (204 No Content):** Тело пустое.

**Ошибки:**
| Код | Сценарий |
|-----|----------|
| 404 | Short ID не найден или уже удалён |
| 429 | Rate limit превышен |

### 5.5 Rate Limiting

- Лимит: **30 запросов в минуту** на IP-адрес (настраивается через env `RATE_LIMIT_REQUESTS` и `RATE_LIMIT_WINDOW`).
- Реализация: sliding window через Redis Sorted Set. При каждом запросе добавляется timestamp в sorted set, удаляются записи старше window, проверяется размер.
- Заголовки ответа: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`.

### 5.6 Swagger

Доступен по адресу `/docs` (Swagger UI) и `/redoc` (ReDoc). Автогенерируется FastAPI из Pydantic-схем и docstrings.

---

## 6. Нефункциональные требования

### 6.1 Безопасность

- **Валидация URL:** Принимаются только `http` и `https` схемы. Запрещены `javascript:`, `data:`, `file:`, `ftp:`. Реализуется через кастомный Pydantic-валидатор.
- **SSRF-защита:** Опционально (v2) — проверка, что URL не указывает на private IP-диапазоны (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 127.0.0.0/8).
- **SQL-инъекции:** Исключены — используется SQLAlchemy с параметризованными запросами.
- **CORS:** Настроен через middleware. В production — whitelist доменов через env `CORS_ORIGINS`.
- **Secrets:** Все секреты (пароли БД, Redis) — через переменные окружения, `.env` файл в gitignore.
- **HTTPS:** В production — за reverse proxy (nginx/traefik) с TLS-терминацией.

### 6.2 Производительность

- **Кэш-хит:** Редирект через Redis — < 5ms при кэш-хите.
- **Кэш-мисс:** Редирект через PostgreSQL — < 20ms.
- **Сокращение URL:** < 50ms (включая генерацию, запись в БД и кэш).
- **Connection pooling:** SQLAlchemy async pool `size=10, max_overflow=20`. Redis — пул из 50 соединений.
- **Счётчик переходов:** Асинхронный инкремент в Redis (не блокирует редирект). Flush в БД — батчами каждые 60 секунд.

### 6.3 Масштабирование

- **Stateless:** Приложение не хранит состояние — горизонтальное масштабирование за балансировщиком.
- **Redis:** Кластерный режим при росте. Кэш и счётчики — разные logical DB.
- **PostgreSQL:** Read-replicas для `GET /stats` при высокой нагрузке. Партиционирование таблицы `urls` по `created_at` при > 10M записей.
- **Short ID генерация:** Base62 (a-z, A-Z, 0-9) = 62^7 ≈ 3.5 триллиона комбинаций. Коллизии маловероятны, retry-логика — до 3 попыток.

### 6.4 Надёжность

- **Graceful shutdown:** При SIGTERM — завершение текущих запросов, flush счётчиков в БД.
- **Health check:** `GET /health` — проверка подключения к PostgreSQL и Redis. Возвращает 200 или 503.
- **Ретраи:** При коллизии short_id — генерация нового, до 3 попыток. При недоступности Redis — fallback к PostgreSQL (degraded mode, логируется warning).

---

## 7. Структура проекта

```
url-shortener/
├── docker-compose.yml
├── Dockerfile
├── .env.example
├── pyproject.toml
├── alembic.ini
├── README.md
├── alembic/
│   ├── env.py
│   └── versions/
│       └── 001_initial_schema.py
├── src/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app, lifespan, middleware registration
│   ├── config.py                  # Pydantic Settings (env vars)
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py                # Dependency injection (db session, redis)
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py          # Объединение всех роутеров
│   │       ├── shorten.py         # POST /shorten
│   │       ├── redirect.py        # GET /{short_id}
│   │       ├── stats.py          # GET /stats/{short_id}
│   │       └── delete.py         # DELETE /{short_id}
│   ├── core/
│   │   ├── __init__.py
│   │   ├── database.py            # Async engine, session factory
│   │   ├── redis_client.py       # Redis connection, pool
│   │   └── exceptions.py          # Custom exceptions
│   ├── middleware/
│   │   ├── __init__.py
│   │   ├── rate_limit.py          # RateLimitMiddleware
│   │   └── logging.py             # RequestLoggingMiddleware
│   ├── models/
│   │   ├── __init__.py
│   │   └── url.py                 # SQLAlchemy model: Url
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── url.py                 # Pydantic: ShortenRequest, ShortenResponse, StatsResponse
│   │   └── common.py              # ErrorResponse, HealthResponse
│   ├── repositories/
│   │   ├── __init__.py
│   │   └── url_repository.py      # CRUD operations
│   ├── services/
│   │   ├── __init__.py
│   │   ├── url_service.py        # Генерация short_id, создание
│   │   ├── cache_service.py      # Redis cache get/set/delete
│   │   ├── stats_service.py      # Counter increment, flush logic
│   │   └── stats_flusher.py      # Background task: flush counters to DB
│   └── utils/
│       ├── __init__.py
│       └── short_id.py           # Base62 generator
├── tests/
│   ├── __init__.py
│   ├── conftest.py               # Fixtures: test client, test DB, test Redis
│   ├── unit/
│   │   ├── test_short_id.py      # Генерация base62, уникальность
│   │   ├── test_url_validation.py # Валидация URL
│   │   └── test_rate_limit.py    # Логика rate limiter
│   ├── integration/
│   │   ├── test_shorten.py       # POST /shorten — полный цикл
│   │   ├── test_redirect.py      # GET /{id} — кэш хит/мисс
│   │   ├── test_stats.py         # GET /stats/{id}
│   │   ├── test_delete.py        # DELETE /{id} — soft delete + cache invalidation
│   │   └── test_health.py        # GET /health
│   └── e2e/
│       └── test_full_flow.py     # Создать → редирект → статистика → удалить → 404
└── scripts/
    └── seed.py                   # Скрипт для загрузки тестовых данных
```

### 7.1 Переменные окружения (.env.example)

```
# Application
APP_ENV=development
APP_HOST=0.0.0.0
APP_PORT=8000
APP_BASE_URL=http://localhost:8000

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=url_shortener
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Rate Limiting
RATE_LIMIT_REQUESTS=30
RATE_LIMIT_WINDOW=60

# Cache
CACHE_TTL_SECONDS=86400

# CORS
CORS_ORIGINS=*
```

---

## Дополнение: Алгоритм генерации short_id

1. Генерируется 7 случайных байтов через `secrets.token_bytes(7)`.
2. Каждый байт отображается в символ base62-алфавита (`0-9a-zA-Z`) через операцию `% 62`.
3. Полученная строка проверяется на коллизию в Redis (cache miss → PostgreSQL).
4. При коллизии — повторная генерация, до 3 попыток.
5. При исчерпании попыток — HTTP 500 с логированием ошибки.

---

**Конец документа.** Это — единственный источник правды для реализации. Любые отклонения требуют согласования с Архитектором.