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

**Версия:** 1.0  
**Автор:** Архитектор  
**Статус:** Утверждён  

---

## 1. Обзор

### Назначение системы

Микросервис URL Shortener принимает длинные URL-адреса и возвращает короткие идентификаторы. При обращении к короткой ссылке сервис выполняет HTTP-редирект (307) на исходный URL. Сервис также предоставляет статистику переходов и возможность удаления ссылок.

### Ключевые сценарии использования

1. **Сокращение URL.** Пользователь отправляет POST-запрос с длинным URL. Сервис генерирует уникальный короткий идентификатор (6 символов, base62), сохраняет в PostgreSQL, кэширует в Redis и возвращает короткую ссылку.
2. **Редирект.** Пользователь обращается по короткой ссылке. Сервис ищет URL в Redis (кэш), при промахе — в PostgreSQL, инкрементирует счётчик переходов (Redis HINCRBY), выполняет 307-редирект.
3. **Статистика.** Пользователь запрашивает GET /stats/{id}. Сервис возвращает исходный URL, количество переходов и дату создания.
4. **Удаление.** DELETE /{id} помечает запись как удалённую (soft delete), инвалидирует кэш.

---

## 2. Технологический стек

| Компонент | Технология | Обоснование |
|-----------|-----------|-------------|
| Язык | Python 3.11+ | Быстрая разработка, богатая экосистема, нативная async-поддержка |
| Web-фреймворк | FastAPI 0.110+ | Async, автогенерация OpenAPI/Swagger, Pydantic-валидация, высокая производительность |
| ORM | SQLAlchemy 2.0 (async) | Зрелая ORM, async-поддержка, совместима с FastAPI |
| БД | PostgreSQL 15 | Реляционная БД с надёжными транзакциями, индексами, B-tree для быстрого поиска по short_code |
| Кэш | Redis 7 | In-memory хранилище для кэширования URL и счётчиков переходов; низкая задержка (<1 мс) |
| Миграции | Alembic | Стандарт для SQLAlchemy, версионирование схемы |
| Rate Limiting | slowapi (на базе limits) | Интеграция с FastAPI, стратегия fixed-window на Redis |
| Валидация URL | Pydantic + кастомный валидатор (urllib.parse + проверка схемы) | Строгая проверка на уровне схемы запроса |
| Тестирование | pytest + pytest-asyncio + httpx (AsyncClient) | Покрытие unit и integration тестами |
| Контейнеризация | Docker + docker-compose | Воспроизводимое окружение для разработки и продакшена |
| Логирование | logging (стандартный) + structlog | Структурированные логи для observability |

---

## 3. Архитектура

### Диаграмма компонентов (текст)

```
                    ┌──────────────────────────┐
                    │       Клиент (браузер)    │
                    └────────────┬─────────────┘
                                 │ HTTP
                                 ▼
                    ┌──────────────────────────┐
                    │      FastAPI App         │
                    │  ┌────────────────────┐  │
                    │  │   API Routers       │  │
                    │  │  /shorten /{id}     │  │
                    │  │  /stats/{id} DELETE │  │
                    │  └────────┬───────────┘  │
                    │           │              │
                    │  ┌────────▼───────────┐  │
                    │  │  Service Layer      │  │
                    │  │  (бизнес-логика)    │  │
                    │  └───┬──────────┬──────┘  │
                    │      │          │         │
                    │ ┌────▼───┐ ┌───▼──────┐   │
                    │ │Cache   │ │Repository│   │
                    │ │Manager │ │  Layer   │   │
                    │ │(Redis) │ │(PG via   │   │
                    │ │        │ │SQLAlchemy│   │
                    │ └────┬───┘ └────┬─────┘   │
                    └──────┼──────────┼─────────┘
                           │          │
              ┌────────────▼──┐  ┌────▼──────────┐
              │     Redis     │  │  PostgreSQL   │
              │  (cache +     │  │  (источник     │
              │   counters)   │  │   истины)      │
              └───────────────┘  └───────────────┘
```

### Описание компонентов

- **API Routers** — принимают HTTP-запросы, валидируют входные данные через Pydantic-схемы, делегируют в Service Layer.
- **Service Layer** — содержит бизнес-логику: генерация short_code, проверка дубликатов, инкремент счётчика, инвалидация кэша. Не зависит от HTTP-контекста.
- **Cache Manager** — абстракция над Redis. Хранит映射 `short_code → original_url` с TTL 24 часа. Хранит счётчики переходов в Redis Hash `stats:{short_code}`.
- **Repository Layer** — абстракция над PostgreSQL через SQLAlchemy. CRUD-операции над таблицей `urls`.
- **Rate Limiter Middleware** — на базе slowapi, ограничивает 30 запросов/мин на IP для POST /shorten и 100/мин для остальных.
- **PostgreSQL** — источник истины. Хранит таблицу `urls` с индексами по `short_code` и `created_at`.
- **Redis** — кэш первого уровня. Ускоряет редиректы до <5 мс. При недоступности Redis сервис деградирует до чтения из PostgreSQL (circuit breaker).

---

## 4. Модель данных

### Таблица `urls`

| Поле | Тип | Ограничения | Описание |
|------|-----|------------|----------|
| `id` | BIGSERIAL | PK | Внутренний идентификатор |
| `short_code` | VARCHAR(10) | UNIQUE, NOT NULL, INDEX | Короткий код (base62, 6 символов) |
| `original_url` | TEXT | NOT NULL | Исходный URL |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Дата создания |
| `is_deleted` | BOOLEAN | NOT NULL, DEFAULT false | Soft delete флаг |
| `expires_at` | TIMESTAMPTZ | NULL | Опциональная дата истечения |

### Индексы

- `idx_urls_short_code` — UNIQUE B-tree по `short_code` — для O(log n) поиска при редиректе.
- `idx_urls_created_at` — B-tree по `created_at` — для аналитики и очистки.

### Redis-структуры

- `url:{short_code}` → строка (original_url), TTL 24h.
- `stats:{short_code}` → Hash с полями `clicks` (INT), `last_accessed` (TIMESTAMP).
- `ratelimit:{ip}:{endpoint}` → счётчик для rate limiter, TTL 60s.

---

## 5. API-контракты

### POST /shorten

**Запрос:**
```json
{
  "url": "https://example.com/very/long/path?query=1"
}
```

**Валидация:** `url` — обязательное поле, строка, должна иметь схему `http` или `https`, валидный домен. Максимальная длина — 2048 символов.

**Ответ 201 Created:**
```json
{
  "short_code": "aB3x9Q",
  "short_url": "http://localhost:8000/aB3x9Q",
  "original_url": "https://example.com/very/long/path?query=1"
}
```

**Ошибки:**
- `400 Bad Request` — невалидный URL.
- `409 Conflict` — URL уже сокращён (возвращается существующий short_code).
- `429 Too Many Requests` — превышен rate limit.

---

### GET /{short_code}

**Редирект.** Если `short_code` найден и не удалён — `307 Temporary Redirect` с заголовком `Location: <original_url>`. Инкрементирует счётчик переходов.

**Ошибки:**
- `404 Not Found` — код не существует или удалён.
- `410 Gone` — ссылка истекла по `expires_at`.

---

### GET /stats/{short_code}

**Ответ 200 OK:**
```json
{
  "short_code": "aB3x9Q",
  "original_url": "https://example.com/very/long/path?query=1",
  "clicks": 42,
  "created_at": "2025-01-15T10:30:00Z"
}
```

**Ошибки:**
- `404 Not Found` — код не найден.

---

### DELETE /{short_code}

**Ответ 204 No Content** — успешное soft-delete. Инвалидирует кэш Redis.

**Ошибки:**
- `404 Not Found` — код не найден.
- `409 Conflict` — уже удалён.

---

### Общие заголовки ответов

- `X-RateLimit-Limit` — лимит запросов.
- `X-RateLimit-Remaining` — оставшиеся запросы.
- `X-RateLimit-Reset` — время сброса (Unix timestamp).

### Swagger

Доступен по адресу `/docs` (Swagger UI) и `/redoc` (ReDoc). Автогенерируется FastAPI из Pydantic-моделей и docstrings.

---

## 6. Нефункциональные требования

### Безопасность

- **Валидация URL:** только `http` и `https` схемы; блокировка `localhost`, `127.0.0.1`, `0.0.0.0`, `169.254.*` (SSRF-защита) — настраивается через env-переменную `BLOCK_PRIVATE_IPS=true`.
- **Rate Limiting:** 30 запросов/мин на IP для POST /shorten; 100/мин для GET. Реализовано через slowapi + Redis backend.
- **CORS:** по умолчанию отключён; включается через `ALLOWED_ORIGINS` env.
- **Secrets:** все секреты (пароли БД, Redis) — через переменные окружения, не в коде.
- **Логи:** не логируем original_url целиком (возможны чувствительные данные) — только short_code и метаданные.

### Производительность

- **Целевая задержка редиректа:** < 10 мс при кэш-хите (Redis), < 50 мс при кэш-миссе (PostgreSQL).
- **Throughput:** 5000 RPS на одном инстансе (async FastAPI + connection pool).
- **Connection Pool:** SQLAlchemy pool_size=20, max_overflow=10. Redis-пул — 50 соединений.
- **Счётчик переходов:** асинхронная запись в Redis (HINCRBY), периодическая синхронизация в PostgreSQL (background task каждые 60 секунд) — снижает нагрузку на БД.

### Масштабирование

- **Горизонтальное:** сервис stateless — масштабируется добавлением инстансов за load balancer.
- **Redis:** поддерживает cluster mode для горизонтального масштабирования кэша.
- **PostgreSQL:** read-replicas для GET-операций (stats) при росте нагрузки.
- **Генерация short_code:** base62-кодирование последовательности из PostgreSQL sequence + retry при коллизии (макс. 3 попытки).

### Отказоустойчивость

- **Redis недоступен:** сервис продолжает работать, читая напрямую из PostgreSQL (circuit breaker с timeout 1s).
- **PostgreSQL недоступен:** сервис возвращает `503 Service Unavailable` для всех запросов, кроме GET /{id} при кэш-хите.
- **Healthcheck:** `GET /health` возвращает `200` при доступности БД и Redis, `503` при отказе.

### Тестирование

- **Unit-тесты:** генерация short_code, валидация URL, бизнес-логика service layer.
- **Integration-тесты:** полный цикл через httpx AsyncClient с testcontainers (PostgreSQL + Redis в Docker).
- **Покрытие:** минимум 85%.
- **Запуск:** `pytest --cov=app --cov-report=term-missing`.

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
│   ├── main.py                  # FastAPI app, middleware, lifespan
│   ├── config.py                # Pydantic Settings (env vars)
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py              # Dependency injection (db session, redis)
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py        # Объединение роутеров
│   │       ├── shorten.py       # POST /shorten
│   │       ├── redirect.py      # GET /{short_code}
│   │       ├── stats.py         # GET /stats/{short_code}
│   │       └── delete.py        # DELETE /{short_code}
│   ├── core/
│   │   ├── __init__.py
│   │   ├── security.py          # SSRF-проверки, валидация URL
│   │   ├── rate_limiter.py      # slowapi конфигурация
│   │   └── exceptions.py        # Кастомные исключения + handlers
│   ├── db/
│   │   ├── __init__.py
│   │   ├── session.py           # Async engine, sessionmaker
│   │   └── redis_client.py      # Redis connection pool
│   ├── models/
│   │   ├── __init__.py
│   │   └── url.py               # SQLAlchemy модель Url
│   ├── repositories/
│   │   ├── __init__.py
│   │   └── url_repository.py    # CRUD над таблицей urls
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── shorten.py           # ShortenRequest, ShortenResponse
│   │   └── stats.py             # StatsResponse
│   ├── services/
│   │   ├── __init__.py
│   │   ├── url_service.py       # Бизнес-логика сокращения
│   │   ├── cache_service.py     # Redis кэш + счётчики
│   │   └── code_generator.py    # base62 генерация short_code
│   └── utils/
│       ├── __init__.py
│       └── base62.py            # Кодирование/декодирование base62
└── tests/
    ├── __init__.py
    ├── conftest.py              # Фикстуры: test DB, Redis, client
    ├── unit/
    │   ├── test_base62.py
    │   ├── test_url_validation.py
    │   └── test_code_generator.py
    └── integration/
        ├── test_shorten.py
        ├── test_redirect.py
        ├── test_stats.py
        ├── test_delete.py
        └── test_rate_limiting.py
```

---

## Приложение А: Переменные окружения

| Переменная | Значение по умолчанию | Описание |
|-----------|----------------------|----------|
| `DATABASE_URL` | `postgresql+asyncpg://user:pass@localhost:5432/shortener` | DSN PostgreSQL |
| `REDIS_URL` | `redis://localhost:6379/0` | DSN Redis |
| `SHORT_CODE_LENGTH` | `6` | Длина короткого кода |
| `CACHE_TTL_SECONDS` | `86400` | TTL кэша в Redis (24ч) |
| `RATE_LIMIT_SHORTEN` | `30/minute` | Лимит для POST /shorten |
| `RATE_LIMIT_DEFAULT` | `100/minute` | Лимит для остальных |
| `BLOCK_PRIVATE_IPS` | `true` | Блокировка SSRF |
| `ALLOWED_ORIGINS` | `""` | CORS origins (через запятую) |
| `BASE_URL` | `http://localhost:8000` | Базовый URL для генерации short_url |

---

**Документ завершён.** Это — единственный источник правды для команды. Любые отклонения от спецификации требуют согласования с Архитектором.