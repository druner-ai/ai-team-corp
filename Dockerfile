# Multi-stage build for URL Shortener Service
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies if needed (none for pure Python)
COPY requirements.txt requirements-dev.txt ./

# Create virtual environment and install all dependencies
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.txt -r requirements-dev.txt

# Final stage
FROM python:3.12-slim

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application code and tests
COPY app/ ./app/
COPY tests/ ./tests/
COPY scripts/ ./scripts/
COPY pyproject.toml pytest.ini ./

# Set environment variables
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1

# Create data directory with proper permissions
RUN mkdir -p /app/data && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# Health check using Python (no extra dependencies)
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
