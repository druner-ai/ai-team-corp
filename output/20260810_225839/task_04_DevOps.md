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
# url-shortener/Dockerfile
```dockerfile
# Multi-stage build
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Second stage: runtime
FROM python:3.12-slim AS runtime

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

# Copy only installed packages from builder
COPY --from=builder /root/.local /home/appuser/.local

# Copy application code
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Set path to include local binaries
ENV PATH=/home/appuser/.local/bin:$PATH

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

# url-shortener/docker-compose.yml
```yaml
version: '3.9'

services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: urlshortener
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s
    restart: unless-stopped
    networks:
      - app-network

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s
    restart: unless-stopped
    networks:
      - app-network

  app:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    volumes:
      - ./app:/app/app
    env_file:
      - .env
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    restart: unless-stopped
    networks:
      - app-network

volumes:
  pgdata:
  redis-data:

networks:
  app-network:
    driver: bridge
```

# url-shortener/.env.example
```bash
# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/urlshortener

# Redis
REDIS_URL=redis://redis:6379/0

# Application
BASE_URL=http://localhost:8000
SHORT_CODE_LENGTH=6
CACHE_TTL_SECONDS=3600

# Rate Limiting
RATE_LIMIT_SHORTEN=10/minute
RATE_LIMIT_REDIRECT=100/minute
RATE_LIMIT_STATS=30/minute
RATE_LIMIT_DELETE=10/minute

# Background Sync
SYNC_INTERVAL_SECONDS=300
```

# url-shortener/README.md
```markdown
# URL Shortener Microservice

## Overview

A production-ready URL shortener microservice built with FastAPI, PostgreSQL, and Redis. Features include:
- URL shortening with base62 encoding
- Caching with Redis for high-performance redirects
- Click statistics and tracking
- Soft-delete functionality
- Rate limiting
- SSRF protection
- Docker containerization with health checks

## Quick Start

### Prerequisites
- Docker and Docker Compose v2+
- Git

### Installation

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

4. Verify services are healthy:
   ```bash
   docker compose ps
   ```

5. Access the application:
   - API: http://localhost:8000
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

## API Endpoints

### Create Short URL
```bash
curl -X POST http://localhost:8000/shorten/ \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/very/long/url"}'
```

### Redirect
```bash
curl -L http://localhost:8000/{short_code}
```

### Get Statistics
```bash
curl http://localhost:8000/stats/{short_code}
```

### Delete URL
```bash
curl -X DELETE http://localhost:8000/{short_code}
```

### Health Check
```bash
curl http://localhost:8000/health
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://postgres:postgres@db:5432/urlshortener` |
| `REDIS_URL` | Redis connection string | `redis://redis:6379/0` |
| `BASE_URL` | Base URL for short links | `http://localhost:8000` |
| `SHORT_CODE_LENGTH` | Length of generated short codes | `6` |
| `CACHE_TTL_SECONDS` | Redis cache TTL | `3600` |
| `RATE_LIMIT_*` | Rate limits for different endpoints | See `.env.example` |
| `SYNC_INTERVAL_SECONDS` | Click sync interval | `300` |

## Architecture

```
┌──────────────┐     ┌──────────────────────────────────┐     ┌─────────────┐
│   Client     │────▶│         FastAPI Application      │────▶│   Redis     │
│  (Browser/   │     │                                  │     │  (Cache +  │
│   curl)      │◀────│  ┌────────────────────────────┐  │◀────│  RateLimit) │
└──────────────┘     │  │     API Router Layer       │  │     └─────────────┘
                     │  │  (shorten, redirect, stats)│  │
                     │  └────────────┬───────────────┘  │     ┌─────────────┐
                     │               │                    │────▶│ PostgreSQL │
                     │  ┌────────────▼───────────────┐  │     │   (Source  │
                     │  │     Service Layer           │  │◀────│    of     │
                     │  │  (business logic, cache     │  │     │  Truth)   │
                     │  │   orchestration)            │  │     └─────────────┘
                     │  └────────────┬───────────────┘  │
                     │               │                    │
                     │  ┌────────────▼───────────────┐  │
                     │  │   Repository Layer          │  │
                     │  │  (SQLAlchemy + Redis DAO)  │  │
                     │  └────────────────────────────┘  │
                     └──────────────────────────────────┘
```

## Development

### Running Locally
```bash
# Start dependencies
docker compose up -d db redis

# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Running Tests
```bash
# Setup test database
docker compose exec db createdb test_urlshortener

# Run tests
pytest -v --cov=app --cov-report=term-missing
```

### Code Quality
```bash
# Linting
ruff check app/

# Type checking
mypy app/
```

## Docker Images

| Service | Image | Version |
|---------|-------|---------|
| Application | python | 3.12-slim |
| PostgreSQL | postgres | 16-alpine |
| Redis | redis | 7-alpine |

## Health Checks

All services include Docker health checks:
- **PostgreSQL**: `pg_isready -U postgres`
- **Redis**: `redis-cli ping`
- **Application**: HTTP GET to `/health` endpoint

## Security

- SSRF protection blocks private IP ranges
- Input validation via Pydantic
- Rate limiting to prevent abuse
- Non-root user in container
- Environment variables for secrets (never in code)

## License

MIT
```