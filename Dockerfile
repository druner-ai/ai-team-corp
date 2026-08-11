# Stage 1: builder
FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-dev.txt ./
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /wheels -r requirements.txt

# Stage 2: runtime
FROM python:3.12-slim

WORKDIR /app

RUN groupadd -r appuser && useradd -r -g appuser appuser

COPY --from=builder /wheels /wheels
COPY requirements-dev.txt ./
RUN pip install --no-cache /wheels/* \
    && pip install --no-cache -r requirements-dev.txt \
    && rm -rf /wheels requirements-dev.txt

RUN mkdir -p /app/data && chown -R appuser:appuser /app/data

COPY --chown=appuser:appuser app/ ./app/
COPY --chown=appuser:appuser tests/ ./tests/
COPY --chown=appuser:appuser migrations/ ./migrations/
COPY --chown=appuser:appuser pytest.ini ./

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]