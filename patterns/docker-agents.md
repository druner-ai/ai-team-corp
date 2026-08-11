# Docker & CI/CD Patterns для DevOps-агента

Машиночитаемые паттерны для генерации production-ready Docker и GitHub Actions.

## Dockerfile (Python/FastAPI)

### Multi-stage build — обязательно

```dockerfile
# Stage 1: builder
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt


# Stage 2: runtime
FROM python:3.12-slim

WORKDIR /app

# Create non-root user
RUN groupadd -r app && useradd -r -g app app

# Copy wheels from builder
COPY --from=builder /app/wheels /wheels
RUN pip install --no-cache /wheels/* && rm -rf /wheels

# Copy app code
COPY --chown=app:app . .

USER app

# Healthcheck
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Anti-patterns

| ❌ Не делай | ✅ Делай | Почему |
|:---|:---|:---|
| `FROM python:3.12` | `FROM python:3.12-slim` | Slim на 500MB меньше |
| `pip install` без wheels | Multi-stage с `--wheel-dir` | Кэширование слоёв |
| `USER root` | `USER app` (non-root) | Безопасность |
| `COPY . .` без .dockerignore | `.dockerignore` с `.git`, `__pycache__` | Скорость build |
| `latest` теги | Фиксированные версии | Воспроизводимость |

## docker-compose.yml

```yaml
services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=sqlite:///./data.db
    volumes:
      - ./data:/app/data  # persistent data
    healthcheck:
      test: ["CMD", "python", "-c", "import httpx; httpx.get('http://localhost:8000/health')"]
      interval: 30s
      timeout: 3s
      retries: 3
      start_period: 5s
    restart: unless-stopped

  # Для тестов в CI
  test:
    build: .
    command: pytest tests/ -v
    environment:
      - DATABASE_URL=sqlite:///:memory:
    depends_on:
      - app
```

### Anti-patterns

| ❌ Не делай | ✅ Делай |
|:---|:---|
| `version: "3.8"` в Compose V2 | Без `version` (deprecated) |
| `container_name:` | Автоматические имена |
| `network_mode: host` | `ports:` маппинг |
| `.env` в образе | `environment:` или `env_file:` |

## GitHub Actions CI/CD

### Полный workflow для FastAPI

```yaml
name: CI

on:
  push:
    branches: [master, ai-team/**]
  pull_request:
    branches: [master]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Create venv
        run: |
          python -m venv .venv
          .venv/bin/pip install -r requirements.txt -r requirements-dev.txt

      - name: Run tests
        run: .venv/bin/pytest tests/ -v --tb=short
        # БЕЗ || true — тесты должны падать честно

      - name: Lint
        run: .venv/bin/ruff check .

  build:
    runs-on: ubuntu-latest
    needs: test
    steps:
      - uses: actions/checkout@v4

      - name: Build Docker image
        run: docker build -t app:test .

      - name: Test image
        run: |
          docker run --rm -d --name testapp -p 8000:8000 app:test
          sleep 5
          curl -f http://localhost:8000/health || exit 1
          docker stop testapp
```

### Anti-patterns

| ❌ Не делай | ✅ Делай |
|:---|:---|
| `|| true` после pytest | Пусть падает с exit code 1 |
| `python -m pytest` без venv | `.venv/bin/pytest` |
| `pip install pytest` только | `-r requirements.txt -r requirements-dev.txt` |
| `pytest tests/` без `--tb=short` | `--tb=short` для читаемых логов |
| `on: [push]` без branches | `branches: [master, ai-team/**]` |

## Healthcheck endpoint (обязателен)

```python
# app/routers/health.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
async def health():
    return {"status": "ok"}
```

## .dockerignore

```
.git
__pycache__
*.pyc
*.pyo
*.pyd
.Python
.venv
venv
tests/
*.md
.dockerignore
Dockerfile
docker-compose.yml
```
