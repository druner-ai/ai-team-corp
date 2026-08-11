# Stage 1: builder
FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

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

# Healthcheck using built-in urllib
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

EXPOSE 8000

CMD ["uvicorn", "src.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
