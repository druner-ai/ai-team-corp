"""
AI Team Configuration — модели, роли, параметры.
Версия 1.0.0 (2026-08-10).
"""

VERSION = "1.0.0"

# Модели через OpenRouter
# Цены за 1M токенов (вход/выход), август 2026
MODELS = {
    "architect": {
        "name": "z-ai/glm-5.2",
        "temperature": 0.3,
        "timeout": 120,
        "max_retry": 2,
        "price_per_1m": (1.40, 4.40),  # (input, output)
    },
    "developer": {
        "name": "deepseek/deepseek-v4-pro",
        "temperature": 0.1,
        "timeout": 180,
        "max_retry": 2,
        "price_per_1m": (0.44, 0.87),
    },
    "qa": {
        "name": "mistralai/codestral-2508",
        "temperature": 0.2,
        "timeout": 90,
        "max_retry": 2,
        "price_per_1m": (0.30, 0.90),
    },
    "devops": {
        "name": "deepseek/deepseek-v4-pro",
        "temperature": 0.0,
        "timeout": 60,
        "max_retry": 2,
        "price_per_1m": (0.69, 1.37),
    },
}

# Fallback-модель для всех ролей при ошибке
FALLBACK_MODEL = "deepseek/deepseek-v4-flash"

# Бюджет на один запуск (стоп, если превышен)
MAX_BUDGET_USD = 0.15

# Максимум циклов ревью (QA → разработчик → правки)
MAX_REVIEW_CYCLES = 1

# Максимум попыток исправить падающий CI (CI fix loop)
MAX_CI_FIX_ATTEMPTS = 3

# Выходная директория для артефактов
OUTPUT_DIR = "output"
