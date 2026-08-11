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

**URL Shortener** — микросервис для сокращения длинных URL-адресов и отслеживания статистики переходов. Система принимает длинный URL, генерирует уникальный короткий идентификатор (7 символов), сохраняет маппинг в PostgreSQL и кэширует в Redis для быстрого чтения. При обращении к короткому ID сервис редиректит на оригинальный URL и инкрементирует счётчик кликов. Дополнительно предоставляется статистика переходов и возможность удаления сокращённых ссылок.

**Ключевые сценарии использования:**

1. **Сокращение URL:** Пользователь отправляет POST-запрос с длинным URL → сервис валидирует URL, генерирует 7-символьный ID, сохраняет в БД и кэш, возвращает короткий URL.
2. **Редирект:** Пользователь обращается к `GET /{id}` → сервис ищет URL в Redis (fallback в PostgreSQL), инкрементирует счётчик кликов, возвращает HTTP 301 Redirect.
3. **Просмотр статистики:** Пользователь запрашивает `GET /stats/{id}` → сервис возвращает оригинальный URL, количество переходов, дату создания.
4. **Удаление ссылки:** `DELETE /{id}` → сервис помечает запись как удалённую (soft delete), инвалидирует кэш.

---

## 2. Технологический стек

| Компонент | Технология | Обоснование |
|-----------|-----------|-------------|
| Язык | Python 3.11+ | Современный, быстрый, богатая экосистема |
| Web-фреймворк | FastAPI 0.110+ | Async-native, автогенерация OpenAPI/Swagger, валидация через Pydantic |
| ASGI-сервер | Uvicorn с uvloop | Высокая производительность для async I/O |
| БД | PostgreSQL 15 | Надёжное хранилище, индексы, транзакционность |
| ORM | SQLAlchemy 2.0 (async) | Зрелая ORM с async-поддержкой |
| Кэш | Redis 7 | In-memory хранилище для O(1) чтения URL, TTL-кэширование |
| Rate Limiting | Redis + sliding window | Атомарные операции Lua-скриптом, точный лимит 100 req/min |
| Миграции | Alembic | Версионирование схемы БД |
| Тестирование | pytest + pytest-asyncio + httpx | Async-тесты, изоляция через testcontainers или in-memory |
| Валидация | Pydantic v2 + validators | Встроенная валидация URL, кастомные валидаторы |
| Логирование | structlog / loguru | Структурированные логи для observability |
| Контейнеризация | Docker + docker-compose | Воспроизводимое окружение |

---

## 3. Архитектура

### Диаграмма компонентов (текстом)

```
                    ┌─────────────────────────────────────────────┐
                    │              Client (Browser/cURL)          │
                    └──────────────────────┬──────────────────────┘
                                           │ HTTP
                                           ▼
                    ┌─────────────────────────────────────────────┐
                    │           FastAPI Application               │
                    │  ┌───────────┐  ┌──────────┐  ┌─────────┐  │
                    │  │ Middleware│  │ Routers  │  │Services │  │
                    │  │ (Rate     │  │ /shorten │  │ URLSvc  │  │
                    │  │  Limiter) │  │ /{id}    │  │ StatsSvc│  │
                    │  │           │  │ /stats   │  │ IDGen   │  │
                    │  │           │  │ DELETE   │  │         │  │
                    │  └───────────┘  └──────────┘  └────┬────┘  │
                    └───────────────────────────────────┼────────┘
                                                        │
                              ┌────────────────────────┼────────────────┐
                              │                        │                │
                              ▼                        ▼                ▼
                    ┌──────────────┐         ┌──────────────┐  ┌──────────────┐
                    │    Redis     │         │ PostgreSQL   │  │   Redis      │
                    │  (URL Cache) │         │  (Source of  │  │ (Rate Limit  │
                    │  TTL: 24h    │         │   Truth)     │  │  Counters)   │
                    └──────────────┘         └──────────────┘  └──────────────┘
```

### Описание компонентов

- **API Layer (Routers):** Принимает HTTP-запросы, валидирует входные данные через Pydantic-схемы, делегирует бизнес-логику сервисам. Четыре роутера: shorten, redirect, stats, delete.
- **Rate Limiter Middleware:** Перехватывает каждый запрос, проверяет счётчик в Redis по IP клиента. Использует sliding window алгоритм через Lua-скрипт для атомарности. При превышении лимита возвращает HTTP 429.
- **URL Service:** Бизнес-логика сокращения. Генерирует ID, проверяет коллизии, сохраняет в БД, заполняет кэш.
- **ID Generator:** Генерирует 7-символьный ID из алфавита `[a-zA-Z0-9]` (62 символа). Использует `secrets.token_urlsafe` или base62-кодирование случайного числа. 62^7 ≈ 3.5 триллиона комбинаций — коллизии крайне редки, но проверяются.
- **Stats Service:** Читает статистику из БД. Счётчик кликов обновляется асинхронно: инкремент в Redis (HINCRBY), периодический flush в PostgreSQL (background task каждые 30 секунд).
- **Cache Layer (Redis):** Хранит маппинг `short_id → {original_url, created_at}` с TTL 24 часа. При cache miss — чтение из БД и заполнение кэша.
- **Graceful Shutdown:** При получении SIGTERM/SIGINT Uvicorn прекращает принимать новые соединения, дожидается завершения in-flight запросов, flush'ит счётчики кликов из Redis в PostgreSQL, закрывает пулы соединений.

---

## 4. Модель данных

### Сущность: `urls`

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | `SERIAL` | Первичный ключ (внутренний) |
| `short_id` | `VARCHAR(7)` | Короткий идентификатор, UNIQUE, NOT NULL |
| `original_url` | `TEXT` | Оригинальный URL, NOT NULL |
| `created_at` | `TIMESTAMPTZ` | Время создания, DEFAULT NOW() |
| `expires_at` | `TIMESTAMPTZ` | Время истечения (NULL = бессрочно) |
| `is_deleted` | `BOOLEAN` | Soft delete флаг, DEFAULT FALSE |
| `click_count` | `BIGINT` | Количество переходов, DEFAULT 0 |

### Индексы

```sql
CREATE UNIQUE INDEX idx_urls_short_id ON urls(short_id) WHERE is_deleted = FALSE;
CREATE INDEX idx_urls_created_at ON urls(created_at);
```

### Сущность в Redis (кэш)

```
Key:   url:{short_id}
Value: JSON {"original_url": "...", "created_at": "...", "click_count": 123}
TTL:   86400 (24 часа)

Key:   clicks:{short_id}
Value: INTEGER (буфер инкрементов кликов)
TTL:   без TTL (flush в БД каждые 30 сек)
```

---

## 5. API-контракты

### POST /shorten

**Запрос:**
```json
{
  "url": "https://example.com/very/long/path?query=1",
  "custom_alias": null,
  "expires_at": null
}
```

- `url` (обязательное): валидный HTTP/HTTPS URL. Проверяется схема, наличие домена, отсутствие localhost/private IP (опционально).
- `custom_alias` (опциональное): строка 3–16 символов `[a-zA-Z0-9_-]`.
- `expires_at` (опциональное): ISO 8601 timestamp в будущем.

**Ответ (201 Created):**
```json
{
  "short_id": "aB3xK9q",
  "short_url": "https://sho.rt/aB3xK9q",
  "original_url": "https://example.com/very/long/path?query=1",
  "created_at": "2025-01-15T10:30:00Z",
  "expires_at": null
}
```

**Ошибки:**
- `400 Bad Request` — невалидный URL
- `409 Conflict` — custom_alias уже занят
- `422 Unprocessable Entity` — ошибка валидации Pydantic

---

### GET /{id}

**Поведение:** Ищет `short_id` в Redis → (fallback PostgreSQL). Инкрементирует счётчик кликов. Возвращает редирект.

**Ответ (301 Moved Permanently):**
```
Location: https://example.com/very/long/path?query=1
```

**Ошибки:**
- `404 Not Found` — ID не существует или удалён
- `410 Gone` — срок действия истёк

---

### GET /stats/{id}

**Ответ (200 OK):**
```json
{
  "short_id": "aB3xK9q",
  "original_url": "https://example.com/very/long/path?query=1",
  "click_count": 42,
  "created_at": "2025-01-15T10:30:00Z",
  "expires_at": null,
  "is_active": true
}
```

**Ошибки:**
- `404 Not Found` — ID не существует

---

### DELETE /{id}

**Поведание:** Soft delete — устанавливает `is_deleted = TRUE`, инвалидирует кэш Redis (`DEL url:{short_id}`).

**Ответ (204 No Content):** пустое тело

**Ошибки:**
- `404 Not Found` — ID не существует

---

### Общие заголовки ответов

- `X-RateLimit-Limit: 100`
- `X-RateLimit-Remaining: 87`
- `X-RateLimit-Reset: 1737000000`

При превышении лимита: `429 Too Many Requests` с `Retry-After` заголовком.

---

## 6. Нефункциональные требования

### Безопасность
- **Валидация URL:** Принимаются только `http` и `https` схемы. Блокировка SSRF: опциональная проверка на private IP диапазоны (10.x, 172.16-31.x, 192.168.x, 127.x).
- **Rate Limiting:** 100 запросов в минуту на IP. Реализация через Redis sliding window.
- **SQL Injection:** Использование параметризованных запросов SQLAlchemy ORM.
- **Secrets:** Все секреты (пароли БД, Redis) через переменные окружения, не в коде.
- **CORS:** Настраиваемый через env-переменные, по умолчанию `*` для API.

### Производительность
- **Чтение (редирект):** < 5ms при cache hit в Redis (p99 < 20ms).
- **Запись (сокращение):** < 50ms (p99 < 100ms) включая проверку коллизии.
- **Connection pooling:** SQLAlchemy async pool (размер 10, max_overflow 20). Redis connection pool (размер 50).
- **Асинхронность:** Все I/O операции (БД, Redis) — async, без блокировок event loop.

### Масштабирование
- **Stateless:** Приложение не хранит состояние — горизонтальное масштабирование за балансировщиком.
- **Redis:** Может быть кластеризован. Кэш-промахи терпимы (fallback в БД).
- **PostgreSQL:** Read-replicas для `GET /stats` при росте нагрузки. Партиционирование таблицы `urls` по `created_at` при >10M записей.
- **Click counter flush:** Background task каждые 30 сек, батч-обновление — снижает нагрузку на БД.

### Надёжность
- **Graceful Shutdown:** SIGTERM → stop accepting → drain connections (timeout 30s) → flush click counters → close pools → exit.
- **Health check:** `GET /health` → проверка соединений БД и Redis. `GET /ready` для k8s readiness probe.
- **Ретраи:** При коллизии short_id — до 3 попыток регенерации.

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
│   └── versions/
│       └── 001_initial.py
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app, lifespan, middleware
│   ├── config.py                  # Pydantic Settings (env vars)
│   ├── dependencies.py            # DI: db session, redis client
│   ├── api/
│   │   ├── __init__.py
│   │   ├── router.py              # Объединение всех роутеров
│   │   ├── shorten.py             # POST /shorten
│   │   ├── redirect.py            # GET /{id}
│   │   ├── stats.py               # GET /stats/{id}
│   │   └── delete.py              # DELETE /{id}
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── url.py                 # ShortenRequest, ShortenResponse
│   │   └── stats.py               # StatsResponse
│   ├── models/
│   │   ├── __init__.py
│   │   └── url.py                 # SQLAlchemy модель Url
│   ├── services/
│   │   ├── __init__.py
│   │   ├── url_service.py         # create_short_url, get_url, delete_url
│   │   ├── stats_service.py       # get_stats, flush_clicks
│   │   └── id_generator.py        # generate_short_id (7 chars, base62)
│   ├── core/
│   │   ├── __init__.py
│   │   ├── database.py            # async engine, sessionmaker
│   │   ├── redis.py               # async Redis client, pool
│   │   └── rate_limiter.py        # Sliding window limiter (Lua script)
│   ├── middleware/
│   │   ├── __init__.py
│   │   └── rate_limit.py          # Rate limit middleware
│   └── tasks/
│       ├── __init__.py
│       └── click_flusher.py       # Background task: flush counters to DB
├── tests/
│   ├── __init__.py
│   ├── conftest.py                # Fixtures: test client, db, redis
│   ├── test_shorten.py
│   ├── test_redirect.py
│   ├── test_stats.py
│   ├── test_delete.py
│   ├── test_rate_limit.py
│   ├── test_validation.py
│   └── test_id_generator.py
└── scripts/
    ├── lua/
    │   └── rate_limit.lua         # Sliding window Lua script
    └── run_tests.sh
```

### Переменные окружения (.env.example)

```
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/urlshortener
REDIS_URL=redis://localhost:6379/0
BASE_URL=https://sho.rt
RATE_LIMIT_PER_MINUTE=100
CLICK_FLUSH_INTERVAL_SECONDS=30
SHORT_ID_LENGTH=7
LOG_LEVEL=INFO
CORS_ORIGINS=*
```

---

**Этот документ — единственный источник правды.** Разработчик реализует код строго по описанным контрактам. DevOps разворачивает согласно стеку и переменным окружения. Любые отклонения требуют обновления этого документа.