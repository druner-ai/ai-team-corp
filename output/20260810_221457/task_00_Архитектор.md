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

**URL Shortener** — микросервис, принимающий длинный URL и возвращающий короткий идентификатор (7 символов). При обращении к короткому ID сервис редиректит на оригинальный URL, ведёт статистику переходов и позволяет удалять ссылки.

**Ключевые сценарии использования:**

1. **Сокращение URL.** Пользователь отправляет POST-запрос с длинным URL. Сервис валидирует URL, генерирует уникальный 7-символьный ID, сохраняет в PostgreSQL, кэширует в Redis и возвращает короткую ссылку.
2. **Редирект.** При GET-запросе к `/{id}` сервис ищет URL сначала в Redis, при отсутствии — в PostgreSQL, инкрементирует счётчик переходов, возвращает HTTP 301 (или 302) с заголовком `Location`.
3. **Статистика.** GET-запрос к `/stats/{id}` возвращает оригинальный URL, количество переходов, дату создания и срок действия.
4. **Удаление.** DELETE-запрос к `/{id}` помечает запись как удалённую (soft delete) и инвалидирует кэш.

---

## 2. Технологический стек

| Компонент | Технология | Обоснование |
|---|---|---|
| Язык | Python 3.11+ | Современная типизация, async, богатая экосистема |
| Web-фреймворк | FastAPI 0.110+ | Нативная async-поддержка, автогенерация OpenAPI/Swagger, валидация через Pydantic |
| ASGI-сервер | Uvicorn с uvloop | Высокая производительность, graceful shutdown через сигналы SIGTERM/SIGINT |
| БД | PostgreSQL 15 | Реляционная надёжность, индексы, транзакционность, расширение `pgcrypto` при необходимости |
| ORM | SQLAlchemy 2.0 (async) + asyncpg | Async-драйвер для PostgreSQL, типобезопасные модели |
| Кэш | Redis 7 | Хранение URL-маппингов, счётчиков переходов, rate-limiting через sliding window |
| Миграции | Alembic | Версионирование схемы БД |
| Валидация | Pydantic v2 | Декларативная валидация URL, сериализация ответов |
| Rate limiting | Redis + кастомный middleware | Sliding window на 100 запросов/мин по IP |
| Тесты | pytest + pytest-asyncio + httpx | Async-тестирование API, изоляция через testcontainers или in-memory |
| Контейнеризация | Docker + docker-compose | Воспроизводимое окружение |

---

## 3. Архитектура

### Диаграмма компонентов (текстовая)

```
                    ┌──────────────────────────┐
                    │       Client / Browser   │
                    └────────────┬─────────────┘
                                 │ HTTP
                    ┌────────────▼─────────────┐
                    │      Uvicorn (ASGI)      │
                    │   graceful shutdown      │
                    └────────────┬─────────────┘
                                 │
                    ┌────────────▼─────────────┐
                    │       FastAPI App        │
                    │  ┌────────────────────┐  │
                    │  │  Middleware Layer   │  │
                    │  │  - RateLimiter      │  │
                    │  │  - RequestID        │  │
                    │  │  - ErrorHandling    │  │
                    │  └────────┬───────────┘  │
                    │  ┌────────▼───────────┐  │
                    │  │   API Routers       │  │
                    │  │  /shorten /{id}     │  │
                    │  │  /stats/{id}        │  │
                    │  └────────┬───────────┘  │
                    │  ┌────────▼───────────┐  │
                    │  │   Service Layer     │  │
                    │  │  - URLShortener     │  │
                    │  │  - StatsService     │  │
                    │  │  - IDGenerator      │  │
                    │  └────┬─────────┬──────┘  │
                    └───────┼─────────┼─────────┘
                            │         │
               ┌────────────▼───┐  ┌──▼──────────┐
               │   PostgreSQL   │  │    Redis    │
               │  (источник     │  │  (кэш URL,  │
               │   правды)      │  │  счётчики,  │
               │                │  │  rate-limit)│
               └────────────────┘  └─────────────┘
```

### Описание компонентов

- **Uvicorn (ASGI-сервер).** Принимает HTTP-соединения, управляет event loop. При получении SIGTERM прекращает принимать новые соединения, дожидается завершения текущих запросов (graceful shutdown), таймаут — 30 секунд.
- **Middleware Layer.** RateLimiter проверяет лимит 100 запросов/мин по IP через Redis. RequestID добавляет заголовок `X-Request-ID` для трассировки. ErrorHandling перехватывает исключения и возвращает стандартизированные JSON-ошибки.
- **API Routers.** Тонкий слой: валидация входных данных через Pydantic, делегирование бизнес-логики в Service Layer.
- **Service Layer.** Содержит бизнес-логику. `URLShortenerService` — создание, получение, удаление. `StatsService` — агрегация статистики. `IDGenerator` — генерация 7-символьного ID (Base62-кодирование случайного числа + проверка уникальности).
- **PostgreSQL.** Источник правды. Хранит все URL-маппинги и метаданные.
- **Redis.** Кэш URL-маппингов (TTL 1 час), буфер счётчиков переходов (синхронизация в БД батчами или при запросе статистики), хранилище rate-limit счётчиков.

---

## 4. Модель данных

### Сущность `url_mapping` (PostgreSQL)

| Поле | Тип | Описание |
|---|---|---|
| `id` | `VARCHAR(7) PK` | Короткий идентификатор, Base62 |
| `original_url` | `TEXT NOT NULL` | Оригинальный URL |
| `created_at` | `TIMESTAMPTZ NOT NULL DEFAULT NOW()` | Время создания |
| `expires_at` | `TIMESTAMPTZ` | Срок действия (nullable = бессрочно) |
| `is_deleted` | `BOOLEAN NOT NULL DEFAULT FALSE` | Soft delete флаг |
| `click_count` | `BIGINT NOT NULL DEFAULT 0` | Количество переходов |

**Индексы:**
- `PRIMARY KEY (id)` — быстрый поиск по короткому ID
- `INDEX idx_original_url (original_url)` — поиск дубликатов (опционально, для дедупликации)
- `INDEX idx_expires_at (expires_at) WHERE is_deleted = FALSE` — для джоба очистки истёкших ссылок

### Redis-структуры

| Ключ | Тип | TTL | Описание |
|---|---|---|---|
| `url:{id}` | String (original_url) | 3600с | Кэш маппинга короткий ID → URL |
| `stats:{id}` | String (counter) | без TTL | Буфер счётчика переходов |
| `ratelimit:{ip}` | Sorted Set | 60с | Sliding window для rate limiting |

---

## 5. API-контракты

### POST `/shorten`

**Запрос:**
```json
{
  "url": "https://example.com/very/long/path?query=1",
  "expires_at": "2025-12-31T23:59:59Z"
}
```
Поле `expires_at` — опциональное (ISO 8601).

**Валидация URL:**
- Схема: `http` или `https`
- Наличие домена
- Длина ≤ 2048 символов
- Запрет локальных адресов (`localhost`, `127.0.0.1`, `10.x`, `192.168.x`) — опционально, через конфиг

**Ответ 201 Created:**
```json
{
  "short_id": "aB3x9Qk",
  "short_url": "https://sho.rt/aB3x9Qk",
  "original_url": "https://example.com/very/long/path?query=1",
  "created_at": "2025-01-15T10:30:00Z",
  "expires_at": "2025-12-31T23:59:59Z"
}
```

**Ошибки:**
- `400 Bad Request` — невалидный URL
- `429 Too Many Requests` — превышен rate limit

---

### GET `/{id}`

**Параметр:** `id` — 7-символьный строковый идентификатор (паттерн `^[A-Za-z0-9]{7}$`)

**Поведение:**
1. Проверка формата ID
2. Поиск в Redis → при промахе — PostgreSQL
3. Проверка `is_deleted` и `expires_at`
4. Инкремент счётчика в Redis
5. Редирект

**Ответ 301 Moved Permanently:**
```
Location: https://example.com/very/long/path?query=1
```

**Ошибки:**
- `404 Not Found` — ID не существует или удалён
- `410 Gone` — срок действия истёк
- `400 Bad Request` — неверный формат ID

---

### GET `/stats/{id}`

**Ответ 200 OK:**
```json
{
  "short_id": "aB3x9Qk",
  "original_url": "https://example.com/very/long/path?query=1",
  "click_count": 1542,
  "created_at": "2025-01-15T10:30:00Z",
  "expires_at": "2025-12-31T23:59:59Z",
  "is_active": true
}
```

**Ошибки:**
- `404 Not Found` — ID не существует
- `400 Bad Request` — неверный формат ID

---

### DELETE `/{id}`

**Поведение:** Soft delete — установка `is_deleted = TRUE`, инвалидация кэша Redis (`DEL url:{id}`, `DEL stats:{id}`).

**Ответ 204 No Content** — успешно удалено.

**Ошибки:**
- `404 Not Found` — ID не существует
- `400 Bad Request` — неверный формат ID

---

### Общий формат ошибок

```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Short URL not found",
    "request_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

### Swagger

Доступен по адресу `/docs` (Swagger UI) и `/redoc` (ReDoc). FastAPI генерирует автоматически из Pydantic-моделей и декораторов маршрутов.

---

## 6. Нефункциональные требования

### Безопасность
- **Rate limiting:** 100 запросов/мин на IP. Реализация — sliding window через Redis sorted set. При превышении возвращается `429` с заголовком `Retry-After`.
- **Валидация URL:** запрет SSRF-векторов (локальные адреса, private ranges) через конфигурируемый список.
- **SQL-инъекции:** предотвращены через параметризованные запросы SQLAlchemy.
- **Заголовки безопасности:** `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Strict-Transport-Security` (при HTTPS).
- **Логирование:** без записи полных URL в логи при уровне INFO (PII-защита), на DEBUG — полный лог.

### Производительность
- **Cache hit ratio** для GET `/{id}` — ожидается >90% при активном использовании.
- **Время ответа:** P99 < 50ms для редиректа (cache hit), P99 < 200ms для POST `/shorten`.
- **Генерация ID:** Base62 (символы `A-Za-z0-9`), 7 символов = 62^7 ≈ 3.5 триллиона комбинаций. Вероятность коллизии при 10 млн ссылок — пренебрежимо мала, но проверка уникальности обязательна (retry до 3 раз при коллизии).

### Масштабирование
- **Горизонтальное:** сервис stateless (кроме in-memory кэша, который не критичен), масштабируется добавлением инстансов за load balancer.
- **Redis:** при росте — Redis Cluster для шардирования.
- **PostgreSQL:** read-replicas для `/stats` запросов при высокой нагрузке.
- **Буферизация счётчиков:** счётчики переходов накапливаются в Redis, периодически (каждые 100 переходов или раз в минуту) сбрасываются в PostgreSQL, что снижает нагрузку на БД.

### Graceful Shutdown
- Uvicorn перехватывает `SIGTERM`/`SIGINT`.
- Прекращает приём новых соединений.
- Дожидается завершения активных запросов (timeout 30с).
- Закрывает пулы соединений PostgreSQL и Redis.
- Сбрасывает несохранённые счётчики из Redis в PostgreSQL.

### Надёжность
- **Health check:** `GET /health` → `200 {"status": "ok"}` (проверяет connectivity к PostgreSQL и Redis).
- **Readiness check:** `GET /ready` — проверяет готовность к приёму трафика.
- **Ретраи:** при недоступности Redis — fallback к PostgreSQL (с логированием предупреждения).

---

## 7. Структура проекта

```
url-shortener/
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
├── alembic.ini
├── .env.example
├── README.md
├── alembic/
│   ├── env.py
│   └── versions/
│       └── 001_initial.py
├── src/
│   ├── __init__.py
│   ├── main.py                    # Точка входа, создание FastAPI app, middleware
│   ├── config.py                  # Настройки через pydantic-settings
│   ├── dependencies.py            # DI: получение сессий БД, Redis-клиента
│   ├── api/
│   │   ├── __init__.py
│   │   ├── router.py              # Объединение всех роутеров
│   │   ├── shorten.py             # POST /shorten
│   │   ├── redirect.py            # GET /{id}
│   │   ├── stats.py               # GET /stats/{id}
│   │   └── delete.py              # DELETE /{id}
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── shorten.py             # ShortenRequest, ShortenResponse
│   │   ├── stats.py               # StatsResponse
│   │   └── errors.py              # ErrorResponse
│   ├── models/
│   │   ├── __init__.py
│   │   └── url_mapping.py         # SQLAlchemy-модель
│   ├── services/
│   │   ├── __init__.py
│   │   ├── url_shortener.py       # URLShortenerService
│   │   ├── stats.py               # StatsService
│   │   └── id_generator.py        # IDGenerator (Base62)
│   ├── middleware/
│   │   ├── __init__.py
│   │   ├── rate_limiter.py        # RateLimiter middleware
│   │   ├── request_id.py          # RequestID middleware
│   │   └── error_handler.py       # Глобальный error handler
│   ├── db/
│   │   ├── __init__.py
│   │   ├── postgres.py            # Async engine, session factory
│   │   └── redis.py               # Redis-клиент, connection pool
│   └── utils/
│       ├── __init__.py
│       ├── url_validator.py       # Валидация URL, SSRF-защита
│       └── base62.py              # Base62 кодирование/декодирование
└── tests/
    ├── __init__.py
    ├── conftest.py                # Фикстуры: test client, БД, Redis
    ├── test_shorten.py
    ├── test_redirect.py
    ├── test_stats.py
    ├── test_delete.py
    ├── test_rate_limiter.py
    ├── test_url_validator.py
    └── test_id_generator.py
```

### Конфигурация (`.env.example`)

```
APP_HOST=0.0.0.0
APP_PORT=8000
APP_BASE_URL=https://sho.rt
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/urlshortener
REDIS_URL=redis://localhost:6379/0
RATE_LIMIT_PER_MINUTE=100
CACHE_TTL_SECONDS=3600
SHUTDOWN_TIMEOUT_SECONDS=30
LOG_LEVEL=INFO
```

---

**Этот документ — единственный источник правды.** Разработчик реализует код строго по описанным контрактам. DevOps разворачивает инфраструктуру согласно указанному стеку и конфигурации. Любые отклонения требуют обновления этого документа.