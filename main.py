#!/usr/bin/env python3
"""
AI Team Corporation — оркестратор AI-команды разработки.

Архитектор (GLM-5.2) → Разработчик (DeepSeek V4 Pro) + QA архитектуры (параллельно)
    → QA кода (DeepSeek Flash) → правки (макс 1 цикл) → DevOps (DeepSeek Flash)

Использование:
    uv run python main.py "Создай REST API для блога..."

Или через stdin:
    echo "Задача..." | uv run python main.py
"""

import sys
import time
import os
import re
import signal
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
load_dotenv("/home/deploy/hermes/data/.env")  # единый источник ключей
from crewai import Crew, Process

from config import MODELS, FALLBACK_MODEL, MAX_BUDGET_USD, MAX_REVIEW_CYCLES, OUTPUT_DIR, VERSION
from agents import architect, developer, qa_gate, devops
from tasks import make_tasks

# ─── budget tracker ────────────────────────────────────────────

class BudgetExceeded(Exception):
    pass

_estimated_cost = 0.0

def _track_tokens(text_in: str, text_out: str, model_key: str) -> None:
    """Примерный подсчёт стоимости и проверка бюджета."""
    global _estimated_cost
    price_in, price_out = MODELS[model_key]["price_per_1m"]
    tokens_in = len(text_in) / 4
    tokens_out = len(text_out) / 4
    cost = (tokens_in / 1_000_000) * price_in + (tokens_out / 1_000_000) * price_out
    _estimated_cost += cost

    if _estimated_cost > MAX_BUDGET_USD:
        raise BudgetExceeded(
            f"Бюджет ${MAX_BUDGET_USD:.2f} превышен (${_estimated_cost:.4f}). "
            f"Остановка."
        )


# ─── artifact saver ────────────────────────────────────────────

def save_artifacts(result: str, run_dir: Path) -> dict[str, Path]:
    """Извлечь файлы из markdown-блоков и сохранить на диск."""
    saved = {}
    # Ищем блоки: ```python path/to/file.py ... ``` или ```dockerfile path/Dockerfile ... ```
    pattern = re.compile(
        r'```(?:python|dockerfile|yaml|yml|json|toml|env|markdown|md|text|sql|sh|bash)?\s+(\S+)\n(.*?)```',
        re.DOTALL
    )
    for match in pattern.finditer(result):
        filepath = match.group(1).strip()
        content = match.group(2).strip()
        # Пропускаем явно не-файловые метки
        if filepath in ("python", "dockerfile", "yaml", "json", "markdown", "bash"):
            continue
        full_path = run_dir / filepath
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content)
        saved[filepath] = full_path

    return saved


def save_report(result: str, run_dir: Path, metrics: dict) -> Path:
    """Сохранить полный отчёт с метриками."""
    report_path = run_dir / "REPORT.md"
    report = f"""# AI Team — Отчёт о выполнении

**Дата:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Версия конфигурации:** {VERSION}

## Метрики

| Параметр | Значение |
|----------|----------|
| Время выполнения | {metrics['duration']:.1f} сек |
| Токенов (вход) | ~{metrics['tokens_in']} |
| Токенов (выход) | ~{metrics['tokens_out']} |
| Примерная цена | ${metrics['cost']:.4f} |
| Модели | {metrics['models']} |
| Статус | {metrics['status']} |

## Полный вывод команды

{result}
"""
    report_path.write_text(report)
    return report_path


# ─── signal handler ────────────────────────────────────────────

def _signal_handler(signum, frame):
    print(f"\n⏹️ Получен сигнал {signum}. Завершение...")
    sys.exit(0)

signal.signal(signal.SIGTERM, _signal_handler)
signal.signal(signal.SIGINT, _signal_handler)


# ─── main ──────────────────────────────────────────────────────

def validate_task(task: str) -> str | None:
    """Вернуть ошибку если задача слишком короткая, иначе None."""
    if len(task.strip()) < 50:
        return (
            "❌ Задача слишком короткая (нужно минимум 50 символов).\n"
            "Опиши: цель, технологии, ограничения, ожидаемый результат."
        )
    return None


def main():
    # ── читаем задачу ──────────────────────────────────────────
    if len(sys.argv) > 1:
        task = " ".join(sys.argv[1:])
    elif not sys.stdin.isatty():
        task = sys.stdin.read().strip()
    else:
        print("Использование: uv run python main.py 'описание задачи...'")
        print("Или: echo 'задача' | uv run python main.py")
        sys.exit(1)

    error = validate_task(task)
    if error:
        print(error)
        sys.exit(1)

    print(f"╔══════════════════════════════════════════════╗")
    print(f"║        🏗️  AI Team Corporation v{VERSION}        ║")
    print(f"╠══════════════════════════════════════════════╣")
    print(f"║  Архитектор:  {MODELS['architect']['name']}")
    print(f"║  Разработчик: {MODELS['developer']['name']}")
    print(f"║  QA Gate:     {MODELS['qa']['name']}")
    print(f"║  DevOps:      {MODELS['devops']['name']}")
    print(f"║  Бюджет:      ${MAX_BUDGET_USD:.2f}")
    print(f"╚══════════════════════════════════════════════╝")
    print(f"\n📋 Задача: {task[:200]}{'...' if len(task) > 200 else ''}\n")

    # ── создаём директорию для этого запуска ───────────────────
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = Path(OUTPUT_DIR) / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)

    # ── запускаем команду ──────────────────────────────────────
    start_time = time.time()
    tasks = make_tasks(task)

    crew = Crew(
        agents=[architect, developer, qa_gate, devops],
        tasks=tasks,
        process=Process.sequential,  # Архитектор → Разработчик → QA → DevOps
        verbose=True,
    )

    try:
        result = crew.kickoff()
        status = "✅ Успешно"
    except BudgetExceeded as e:
        result = str(e)
        status = "💰 Бюджет превышен"
    except Exception as e:
        result = f"❌ Ошибка выполнения: {type(e).__name__}: {e}"
        status = f"❌ Ошибка: {type(e).__name__}"

    duration = time.time() - start_time

    # ── метрики ────────────────────────────────────────────────
    result_str = str(result)
    tokens_in = len(task) // 4
    tokens_out = len(result_str) // 4

    metrics = {
        "duration": duration,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "cost": _estimated_cost,
        "models": ", ".join(
            f"{k}={v['name'].split('/')[1]}" for k, v in MODELS.items()
        ),
        "status": status,
    }

    # ── сохраняем артефакты ────────────────────────────────────
    saved_files = save_artifacts(result_str, run_dir)
    report_path = save_report(result_str, run_dir, metrics)

    # ── вывод ──────────────────────────────────────────────────
    print(f"\n{'─' * 54}")
    print(f"📊 Метрики выполнения")
    print(f"{'─' * 54}")
    print(f"  Статус:         {status}")
    print(f"  Время:          {duration:.1f} сек")
    print(f"  Токенов вход:   ~{tokens_in}")
    print(f"  Токенов выход:  ~{tokens_out}")
    print(f"  Цена:           ${_estimated_cost:.4f}")
    print(f"  Артефактов:     {len(saved_files)} файлов")
    print(f"  Отчёт:          {report_path}")
    if saved_files:
        print(f"\n  📁 Сохранённые файлы:")
        for name, path in sorted(saved_files.items()):
            print(f"     {name}")


if __name__ == "__main__":
    main()
