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
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Final stage
FROM python:3.11-slim

WORKDIR /app

# Copy only necessary files from builder
COPY --from=builder /root/.local /root/.local

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser -u 1000 appuser

# Copy application code
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Update PATH for local Python packages
ENV PATH=/root/.local/bin:$PATH

# Expose port
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

```yaml
# url-shortener/docker-compose.yml
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
      - DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
      - REDIS_URL=redis://redis:6379/0
      - BASE_URL=http://localhost:8000
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]
      interval: 30s
      timeout: 10s
      start_period: 10s
      retries: 3
    networks:
      - url-shortener-network
    volumes:
      - app_data:/app/data

  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=${POSTGRES_DB}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    networks:
      - url-shortener-network

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    networks:
      - url-shortener-network

networks:
  url-shortener-network:
    driver: bridge

volumes:
  postgres_data:
    driver: local
  redis_data:
    driver: local
  app_data:
    driver: local
```

```env
# url-shortener/.env.example
# Database
POSTGRES_USER=urluser
POSTGRES_PASSWORD=urlpass
POSTGRES_DB=urlshortener
DATABASE_URL=postgresql+asyncpg://urluser:urlpass@postgres:5432/urlshortener

# Redis
REDIS_URL=redis://redis:6379/0

# Application
RATE_LIMIT_PER_MINUTE=100
SHORT_ID_LENGTH=7
CACHE_TTL_SECONDS=3600
BASE_URL=http://localhost:8000
MAX_URL_LENGTH=2048
STATS_SYNC_THRESHOLD=10
SHUTDOWN_TIMEOUT_SECONDS=30

# Optional
REDIS_PASSWORD=
```

```markdown
# url-shortener/README.md

# URL Shortener Microservice

A high-performance URL shortening microservice built with FastAPI, PostgreSQL, and Redis.

## Features

- **URL Shortening**: Create short URLs (7-character base62 IDs)
- **Fast Redirects**: Redis-cached redirects with <50ms p99 latency
- **Click Statistics**: Track and retrieve click counts
- **URL Deletion**: Soft delete with cache cleanup
- **Rate Limiting**: Redis-based sliding window rate limiting (100 req/min per IP)
- **SSRF Protection**: Blocks requests to private/internal IPs
- **Health Checks**: Monitors database and Redis connectivity
- **Graceful Shutdown**: Proper connection cleanup on SIGTERM/SIGINT

## Tech Stack

- **Python 3.11+** with async/await
- **FastAPI** for REST API with auto-generated OpenAPI docs
- **SQLAlchemy 2.0** (async) with PostgreSQL 15
- **Redis 7** for caching and rate limiting
- **Alembic** for database migrations
- **Docker** and docker-compose for containerization

## Quick Start

### Prerequisites

- Docker and docker-compose (v2.0+)
- Python 3.11+ (for local development)

### Using Docker (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd url-shortener

# Copy environment file and configure
cp .env.example .env
# Edit .env if needed (defaults work for local development)

# Start all services
docker compose up -d

# Run database migrations
docker compose exec app alembic upgrade head

# Verify health
curl http://localhost:8000/health

# View logs
docker compose logs -f app
```

### Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Start PostgreSQL and Redis
docker compose up -d postgres redis

# Run migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API Endpoints

### POST /shorten
Create a short URL.

```bash
curl -X POST http://localhost:8000/shorten \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/very/long/path"}'
```

### GET /{id}
Redirect to original URL.

```bash
curl -I http://localhost:8000/aB3x9Qk
```

### GET /stats/{id}
Get URL statistics.

```bash
curl http://localhost:8000/stats/aB3x9Qk
```

### DELETE /{id}
Delete a short URL.

```bash
curl -X DELETE http://localhost:8000/aB3x9Qk
```

### GET /health
Health check.

```bash
curl http://localhost:8000/health
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Configuration

Configuration is done via environment variables (see `.env.example`):

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://...` | PostgreSQL connection string |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection string |
| `RATE_LIMIT_PER_MINUTE` | `100` | Max requests per minute per IP |
| `SHORT_ID_LENGTH` | `7` | Length of generated short IDs |
| `CACHE_TTL_SECONDS` | `3600` | Redis cache TTL in seconds |
| `BASE_URL` | `http://localhost:8000` | Base URL for short links |
| `MAX_URL_LENGTH` | `2048` | Maximum original URL length |
| `STATS_SYNC_THRESHOLD` | `10` | Clicks before syncing to DB |
| `SHUTDOWN_TIMEOUT_SECONDS` | `30` | Graceful shutdown timeout |

## Testing

```bash
# Run all tests
pytest -v

# Run with coverage
pytest -v --cov=app --cov-report=html

# Run specific test file
pytest -v tests/test_shorten.py
```

## Architecture

The service follows a layered architecture:

- **Routers**: Handle HTTP request/response
- **Services**: Business logic layer
- **Models**: SQLAlchemy database models
- **Middleware**: Rate limiting, CORS
- **Utils**: Short ID generation, URL validation

### Data Flow (Redirect)

1. Request hits Rate Limit Middleware
2. Router delegates to UrlService
3. Service checks Redis cache first
4. Cache miss → queries PostgreSQL
5. Records click in Redis buffer (async)
6. Returns 302 redirect

### Caching Strategy

- **Hot cache**: URLs cached in Redis with 1-hour TTL
- **Stats buffering**: Click counts buffered in Redis, synced to DB every N clicks
- **Rate limiting**: Sliding window counters in Redis per IP (atomic Lua script)

## Production Deployment

```bash
# Build and start with multiple workers
docker compose up -d --scale app=4

# The service is stateless and can be horizontally scaled
# behind a load balancer with shared Redis and PostgreSQL
```

## Security

- URL scheme validation (http/https only)
- SSRF protection (blocks private IPs)
- Rate limiting per IP
- SQL injection prevention via parameterized queries
- No sensitive data in logs
- Non-root user in container

## Troubleshooting

### Common Issues

1. **Port already in use**: Change ports in `docker-compose.yml` or stop conflicting services
2. **Database connection refused**: Ensure PostgreSQL is healthy: `docker compose ps`
3. **Redis connection refused**: Ensure Redis is healthy: `docker compose ps`
4. **Migration errors**: Run `docker compose exec app alembic upgrade head` again

### Logs

```bash
# View all logs
docker compose logs

# Follow specific service
docker compose logs -f app

# View last 100 lines
docker compose logs --tail=100 app
```

## License

MIT
```