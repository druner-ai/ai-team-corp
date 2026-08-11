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
### url-shortener/Dockerfile
```dockerfile
# Multi-stage build for TODO REST API
FROM python:3.11-slim AS builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim AS final

# Install curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home appuser

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY app/ ./app/
COPY alembic.ini .
COPY alembic/ ./alembic/

# Create data directory and set ownership
RUN mkdir -p /app/data && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

EXPOSE 8000

# Healthcheck using the /health endpoint
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### url-shortener/docker-compose.yml
```yaml
version: "3.8"

services:
  api:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
    environment:
      - DATABASE_URL=sqlite+aiosqlite:///./data/tasks.db
      - LOG_LEVEL=INFO
      - APP_ENV=production
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 3s
      retries: 3
      start_period: 5s
```

### url-shortener/.env.example
```ini
DATABASE_URL=sqlite+aiosqlite:///./data/tasks.db
LOG_LEVEL=INFO
APP_ENV=development
```

### url-shortener/README.md
```markdown
# TODO REST API

Минималистичный REST API для управления списком задач (TODO).

## Быстрый старт с Docker

1. Убедитесь, что установлены Docker и Docker Compose.
2. Скопируйте `.env.example` в `.env` (при необходимости измените переменные):
   ```bash
   cp .env.example .env
   ```
3. Запустите приложение:
   ```bash
   docker compose up --build
   ```
4. API будет доступно по адресу [http://localhost:8000](http://localhost:8000).
5. Документация Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs).

## Структура проекта

- `app/` – исходный код FastAPI-приложения
- `alembic/` – миграции базы данных
- `data/` – директория для файла SQLite (создаётся автоматически)
- `Dockerfile` – multi-stage сборка образа
- `docker-compose.yml` – описание сервисов
- `.env.example` – пример переменных окружения

## Переменные окружения

| Переменная | По умолчанию | Описание |
|------------|-------------|----------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./data/tasks.db` | Строка подключения к БД |
| `LOG_LEVEL` | `INFO` | Уровень логирования |
| `APP_ENV` | `development` | Окружение |

## Healthcheck

Приложение проверяет свою работоспособность через эндпоинт `/health`. Docker Compose и Dockerfile содержат настройки автоматической проверки состояния.
```