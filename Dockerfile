# Stage 1: builder
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements files
COPY requirements.txt requirements-dev.txt ./

# Build wheels for all dependencies
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels \
    -r requirements.txt -r requirements-dev.txt


# Stage 2: runtime
FROM python:3.12-slim

WORKDIR /app

# Create non-root user
RUN groupadd -r app && useradd -r -g app app

# Copy wheels from builder and install
COPY --from=builder /app/wheels /wheels
RUN pip install --no-cache /wheels/* && rm -rf /wheels

# Copy application code and tests
COPY --chown=app:app app/ ./app/
COPY --chown=app:app tests/ ./tests/
COPY --chown=app:app pytest.ini ./

USER app

# Healthcheck
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health')" || exit 1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
