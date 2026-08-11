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

```url-shortener/Dockerfile
```dockerfile
FROM python:3.11-slim AS builder

WORKDIR /app

# Install system dependencies for building
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Final stage
FROM python:3.11-slim

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /root/.local /home/appuser/.local

# Copy application code
COPY --chown=appuser:appuser . .

# Copy entrypoint script
COPY --chown=appuser:appuser docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Set environment variables
ENV PATH=/home/appuser/.local/bin:$PATH \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1

EXPOSE 8000

USER appuser

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```url-shortener/docker-compose.yml
```yaml
version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:postgrespassword@db:5432/urlshortener
      - REDIS_URL=redis://redis:6379/0
      - BASE_URL=http://localhost:8000
      - RATE_LIMIT_PER_MINUTE=100
      - CACHE_TTL_SECONDS=3600
      - LOG_LEVEL=INFO
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    networks:
      - url-shortener-network

  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgrespassword
      POSTGRES_DB: urlshortener
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d urlshortener"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s
    restart: unless-stopped
    networks:
      - url-shortener-network

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redisdata:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5
      start_period: 5s
    restart: unless-stopped
    networks:
      - url-shortener-network

volumes:
  pgdata:
    driver: local
  redisdata:
    driver: local

networks:
  url-shortener-network:
    driver: bridge
```

```url-shortener/.env.example
# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgrespassword@localhost:5432/urlshortener

# Redis
REDIS_URL=redis://localhost:6379/0

# Base URL (used for generating full short links)
BASE_URL=http://localhost:8000

# Rate limit: maximum requests per IP per minute
RATE_LIMIT_PER_MINUTE=100

# Cache TTL for redirect cache (seconds)
CACHE_TTL_SECONDS=3600

# Log level (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO
```

```url-shortener/README.md
# URL Shortener Microservice

A production-ready URL shortener service built with FastAPI, PostgreSQL, and Redis.

## Quick Start

### Prerequisites
- Docker and Docker Compose installed
- Git (optional)

### Running the Service

1. Clone the repository:
```bash
git clone <repository-url>
cd url-shortener
```

2. Create environment file:
```bash
cp .env.example .env
```

3. Start all services:
```bash
docker compose up -d
```

4. Verify the service is running:
```bash
curl http://localhost:8000/health
```

5. Access the API documentation:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Endpoints

### Create Short URL
```bash
curl -X POST http://localhost:8000/shorten \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/very/long/url"}'
```

### Redirect to Original URL
```bash
curl -L http://localhost:8000/{short_id}
```

### Get URL Statistics
```bash
curl http://localhost:8000/stats/{short_id}
```

### Delete Short URL
```bash
curl -X DELETE http://localhost:8000/{short_id}
```

## Architecture

- **FastAPI** - Web framework with async support
- **PostgreSQL 15** - Primary data store
- **Redis 7** - Caching and rate limiting
- **SQLAlchemy 2.0** - Async ORM
- **Alembic** - Database migrations

## Configuration

All configuration is done via environment variables (see `.env.example`):

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://postgres:postgrespassword@db:5432/urlshortener` |
| `REDIS_URL` | Redis connection string | `redis://redis:6379/0` |
| `BASE_URL` | Base URL for short links | `http://localhost:8000` |
| `RATE_LIMIT_PER_MINUTE` | Max requests per IP per minute | `100` |
| `CACHE_TTL_SECONDS` | Cache TTL for redirects | `3600` |
| `LOG_LEVEL` | Logging level | `INFO` |

## Development

### Running Tests
```bash
docker compose exec app pytest -v
```

### Database Migrations
```bash
# Create new migration
docker compose exec app alembic revision --autogenerate -m "description"

# Apply migrations
docker compose exec app alembic upgrade head
```

## Health Checks

All services have health checks configured:
- **App**: HTTP health endpoint at `/health`
- **PostgreSQL**: `pg_isready` command
- **Redis**: `redis-cli ping` command

## Stopping the Service

```bash
docker compose down
```

To remove volumes as well:
```bash
docker compose down -v
```
```