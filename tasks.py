"""
Задачи для каждой роли AI-команды.
v2.1 — DevOps генерирует CI/CD.
"""

from crewai import Task
from agents import architect, developer, qa_gate, devops
from output_models import CodeOutput
from patterns import load_patterns

# Загружаем паттерны один раз при импорте
_patterns = load_patterns()


def make_tasks(task_description: str) -> list[Task]:
    """Создать все задачи для команды на основе входящего описания."""

    architecture_doc = Task(
        description=f"""
        Ты получил задачу от пользователя. Спроектируй полное решение.

        ЗАДАЧА ПОЛЬЗОВАТЕЛЯ:
        {task_description}

        Твой документ ДОЛЖЕН содержать (markdown, минимум 500 слов):
        1. **Обзор**: что делает система, ключевые сценарии использования
        2. **Технологический стек**: языки, фреймворки, БД, кэш, очереди — с обоснованием выбора
        3. **Архитектура**: диаграмма компонентов (текстом), описание каждого
        4. **Модель данных**: сущности, поля, связи, индексы
        5. **API-контракты**: endpoints, методы, форматы запросов/ответов, коды ошибок
        6. **Нефункциональные требования**: безопасность, производительность, масштабирование
        7. **Структура проекта**: дерево файлов и папок

        Это — ЕДИНСТВЕННЫЙ источник правды для Разработчика и DevOps.
        Не сжимай информацию в YAML/JSON — пиши полный человекочитаемый текст.
        """,
        expected_output="Полный архитектурный документ в формате Markdown (минимум 500 слов, "
                       "содержит все 7 разделов). Документ самодостаточен — "
                       "Разработчик не должен додумывать.",
        agent=architect,
    )

    coding_task = Task(
        description="""
        Напиши код строго по архитектурному документу, который создал Архитектор.

        ВАЖНО — ФОРМАТ ОТВЕТА:
        Ты должен вернуть JSON с полем files — массив объектов, каждый с полями path и content.
        Пример:
        {
          "files": [
            {"path": "app/main.py", "content": "from fastapi import FastAPI\\n..."},
            {"path": "requirements.txt", "content": "fastapi==0.110.0\\n..."},
            {"path": "tests/test_api.py", "content": "import pytest\\n..."}
          ]
        }

        ПРАВИЛА ДЛЯ ПУТЕЙ:
        - Каждый путь ДОЛЖЕН иметь расширение файла (.py, .md, .txt, .json, .yml, .toml)
        - Примеры ПРАВИЛЬНЫХ путей: "app/main.py", "tests/__init__.py", "Dockerfile"
        - Примеры НЕПРАВИЛЬНЫХ: "app" (нет расширения), "notes_api" (нет расширения)

        ТРЕБОВАНИЯ К КОДУ:
        - Включай requirements.txt (все runtime-зависимости)
        - Включай requirements-dev.txt (все test-зависимости: pytest, httpx, pytest-asyncio, aiosqlite и т.д.)
        - Включай pytest.ini или conftest.py в корне с настройкой pythonpath
        - КРИТИЧНО: conftest.py ДОЛЖЕН инициализировать БД для тестов (см. шаблон в templates/conftest_sqlite_no_orm.py)
          * Используй in-memory SQLite (:memory:) для скорости и изоляции
          * Применяй схему из sql/init.sql или создавай таблицы inline
          * Используй fixture scope="function" — новая БД на каждый тест
          * Для FastAPI dependency override используй app.dependency_overrides

        ПАТТЕРНЫ ТЕСТИРОВАНИЯ (обязательно следуй):
        {_patterns['pytest']}

        КРИТИЧНО — DEPENDENCY INJECTION:
        - Все функции-обработчики ДОЛЖНЫ получать БД через Depends(get_db)
        - ЗАПРЕЩЕНО использовать глобальные переменные для подключения к БД
        - get_db() должна быть generator function (yield, не return)
        - Тесты подменяют БД через app.dependency_overrides[get_db] — это работает только с DI

        КРИТИЧНО — ЗАВИСИМОСТИ ДЛЯ ТЕСТОВ:
        Все библиотеки, которые импортируются в tests/ (httpx, pytest-asyncio, aiosqlite,
        freezegun и т.д.), ДОЛЖНЫ быть в requirements-dev.txt. DevOps будет использовать
        этот файл для CI. Если тест импортирует модуль — он должен быть установлен.

        КАЧЕСТВО:
        - Типизация (type hints) на всех публичных функциях
        - Документирующие комментарии к классам и сложным функциям
        - Обработка ошибок (не голые try/except)
        - Валидация входных данных
        """,
        expected_output="JSON с полем files — массив всех файлов проекта с путями и содержимым.",
        agent=developer,
        output_pydantic=CodeOutput,
    )

    review_task = Task(
        description="""
        Проверь код Разработчика на соответствие архитектурному документу Архитектора.

        КРИТИЧНО — ЗАПУСК ТЕСТОВ:
        1. Используй инструмент run_tests с путём к директории с кодом
        2. Проанализируй результат: если есть failed/error — это 🔴 критично
        3. Даже если код выглядит правильно, но тесты падают — это No-Go

        ЧТО ПРОВЕРЯТЬ:
        1. **Запуск тестов**: run_tests — все ли проходят? (ОБЯЗАТЕЛЬНО)
        2. **Соответствие архитектуре**: все ли компоненты реализованы? Нет ли лишнего?
        3. **Безопасность**: SQL-инъекции, XSS, утечки секретов, небезопасные зависимости
        4. **Обработка ошибок**: все ли исключения обработаны? Нет ли голых try/except?
        5. **Валидация**: проверяются ли входные данные на всех endpoint-ах?
        6. **Тесты**: есть ли они? Покрывают ли основные сценарии?
        7. **Style guide**: PEP 8, нейминг, типизация

        ФОРМАТ ОТВЕТА:
        Для каждой найденной проблемы:
        - Приоритет: 🔴 (критично — блокирует запуск) / 🟡 (важно — нужно исправить) / 🟢 (минор — можно так)
        - Файл и строка (если применимо)
        - Описание проблемы
        - Предложение по исправлению

        В конце: ИТОГОВЫЙ ВЕРДИКТ — ✅ Go (тесты проходят, нет критических проблем) или ❌ No-Go (тесты падают ИЛИ есть критические проблемы).
        Если No-Go — перечисли КОНКРЕТНЫЕ файлы и строки, которые нужно исправить.
        """,
        expected_output="Отчёт о проверке: список проблем с приоритетами + вердикт Go/No-Go.",
        agent=qa_gate,
    )

    fix_task = Task(
        description="""
        QA Gate нашёл проблемы в твоём коде. Исправь ИСКЛЮЧИТЕЛЬНО то, что указано в отчёте QA.

        ВАЖНО — ФОРМАТ ОТВЕТА:
        Верни JSON с полем files — массив ВСЕХ файлов (исправленных + неизменённых).
        Каждый файл: {{"path": "...", "content": "..."}}

        ПРАВИЛА:
        - Исправляй только проблемы с приоритетом 🔴 и 🟡
        - 🟢 (минор) — только если есть время и это не меняет архитектуру
        - НЕ переписывай код с нуля — точечные правки
        - Верни ПОЛНУЮ кодовую базу (все файлы), а не только исправленные
        - В поле content первого файла добавь комментарий с перечнем исправлений
        """,
        expected_output="JSON с полем files — полная кодовая база с исправлениями.",
        agent=developer,
        output_pydantic=CodeOutput,
    )

    # Дублируем тестовые зависимости в requirements-dev.txt для CI
    # (Dockerfile и docker-compose не используются в CI, но должны быть консистентны)
    devops_context = """
    Предыдущие этапы завершены. Архитектура, код и тесты написаны.
    Тебе нужно упаковать решение в Docker и настроить CI/CD.

    ИНФОРМАЦИЯ О ЗАВИСИМОСТЯХ:
    Разработчик должен был создать requirements.txt и requirements-dev.txt.
    Если requirements-dev.txt отсутствует — СОЗДАЙ его, прочитав все импорты в tests/.
    Типичные test-зависимости: pytest, httpx, pytest-asyncio, aiosqlite, freezegun.

    В CI (.github/workflows/ci.yml) устанавливай ОБА:
    pip install -r requirements.txt -r requirements-dev.txt
    """

    docker_task = Task(
        description=f"""{devops_context}

        Упакуй готовое решение в Docker и настрой CI/CD.

        ВАЖНО — ФОРМАТ ОТВЕТА:
        Верни JSON с полем files — массив объектов с path и content.
        Пример: {{"files": [{{"path": "Dockerfile", "content": "FROM python:3.11..."}}]}}

        ЧТО СДЕЛАТЬ (только инфраструктура, код уже есть):
        - Dockerfile (multi-stage build)
        - docker-compose.yml (все сервисы)
        - .github/workflows/ci.yml (GitHub Actions CI/CD)

        НЕ генерируй: README.md, .env.example, .gitignore — они уже есть от Разработчика.
        Сфокусируйся только на Docker и CI.

        ПАТТЕРНЫ DOCKER И CI/CD (обязательно следуй):
        {_patterns['docker']}

        ВАЖНО — CI/CD (.github/workflows/ci.yml):
        - actions/setup-python@v5, python 3.12
        - Установка: python -m venv .venv && pip install -r requirements.txt && pip install -r requirements-dev.txt
        - Тесты: .venv/bin/pytest tests/ -v --tb=short
        - БЕЗ || true — тесты должны падать честно
        - Триггеры: push на master и ai-team/**, pull_request на master
        - Добавь build job: docker build если есть Dockerfile

        КРИТИЧНО — PYTHONPATH:
        В корне проекта ДОЛЖЕН быть pytest.ini или conftest.py с настройкой pythonpath.
        ПРАВИЛЬНЫЙ формат pytest.ini (секция [pytest], не [tool:pytest]):
        [pytest]
        pythonpath = .
        testpaths = tests
        Без этого pytest не найдёт модули app/ в CI.

        КРИТИЧНО — ЗАВИСИМОСТИ ДЛЯ ТЕСТОВ:
        Разработчик ДОЛЖЕН был создать requirements-dev.txt со всеми test-зависимостями.
        Если его нет — СОЗДАЙ сам, прочитав все импорты в tests/. Типичные: pytest, httpx,
        pytest-asyncio, aiosqlite. В CI устанавливай ОБА файла: -r requirements.txt -r requirements-dev.txt.
        Если тест импортирует модуль, которого нет ни в одном requirements — CI упадёт.

        ВАЖНО — Dockerfile:
        - Копируй ВЕСЬ код приложения (app/, tests/, и т.д.)
        - ОБЯЗАТЕЛЬНО добавь COPY tests/ ./tests/ — тесты должны быть в образе
        - Установи pytest и все тестовые зависимости

        ПРАВИЛА:
        - Не используй latest-теги — фиксируй версии
        - Не копируй .env в образ
        - Используй не-root пользователя в контейнере
        - НЕ указывай version в docker-compose.yml (Compose V2 не требует)
        """,
        expected_output="JSON с полем files — Dockerfile, docker-compose.yml, .env.example, README.md, CI/CD.",
        agent=devops,
        output_pydantic=CodeOutput,
    )

    return [architecture_doc, coding_task, review_task, fix_task, docker_task]
