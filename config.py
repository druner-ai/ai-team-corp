"""
AI Team Configuration — модели, роли, параметры.
Версия 1.0.0 (2026-08-10).
"""

import os

VERSION = "1.0.0"

# Модели через OpenRouter.
# Цены за 1M токенов (вход/выход) сверены с https://openrouter.ai/api/v1/models
# 2026-08-12. До этой сверки в конфиге стояли цифры, разошедшиеся с прайсом по
# всем ролям сразу: архитектор был завышен втрое (1.40/4.40 против 0.49/1.54),
# deepseek занижен в 2.7 раза (0.44/0.87 против 1.168/2.336), а devops имел
# третью цену (0.69/1.37) при той же модели, что и разработчик. Из-за этого
# стоимость всех 26 прогонов была занижена в среднем на 28%.
# Цены обновляются на старте прогона из API (main._refresh_prices), эти
# значения — запасные на случай недоступности OpenRouter.
MODELS = {
    "architect": {
        "name": "z-ai/glm-5.2",
        "temperature": 0.3,
        "timeout": 120,
        "price_per_1m": (0.49, 1.54),  # (input, output)
    },
    "developer": {
        "name": "deepseek/deepseek-v4-pro",
        "temperature": 0.1,
        "timeout": 180,
        "price_per_1m": (1.168, 2.336),
    },
    "qa": {
        # codestral-2508 дважды не вызвал run_tests и сочинил отчёт о
        # несуществующих проблемах (прогон 20260812_095229: заявил об
        # отсутствии tests/, pytest.ini и requirements-dev.txt, которые
        # лежали на месте). Роль требует надёжного вызова инструментов.
        "name": "deepseek/deepseek-v4-pro",
        "temperature": 0.2,
        "timeout": 120,
        "price_per_1m": (1.168, 2.336),
    },
    "devops": {
        "name": "deepseek/deepseek-v4-pro",
        "temperature": 0.0,
        "timeout": 60,
        "price_per_1m": (1.168, 2.336),
    },
    # UX/UI дизайнер проектирует интерфейс (design.md + styles.css + index.html).
    # Kimi силён в HTML/CSS/вёрстке; цена сверена с OpenRouter 2026-08-13.
    "ux_designer": {
        "name": "moonshotai/kimi-k2.7-code",
        "temperature": 0.6,
        "timeout": 120,
        "price_per_1m": (0.67, 3.4),
    },
    # Дешёвая модель для всех ролей после превышения soft-порога бюджета.
    "fallback": {
        "name": "deepseek/deepseek-v4-flash",
        "temperature": 0.1,
        "timeout": 180,
        "price_per_1m": (0.14, 0.28),
    },
}

# Fallback-модель для всех ролей при переборе бюджета
FALLBACK_MODEL = MODELS["fallback"]["name"]

# Состав моделей по фазам — для честной атрибуции стоимости.
# CrewAI отдаёт токены на весь kickoff, без разбивки по задачам (в TaskOutput
# полей с токенами нет), поэтому вес роли внутри фазы — доля её задач.
# Фаза A: архитектура (architect), тесты и код (developer), ревю (qa).
PHASE_MODEL_WEIGHTS = {
    "A": {"architect": 1 / 4, "developer": 2 / 4, "qa": 1 / 4},
    # Фаза A разбита на A1 (только спека) и A2 (тесты, код, ревю), поэтому
    # у них разный состав моделей. Test Designer идёт на модели developer:
    # отдельного ключа test_designer в MODELS нет.
    "A1": {"architect": 1.0},
    "A1F": {"architect": 1.0},
    "A1D": {"ux_designer": 1.0},
    "A2": {"developer": 2 / 3, "qa": 1 / 3},
    "B": {"developer": 1.0},
    "C": {"devops": 1.0},
    "D": {"architect": 1.0},   # арбитр работает на модели архитектора
    "D2": {"developer": 1.0},  # доводка после арбитра — снова разработчик
}

# Два порога бюджета на прогон.
# Мягкий: следующая фаза идёт на дешёвой модели. Жёсткий: прогон останавливается
# с сохранением артефактов. Раньше был один MAX_BUDGET_USD = 0.15, который
# проверялся после всей работы и влиял ровно на пропуск деплоя: самый дорогой
# прогон стоил $0.4395, то есть 293% лимита, и лимит не остановил ничего.
# Переопределяются окружением: пороги нужно уметь проверять на дешёвом прогоне,
# не правя код, и уметь опустить на конкретном запуске.
SOFT_BUDGET_USD = float(os.getenv("AI_TEAM_SOFT_BUDGET_USD", "0.15"))
HARD_BUDGET_USD = float(os.getenv("AI_TEAM_HARD_BUDGET_USD", "0.30"))

# Максимум попыток починить локально красные тесты (фаза B до PR).
# Заменил MAX_REVIEW_CYCLES, который импортировался, но нигде не читался:
# цикла правок до этого не было вовсе — fix выполнялся ровно один раз и вслепую.
MAX_FIX_ATTEMPTS = 2

# Максимум попыток доводки ПОСЛЕ арбитра (фаза D2): арбитр может отдать
# правку, которая сама не проходит тесты (пропущенный import, pydantic v1).
# Даём разработчику ещё пару попыток починить код арбитра, не трогая tests/.
MAX_ARBITER_FIX_ATTEMPTS = 2

# Максимум попыток исправить падающий CI (CI fix loop)
MAX_CI_FIX_ATTEMPTS = 3

# Таймаут одного теста (pytest --timeout). Зависший тест = красный гейт, а не
# краш оркестратора (subprocess.TimeoutExpired). Переопределяется окружением.
TEST_TIMEOUT = int(os.getenv("AI_TEAM_TEST_TIMEOUT", "120"))

# ─── Лимиты прогона — единый источник правды (Loop Engineering) ──
# Все ограничения в одном месте: бюджет, попытки, таймаут. Агенты должны
# знать свои границы (сколько попыток осталось, какой таймаут), а не получать
# молчаливый обрыв. Плоские имена выше — обратная совместимость для импортов.
LIMITS = {
    "soft_budget_usd": SOFT_BUDGET_USD,
    "hard_budget_usd": HARD_BUDGET_USD,
    "max_fix_attempts": MAX_FIX_ATTEMPTS,
    "max_arbiter_fix_attempts": MAX_ARBITER_FIX_ATTEMPTS,
    "max_ci_fix_attempts": MAX_CI_FIX_ATTEMPTS,
    "test_timeout_seconds": TEST_TIMEOUT,
}

# Выходная директория для артефактов
OUTPUT_DIR = "output"
