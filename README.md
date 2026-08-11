# URL Shortener Service

Простой и быстрый сервис сокращения ссылок на FastAPI + SQLite.

## Быстрый старт

```bash
make install
make migrate
make run
```

Приложение будет доступно на `http://localhost:8000`.

## API

- **POST /api/v1/urls** – создать короткую ссылку
- **GET /r/{slug}** – перейти по короткой ссылке
- **GET /api/v1/urls/{slug}/stats** – статистика переходов
- **DELETE /api/v1/urls/{slug}** – деактивировать ссылку
- **GET /health** – проверка работоспособности

## Переменные окружения

Скопируйте `.env.example` в `.env` и при необходимости измените.

## Тестирование

```bash
make test
```
