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

```dockerfile
# url-shortener/Dockerfile
# Stage 1: Build stage
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime stage
FROM python:3.11-slim AS runtime

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

WORKDIR /app

# Copy only the installed packages from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY --chown=appuser:appuser . .

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Switch to non-root user
USER appuser

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# url-shortener/docker-compose.yml
version: "3.8"

services:
  postgres:
    image: postgres:15
    container_name: urlshortener-postgres
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-user}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-pass}
      POSTGRES_DB: ${POSTGRES_DB:-urlshortener}
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-user} -d ${POSTGRES_DB:-urlshortener}"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s
    restart: unless-stopped

  redis:
    image: redis:7
    container_name: urlshortener-redis
    ports:
      - "6379:6379"
    volumes:
      - redisdata:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s
    restart: unless-stopped

  app:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: urlshortener-app
    env_file:
      - .env
    environment:
      DATABASE_URL: postgresql+asyncpg://${POSTGRES_USER:-user}:${POSTGRES_PASSWORD:-pass}@postgres:5432/${POSTGRES_DB:-urlshortener}
      REDIS_URL: redis://redis:6379/0
      UVICORN_HOST: "0.0.0.0"
      UVICORN_PORT: "8000"
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    restart: unless-stopped

volumes:
  pgdata:
  redisdata:
```

```text
# url-shortener/.env.example
# Database
POSTGRES_USER=user
POSTGRES_PASSWORD=pass
POSTGRES_DB=urlshortener
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/urlshortener

# Redis
REDIS_URL=redis://localhost:6379/0

# Application
BASE_URL=https://short.example.com
RATE_LIMIT_PER_MINUTE=100
CACHE_TTL_SECONDS=3600
SHORT_ID_LENGTH=7

# Uvicorn
UVICORN_WORKERS=4
UVICORN_HOST=0.0.0.0
UVICORN_PORT=8000
```

```markdown
# url-shortener/README.md

# URL Shortener Microservice

A production-ready URL shortener microservice built with FastAPI, PostgreSQL, and Redis.

## Quick Start

### Prerequisites
- Docker and Docker Compose installed on your system

### Running the Application

1. Clone the repository and navigate to the project directory:
```bash
cd url-shortener
```

2. Copy the example environment file and adjust if needed:
```bash
cp .env.example .env
```

3. Start all services with a single command:
```bash
docker compose up
```

The application will be available at `http://localhost:8000`.

### API Documentation
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Health Check
```bash
curl http://localhost:8000/health
```

### Example Usage

**Create a short URL:**
```bash
curl -X POST http://localhost:8000/api/v1/shorten \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/very/long/path"}'
```

**Redirect to original URL:**
```bash
curl -L http://localhost:8000/api/v1/{short_id}
```

**Get statistics:**
```bash
curl http://localhost:8000/api/v1/stats/{short_id}
```

**Delete a short URL:**
```bash
curl -X DELETE http://localhost:8000/api/v1/{short_id}
```

### Stopping the Application
```bash
docker compose down
```

To remove volumes as well:
```bash
docker compose down -v
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `POSTGRES_USER` | PostgreSQL username | `user` |
| `POSTGRES_PASSWORD` | PostgreSQL password | `pass` |
| `POSTGRES_DB` | PostgreSQL database name | `urlshortener` |
| `DATABASE_URL` | Full database connection string | `postgresql+asyncpg://user:pass@localhost:5432/urlshortener` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `BASE_URL` | Base URL for shortened links | `https://short.example.com` |
| `RATE_LIMIT_PER_MINUTE` | Maximum requests per minute per IP | `100` |
| `CACHE_TTL_SECONDS` | Cache TTL for redirects | `3600` |
| `SHORT_ID_LENGTH` | Length of generated short IDs | `7` |
| `UVICORN_WORKERS` | Number of uvicorn workers | `4` |
| `UVICORN_HOST` | Host to bind | `0.0.0.0` |
| `UVICORN_PORT` | Port to listen on | `8000` |

### Architecture

The application consists of three services:
- **app**: FastAPI application with async endpoints
- **postgres**: PostgreSQL database for persistent storage
- **redis**: Redis for caching and rate limiting

### Health Checks

All services have health checks configured:
- **PostgreSQL**: Uses `pg_isready` to verify database availability
- **Redis**: Uses `redis-cli ping` to verify cache availability
- **App**: Checks the `/health` endpoint every 30 seconds

### Volumes

- `pgdata`: Persistent PostgreSQL data
- `redisdata`: Persistent Redis data
```