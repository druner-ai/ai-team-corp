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

    task_name = output.name or "unknown"
    agent_role = str(output.agent) if output.agent else "unknown"
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
        est_tokens_in = len(task_name) // 4
        est_tokens_out = len(raw_output) // 4
        _total_tokens_in += est_tokens_in
        _total_tokens_out += est_tokens_out

        # Считаем стоимость по оценке
        model_key = _role_to_model_key(agent_role)
        price_in, price_out = MODELS.get(model_key, MODELS["developer"])["price_per_1m"]
        cost = (est_tokens_in / 1_000_000) * price_in + (est_tokens_out / 1_000_000) * price_out
        _total_cost += cost


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

def _is_valid_filepath(filepath: str) -> bool:
    """Проверить, похож ли путь на реальный файл."""
    # Имена без расширения, но с путём
    special_names = {"Dockerfile", "Makefile", "docker-compose.yml", "docker-compose.yaml",
                     ".env.example", ".gitignore", "README.md", "LICENSE", "requirements.txt",
                     "pyproject.toml"}
    if filepath in special_names or filepath.split("/")[-1] in special_names:
        return True
    # Должен содержать / (директорию) или заканчиваться известным расширением
    valid_extensions = {".py", ".md", ".yml", ".yaml", ".toml", ".txt", ".env", ".sh", 
                        ".json", ".cfg", ".ini", ".example", ".sql", ".html", ".css", ".js"}
    has_slash = "/" in filepath
    has_ext = any(filepath.endswith(ext) for ext in valid_extensions)
    if not (has_slash or has_ext):
        return False
    # Не markdown-артефакты
    if filepath.startswith("*") or filepath.startswith("┌") or filepath.startswith("│"):
        return False
    # Не SQL/JSON строки
    if filepath.startswith("DATABASE_URL") or filepath.startswith("{"):
        return False
    if filepath.startswith("@") and not has_slash:
        return False
    return True


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
        if filepath in skip_labels:
            continue
        # Игнорируем слишком короткое содержимое
        if len(content) < 20:
            continue
        # Убираем markdown-разметку из имени файла
        filepath = filepath.strip("`*\"'")
        # Проверяем, похоже ли на реальный путь
        if not _is_valid_filepath(filepath):
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


def save_report(run_dir: Path, metrics: dict, deploy_report: str = "") -> Path:
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

{deploy_report}
"""
    report_path.write_text(report)
    return report_path


# ─── deploy & verify ─────────────────────────────────────────

def deploy_and_verify(run_dir: Path) -> str:
    """DevOps Phase 2: docker compose up, тесты, healthcheck, cleanup."""
    import subprocess
    import shutil
    import tempfile

    # Ищем docker-compose.yml среди сохранённых файлов
    compose_files = list(run_dir.rglob("docker-compose.yml")) + list(run_dir.rglob("docker-compose.yaml"))
    dockerfiles = list(run_dir.rglob("Dockerfile"))

    if not compose_files:
        return "⚠️ docker-compose.yml не найден — деплой пропущен."

    compose_path = compose_files[0]
    project_dir = compose_path.parent

    # Проверяем, что порты 8000, 5432, 6379 свободны
    for port in [8000, 5432, 6379]:
        r = subprocess.run(
            f"ss -tlnp | grep -q ':{port}'", shell=True,
            capture_output=True, timeout=5
        )
        if r.returncode == 0:
            return f"⚠️ Порт {port} занят — деплой пропущен."

    # Проверяем Docker
    r = subprocess.run("which docker 2>/dev/null", shell=True, capture_output=True)
    if r.returncode != 0:
        return "⚠️ Docker не установлен — деплой пропущен."

    report_lines = ["## 🚀 Деплой и верификация\n"]
    start = time.time()

    try:
        # Копируем .env.example → .env если нужно
        env_example = project_dir / ".env.example"
        env_file = project_dir / ".env"
        if env_example.exists() and not env_file.exists():
            shutil.copy(env_example, env_file)
            report_lines.append("📋 .env.example → .env (скопирован)\n")

        # 1. Запускаем сервисы
        report_lines.append("### 1. Запуск сервисов\n```")
        r = subprocess.run(
            "docker compose up -d --wait --wait-timeout 60",
            shell=True, cwd=str(project_dir),
            capture_output=True, text=True, timeout=120
        )
        report_lines.append(r.stdout.strip())
        if r.stderr.strip():
            report_lines.append(r.stderr.strip())
        report_lines.append("```")
        if r.returncode != 0:
            report_lines.append(f"\n❌ docker compose up failed (exit {r.returncode})")

            # Cleanup
            subprocess.run("docker compose down -v 2>/dev/null", shell=True,
                          cwd=str(project_dir), capture_output=True, timeout=30)
            return "\n".join(report_lines)

        # 2. Healthcheck
        time.sleep(5)
        report_lines.append("\n### 2. Healthcheck\n```")
        r = subprocess.run(
            "curl -sf http://localhost:8000/openapi.json | head -c 500",
            shell=True, capture_output=True, text=True, timeout=15
        )
        if r.returncode == 0:
            report_lines.append("✅ Сервис отвечает (OpenAPI JSON)")
            report_lines.append(r.stdout[:300])
        else:
            report_lines.append(f"❌ Сервис не отвечает: {r.stderr[:200]}")
        report_lines.append("```")

        # 3. Прогоняем тесты в контейнере
        report_lines.append("\n### 3. Тесты (pytest в контейнере)\n```")
        container = subprocess.run(
            "docker compose ps -q app 2>/dev/null || docker compose ps -q web 2>/dev/null",
            shell=True, cwd=str(project_dir),
            capture_output=True, text=True, timeout=10
        )
        app_container = container.stdout.strip()

        if app_container:
            r = subprocess.run(
                f"docker exec {app_container} pytest tests/ -v --tb=short 2>&1",
                shell=True, capture_output=True, text=True, timeout=120
            )
            report_lines.append(r.stdout.strip()[:2000])
            if r.stderr.strip():
                report_lines.append("--- stderr ---")
                report_lines.append(r.stderr.strip()[:500])
            test_passed = (r.returncode == 0)
        else:
            report_lines.append("⚠️ Контейнер приложения не найден")
            test_passed = False
        report_lines.append("```")

        duration = time.time() - start
        report_lines.append(f"\n⏱️ Деплой: {duration:.1f} сек | Тесты: {'✅' if test_passed else '❌'}")

        return "\n".join(report_lines)

    except subprocess.TimeoutExpired:
        return "\n".join(report_lines) + "\n❌ Таймаут деплоя (120 сек)"
    except Exception as e:
        return "\n".join(report_lines) + f"\n❌ Ошибка деплоя: {e}"
    finally:
        # Всегда чистим
        subprocess.run(
            "docker compose down -v 2>/dev/null",
            shell=True, cwd=str(project_dir),
            capture_output=True, timeout=30
        )


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

    # ── Сохраняем артефакты ДО деплоя ──────────────────────────
    saved_files = save_all_artifacts(run_dir)
    final_extracted = _extract_files(result_str, run_dir)
    saved_files.update(final_extracted)

    # ── Деплой и верификация (DevOps phase 2) ──────────────────
    deploy_report = ""
    if status == "✅ Успешно":
        deploy_report = deploy_and_verify(run_dir)

    metrics = {
        "duration": duration,
        "tokens_in": _total_tokens_in,
        "tokens_out": _total_tokens_out,
        "cost": _total_cost,
        "models": ", ".join(f"{k}={v['name'].split('/')[1]}" for k, v in MODELS.items()),
        "status": status,
    }

    report_path = save_report(run_dir, metrics, deploy_report)

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
