# ============================================================
# Stage 1: Builder — установка зависимостей и сборка
# ============================================================
FROM python:3.11-slim AS builder

# Фиксируем версию pip и setuptools
RUN pip install --no-cache-dir --upgrade pip==24.0 setuptools==69.5.1

WORKDIR /build

# Копируем только файлы с зависимостями для кэширования слоя
COPY pyproject.toml alembic.ini ./

# Устанавливаем production-зависимости
RUN pip install --no-cache-dir .

# ============================================================
# Stage 2: Runtime — минимальный образ для запуска
# ============================================================
FROM python:3.11-slim AS runtime

# Создаём непривилегированного пользователя
RUN groupadd -r appgroup && useradd -r -g appgroup -d /app -s /sbin/nologin appuser

WORKDIR /app

# Копируем установленные пакеты из builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Копируем исходный код приложения (без .env и лишних файлов)
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini pyproject.toml ./
COPY scripts/ ./scripts/

# Скрипт запуска (миграции + uvicorn)
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Переключаемся на непривилегированного пользователя
USER appuser

# Healthcheck (проверяет, что приложение отвечает)
HEALTHCHECK --interval=10s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/openapi.json')" || exit 1

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]