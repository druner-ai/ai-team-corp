# Patterns Library для AI Team Corp

Этот каталог содержит **проверенные паттерны**, которые загружаются в промпты агентов. Каждый файл — машиночитаемый гайд для конкретной роли/домена.

## Структура

| Файл | Для кого | Что покрывает |
|:---|:---|:---|
| `fastapi-agents.md` | Разработчик, QA | FastAPI: async, Pydantic v2, SQLAlchemy 2.0, тестирование, JWT |
| `docker-agents.md` | DevOps | Dockerfile, docker-compose, CI/CD, GitHub Actions |
| `pytest-agents.md` | Разработчик, QA | pytest, fixtures, conftest.py, БД-тестирование |
| `architecture-agents.md` | Архитектор | Проектирование API, структура проекта, DDD |

## Как использовать

В `tasks.py` агенты получают паттерны через `{patterns['fastapi']}`:

```python
from patterns import load_patterns

patterns = load_patterns()

Task(
    description=f"""
    ...
    {patterns['fastapi']}
    ...
    """
)
```

## Источники

- `fastapi-agents.md` — zhanymkanov/fastapi-best-practices (AGENTS.md)
- `docker-agents.md` — best practices from Docker, GitHub Actions docs
- `pytest-agents.md` — pytest docs, FastAPI testing tutorial
- `architecture-agents.md` — FastAPI project structure best practices
