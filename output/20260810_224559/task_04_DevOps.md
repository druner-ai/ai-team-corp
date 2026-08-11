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

```markdown
## url-shortener/Dockerfile

```dockerfile
# Stage 1: Build dependencies
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies if needed (none for this project)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime image
FROM python:3.11-slim AS runtime

# Create non-root user
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

WORKDIR /app

# Copy only necessary files from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY src/ src/
COPY alembic/ alembic/
COPY alembic.ini pyproject.toml ./

# Ensure proper permissions
RUN chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

# Healthcheck using Python's built-in urllib
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## url-shortener/docker-compose.yml

```yaml
version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    env_file:
      - .env
    environment:
      - POSTGRES_HOST=db
      - REDIS_HOST=redis
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]
      interval: 30s
      timeout: 10s
      start_period: 10s
      retries: 3
    restart: unless-stopped

  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: url_shortener
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d url_shortener"]
      interval: 10s
      timeout: 5s
      start_period: 10s
      retries: 5
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redisdata:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      start_period: 5s
      retries: 5
    restart: unless-stopped

volumes:
  pgdata:
  redisdata:
```

---

## url-shortener/.env.example

```env
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

## url-shortener/README.md

```markdown
# URL Shortener Microservice

Сервис сокращения длинных URL-адресов с отслеживанием статистики переходов.

## Быстрый старт

1. Скопируйте `.env.example` в `.env` и при необходимости измените переменные:
   ```bash
   cp .env.example .env
   ```

2. Запустите все сервисы одной командой:
   ```bash
   docker compose up --build
   ```

3. Сервис будет доступен по адресу `http://localhost:8000`.

## Переменные окружения

| Переменная | Описание | Значение по умолчанию |
|------------|----------|-----------------------|
| `APP_ENV` | Окружение (development/production) | `development` |
| `APP_HOST` | Хост приложения | `0.0.0.0` |
| `APP_PORT` | Порт приложения | `8000` |
| `APP_BASE_URL` | Базовый URL для генерации коротких ссылок | `http://localhost:8000` |
| `POSTGRES_HOST` | Хост PostgreSQL | `localhost` |
| `POSTGRES_PORT` | Порт PostgreSQL | `5432` |
| `POSTGRES_DB` | Имя базы данных | `url_shortener` |
| `POSTGRES_USER` | Пользователь БД | `postgres` |
| `POSTGRES_PASSWORD` | Пароль БД | `postgres` |
| `REDIS_HOST` | Хост Redis | `localhost` |
| `REDIS_PORT` | Порт Redis | `6379` |
| `REDIS_DB` | Номер БД Redis | `0` |
| `RATE_LIMIT_REQUESTS` | Максимум запросов в минуту с одного IP | `30` |
| `RATE_LIMIT_WINDOW` | Окно rate limiting (сек) | `60` |
| `CACHE_TTL_SECONDS` | Время жизни кэша в Redis (сек) | `86400` |
| `CORS_ORIGINS` | Разрешённые CORS-источники (через запятую или `*`) | `*` |

## API Endpoints

| Метод | Путь | Описание |
|-------|------|----------|
| `POST` | `/shorten` | Создать короткую ссылку |
| `GET` | `/{short_id}` | Редирект на оригинальный URL |
| `GET` | `/stats/{short_id}` | Статистика переходов |
| `DELETE` | `/{short_id}` | Удалить ссылку (soft delete) |
| `GET` | `/health` | Health check |

## Healthcheck

Каждый сервис имеет встроенный healthcheck:

- **app**: `GET /health` — проверяет подключение к PostgreSQL и Redis.
- **db**: `pg_isready` — проверяет готовность PostgreSQL.
- **redis**: `redis-cli ping` — проверяет доступность Redis.

## Структура проекта

```
url-shortener/
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── pyproject.toml
├── alembic.ini
├── README.md
├── alembic/
├── src/
│   ├── main.py
│   ├── config.py
│   ├── api/
│   ├── core/
│   ├── middleware/
│   ├── models/
│   ├── repositories/
│   ├── schemas/
│   ├── services/
│   └── utils/
└── tests/
```

## Примечания

- Для production измените `APP_ENV=production` и ограничьте `CORS_ORIGINS`.
- Пароли и секреты храните только в `.env`, не коммитьте этот файл.
- Для миграций БД используйте Alembic: `alembic upgrade head`.
```