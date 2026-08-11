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

```yaml
# url-shortener/docker-compose.yml
version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: url-shortener-app
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://user:password@db:5432/urlshortener
      - REDIS_URL=redis://cache:6379/0
      - SECRET_KEY=${SECRET_KEY:-change-me-in-production}
      - RATE_LIMIT_PER_MINUTE=${RATE_LIMIT_PER_MINUTE:-100}
      - CACHE_TTL_SECONDS=${CACHE_TTL_SECONDS:-300}
    depends_on:
      db:
        condition: service_healthy
      cache:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    volumes:
      - app_data:/app/data
    networks:
      - url-shortener-network
    restart: unless-stopped

  db:
    image: postgres:16-alpine
    container_name: url-shortener-db
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=urlshortener
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user -d urlshortener"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s
    networks:
      - url-shortener-network
    restart: unless-stopped

  cache:
    image: redis:7-alpine
    container_name: url-shortener-cache
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s
    networks:
      - url-shortener-network
    restart: unless-stopped

volumes:
  postgres_data:
    driver: local
  redis_data:
    driver: local
  app_data:
    driver: local

networks:
  url-shortener-network:
    driver: bridge
```

```dockerfile
# url-shortener/Dockerfile
# Stage 1: Build stage
FROM python:3.12-slim-bookworm AS builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies for building
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /bin/bash appuser

# Set working directory
WORKDIR /app

# Copy only requirements first for better caching
COPY pyproject.toml .

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Stage 2: Runtime stage
FROM python:3.12-slim-bookworm AS runtime

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_HOME=/app

# Install runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser -d ${APP_HOME} -s /bin/bash appuser

# Set working directory
WORKDIR ${APP_HOME}

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=appuser:appuser . .

# Create data directory for persistent storage
RUN mkdir -p ${APP_HOME}/data && chown appuser:appuser ${APP_HOME}/data

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

```env
# url-shortener/.env.example
# Application Settings
SECRET_KEY=change-me-in-production
RATE_LIMIT_PER_MINUTE=100
CACHE_TTL_SECONDS=300

# Database Settings
DATABASE_URL=postgresql+asyncpg://user:password@db:5432/urlshortener
POSTGRES_USER=user
POSTGRES_PASSWORD=password
POSTGRES_DB=urlshortener

# Redis Settings
REDIS_URL=redis://cache:6379/0

# Application Port
APP_PORT=8000

# Logging Level
LOG_LEVEL=INFO
```

```markdown
# url-shortener/README.md

# URL Shortener Service

A production-ready URL shortener service built with FastAPI, PostgreSQL, and Redis.

## Features

- Create short URLs with optional expiration
- Redirect to original URLs with click tracking
- View statistics for shortened URLs
- Soft-delete functionality
- Rate limiting
- URL validation with SSRF protection
- Caching with Redis
- Health check endpoint
- Docker containerization

## Prerequisites

- Docker and Docker Compose
- Python 3.12+ (for local development)

## Quick Start

### Using Docker (Recommended)

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd url-shortener
   ```

2. Copy the environment file:
   ```bash
   cp .env.example .env
   ```

3. Edit `.env` with your settings (or use defaults for development)

4. Start the services:
   ```bash
   docker compose up -d
   ```

5. The API will be available at `http://localhost:8000`

6. Check service health:
   ```bash
   curl http://localhost:8000/health
   ```

### Local Development

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -e .
   ```

3. Set up PostgreSQL and Redis (using Docker):
   ```bash
   docker run -d --name postgres -e POSTGRES_USER=user -e POSTGRES_PASSWORD=password -e POSTGRES_DB=urlshortener -p 5432:5432 postgres:16-alpine
   docker run -d --name redis -p 6379:6379 redis:7-alpine
   ```

4. Copy and edit environment file:
   ```bash
   cp .env.example .env
   ```

5. Run database migrations:
   ```bash
   alembic upgrade head
   ```

6. Start the application:
   ```bash
   uvicorn src.main:app --reload --port 8000
   ```

## API Endpoints

### Create Short URL
```http
POST /shorten
Content-Type: application/json

{
  "url": "https://example.com/very/long/path?query=1",
  "expires_at": "2025-12-31T23:59:59Z"  // Optional
}
```

### Redirect to Original URL
```http
GET /{short_id}
```

### Get URL Statistics
```http
GET /stats/{short_id}
```

### Delete Short URL
```http
DELETE /{short_id}
```

### Health Check
```http
GET /health
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Secret key for security | `change-me-in-production` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://user:password@db:5432/urlshortener` |
| `REDIS_URL` | Redis connection string | `redis://cache:6379/0` |
| `RATE_LIMIT_PER_MINUTE` | Maximum requests per minute | `100` |
| `CACHE_TTL_SECONDS` | Cache time-to-live in seconds | `300` |
| `LOG_LEVEL` | Logging level | `INFO` |

## Docker Commands

### Start services
```bash
docker compose up -d
```

### Stop services
```bash
docker compose down
```

### View logs
```bash
docker compose logs -f
```

### Rebuild and restart
```bash
docker compose up -d --build
```

### Run tests
```bash
docker compose exec app pytest
```

## Project Structure

```
url-shortener/
├── docker-compose.yml
├── Dockerfile
├── .env.example
├── README.md
├── pyproject.toml
├── alembic.ini
├── alembic/
│   ├── env.py
│   └── versions/
│       └── 001_initial.py
├── src/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── dependencies.py
│   ├── models.py
│   ├── schemas.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py
│   ├── db/
│   │   ├── __init__.py
│   │   ├── postgres.py
│   │   └── redis.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── url_service.py
│   │   └── id_generator.py
│   └── utils/
│       ├── __init__.py
│       └── url_validator.py
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_shorten.py
    ├── test_redirect.py
    ├── test_stats.py
    ├── test_delete.py
    ├── test_rate_limit.py
    ├── test_url_validator.py
    └── test_id_generator.py
```

## Testing

Run tests with coverage:
```bash
pytest --cov=src --cov-report=term-missing
```

## Security

- Non-root user in Docker containers
- URL validation with SSRF protection
- Rate limiting
- Input validation
- Environment variables for sensitive data
- Health checks for all services

## License

MIT
```