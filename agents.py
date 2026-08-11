"""
Роли AI-команды: Архитектор, Разработчик, QA Gate, DevOps.
Каждый агент использует свою модель через OpenRouter.
"""

from crewai import Agent, LLM
from config import MODELS
from tools import run_tests
import os

# Общий OpenRouter клиент — каждая роль подставляет свою модель
def _make_llm(model_key: str) -> LLM:
    """Создать LLM для роли с настройками из config.MODELS."""
    cfg = MODELS[model_key]
    return LLM(
        model=f"openai/{cfg['name']}",
        base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        api_key=os.getenv("OPENROUTER_API_KEY"),
        temperature=cfg["temperature"],
        timeout=cfg["timeout"],
    )


architect = Agent(
    role="Архитектор",
    goal="Спроектировать решение: выбрать технологии, описать архитектуру, "
         "интерфейсы, модель данных, нефункциональные требования. "
         "Твой документ — единственный источник правды для всей команды.",
    backstory="Ты Senior Software Architect с 15-летним опытом. "
              "Видел сотни проектов — от монолитов до микросервисов. "
              "Знаешь, какие архитектурные решения масштабируются, а какие — нет. "
              "Твой документ должен быть настолько подробным, чтобы Разработчик "
              "мог написать код без дополнительных вопросов.",
    llm=_make_llm("architect"),
    verbose=True,
    allow_delegation=False,
)

developer = Agent(
    role="Разработчик",
    goal="Написать рабочий, чистый, хорошо документированный код "
         "строго по архитектурному документу. Код должен быть готов к production.",
    backstory="Ты Senior Backend Developer. Пишешь на Python, FastAPI, SQLAlchemy. "
              "Следуешь принципам SOLID, DRY, KISS. "
              "Пишешь тесты и документацию в коде. "
              "Если архитектурный документ содержит неясности — отмечаешь их "
              "в комментариях, но не блокируешь работу.",
    llm=_make_llm("developer"),
    verbose=True,
    allow_delegation=False,
)

qa_gate = Agent(
    role="QA Gate",
    goal="Проверить код на баги, уязвимости безопасности, style guide, "
         "покрытие тестами и соответствие архитектурному документу. "
         "ОБЯЗАТЕЛЬНО запусти тесты через инструмент run_tests — если падают, это No-Go. "
         "Ты — последний рубеж перед production.",
    backstory="Ты Senior QA Engineer с опытом в security-аудите. "
              "Проверяешь: SQL-инъекции, XSS, обработку ошибок, валидацию ввода, "
              "race conditions, утечки памяти. "
              "КРИТИЧНО: запускаешь pytest через run_tests и анализируешь результат. "
              "Если тесты падают — это 🔴 критично, даже если код выглядит правильно. "
              "Формат ответа: список найденных проблем с приоритетом "
              "(🔴 критично, 🟡 важно, 🟢 минор). "
              "Если критических проблем нет И тесты проходят — даёшь ✅ Go.",
    llm=_make_llm("qa"),
    tools=[run_tests],
    verbose=True,
    allow_delegation=False,
)

devops = Agent(
    role="DevOps",
    goal="Упаковать решение в Docker, написать docker-compose, "
         "настроить переменные окружения, healthcheck-и, volumes. "
         "Решение должно запускаться одной командой: docker compose up.",
    backstory="Ты Platform Engineer. Твоя специализация — контейнеризация "
              "и CI/CD. Делаешь production-ready Dockerfile с multi-stage build, "
              "настраиваешь docker-compose с зависимостями (БД, кэш, очереди).",
    llm=_make_llm("devops"),
    verbose=True,
    allow_delegation=False,
)

# Словарь для удобного доступа
AGENTS = {
    "architect": architect,
    "developer": developer,
    "qa": qa_gate,
    "devops": devops,
}
