# DevOps

## Задача

        Упакуй готовое решение в Docker.

        ЧТО СДЕЛАТЬ:
        1. **Dockerfile**: multi-stage build, используй путь `url-shortener/Dockerfile`
        2. **docker-compose.yml**: все сервисы, путь `url-shortener/docker-compose.yml`
        3. **.env.example**: все переменные, путь `url-shortener/.env.example`
        4. **README.md**: как запустить, путь `url-shortener/README.md`
        5. **Healthcheck**: для каждого сервиса

        ПРАВИЛА:
        - Не используй latest-теги — фиксируй версии
        - Не копируй .env в образ
        - Используй не-root пользователя в контейнере
        - Пути файлов ВСЕГДА начинай с `url-shortener/`, не с `path/to/`
        

## Результат

### url-shortener/Dockerfile

```dockerfile
# syntax=docker/dockerfile:1.7

# ---------- Stage 1: Build dependencies ----------
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /wheels -r requirements.txt

# ---------- Stage 2: Runtime ----------
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_HOME=/app \
    APP_USER=appuser \
    APP_UID=10001

# Create non-root user
RUN groupadd --gid ${APP_UID} ${APP_USER} \
    && useradd --uid ${APP_UID} --gid ${APP_USER} --shell /bin/bash --create-home ${APP_USER}

WORKDIR ${APP_HOME}

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy wheels from builder stage
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/*

# Copy application code
COPY --chown=${APP_USER}:${APP_USER} . .

# Create necessary directories
RUN mkdir -p /app/alembic/versions \
    && chown -R ${APP_USER}:${APP_USER} /app

# Switch to non-root user
USER ${APP_USER}

# Expose port
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

---

### url-shortener/docker-compose.yml

```yaml
version: "3.8"

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: url-shortener-app
    ports:
      - "${APP_PORT:-8000}:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER:-shortener}:${POSTGRES_PASSWORD:-shortener_pass}@db:5432/${POSTGRES_DB:-shortener_db}
      - REDIS_URL=redis://redis:6379/0
      - BASE_URL=${BASE_URL:-http://localhost:8000}
      - SHORT_CODE_LENGTH=${SHORT_CODE_LENGTH:-6}
      - CACHE_TTL_SECONDS=${CACHE_TTL_SECONDS:-86400}
      - RATE_LIMIT_SHORTEN=${RATE_LIMIT_SHORTEN:-30/minute}
      - RATE_LIMIT_DEFAULT=${RATE_LIMIT_DEFAULT:-100/minute}
      - BLOCK_PRIVATE_IPS=${BLOCK_PRIVATE_IPS:-true}
      - ALLOWED_ORIGINS=${ALLOWED_ORIGINS:-}
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped
    networks:
      - url-shortener-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s

  db:
    image: postgres:15-alpine
    container_name: url-shortener-db
    environment:
      - POSTGRES_USER=${POSTGRES_USER:-shortener}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-shortener_pass}
      - POSTGRES_DB=${POSTGRES_DB:-shortener_db}
    ports:
      - "${POSTGRES_PORT:-5432}:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped
    networks:
      - url-shortener-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-shortener} -d ${POSTGRES_DB:-shortener_db}"]
      interval: 5s
      timeout: 5s
      retries: 5
      start_period: 5s

  redis:
    image: redis:7-alpine
    container_name: url-shortener-redis
    command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru
    ports:
      - "${REDIS_PORT:-6379}:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped
    networks:
      - url-shortener-network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5
      start_period: 5s

  migrate:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: url-shortener-migrate
    command: alembic upgrade head
    environment:
      - DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER:-shortener}:${POSTGRES_PASSWORD:-shortener_pass}@db:5432/${POSTGRES_DB:-shortener_db}
    depends_on:
      db:
        condition: service_healthy
    restart: "no"
    networks:
      - url-shortener-network

volumes:
  postgres_data:
    name: url-shortener-postgres-data
  redis_data:
    name: url-shortener-redis-data

networks:
  url-shortener-network:
    name: url-shortener-network
    driver: bridge
```

---

### url-shortener/.env.example

```env
# ============================================
# URL Shortener - Environment Configuration
# ============================================

# --- Application ---
APP_PORT=8000
BASE_URL=http://localhost:8000
LOG_LEVEL=INFO

# --- Database ---
POSTGRES_USER=shortener
POSTGRES_PASSWORD=shortener_pass
POSTGRES_DB=shortener_db
POSTGRES_PORT=5432

# --- Redis ---
REDIS_PORT=6379

# --- Application Settings ---
SHORT_CODE_LENGTH=6
CACHE_TTL_SECONDS=86400

# --- Rate Limiting ---
RATE_LIMIT_SHORTEN=30/minute
RATE_LIMIT_DEFAULT=100/minute

# --- Security ---
BLOCK_PRIVATE_IPS=true
ALLOWED_ORIGINS=

# --- Docker Compose Specific ---
# These are used by docker-compose.yml for service configuration
# DATABASE_URL and REDIS_URL are constructed automatically in docker-compose.yml
# Do not override them here unless you know what you're doing
```

---

### url-shortener/README.md

```markdown
# URL Shortener Microservice

Высокопроизводительный микросервис для сокращения URL-адресов.

## Возможности

- Сокращение длинных URL до коротких кодов (6 символов, base62)
- Редирект по коротким ссылкам (307 Temporary Redirect)
- Статистика переходов
- Мягкое удаление ссылок (soft delete)
- Кэширование в Redis для быстрых редиректов
- Rate limiting для защиты от злоупотреблений
- SSRF-защита при валидации URL
- Полностью асинхронная архитектура (FastAPI + asyncpg + aioredis)
- Автоматическая синхронизация счётчиков из Redis в PostgreSQL

## Технологический стек

- **Python 3.11+**
- **FastAPI** — веб-фреймворк
- **SQLAlchemy 2.0 (async)** — ORM
- **PostgreSQL 15** — основное хранилище
- **Redis 7** — кэш и счётчики
- **Alembic** — миграции БД
- **slowapi** — rate limiting
- **Docker** — контейнеризация

## Быстрый старт

### Предварительные требования

- Docker 20.10+ и Docker Compose 2.0+
- Python 3.11+ (для локальной разработки)

### Запуск через Docker Compose (рекомендуемый способ)

```bash
# 1. Клонировать репозиторий
git clone <repo-url>
cd url-shortener

# 2. Скопировать .env.example в .env и настроить переменные
cp .env.example .env

# 3. Запустить все сервисы одной командой
docker compose up -d

# 4. Проверить статус сервисов
docker compose ps

# 5. Применить миграции (выполняется автоматически сервисом migrate)
#    Но можно выполнить вручную:
docker compose run --rm migrate

# 6. Проверить здоровье сервиса
curl http://localhost:8000/health
```

Сервис будет доступен по адресу `http://localhost:8000`.

Swagger документация: `http://localhost:8000/docs`

### Остановка сервисов

```bash
# Остановить все сервисы
docker compose down

# Остановить и удалить volumes (данные будут потеряны!)
docker compose down -v
```

### Просмотр логов

```bash
# Логи всех сервисов
docker compose logs -f

# Логи конкретного сервиса
docker compose logs -f app
docker compose logs -f db
docker compose logs -f redis
```

### Локальная разработка (без Docker)

```bash
# 1. Создать виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# 2. Установить зависимости
pip install -r requirements.txt

# 3. Запустить PostgreSQL и Redis (через Docker)
docker compose up -d db redis

# 4. Настроить переменные окружения
export DATABASE_URL="postgresql+asyncpg://shortener:shortener_pass@localhost:5432/shortener_db"
export REDIS_URL="redis://localhost:6379/0"
export BASE_URL="http://localhost:8000"

# 5. Применить миграции
alembic upgrade head

# 6. Запустить сервер
uvicorn app.main:app --reload --port 8000
```

### Запуск тестов

```bash
# Все тесты с покрытием
pytest --cov=app --cov-report=term-missing

# Только unit-тесты
pytest tests/unit/

# Только интеграционные тесты
pytest tests/integration/
```

## API Endpoints

### POST /shorten
Создать короткую ссылку.

```bash
curl -X POST http://localhost:8000/shorten \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/very/long/path"}'
```

**Ответ 201 Created:**
```json
{
  "short_code": "aB3x9Q",
  "short_url": "http://localhost:8000/aB3x9Q",
  "original_url": "https://example.com/very/long/path"
}
```

### GET /{short_code}
Перейти по короткой ссылке (редирект 307).

```bash
curl -L http://localhost:8000/aB3x9Q
```

### GET /stats/{short_code}
Получить статистику переходов.

```bash
curl http://localhost:8000/stats/aB3x9Q
```

**Ответ 200 OK:**
```json
{
  "short_code": "aB3x9Q",
  "original_url": "https://example.com/very/long/path",
  "clicks": 42,
  "created_at": "2025-01-15T10:30:00Z"
}
```

### DELETE /{short_code}
Удалить короткую ссылку (soft delete).

```bash
curl -X DELETE http://localhost:8000/aB3x9Q
```

### GET /health
Проверка здоровья сервиса.

```bash
curl http://localhost:8000/health
```

**Ответ 200 OK:**
```json
{
  "status": "healthy",
  "checks": {
    "database": "healthy",
    "redis": "healthy"
  }
}
```

## Переменные окружения

| Переменная | Описание | По умолчанию |
|-----------|----------|-------------|
| `DATABASE_URL` | DSN для PostgreSQL | `postgresql+asyncpg://...` |
| `REDIS_URL` | DSN для Redis | `redis://localhost:6379/0` |
| `SHORT_CODE_LENGTH` | Длина короткого кода | `6` |
| `CACHE_TTL_SECONDS` | TTL кэша в секундах | `86400` |
| `BASE_URL` | Базовый URL сервиса | `http://localhost:8000` |
| `RATE_LIMIT_SHORTEN` | Лимит для POST /shorten | `30/minute` |
| `RATE_LIMIT_DEFAULT` | Лимит для остальных | `100/minute` |
| `BLOCK_PRIVATE_IPS` | Блокировка SSRF | `true` |
| `ALLOWED_ORIGINS` | CORS origins (через запятую) | `""` |
| `LOG_LEVEL` | Уровень логирования | `INFO` |

## Архитектура

```
Client → FastAPI → Service Layer → Repository (PostgreSQL)
                    ↓
                 Cache Manager (Redis)
```

- **API Layer**: Валидация запросов, rate limiting
- **Service Layer**: Бизнес-логика
- **Repository Layer**: Доступ к данным
- **Cache Manager**: Кэширование и счётчики

## Структура проекта

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
│   ├── main.py
│   ├── config.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py
│   │       ├── shorten.py
│   │       ├── redirect.py
│   │       ├── stats.py
│   │       └── delete.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── security.py
│   │   ├── rate_limiter.py
│   │   └── exceptions.py
│   ├── db/
│   │   ├── __init__.py
│   │   ├── session.py
│   │   └── redis_client.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── url.py
│   ├── repositories/
│   │   ├── __init__.py
│   │   └── url_repository.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── shorten.py
│   │   └── stats.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── url_service.py
│   │   ├── cache_service.py
│   │   └── code_generator.py
│   └── utils/
│       ├── __init__.py
│       └── base62.py
└── tests/
    ├── __init__.py
    ├── conftest.py
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

## Лицензия

MIT
```