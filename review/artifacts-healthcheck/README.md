# Health Check Service

Легковесный HTTP-сервис для мониторинга состояния (liveness/readiness) приложения.

## Endpoint

- `GET /health` — возвращает статус, uptime и версию.

## Быстрый старт

### Локально

```bash
pip install -r requirements-dev.txt
make run
```

Проверка:
```bash
curl http://localhost:8000/health
```

### Docker

```bash
make docker-build
docker run -p 8000:8000 health-check-service:1.0.0
```

## Переменные окружения

| Переменная     | Описание                     | По умолчанию   |
|----------------|------------------------------|----------------|
| `APP_VERSION`  | Версия сервиса               | `1.0.0`        |
| `ENVIRONMENT`  | Окружение (development/prod) | `development`  |
| `LOG_LEVEL`    | Уровень логирования          | `INFO`         |

## Тестирование

```bash
make test
```

## Линтинг

```bash
make lint
```
