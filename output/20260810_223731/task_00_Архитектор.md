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

Микросервис URL Shortener принимает длинные URL-адреса и возвращает короткие 7-символьные идентификаторы. При обращении к короткой ссылке сервис перенаправляет пользователя на исходный URL. Сервис также предоставляет статистику переходов и возможность удаления ссылок.

**Ключевые сценарии использования:**

- **Создание короткой ссылки:** Пользователь отправляет POST-запрос с длинным URL, получает короткий ID (7 символов) и полный короткий URL.
- **Редирект:** При обращении к `GET /{id}` сервис ищет оригинальный URL, инкрементирует счётчик переходов и возвращает HTTP 301/302 с заголовком `Location`.
- **Просмотр статистики:** `GET /stats/{id}` возвращает оригинальный URL, количество переходов и дату создания.
- **Удаление ссылки:** `DELETE /{id}` помечает ссылку как удалённую (soft delete), после чего редирект невозможен.
- **Rate limiting:** Все эндпоинты ограничены 100 запросами в минуту на IP-адрес клиента.

---

## 2. Технологический стек

| Компонент | Технология | Обоснование |
|-----------|-----------|-------------|
| Язык | Python 3.11+ | Современная типизация, async/await, широкая экосистема |
| Web-фреймворк | FastAPI 0.110+ | Нативная async-поддержка, автогенерация OpenAPI/Swagger, Pydantic-валидация |
| ASGI-сервер | Uvicorn | Рекомендуемый сервер для FastAPI, поддержка graceful shutdown через сигналы SIGTERM/SIGINT |
| БД | PostgreSQL 15 | Реляционное хранилище, надёжность, индексы, транзакции |
| ORM | SQLAlchemy 2.0 (async) | Зрелая ORM с async-поддержкой, совместимость с Pydantic |
| Кэш | Redis 7 | Кэширование редиректов (hot keys), хранение rate-limit счётчиков, быстрый read-path |
| Миграции | Alembic | Стандарт де-факто для SQLAlchemy-миграций |
| Тестирование | pytest + httpx + pytest-asyncio | Интеграционные и unit-тесты, async-клиент для FastAPI |
| Контейнеризация | Docker + docker-compose | Воспроизводимое окружение для разработки и продакшена |

---

## 3. Архитектура

```
                    ┌──────────────────────────┐
                    │       Client / Browser    │
                    └────────────┬─────────────┘
                                 │ HTTP
                                 ▼
                    ┌──────────────────────────┐
                    │      Uvicorn (ASGI)      │
                    │   ┌──────────────────┐   │
                    │   │     FastAPI      │   │
                    │   │  Middleware:     │   │
                    │   │  - RateLimiter   │   │
                    │   │  - ExceptionHdlr  │   │
                    │   └────────┬─────────┘   │
                    └────────────┼─────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              ▼                  ▼                   ▼
     ┌────────────────┐  ┌──────────────┐   ┌────────────────┐
     │  URL Service   │  │ Stats Service│   │  Delete Service│
     │  (shorten/     │  │ (stats/      │   │ (soft-delete)  │
     │   redirect)    │  │  increment)  │   │                │
     └───────┬────────┘  └──────┬───────┘   └───────┬────────┘
             │                  │                   │
             ▼                  ▼                   ▼
     ┌─────────────────────────────────────────────────────┐
     │                    Redis (cache)                     │
     │  - cache:{id} → original_url (TTL 1h)                │
     │  - ratelimit:{ip}:{minute} → count                   │
     └─────────────────────────────────────────────────────┘
             │
             ▼
     ┌─────────────────────────────────────────────────────┐
     │                  PostgreSQL                           │
     │  - urls table (id, original_url, created_at,         │
     │    clicks, deleted)                                   │
     └─────────────────────────────────────────────────────┘
```

**Описание компонентов:**

- **FastAPI Application:** Точка входа. Регистрирует роутеры, middleware, обработчики жизненного цикла (startup/shutdown).
- **Rate Limiter Middleware:** Перехватывает каждый запрос, проверяет счётчик в Redis по ключу `ratelimit:{ip}:{minute}`. При превышении 100 — возвращает 429.
- **URL Service:** Обрабатывает `POST /shorten` (генерация ID, запись в БД) и `GET /{id}` (чтение из кэша → БД, редирект).
- **Stats Service:** Обрабатывает `GET /stats/{id}` и инкрементирует счётчик кликов при редиректе.
- **Delete Service:** Обрабатывает `DELETE /{id}`, устанавливает `deleted=True`.
- **Redis:** Кэш редиректов (hot path), хранилище rate-limit счётчиков.
- **PostgreSQL:** Основное хранилище данных о ссылках.

---

## 4. Модель данных

### Таблица `urls`

| Поле | Тип | Ограничения | Описание |
|------|-----|-------------|----------|
| `id` | `VARCHAR(7)` | PRIMARY KEY | Короткий идентификатор (7 символов, base62) |
| `original_url` | `TEXT` | NOT NULL | Исходный длинный URL |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT NOW() | Время создания |
| `clicks` | `BIGINT` | NOT NULL, DEFAULT 0 | Количество переходов |
| `deleted` | `BOOLEAN` | NOT NULL, DEFAULT FALSE | Флаг soft-delete |

### Индексы

- `PRIMARY KEY` на `id` — быстрый lookup при редиректе.
- `idx_urls_original_url` на `original_url` — для проверки дубликатов (опционально, можно использовать для возврата существующего ID).
- `idx_urls_created_at` на `created_at` — для аналитики и очистки.

### Генерация короткого ID

Используется алфавит base62: `[a-zA-Z0-9]` (62 символа). 7 символов дают 62^7 ≈ 3.5 триллиона комбинаций. Алгоритм:

1. Генерируем случайное число в диапазоне `[0, 62^7)`.
2. Кодируем в base62, дополняем до 7 символов слева нулями (символом `0`).
3. Проверяем отсутствие коллизии в БД. При коллизии — повторяем (вероятность мала при разумном объёме).

---

## 5. API-контракты

### POST /shorten

**Запрос:**
```json
{
  "url": "https://example.com/very/long/path?query=1"
}
```

**Валидация URL:** Pydantic-валидатор проверяет, что URL имеет схему `http` или `https`, содержит валидный домен. Невалидные URL → 422.

**Ответ (201 Created):**
```json
{
  "id": "aB3x9Kq",
  "short_url": "http://localhost:8000/aB3x9Kq",
  "original_url": "https://example.com/very/long/path?query=1"
}
```

**Ошибки:**
- `422` — невалидный URL в теле запроса.
- `429` — превышен rate limit.

---

### GET /{id}

**Поведение:** Ищет `id` в Redis-кэше. Если нет — читает из PostgreSQL, кэширует с TTL 1 час. Если `deleted=True` или запись не найдена — возвращает 404. При успешном нахождении — инкрементирует `clicks` (через `UPDATE urls SET clicks = clicks + 1`) и возвращает редирект.

**Ответ (302 Found):**
```
Location: https://example.com/very/long/path?query=1
```

**Ошибки:**
- `404` — ссылка не найдена или удалена.
- `429` — превышен rate limit.

---

### GET /stats/{id}

**Ответ (200 OK):**
```json
{
  "id": "aB3x9Kq",
  "original_url": "https://example.com/very/long/path?query=1",
  "clicks": 142,
  "created_at": "2025-01-15T10:30:00Z"
}
```

**Ошибки:**
- `404` — ссылка не найдена или удалена.
- `429` — превышен rate limit.

---

### DELETE /{id}

**Поведение:** Устанавливает `deleted = True` в БД, инвалидирует кэш в Redis (`DEL cache:{id}`).

**Ответ (204 No Content):** Тело ответа пустое.

**Ошибки:**
- `404` — ссылка не найдена.
- `429` — превышен rate limit.

---

### Общие коды ошибок

| Код | Описание |
|-----|----------|
| 422 | Ошибка валидации тела запроса |
| 404 | Ресурс не найден |
| 429 | Rate limit превышен (заголовок `Retry-After` в секундах) |
| 500 | Внутренняя ошибка сервера |

### Swagger

Доступен по адресу `/docs` (Swagger UI) и `/redoc` (ReDoc). FastAPI генерирует автоматически на основе type hints и Pydantic-моделей.

---

## 6. Нефункциональные требования

### Безопасность

- **Валидация URL:** Принимаются только `http` и `https` схемы. Запрещены `javascript:`, `file:`, `data:` и другие потенциально опасные схемы. Проверяется корректность домена (наличие точки, валидные символы).
- **SSRF-защита:** Опционально — блокировка ссылок на приватные IP-диапазоны (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 127.0.0.0/8) при создании.
- **Rate limiting:** 100 запросов/мин на IP. Реализовано через Redis (атомарный `INCR` + `EXPIRE`). Ключ: `ratelimit:{ip}:{minute_bucket}`. При `count > 100` возвращаем 429 с заголовком `Retry-After`.
- **SQL-инъекции:** Используется SQLAlchemy ORM с параметризованными запросами — риск отсутствует.
- **Логирование:** Структурированные логи (JSON) с уровнем INFO для запросов, ERROR для исключений. Не логируем полные URL пользователей в продакшене (privacy).

### Производительность

- **Редирект (read path):** Сначала Redis-кэш (latency ~1ms). Cache miss → PostgreSQL (~5-10ms). Кэш заполняется на 1 час. Ожидаемая пропускная способность: 10 000+ редиректов/сек на одном инстансе.
- **Создание ссылки (write path):** ~10-20ms (запись в PostgreSQL). Генерация ID — O(1) + проверка коллизии.
- **Инкремент кликов:** Выполняется асинхронно (через background task FastAPI или отдельный worker) для минимизации latency редиректа. В простейшей реализации — синхронный `UPDATE`, что приемлемо для MVP.
- **Connection pooling:** SQLAlchemy async pool, `pool_size=20`, `max_overflow=10`.

### Масштабирование

- **Горизонтальное масштабирование:** Сервис stateless — можно запускать несколько реплик за load balancer. Redis и PostgreSQL — общие.
- **Redis:** Можно перейти на Redis Cluster при росте нагрузки на кэш.
- **PostgreSQL:** Read-реплики для `GET /stats` и `GET /{id}` (если допустима eventual consistency для счётчика кликов). Master — для записи.
- **Очереди (будущее):** При высоком трафике инкремент кликов можно вынести в очередь (Celery/RabbitMQ) для батчинг-записей в БД.

### Graceful Shutdown

- Uvicorn перехватывает `SIGTERM`/`SIGINT`.
- Перестаёт принимать новые соединения.
- Дожидается завершения текущих запросов (timeout 30 сек).
- Закрывает пулы соединений PostgreSQL и Redis.
- Логирует факт завершения.

### Отказоустойчивость

- **Redis недоступен:** Редиректы продолжают работать напрямую через PostgreSQL (с замедлением). Rate limiting переходит в режим "fail-open" (пропускаем запросы, логируем warning).
- **PostgreSQL недоступен:** Сервис возвращает 503 для всех запросов, кроме тех, что обслуживаются кэшем (только редиректы для закэшированных ключей).

---

## 7. Структура проекта

```
url-shortener/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── alembic.ini
├── README.md
├── .env.example
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 001_initial.py
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app, lifespan, middleware
│   ├── config.py                  # Settings (pydantic-settings)
│   ├── database.py                # Async engine, session factory
│   ├── redis_client.py            # Redis connection pool
│   ├── models/
│   │   ├── __init__.py
│   │   └── url.py                 # SQLAlchemy model URLRecord
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── url.py                 # Pydantic: ShortenRequest, ShortenResponse
│   │   └── stats.py               # Pydantic: StatsResponse
│   ├── services/
│   │   ├── __init__.py
│   │   ├── url_service.py         # create_short_url, get_original_url
│   │   ├── stats_service.py       # get_stats, increment_clicks
│   │   └── delete_service.py      # soft_delete, invalidate_cache
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── id_generator.py        # base62 encoding, random ID generation
│   │   └── url_validator.py       # URL validation logic
│   ├── middleware/
│   │   ├── __init__.py
│   │   └── rate_limiter.py        # Redis-based rate limiting
│   └── routers/
│       ├── __init__.py
│       ├── shorten.py             # POST /shorten
│       ├── redirect.py            # GET /{id}
│       ├── stats.py               # GET /stats/{id}
│       └── delete.py              # DELETE /{id}
└── tests/
    ├── __init__.py
    ├── conftest.py                # Fixtures: test client, DB, Redis
    ├── test_shorten.py            # Тесты POST /shorten
    ├── test_redirect.py           # Тесты GET /{id}
    ├── test_stats.py              # Тесты GET /stats/{id}
    ├── test_delete.py             # Тесты DELETE /{id}
    ├── test_rate_limiter.py       # Тесты rate limiting
    ├── test_url_validation.py     # Тесты валидации URL
    └── test_id_generator.py       # Тесты генерации ID
```

### Описание ключевых файлов

- **`app/main.py`**: Создаёт `FastAPI()` с `lifespan`-контекстом (инициализация пулов БД и Redis при старте, корректное закрытие при shutdown). Регистрирует middleware rate limiter, подключает роутеры, настраивает обработчики исключений.
- **`app/config.py`**: `pydantic-settings` `BaseSettings` с переменными окружения: `DATABASE_URL`, `REDIS_URL`, `BASE_URL` (для генерации коротких ссылок), `RATE_LIMIT_PER_MINUTE=100`, `CACHE_TTL_SECONDS=3600`.
- **`app/database.py`**: `create_async_engine` + `async_sessionmaker`. Экспортирует `get_db` dependency для FastAPI.
- **`app/redis_client.py`**: `redis.asyncio.Redis` с connection pool. Экспортирует `get_redis` dependency.
- **`app/utils/id_generator.py`**: Функция `generate_short_id() -> str` — генерирует 7-символьный base62 ID. Функция `encode_base62(num: int) -> str`.
- **`app/middleware/rate_limiter.py`**: Middleware, проверяющее `ratelimit:{ip}:{minute}` в Redis. Возвращает 429 при превышении.
- **`tests/conftest.py`**: Настраивает тестовую БД (SQLite in-memory или test PostgreSQL), мокает/использует test Redis, создаёт `httpx.AsyncClient`.

---

## Заключение

Данный документ описывает полное решение для микросервиса URL Shortener. Разработчик может приступить к реализации, следуя структуре проекта, API-контрактам и модели данных. DevOps может подготовить Docker-окружение на основе описанного стека. Все архитектурные решения обоснованы, нефункциональные требования зафиксированы. Документ является единственным источником правды для команды.