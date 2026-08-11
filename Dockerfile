# Stage 1: Build stage for preparing the application
FROM python:3.11-slim-bookworm AS builder

WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install build dependencies and create virtual environment
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    python -m venv /opt/venv

# Copy and install requirements
COPY requirements.txt .
RUN /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# Stage 2: Final runtime stage
FROM python:3.11-slim-bookworm AS runtime

# Create non-root user
RUN groupadd -r shortener && useradd -r -g shortener -d /app shortener

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

WORKDIR /app

# Copy application code
COPY app/ ./app/
COPY tests/ ./tests/
COPY pyproject.toml .

# Install test dependencies for running tests inside container
COPY requirements-dev.txt .
RUN /opt/venv/bin/pip install --no-cache-dir -r requirements-dev.txt

# Create volume directory for database and set ownership
RUN mkdir -p /app/data && chown -R shortener:shortener /app

# Switch to non-root user
USER shortener

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/api/health').raise_for_status()"

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
