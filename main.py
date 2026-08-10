#!/usr/bin/env python3
"""
AI Team Corporation v1.1 — оркестратор AI-команды разработки.

Архитектор (GLM-5.2) → Разработчик (DeepSeek V4 Pro) + QA архитектуры (параллельно)
    → QA кода (DeepSeek Flash) → правки (макс 1 цикл) → DevOps (DeepSeek Flash)

Фиксы v1.1:
- task_callback: захват вывода КАЖДОЙ задачи (не только последней)
- output_file: сохранение каждой задачи в отдельный файл
- cost: реальный подсчёт токенов из ответов модели
- paths: правильные пути артефактов

Использование:
    uv run python main.py "Создай REST API для блога..."
"""

import sys
import time
import os
import re
import json
import signal
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
load_dotenv("/home/deploy/hermes/data/.env")

from crewai import Crew, Process
from crewai.tasks.task_output import TaskOutput

from config import MODELS, FALLBACK_MODEL, MAX_BUDGET_USD, MAX_REVIEW_CYCLES, OUTPUT_DIR, VERSION
from agents import architect, developer, qa_gate, devops
from tasks import make_tasks

# ─── global state ─────────────────────────────────────────────

_all_outputs: list[tuple[str, str, str]] = []  # (task_name, agent_role, output)
_total_cost: float = 0.0
_total_tokens_in: int = 0
_total_tokens_out: int = 0


# ─── callback: захват вывода каждой задачи ────────────────────

def on_task_complete(output: TaskOutput):
    """Callback — вызывается после каждой завершённой задачи."""
    global _total_cost, _total_tokens_in, _total_tokens_out

    task_name = str(output.task)[:80] if output.task else "unknown"
    agent_role = output.agent.role if output.agent else "unknown"
    raw_output = str(output.raw) if output.raw else ""
    json_output = output.json_dict or {}

    # Сохраняем вывод
    _all_outputs.append((task_name, agent_role, raw_output))

    # Пытаемся достать token usage из ответа модели
    usage = json_output.get("usage") or json_output.get("token_usage") or {}
    tokens_in = usage.get("prompt_tokens", 0) or usage.get("input_tokens", 0)
    tokens_out = usage.get("completion_tokens", 0) or usage.get("output_tokens", 0)

    if tokens_in or tokens_out:
        _total_tokens_in += tokens_in
        _total_tokens_out += tokens_out

        # Определяем модель по роли агента
        model_key = _role_to_model_key(agent_role)
        price_in, price_out = MODELS.get(model_key, MODELS["developer"])["price_per_1m"]
        cost = (tokens_in / 1_000_000) * price_in + (tokens_out / 1_000_000) * price_out
        _total_cost += cost

    # Считаем по символам если API не вернул usage
    else:
        _total_tokens_in += len(str(output.task)) // 4 if output.task else 0
        _total_tokens_out += len(raw_output) // 4


def _role_to_model_key(role: str) -> str:
    role_lower = role.lower()
    if "архитект" in role_lower:
        return "architect"
    elif "разработ" in role_lower:
        return "developer"
    elif "qa" in role_lower:
        return "qa"
    elif "devops" in role_lower:
        return "devops"
    return "developer"


# ─── artifact saver ────────────────────────────────────────────

def _extract_files(text: str, run_dir: Path) -> dict[str, Path]:
    """Извлечь файлы из markdown-блоков с путями."""
    saved = {}
    pattern = re.compile(
        r'```(?:python|dockerfile|yaml|yml|json|toml|env|markdown|md|text|sql|sh|bash)?\s+(\S+)\n(.*?)```',
        re.DOTALL
    )
    for match in pattern.finditer(text):
        filepath = match.group(1).strip()
        content = match.group(2).strip()

        # Пропускаем не-файловые метки
        skip_labels = {"python", "dockerfile", "yaml", "json", "markdown", "bash", "text", "sql", "sh"}
        if filepath in skip_labels or filepath.startswith("http"):
            continue

        # Нормализуем путь
        if filepath.startswith("path/to/"):
            filepath = filepath.replace("path/to/", "", 1)

        full_path = run_dir / filepath
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content)
        saved[filepath] = full_path

    return saved


def save_all_artifacts(run_dir: Path) -> dict[str, Path]:
    """Извлечь файлы из ВСЕХ сохранённых выводов задач."""
    all_files = {}
    for i, (task_name, agent_role, raw_output) in enumerate(_all_outputs):
        extracted = _extract_files(raw_output, run_dir)
        all_files.update(extracted)
        # Также сохраняем сырой вывод каждой задачи
        task_file = run_dir / f"task_{i:02d}_{agent_role.replace(' ', '_')}.md"
        task_file.write_text(f"# {agent_role}\n\n## Задача\n{task_name}\n\n## Результат\n\n{raw_output}")
        all_files[f"task_{i:02d}_{agent_role}.md"] = task_file

    return all_files


def save_report(run_dir: Path, metrics: dict) -> Path:
    """Сохранить финальный отчёт."""
    report_path = run_dir / "REPORT.md"

    # Собираем summary всех задач
    tasks_summary = ""
    for i, (task_name, agent_role, raw_output) in enumerate(_all_outputs):
        preview = raw_output[:300] + "..." if len(raw_output) > 300 else raw_output
        tasks_summary += f"\n### Шаг {i+1}: {agent_role}\n{preview}\n"

    report = f"""# AI Team — Отчёт о выполнении

**Дата:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Версия:** {VERSION}

## Метрики

| Параметр | Значение |
|----------|----------|
| Время выполнения | {metrics['duration']:.1f} сек |
| Токенов (вход) | {metrics['tokens_in']:,} |
| Токенов (выход) | {metrics['tokens_out']:,} |
| Цена | ${metrics['cost']:.4f} |
| Модели | {metrics['models']} |
| Статус | {metrics['status']} |

## Результаты по задачам
{tasks_summary}
"""
    report_path.write_text(report)
    return report_path


# ─── signal handler ────────────────────────────────────────────

def _signal_handler(signum, frame):
    print(f"\n⏹️ Сигнал {signum}. Завершение...")
    sys.exit(0)

signal.signal(signal.SIGTERM, _signal_handler)
signal.signal(signal.SIGINT, _signal_handler)


# ─── main ──────────────────────────────────────────────────────

def validate_task(task: str) -> str | None:
    if len(task.strip()) < 50:
        return "❌ Задача слишком короткая (мин. 50 символов)."
    return None


def main():
    if len(sys.argv) > 1:
        task = " ".join(sys.argv[1:])
    elif not sys.stdin.isatty():
        task = sys.stdin.read().strip()
    else:
        print("Использование: uv run python main.py 'описание задачи...'")
        sys.exit(1)

    error = validate_task(task)
    if error:
        print(error)
        sys.exit(1)

    print(f"╔══════════════════════════════════════════╗")
    print(f"║    🏗️  AI Team Corporation v{VERSION}       ║")
    print(f"╠══════════════════════════════════════════╣")
    print(f"║  Архитектор:  {MODELS['architect']['name']}")
    print(f"║  Разработчик: {MODELS['developer']['name']}")
    print(f"║  QA Gate:     {MODELS['qa']['name']}")
    print(f"║  DevOps:      {MODELS['devops']['name']}")
    print(f"║  Бюджет:      ${MAX_BUDGET_USD:.2f}")
    print(f"╚══════════════════════════════════════════╝")
    print(f"\n📋 Задача: {task[:200]}{'...' if len(task) > 200 else ''}\n")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = Path(OUTPUT_DIR) / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)

    tasks = make_tasks(task)

    crew = Crew(
        agents=[architect, developer, qa_gate, devops],
        tasks=tasks,
        process=Process.sequential,
        task_callback=on_task_complete,
        verbose=True,
    )

    start_time = time.time()
    try:
        result = crew.kickoff()
        status = "✅ Успешно"
    except Exception as e:
        result = str(e)
        status = f"❌ {type(e).__name__}: {e}"

    duration = time.time() - start_time
    result_str = str(result) if result else ""

    metrics = {
        "duration": duration,
        "tokens_in": _total_tokens_in,
        "tokens_out": _total_tokens_out,
        "cost": _total_cost,
        "models": ", ".join(f"{k}={v['name'].split('/')[1]}" for k, v in MODELS.items()),
        "status": status,
    }

    # Сохраняем ВСЕ артефакты из всех задач
    saved_files = save_all_artifacts(run_dir)
    # Сохраняем финальный вывод (DevOps) тоже
    final_extracted = _extract_files(result_str, run_dir)
    saved_files.update(final_extracted)
    report_path = save_report(run_dir, metrics)

    print(f"\n{'─' * 54}")
    print(f"📊 Метрики выполнения")
    print(f"{'─' * 54}")
    print(f"  Статус:         {status}")
    print(f"  Время:          {duration:.1f} сек")
    print(f"  Токенов вход:   {_total_tokens_in:,}")
    print(f"  Токенов выход:  {_total_tokens_out:,}")
    print(f"  Цена:           ${_total_cost:.4f}")
    print(f"  Задач собрано:  {len(_all_outputs)}")
    print(f"  Артефактов:     {len(saved_files)} файлов")
    print(f"  Отчёт:          {report_path}")
    if saved_files:
        print(f"\n  📁 Сохранённые файлы:")
        for name, path in sorted(saved_files.items()):
            print(f"     {name}")


if __name__ == "__main__":
    main()
