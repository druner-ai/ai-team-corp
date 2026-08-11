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

# Архитектурный документ: Микросервис URL Shortener

**Версия:** 1.0.0
**Статус:** Утверждён
**Роль:** Senior Software Architect

---

## 1. Обзор

### 1.1. Назначение системы

Микросервис URL Shortener — это REST API для сокращения длинных URL-адресов в короткие коды, обеспечения перенаправления по коротким ссылкам и сбора базовой статистики переходов. Сервис спроектирован как независимый микросервис, не имеющий внешних зависимостей кроме PostgreSQL и Redis.

### 1.2. Ключевые сценарии использования

| # | Сценарий | Актёр | Описание |
|---|----------|-------|----------|
| UC-1 | Создание короткой ссылки | Клиент | Отправляет POST `/shorten` с оригинальным URL, получает короткий код и полную короткую ссылку. |
| UC-2 | Перенаправление | Пользователь | Открывает `GET /{short_code}`, получает HTTP 302 с `Location` на оригинальный URL. Сервис фиксирует клик. |
| UC-3 | Просмотр статистики | Клиент | Отправляет `GET /stats/{short_code}`, получает количество кликов, дату создания, статус активности. |
| UC-4 | Удаление ссылки | Клиент | Отправляет `DELETE /{short_code}`, сервис помечает ссылку как неактивную. Последующие перенаправления возвращают 410 Gone. |
| UC-5 | Защита от перегрузки | Система | Rate limiter на базе Redis ограничивает количество запросов с одного IP-адреса. |

### 1.3. Границы системы

**Входит в scope:** создание, перенаправление, статистика, удаление, rate limiting, валидация URL, Swagger-документация, unit/integration тесты.

**Не входит в scope:** аутентификация пользователей, кастомные короткие коды, QR-коды, веб-интерфейс, bulk-операции, экспорт статистики, вебхуки.

---

## 2. Технологический стек

### 2.1. Язык и фреймворк

| Компонент | Технология | Версия | Обоснование |
|-----------|-----------|--------|-------------|
| Язык | Python | 3.11+ | Требование задачи. Высокая скорость разработки, богатая экосистема. |
| Web-фреймворк | FastAPI | 0.110+ | Требование задачи. Async-native, автоматическая генерация OpenAPI/Swagger, встроенная валидация через Pydantic, высокая производительность. |
| ASGI-сервер | Uvicorn | 0.27+ | Стандартный ASGI-сервер для FastAPI. В production — за Gunicorn (workers management). |
| Валидация | Pydantic | v2 | Интегрирована с FastAPI, в 5–10 раз быстрее v1, нативная поддержка `HttpUrl`. |
| ORM | SQLAlchemy | 2.0 (async) | Зрелая ORM с поддержкой async через `asyncpg`. Декларативный стиль 2.0. |
| Драйвер БД | asyncpg | 0.29+ | Высокопроизводительный async-драйвер PostgreSQL. |
| Миграции | Alembic | 1.13+ | Стандартный инструмент миграций для SQLAlchemy. |

### 2.2. База данных и кэш

| Компонент | Технология | Версия | Обоснование |
|-----------|-----------|--------|-------------|
| Основное хранилище | PostgreSQL | 15+ | Требование задачи. ACID-транзакции, надёжное хранение ссылок и кликов, богатая индексация, partial indexes для активных ссылок. |
| Кэш + Rate Limiter | Redis | 7+ | Требование задачи. Кэширование `short_code → original_url` для O(1) перенаправлений. Sliding-window rate limiting через sorted sets. Атомарные счётчики кликов через `INCR`. |

### 2.3. Инфраструктура и тестирование

| Компонент | Технология | Обоснование |
|-----------|-----------|-------------|
| Контейнеризация | Docker + docker-compose | Изолированная среда, воспроизводимость. Compose поднимает app + PostgreSQL + Redis одной командой. |
| Тестирование | pytest, pytest-asyncio, httpx (ASGI transport) | Требование задачи. `httpx.AsyncClient` с `ASGITransport` позволяет тестировать FastAPI без запуска сервера. |
| Линтинг | ruff, mypy | Современный линтер (заменяет flake8+isort), статическая типизация. |
| Генерация ID | nanoid | Криптографически случайные короткие коды, base62, 8 символов → 218 триллионов комбинаций. Защита от перебора. |

### 2.4. Очереди

Очереди сообщений (Celery, RabbitMQ, Kafka) **не используются** в данной итерации. Запись детальных кликов выполняется через `BackgroundTasks` FastAPI (fire-and-forget в рамках процесса). Если нагрузка вырастет, следующим шагом будет внедрение Celery + Redis Broker для асинхронной записи кликов.

---

## 3. Архитектура

### 3.1. Диаграмма компонентов (текстовая)

```
                          ┌─────────────────────────────────────────────┐
                          │                  КЛИЕНТ                      │
                          │   (браузер, curl, другое приложение)         │
                          └──────────────────┬──────────────────────────┘
                                             │ HTTP/HTTPS
                                             ▼
                          ┌─────────────────────────────────────────────┐
                          │            NGINX (Reverse Proxy)             │
                          │   TLS-терминация, gzip, таймауты, балансир   │
                          └──────────────────┬──────────────────────────┘
                                             │
                          ┌──────────────────▼──────────────────────────┐
                          │           GUNICORN (process manager)         │
                          │            4 workers × Uvicorn               │
                          └──────────────────┬──────────────────────────┘
                                             │
                          ┌──────────────────▼──────────────────────────┐
                          │              FASTAPI APPLICATION             │
                          │                                              │
                          │  ┌────────────────────────────────────────┐  │
                          │  │         Middleware Layer               │  │
                          │  │  • RateLimitMiddleware (Redis)         │  │
                          │  │  • CORSMiddleware                     │  │
                          │  │  • ExceptionHandlerMiddleware          │  │
                          │  └────────────────┬───────────────────────┘  │
                          │                   │                          │
                          │  ┌────────────────▼───────────────────────┐  │
                          │  │           API Router (v1)              │  │
                          │  │  POST /shorten                         │  │
                          │  │  GET  /{short_code}                    │  │
                          │  │  GET  /stats/{short_code}              │  │
                          │  │  DELETE /{short_code}                  │  │
                          │  └────────────────┬───────────────────────┘  │
                          │                   │                          │
                          │  ┌────────────────▼───────────────────────┐  │
                          │  │          Service Layer                 │  │
                          │  │  • UrlService  (CRUD, кэш-оркестрация) │  │
                          │  │  • ClickService (счётчик, запись клика)│  │
                          │  │  • ShortCodeGenerator (nanoid)         │  │
                          │  │  • UrlValidator (Pydantic + custom)    │  │
                          │  └──────┬─────────────────────┬────────────┘  │
                          │         │                     │               │
                          │  ┌──────▼──────┐       ┌──────▼──────┐        │
                          │  │  Repository │       │ Cache Layer │        │
                          │  │  (SQLAlchemy│       │   (Redis)   │        │
                          │  │   async)    │       │             │        │
                          │  └──────┬──────┘       └──────┬──────┘        │
                          └─────────┼─────────────────────┼───────────────┘
                                    │                     │
                          ┌─────────▼──────┐    ┌────────▼──────┐
                          │  POSTGRESQL    │    │     REDIS     │
                          │  (хранилище)   │    │  (кэш+RL+    )│
                          │                │    │  (счётчики)   │
                          └────────────────┘    └───────────────┘
```

### 3.2. Описание компонентов

**NGINX (Reverse Proxy).** Точка входа. Терминирует TLS, добавляет заголовки безопасности, ограничивает размер тела запроса (1 МБ), передаёт запросы в Gunicorn. В dev-окружении может отсутствовать.

**Gunicorn + Uvicorn workers.** Менеджер процессов. Запускает 4 worker-процесса Uvicorn (класс `uvicorn.workers.UvicornWorker`). Количество workers = `2 × CPU + 1`. Каждый worker — отдельный процесс со своим connection pool к БД и Redis.

**FastAPI Application.** Основной код. Содержит middleware, роутеры, dependency injection, обработчики исключений. Все эндпоинты — `async`.

**Middleware Layer.**
- `RateLimitMiddleware` — проверяет лимиты в Redis перед передачей запроса в роутер. Возвращает 429 при превышении. Лимиты настраиваются per-endpoint.
- `CORSMiddleware` — разрешает кросс-доменные запросы (настраиваемый список origins).
- Глобальный `exception_handler` — перехватывает бизнес-исключения и возвращает стандартизированные JSON-ошибки.

**Service Layer.** Бизнес-логика. Не знает про HTTP (не использует `Request`/`Response`). Принимает DTO (Pydantic-схемы), возвращает доменные объекты. `UrlService` оркестрирует работу между Repository и Cache Layer.

**Repository Layer.** Доступ к PostgreSQL через SQLAlchemy 2.0 async. Инкапсулирует SQL-запросы. Каждый метод — атомарная операция с БД.

**Cache Layer.** Работа с Redis. Три функции:
1. Кэш перенаправлений: `GET url:{short_code}` → `original_url` (TTL 1 час).
2. Rate limiting: sorted set `rl:{ip}:{endpoint}` с sliding window.
3. Счётчик кликов: `INCR clicks:{short_code}` — атомарный инкремент, flush в БД каждые 100 кликов или по cron.

**PostgreSQL.** Постоянное хранилище. Хранит ссылки, клики, метаданные. Источник истины.

**Redis.** Эфемерное хранилище. Кэш, rate limiter, горячие счётчики. Потеря данных в Redis не критична — система деградирует до прямых запросов в БД.

### 3.3. Поток данных: перенаправление (наиболее частый путь)

```
1. Клиент → GET /abc12345
2. RateLimitMiddleware → Redis SISMEMBER (sliding window) → OK
3. RedirectEndpoint → UrlService.get_by_code("abc12345")
4. UrlService → CacheLayer.get("url:abc12345")
   4a. Cache HIT → original_url
   4b. Cache MISS → Repository.get_by_code("abc12345")
       → CacheLayer.set("url:abc12345", original_url, ttl=3600)
5. UrlService → ClickService.record_click(short_code, ip, user_agent)
   → Redis INCR clicks:abc12345 (атомарно, неблокирующе)
   → BackgroundTask: INSERT INTO clicks (...) — асинхронно
6. Endpoint → RedirectResponse(url=original_url, status_code=302)
```

---

## 4. Модель данных

### 4.1. Сущность `urls`

Таблица `urls` — основная сущность, хранит сопоставление короткого кода и оригинального URL.

| Поле | Тип | Ограничения | Описание |
|------|-----|-------------|----------|
| `id` | `BIGSERIAL` | PK, NOT NULL | Внутренний идентификатор (не возвращается в API). |
| `short_code` | `VARCHAR(10)` | UNIQUE, NOT NULL, CHECK(length >= 6) | Короткий код (nanoid, 8 символов). Используется в URL. |
| `original_url` | `VARCHAR(2048)` | NOT NULL, CHECK(length <= 2048) | Оригинальный URL. |
| `is_active` | `BOOLEAN` | NOT NULL, DEFAULT TRUE | `FALSE` после DELETE. Перенаправление возвращает 410. |
| `click_count` | `BIGINT` | NOT NULL, DEFAULT 0 | Количество кликов. Синхронизируется из Redis. |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT NOW() | Время создания. |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT NOW() | Время последнего обновления. |
| `expires_at` | `TIMESTAMPTZ` | NULLABLE | Время истечения. `NULL` = бессрочно. |
| `last_clicked_at` | `TIMESTAMPTZ` | NULLABLE | Время последнего клика. |

**Индексы:**
- `PRIMARY KEY (id)` — кластерный.
- `UNIQUE INDEX idx_urls_short_code ON urls(short_code)` — быстрый lookup по коду.
- `INDEX idx_urls_created_at ON urls(created_at DESC)` — аналитика, очистка.
- `PARTIAL INDEX idx_urls_active_code ON urls(short_code) WHERE is_active = TRUE` — только активные ссылки (ускоряет перенаправление).
- `INDEX idx_urls_expires_at ON urls(expires_at) WHERE expires_at IS NOT NULL` — поиск истёкших ссылок для очистки.

### 4.2. Сущность `clicks`

Таблица `clicks` — журнал кликов для детальной аналитики.

| Поле | Тип | Ограничения | Описание |
|------|-----|-------------|----------|
| `id` | `BIGSERIAL` | PK, NOT NULL | Идентификатор клика. |
| `url_id` | `BIGINT` | FK → urls(id) ON DELETE CASCADE, NOT NULL | Ссылка на родительскую запись. |
| `ip_address` | `VARCHAR(45)` | NOT NULL | IP-адрес клиента (IPv4/IPv6). |
| `user_agent` | `VARCHAR(512)` | NULLABLE | User-Agent клиента. |
| `referer` | `VARCHAR(2048)` | NULLABLE | Referer заголовок. |
| `clicked_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT NOW() | Время клика. |

**Индексы:**
- `PRIMARY KEY (id)`.
- `INDEX idx_clicks_url_id ON clicks(url_id)` — join со статистикой.
- `INDEX idx_clicks_clicked_at ON clicks(clicked_at DESC)` — временные ряды.
- `INDEX idx_clicks_url_clicked ON clicks(url_id, clicked_at DESC)` — составной, для топ-кликов по ссылке.

### 4.3. Партиционирование (future-proof)

Таблица `clicks` растёт линейно с нагрузкой. При достижении 10 млн строк рекомендуется партиционирование по `clicked_at` (monthly partitions). Это не реализуется в первой итерации, но модель данных к этому готова (все запросы к `clicks` фильтруются по `url_id` или `clicked_at`).

### 4.4. ER-диаграмма (текстовая)

```
┌──────────────────────┐       ┌──────────────────────┐
│        urls          │       │       clicks         │
├──────────────────────┤       ├──────────────────────┤
│ id          BIGSERIAL│◄──┐   │ id          BIGSERIAL│
│ short_code  VARCHAR  │   │   │ url_id      BIGINT   │── FK
│ original_url VARCHAR │   └───│ ip_address  VARCHAR  │
│ is_active   BOOLEAN  │       │ user_agent  VARCHAR  │
│ click_count BIGINT   │       │ referer     VARCHAR  │
│ created_at  TIMESTAMPTZ│     │ clicked_at  TIMESTAMPTZ│
│ updated_at  TIMESTAMPTZ│     └──────────────────────┘
│ expires_at  TIMESTAMPTZ│
│ last_clicked_at ...   │
└──────────────────────┘
  1                              N
  └──────────────────────────────┘
         one-to-many
```

---

## 5. API-контракты

Базовый путь: `/api/v1`. Swagger UI: `/docs`. ReDoc: `/redoc`. OpenAPI JSON: `/openapi.json`.

### 5.1. POST `/api/v1/shorten`

Создаёт короткую ссылку.

**Rate limit:** 100 запросов/минута с одного IP.

**Request:**
```http
POST /api/v1/shorten HTTP/1.1
Content-Type: application/json

{
  "url": "https://www.example.com/very/long/path?query=1&foo=bar"
}
```

| Поле | Тип | Обязательное | Валидация |
|------|-----|--------------|-----------|
| `url` | string (URL) | да | Должно быть валидным `http` или `https` URL. Макс. длина 2048. Не допускаются `localhost`, `127.0.0.1`, `0.0.0.0`, приватные диапазоны RFC 1918 (`10.x`, `172.16-31.x`, `192.168.x`). |

**Response 201 Created:**
```json
{
  "short_code": "abc12345",
  "short_url": "http://localhost:8000/abc12345",
  "original_url": "https://www.example.com/very/long/path?query=1&foo=bar",
  "created_at": "2025-01-15T10:30:00Z"
}
```

**Ошибки:**

| Код | Условие | Тело ответа |
|-----|---------|-------------|
| 400 | Невалидный URL (не http/https, приватный IP) | `{"detail": "Invalid URL: must be a public http(s) URL"}` |
| 422 | Отсутствует поле `url` или неверный тип | `{"detail": [{"loc": ["body","url"], "msg": "field required", "type": "value_error.missing"}]}` |
| 429 | Превышен rate limit | `{"detail": "Rate limit exceeded. Retry after 42 seconds."}` с заголовком `Retry-After: 42` |
| 500 | Внутренняя ошибка | `{"detail": "Internal server error"}` |

### 5.2. GET `/api/v1/{short_code}`

Перенаправляет на оригинальный URL.

**Rate limit:** 60 запросов/минута с одного IP.

**Path-параметр:**
| Параметр | Тип | Валидация |
|----------|-----|-----------|
| `short_code` | string | Длина 6–10 символов, base62 `[A-Za-z0-9]` |

**Response 302 Found:**
```http
HTTP/1.1 302 Found
Location: https://www.example.com/very/long/path?query=1&foo=bar
```
Тело ответа пустое. Браузер автоматически переходит по `Location`.

**Ошибки:**

| Код | Условие | Тело ответа |
|-----|---------|-------------|
| 404 | Короткий код не найден | `{"detail": "Short URL not found"}` |
| 410 | Ссылка удалена (is_active=FALSE) | `{"detail": "This short URL has been deactivated"}` |
| 410 | Ссылка истекла (expires_at < NOW()) | `{"detail": "This short URL has expired"}` |
| 422 | Невалидный формат short_code | `{"detail": "Invalid short code format"}` |
| 429 | Превышен rate limit | Аналогично 5.1 |

### 5.3. GET `/api/v1/stats/{short_code}`

Возвращает статистику по короткой ссылке.

**Rate limit:** 100 запросов/минута с одного IP.

**Response 200 OK:**
```json
{
  "short_code": "abc12345",
  "original_url": "https://www.example.com/very/long/path?query=1&foo=bar",
  "is_active": true,
  "click_count": 1547,
  "created_at": "2025-01-15T10:30:00Z",
  "last_clicked_at": "2025-01-20T14:22:11Z",
  "expires_at": null
}
```

**Ошибки:**

| Код | Условие | Тело ответа |
|-----|---------|-------------|
| 404 | Короткий код не найден | `{"detail": "Short URL not found"}` |
| 422 | Невалидный формат | `{"detail": "Invalid short code format"}` |
| 429 | Rate limit | Аналогично 5.1 |

### 5.4. DELETE `/api/v1/{short_code}`

Деактивирует короткую ссылку (soft delete). Записи в `clicks` сохраняются.

**Rate limit:** 30 запросов/минута с одного IP.

**Response 204 No Content:** Тело ответа пустое.

**Ошибки:**

| Код | Условие | Тело ответа |
|-----|---------|-------------|
| 404 | Короткий код не найден | `{"detail": "Short URL not found"}` |
| 422 | Невалидный формат | `{"detail": "Invalid short code format"}` |
| 429 | Rate limit | Аналогично 5.1 |

### 5.5. Единый формат ошибок

Все ошибки возвращают JSON:
```json
{
  "detail": "Человекочитаемое сообщение",
  "error_code": "SHORT_URL_NOT_FOUND"
}
```
Поле `error_code` — машинный код ошибки для клиентской логики. Список кодов: `INVALID_URL`, `SHORT_URL_NOT_FOUND`, `URL_DEACTIVATED`, `URL_EXPIRED`, `RATE_LIMIT_EXCEEDED`, `INVALID_SHORT_CODE`, `INTERNAL_ERROR`.

### 5.6. Health-эндпоинты (инфраструктурные)

| Эндпоинт | Метод | Описание | Response |
|----------|-------|----------|----------|
| `/health` | GET | Liveness probe | `200 {"status": "alive"}` |
| `/ready` | GET | Readiness probe (проверяет БД + Redis) | `200 {"status": "ready"}` или `503 {"status": "not ready", "details": {...}}` |

---

## 6. Нефункциональные требования

### 6.1. Производительность

| Метрика | Целевое значение | Метод достижения |
|---------|------------------|------------------|
| Latency GET /{code} (p99) | < 20 мс | Redis-кэш (hit ratio > 90%), partial index на активные ссылки |
| Latency POST /shorten (p99) | < 50 мс | Минимальная логика, один INSERT |
| Throughput | 5000 RPS на redirect | 4 Uvicorn workers, async I/O, connection pooling |
| Cache hit ratio | > 90% | TTL 1 час, LRU-подобное поведение Redis |

**Connection pool настройки:**
- PostgreSQL: `pool_size=20`, `max_overflow=10` на worker. Итого 4 × 30 = 120 соединений. `max_connections` в PostgreSQL = 200.
- Redis: connection pool `max_connections=50` на worker. Используется `redis.asyncio`.

### 6.2. Масштабирование

**Вертикальное:** увеличение CPU/RAM на узле приложения, увеличение workers в Gunicorn.

**Горизонтальное (stateless app):** FastAPI-приложение не хранит состояние — все state в PostgreSQL и Redis. Добавление реплик приложения за балансировщиком тривиально. Сессии не используются.

**PostgreSQL:** read-replica для `GET /stats` (аналитика) при росте нагрузки. Writes остаются на primary.

**Redis:** Redis Cluster при превышении 100K RPS. Кэш шардируется по `short_code`.

### 6.3. Безопасность

| Требование | Реализация |
|------------|------------|
| Валидация URL | Pydantic `HttpUrl` + кастомный валидатор: запрет `localhost`, приватных IP (RFC 1918), `0.0.0.0`, `::1`. Защита от SSRF и open-redirect на внутренние ресурсы. |
| SQL-инъекции | SQLAlchemy parameterized queries. Никаких raw SQL со строковой интерполяцией. |
| Rate limiting | Sliding window в Redis. Per-IP. Разные лимиты для разных эндпоинтов. Защита от brute-force перебора коротких кодов. |
| HTTPS | NGINX терминирует TLS. Редиректы используют оригинальный URL как есть (клиент ответственен за HTTPS-цель). |
| Заголовки безопасности | `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `X-XSS-Protection: 1; mode=block`, `Strict-Transport-Security` (через NGINX). |
| Секреты | Все секреты (пароли БД, Redis) — в переменных окружения или `.env` (не коммитится). `.env.example` — шаблон. |
| Логирование | Логи не содержат полные URL (возможны чувствительные данные в query-параметрах). Логируется только `short_code` и метаданные. |
| CORS | Настраиваемый список allowed origins через `CORS_ORIGINS` env var. По умолчанию `*` (dev), в production — явный список. |
| Размер запроса | NGINX `client_max_body_size 1m`. FastAPI `Request` body limit через middleware. |

### 6.4. Надёжность

| Требование | Реализация |
|------------|------------|
| Graceful shutdown | FastAPI `lifespan` — закрывает connection pools к БД и Redis при остановке. Gunicorn `--graceful-timeout 30`. |
| Circuit breaker для Redis | Если Redis недоступен, приложение продолжает работать (cache miss → прямой запрос в БД). Rate limiter в fallback-режиме пропускает запросы (fail-open). |
| Retry на коллизию short_code | При INSERT с дубликатом `short_code` (вероятность ~0 с 8-символьным nanoid) — повторная генерация (до 3 попыток). |
| Идемпотентность DELETE | Повторный DELETE уже деактивированной ссылки возвращает 204 (не 404). |
| Резервное копирование | PostgreSQL: pg_dump nightly (через cron в docker-compose или внешний job). Redis: не бэкапится (эфемерный). |

### 6.5. Наблюдаемость (Observability)

| Аспект | Реализация |
|--------|------------|
| Логирование | Python `logging`, JSON-формат (structlog или `python-json-logger`). Уровень настраивается через `LOG_LEVEL` env. |
| Структурированные логи | Каждый запрос логируется с `request_id` (генерируется в middleware), `method`, `path`, `status_code`, `latency_ms`, `ip`. |
| Метрики | (Future) Prometheus-эндпоинт `/metrics` с счётчиками запросов, гистограммами latency. В первой итерации — логирование. |
| Health checks | `/health` (liveness) и `/ready` (readiness) для Kubernetes/Docker. |

### 6.6. Согласованность данных (Cache-Aside)

Стратегия кэширования — **cache-aside** с инвалидацией при DELETE:

1. **Read:** проверяем Redis → если miss, читаем PostgreSQL → записываем в Redis (TTL 1 час).
2. **Delete:** обновляем `is_active=FALSE` в PostgreSQL → удаляем ключ из Redis (`DEL url:{short_code}`).
3. **Click count:** `INCR` в Redis (атомарно). Фоновая задача (BackgroundTasks) каждые 100 кликов или раз в минуту flush'ит значение в PostgreSQL (`UPDATE urls SET click_count = $1 WHERE short_code = $2`).

Возможна кратковременная рассинхронизация `click_count` (до 1 минуты) между Redis и PostgreSQL — это допустимо для статистики. `GET /stats` возвращает значение из Redis (если ключ существует) или из БД.

---

## 7. Структура проекта

```
url-shortener/
│
├── app/                                    # Основной код приложения
│   ├── __init__.py
│   ├── main.py                             # Точка входа: создание FastAPI app, lifespan, middleware, роутеры
│   │
│   ├── core/                               # Сквозная инфраструктура
│   │   ├── __init__.py
│   │   ├── config.py                       # Pydantic Settings: env vars, типизация, дефолты
│   │   ├── logging.py                      # Настройка JSON-логирования, request_id
│   │   └── exceptions.py                   # Кастомные исключения: UrlNotFoundError, UrlDeactivatedError, RateLimitExceededError
│   │
│   ├── api/                                # HTTP-слой
│   │   ├── __init__.py
│   │   ├── deps.py                         # Dependency injection: get_db_session, get_redis, get_url_service
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py                   # Объединение эндпоинтов в APIRouter с prefix /api/v1
│   │       └── endpoints/
│   │           ├── __init__.py
│   │           ├── shorten.py              # POST /shorten
│   │           ├── redirect.py             # GET /{short_code}
│   │           ├── stats.py                # GET /stats/{short_code}
│   │           └── delete.py               # DELETE /{short_code}
│   │
│   ├── schemas/                            # Pydantic-модели (DTO для запросов/ответов)
│   │   ├── __init__.py
│   │   ├── url.py                          # ShortenRequest, ShortenResponse
│   │   ├── stats.py                        # StatsResponse
│   │   └── common.py                       # ErrorResponse, HealthResponse
│   │
│   ├── models/                             # SQLAlchemy ORM-модели
│   │   ├── __init__.py
│   │   ├── base.py                         # DeclarativeBase, общие mixin (TimestampMixin)
│   │   ├── url.py                          # Url model
│   │   └── click.py                        # Click model
│   │
│   ├── repositories/                       # Слой доступа к данным (PostgreSQL)
│   │   ├── __init__.py
│   │   ├── url_repository.py               # get_by_code, create, deactivate, increment_click_count
│   │   └── click_repository.py             # create, count_by_url_id
│   │
│   ├── services/                           # Бизнес-логика
│   │   ├── __init__.py
│   │   ├── url_service.py                  # create_short_url, get_url_by_code, deactivate_url, get_stats
│   │   ├── click_service.py                # record_click (Redis INCR + BackgroundTask INSERT)
│   │   └── short_code_generator.py         # generate_short_code() → nanoid(8), retry on collision
│   │
│   ├── cache/                              # Слой работы с Redis
│   │   ├── __init__.py
│   │   ├── redis_client.py                 # Создание async Redis connection pool
│   │   └── url_cache.py                    # get_url, set_url, delete_url, get_click_count, incr_click_count
│   │
│   ├── middleware/                         # ASGI middleware
│   │   ├── __init__.py
│   │   ├── rate_limit.py                   # RateLimitMiddleware: sliding window via Redis ZSET
│   │   └── request_id.py                   # RequestIdMiddleware: генерация/проброс X-Request-ID
│   │
│   └── utils/                              # Утилиты
│       ├── __init__.py
│       └── url_validator.py                # validate_url(): проверка http/https, запрет приватных IP
│
├── alembic/                                # Миграции БД
│   ├── env.py                              # Конфигурация Alembic (async engine)
│   ├── script.py.mako                      # Шаблон миграции
│   └── versions/
│       └── 001_initial.py                  # Создание таблиц urls, clicks, индексов
│
├── tests/                                  # Тесты (pytest)
│   ├── __init__.py
│   ├── conftest.py                         # Фикстуры: test client, test DB, test Redis, cleanup
│   ├── unit/                               # Unit-тесты (без внешних зависимостей)
│   │   ├── __init__.py
│   │   ├── test_short_code_generator.py    # Уникальность, длина, base62
│   │   ├── test_url_validator.py           # Валидные/невалидные URL, приватные IP
│   │   └── test_schemas.py                 # Pydantic-валидация запросов/ответов
│   ├── integration/                        # Integration-тесты (с БД и Redis через testcontainers)
│   │   ├── __init__.py
│   │   ├── test_shorten.py                 # POST /shorten: успех, невалидный URL, приватный IP, дубликат
│   │   ├── test_redirect.py                # GET /{code}: успех, 404, 410 (deactivated), 410 (expired), кэш
│   │   ├── test_stats.py                   # GET /stats/{code}: успех, 404, click_count
│   │   ├── test_delete.py                  # DELETE /{code}: успех, 404, идемпотентность
│   │   └── test_rate_limit.py              # Превышение лимита → 429, Retry-After
│   └── e2e/                                # Сквозные сценарии
│       ├── __init__.py
│       └── test_full_lifecycle.py          # Создать → перенаправить → статистика → удалить → 410
│
├── alembic.ini                             # Конфигурация Alembic
├── pyproject.toml                          # Зависимости, ruff, mypy, pytest config
├── requirements.txt                        # Production-зависимости (pin versions)
├── requirements-dev.txt                    # Dev-зависимости (pytest, ruff, mypy)
├── Dockerfile                              # Multi-stage build: python:3.11-slim
├── docker-compose.yml                      # app + postgres + redis
├── docker-compose.test.yml                 # app + postgres + redis для тестов
├── .env.example                            # Шаблон переменных окружения
├── .gitignore
├── Makefile                                # Команды: make test, make lint, make migrate, make run
└── README.md                               # Инструкция по запуску
```

### 7.1. Ключевые переменные окружения (`.env.example`)

```env
# Application
APP_NAME=url-shortener
APP_ENV=development                    # development | staging | production
APP_HOST=0.0.0.0
APP_PORT=8000
APP_WORKERS=4
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/url_shortener
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10

# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_MAX_CONNECTIONS=50

# URL Shortener
SHORT_CODE_LENGTH=8
BASE_URL=http://localhost:8000          # Базовый URL для генерации short_url
URL_CACHE_TTL=3600                      # Секунды (1 час)

# Rate Limiting
RATE_LIMIT_SHORTEN=100                  # запросов в минуту
RATE_LIMIT_REDIRECT=60
RATE_LIMIT_STATS=100
RATE_LIMIT_DELETE=30
RATE_LIMIT_WINDOW=60                    # секунды

# CORS
CORS_ORIGINS=*                          # В production: https://example.com,https://app.example.com
```

### 7.2. Команды Makefile

```makefile
run:        docker-compose up --build
test:       pytest tests/ -v --cov=app --cov-report=term-missing
lint:       ruff check app/ tests/ && mypy app/
migrate:    alembic upgrade head
migrate-new: alembic revision --autogenerate -m "$(MSG)"
docker-test: docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from app
```

---

## 8. Приложения

### 8.1. Алгоритм генерации short_code

```python
# app/services/short_code_generator.py
from nanoid import generate

ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"  # base62
LENGTH = 8  # 62^8 ≈ 218 триллионов комбинаций

def generate_short_code() -> str:
    return generate(alphabet=ALPHABET, size=LENGTH)
```

В `UrlService.create_short_url` реализован retry: генерация → INSERT → при `IntegrityError` (duplicate) — повторная генерация (до 3 попыток). После 3 неудач — `500 Internal Error` (практически невозможно при 8 символах).

### 8.2. Алгоритм rate limiting (sliding window)

```python
# Логика RateLimitMiddleware
# Ключ: rl:{ip}:{endpoint}
# Структура: Redis Sorted Set, score = timestamp запроса, member = unique request id

async def check_rate_limit(redis, key: str, limit: int, window: int) -> tuple[bool, int]:
    now = time.time()
    window_start = now - window
    pipe = redis.pipeline()
    pipe.zremrangebyscore(key, 0, window_start)   # Удалить старые записи
    pipe.zadd(key, {str(now): now})                # Добавить текущий запрос
    pipe.zcard(key)                                 # Подсчитать количество
    pipe.expire(key, window)                        # TTL для автоочистки
    _, _, count, _ = await pipe.execute()
    if count > limit:
        retry_after = int(window - (now - window_start))
        return False, retry_after
    return True, 0
```

### 8.3. Стратегия тестирования

| Уровень | Что тестируется | Инструменты | Изоляция |
|---------|----------------|-------------|----------|
| Unit | `short_code_generator`, `url_validator`, Pydantic-схемы | pytest | Без внешних зависимостей |
| Integration | Эндпоинты + БД + Redis | pytest, httpx (ASGITransport), testcontainers (PostgreSQL, Redis) | Отдельные контейнеры на каждый test session |
| E2E | Полный lifecycle: создать → клик → статистика → удалить → 410 | pytest, httpx | Те же контейнеры, что integration |

**Покрытие:** минимум 85% строк кода (`--cov-fail-under=85` в pyproject.toml).

### 8.4. Dockerfile (multi-stage)

```dockerfile
FROM python:3.11-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.11-slim AS runtime
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .
ENV PATH=/root/.local/bin:$PATH
EXPOSE 8000
CMD ["gunicorn", "app.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000"]
```

---

**Конец документа.** Этот документ — единственный источник правды для команды. Любые отклонения от описанной архитектуры требуют обновления данного документа и согласования с Архитектором.