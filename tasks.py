"""
Задачи для каждой роли AI-команды.
v3.0 — TDD: Test Designer пишет тесты ДО кода, Разработчик пишет код под тесты.
"""

from crewai import Task
from agents import architect, test_designer, developer, qa_gate, devops
from output_models import CodeOutput
from patterns import load_patterns

# Загружаем паттерны один раз при импорте
_patterns = load_patterns()


def make_tasks(task_description: str, run_dir: str = "") -> list[Task]:
    """Создать все задачи для команды на основе входящего описания.

    run_dir — абсолютный путь к директории артефактов прогона.
    Нужен QA Gate, чтобы run_tests получил РЕАЛЬНЫЙ путь, а не выдуманный.
    """

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

    # TDD Этап 1: Test Designer пишет тесты ПО АРХИТЕКТУРЕ, не видя кода
    test_design_task = Task(
        description=f"""
        Ты получил архитектурный документ. Напиши ПОЛНЫЙ набор тестов,
        которые описывают ПОВЕДЕНИЕ системы. Ты НЕ ВИДИШЬ код реализации —
        тесты должны быть независимы от того, как Разработчик напишет код.

        ВАЖНО — ФОРМАТ ОТВЕТА:
        Ты должен вернуть JSON с полем files — массив объектов, каждый с полями path и content.
        Пример:
        {{
          "files": [
            {{"path": "tests/conftest.py", "content": "import pytest\\n..."}},
            {{"path": "tests/test_health.py", "content": "import pytest\\n..."}},
            {{"path": "tests/test_create_url.py", "content": "import pytest\\n..."}}
          ]
        }}

        ПРАВИЛА ДЛЯ ПУТЕЙ:
        - Все тесты в директории tests/
        - conftest.py — fixtures (БД, client)
        - test_*.py — тесты для каждого endpoint
        - Каждый путь ДОЛЖЕН иметь расширение .py

        ПАТТЕРНЫ ТЕСТИРОВАНИЯ (обязательно следуй):
        {_patterns['pytest']}

        ТРЕБОВАНИЯ К ТЕСТАМ:
        - Каждый тест проверяет КОНТРАКТ: "система ДОЛЖНА вернуть X при Y"
        - Проверяй и status code, и JSON response
        - Включи тесты на ошибки (404, 422, 400)
        - conftest.py ДОЛЖЕН инициализировать БД (in-memory SQLite)
        - Используй scope="function" — новая БД на каждый тест
        - Используй app.dependency_overrides для подмены БД
        - НЕ пиши код реализации — только тесты

        КРИТИЧНО — ОЖИДАНИЯ ОТ URL:
        Pydantic HttpUrl автоматически нормализует URL (добавляет trailing slash).
        Вместо проверки точного равенства original_url используй:
          assert data["original_url"].rstrip("/") == "https://example.com"
        Это позволяет тесту пройти с ЛЮБОЙ реализацией (HttpUrl или str).

        КРИТИЧНО — НЕЗАВИСИМОСТЬ:
        Ты НЕ ЗНАЕШЬ, какой код напишет Разработчик. Тесты должны быть
        написаны так, чтобы они проходили с ЛЮБОЙ корректной реализацией,
        которая соответствует архитектурному документу.
        """,
        expected_output="JSON с полем files — тесты (conftest.py + test_*.py) по архитектурному документу.",
        agent=test_designer,
        output_pydantic=CodeOutput,
    )

    # TDD Этап 2: Разработчик пишет код, который ПРОХОДИТ тесты
    coding_task = Task(
        description=f"""
        Напиши код, который ПРОХОДИТ тесты Test Designer'а.
        Тесты — это контракт. Код должен соответствовать контракту, а не наоборот.

        ВАЖНО — ФОРМАТ ОТВЕТА:
        Ты должен вернуть JSON с полем files — массив объектов, каждый с полями path и content.
        Пример:
        {{
          "files": [
            {{"path": "app/main.py", "content": "from fastapi import FastAPI\\n..."}},
            {{"path": "app/urls/router.py", "content": "from fastapi import APIRouter\\n..."}},
            {{"path": "requirements.txt", "content": "fastapi==0.110.0\\n..."}},
            {{"path": "requirements-dev.txt", "content": "pytest==8.0.0\\nhttpx==0.27.0\\n..."}},
            {{"path": "pytest.ini", "content": "[pytest]\\npythonpath = .\\n..."}}
          ]
        }}

        ПРАВИЛА ДЛЯ ПУТЕЙ:
        - Каждый путь ДОЛЖЕН иметь расширение файла (.py, .md, .txt, .json, .yml, .toml)
        - Примеры ПРАВИЛЬНЫХ путей: "app/main.py", "app/urls/router.py", "Dockerfile"
        - Примеры НЕПРАВИЛЬНЫХ: "app" (нет расширения), "notes_api" (нет расширения)
        - КРИТИЧНО: НЕ создавай файл и директорию с ОДНИМ именем
          (например, "app/database.py" и "app/database/" — конфликт!)
        - Если нужен пакет "app/database", создавай ТОЛЬКО директорию "app/database/"
          с файлами внутри (например, "app/database/connection.py", "app/database/__init__.py")
        - Если нужен модуль "app/database", создавай ТОЛЬКО файл "app/database.py"

        ПАТТЕРНЫ АРХИТЕКТУРЫ (обязательно следуй):
        {_patterns['architecture']}

        ТРЕБОВАНИЯ К КОДУ:
        - Код ДОЛЖЕН проходить тесты Test Designer'а — это контракт
        - Если тест требует 201 — возвращай 201, не 200
        - Если тест требует поле 'short_code' — возвращай именно 'short_code'
        - Если тест требует 404 — возвращай 404, не 400
        - Включай requirements.txt (все runtime-зависимости)
        - Включай requirements-dev.txt (все test-зависимости: pytest, httpx, pytest-asyncio, aiosqlite)
        - Включай pytest.ini с секцией [pytest] и pythonpath = .
        - КРИТИЧНО: используй FastAPI dependency injection для БД (Depends(get_db))
        - ЗАПРЕЩЕНО: глобальные переменные для подключения к БД
        - get_db() должна быть generator function (yield, не return)
        - Тесты подменяют БД через app.dependency_overrides — это работает только с DI

        КРИТИЧНО — ЕДИНОЕ ПРИЛОЖЕНИЕ:
        - Создавай РОВНО ОДИН файл app/main.py с FastAPI приложением
        - ВСЕ endpoints определяй в main.py (или подключай роутеры через app.include_router)
        - ЗАПРЕЩЕНО создавать app/routers/ если main.py их не подключает
        - Если используешь роутеры — ОБЯЗАТЕЛЬНО: from app.routers import router; app.include_router(router)
        - ВСЕ endpoints из тестов должны быть доступны: /shorten, /health, /{{short_code}}, /stats/{{short_code}}

        КРИТИЧНО — ТИПЫ URL:
        - Используй str (не HttpUrl) для поля original_url в response
        - HttpUrl нормализует URL (добавляет trailing slash) — это ломает тесты
        - Для request model используй str с валидацией вручную, или HttpUrl но response возвращай str

        КРИТИЧНО — СТАТУС РЕДИРЕКТА:
        - Для redirect endpoint используй status_code=307 (Temporary Redirect)
        - 302 Found семантически неверен для временного редиректа
        - RedirectResponse по умолчанию использует 307 — не переопределяй на 302

        КАЧЕСТВО:
        - Типизация (type hints) на всех публичных функциях
        - Документирующие комментарии к классам и сложным функциям
        - Обработка ошибок (не голые try/except)
        - Валидация входных данных
        """,
        expected_output="JSON с полем files — код проекта, который проходит тесты Test Designer'а.",
        agent=developer,
        output_pydantic=CodeOutput,
    )

    review_task = Task(
        description=f"""
        Проверь, что код Разработчика ПРОХОДИТ тесты Test Designer'а.

        КРИТИЧНО — ЗАПУСК ТЕСТОВ:
        1. Вызови инструмент run_tests с ТОЧНО этим путём: {run_dir}
        2. НЕ выдумывай путь — используй только указанный выше
        3. Проанализируй результат: если есть failed/error — это 🔴 критично
        4. Даже если код выглядит правильно, но тесты падают — это No-Go

        ЧТО ПРОВЕРЯТЬ:
        1. **Запуск тестов**: run_tests с путём {run_dir} — все ли проходят? (ОБЯЗАТЕЛЬНО)
        2. **Соответствие тестам**: код проходит ВСЕ тесты Test Designer'а?
        3. **Безопасность**: SQL-инъекции, XSS, утечки секретов, небезопасные зависимости
        4. **Обработка ошибок**: все ли исключения обработаны? Нет ли голых try/except?
        5. **Валидация**: проверяются ли входные данные на всех endpoint-ах?
        6. **Style guide**: PEP 8, нейминг, типизация

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
        QA Gate нашёл проблемы: код не проходит тесты Test Designer'а.
        Исправь код, чтобы он ПРОХОДИЛ тесты. Тесты — это контракт, не трогай их.

        ВАЖНО — ФОРМАТ ОТВЕТА:
        Верни JSON с полем files — массив ВСЕХ файлов (исправленных + неизменённых).
        Каждый файл: {{"path": "...", "content": "..."}}

        ПРАВИЛА:
        - Исправляй ТОЛЬКО код, НЕ трогай тесты — тесты определяют контракт
        - Если тест требует 201 — возвращай 201
        - Если тест требует поле 'short_code' — возвращай 'short_code'
        - Если тест падает с KeyError — проверь, что возвращаешь все поля из теста
        - Если тест падает с 500 — проверь, что БД инициализирована через DI
        - Если тест падает с 404 на /health — добавь endpoint /health в app/main.py
        - Если тест падает с trailing slash ('https://example.com/' vs 'https://example.com') — используй str вместо HttpUrl
        - Если тест падает с 302 vs 307 — используй status_code=307 для redirect
        - НЕ переписывай код с нуля — точечные правки
        - Верни ПОЛНУЮ кодовую базу (все файлы), а не только исправленные
        - В поле content первого файла добавь комментарий с перечнем исправлений
        - КРИТИЧНО: НЕ изменяй тесты, НЕ добавляй новые тесты, НЕ удаляй существующие
        """,
        expected_output="JSON с полем files — полная кодовая база с исправлениями (тесты не тронуты).",
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
        ПРАВИЛЬНЫЙ формат pytest.ini (секция [pytest], не [tool:pytest] и не [tool.pytest.ini_options]):
        [pytest]
        pythonpath = .
        testpaths = tests
        Без этого pytest не найдёт модули app/ в CI.
        ВАЖНО: [tool.pytest.ini_options] — это для pyproject.toml, НЕ для pytest.ini!

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

    return [architecture_doc, test_design_task, coding_task, review_task, fix_task, docker_task]
