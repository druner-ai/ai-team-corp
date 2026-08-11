# Stage 1: Build stage with dependencies
FROM python:3.12-slim AS builder

WORKDIR /app

# Copy requirements and install core dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Install test dependencies (pytest, httpx, pytest-asyncio) so they are available in the final image
RUN pip install --no-cache-dir --user pytest httpx pytest-asyncio

# Stage 2: Production stage
FROM python:3.12-slim

WORKDIR /app

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy installed packages from builder stage
COPY --from=builder /root/.local /home/appuser/.local

# Copy application code, tests, SQL, and project metadata
COPY src/ ./src/
COPY tests/ ./tests/
COPY sql/ ./sql/
COPY pyproject.toml ./

# Ensure data directory exists with correct ownership
RUN mkdir -p /app/data && chown -R appuser:appuser /app

# Make sure scripts in .local are accessible
ENV PATH=/home/appuser/.local/bin:$PATH

# Switch to non-root user
USER appuser

EXPOSE 8000

# Healthcheck using the /health endpoint
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run the application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
