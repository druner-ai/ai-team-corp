#!/usr/bin/env python3
"""
AI Team Corporation v2.0 — оркестратор AI-команды разработки.

Архитектор (GLM-5.2) → Разработчик (DeepSeek V4 Pro) + QA архитектуры (параллельно)
    → QA кода (Codestral 2508) → правки (макс 1 цикл) → DevOps (DeepSeek V4 Pro)

v2.0:
- output_pydantic (JSON) вместо regex markdown-парсинга
- _write_file_safe: единая функция записи с обработкой коллизий
- JSON-first extraction, regex-fallback

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

_all_outputs: list[tuple[str, str, str, dict]] = []  # (task_name, agent_role, raw_output, json_dict)
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
    _all_outputs.append((task_name, agent_role, raw_output, json_output))

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

def _write_file_safe(run_dir: Path, filepath: str, content: str, overwrite: bool = False) -> Path | None:
    """Безопасно записать файл, обрабатывая коллизии имён."""
    # Нормализуем путь
    if filepath.startswith("path/to/"):
        filepath = filepath.replace("path/to/", "", 1)
    filepath = filepath.strip("`*\"'")

    full_path = run_dir / filepath

    # Пропускаем директории
    if full_path.is_dir():
        return None
    # Файл уже существует
    if full_path.exists() and full_path.is_file():
        if overwrite:
            full_path.write_text(content)
            return full_path
        alt = str(full_path) + ".collision"
        Path(alt).write_text(content)
        return Path(alt)

    # Создаём родительские директории
    try:
        full_path.parent.mkdir(parents=True, exist_ok=True)
    except FileExistsError:
        # Какой-то из предков — файл. Переименовываем.
        for ancestor in full_path.parents:
            if ancestor.is_file():
                ancestor.rename(str(ancestor) + ".file")
                break
        full_path.parent.mkdir(parents=True, exist_ok=True)

    full_path.write_text(content)
    return full_path


def _extract_files_json(raw_output: str, run_dir: Path) -> dict[str, Path]:
    """Извлечь файлы из JSON-вывода (output_pydantic). Возвращает {} если не JSON."""
    saved = {}
    try:
        data = json.loads(raw_output)
    except (json.JSONDecodeError, TypeError):
        return saved

    files = data.get("files", [])
    if not isinstance(files, list):
        return saved

    for entry in files:
        if not isinstance(entry, dict):
            continue
        filepath = entry.get("path", "")
        content = entry.get("content", "")
        if not filepath or not content:
            continue
        result = _write_file_safe(run_dir, filepath, content, overwrite=True)
        if result:
            saved[filepath] = result

    return saved


def _extract_files(text: str, run_dir: Path) -> dict[str, Path]:
    """Извлечь файлы: сначала пробуем JSON, затем regex-парсинг markdown."""
    # Сначала JSON (output_pydantic)
    saved = _extract_files_json(text, run_dir)
    if saved:
        return saved

    # Fallback: regex-парсинг markdown блоков
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
        # Пропускаем однобуквенные имена и JSON-артефакты
        if len(filepath) <= 2 or filepath in "[]{}":
            continue
        # Пропускаем мусор: версии зависимостей, разделители, HTTP-статусы, box-drawing
        if any(c in filepath for c in (">=", "==", ">", "<")) or filepath in ("---", "..."):
            continue
        if filepath.startswith("HTTP/") or filepath.startswith("┌") or filepath.startswith("│") or filepath.startswith("└"):
            continue
        if filepath.endswith("/") or "┐" in filepath or "┘" in filepath:
            continue
        if not any(c.isalpha() for c in filepath.replace("/", "").replace(".", "").replace("-", "").replace("_", "")):
            continue
        if len(content) < 20:
            continue

        result = _write_file_safe(run_dir, filepath, content)
        if result:
            saved[filepath] = result

    return saved


def save_all_artifacts(run_dir: Path) -> dict[str, Path]:
    """Извлечь файлы из ВСЕХ сохранённых выводов задач."""
    all_files = {}
    for i, (task_name, agent_role, raw_output, json_dict) in enumerate(_all_outputs):
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
    for i, (task_name, agent_role, raw_output, json_dict) in enumerate(_all_outputs):
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
        # Находим имя сервиса приложения (не db/redis/postgres)
        services = subprocess.run(
            "docker compose config --services 2>/dev/null",
            shell=True, cwd=str(project_dir),
            capture_output=True, text=True, timeout=10
        )
        app_service = None
        infra = {"db", "redis", "postgres", "postgresql", "cache", "broker"}
        for svc in services.stdout.strip().split("\n"):
            if svc and svc.lower() not in infra:
                app_service = svc
                break

        if app_service:
            container = subprocess.run(
                f"docker compose ps -q {app_service} 2>/dev/null",
                shell=True, cwd=str(project_dir),
                capture_output=True, text=True, timeout=10
            )
            app_container = container.stdout.strip()
        else:
            app_container = ""

        if app_container:
            r = subprocess.run(
                f"docker exec {app_container} pytest tests/ -v --tb=short 2>&1",
                shell=True, capture_output=True, text=True, timeout=120
            )
            output = r.stdout.strip()
            # Если тестов нет в контейнере — запускаем с хоста
            if "file or directory not found: tests/" in output or "no tests ran" in output.lower():
                report_lines.append("(тестов нет в контейнере — запускаю с хоста)")
                host_tests = (run_dir / "tests").exists()
                if host_tests:
                    r2 = subprocess.run(
                        f"cd {run_dir} && PYTHONPATH=. {sys.executable} -m pytest tests/ -v --tb=short 2>&1",
                        shell=True, capture_output=True, text=True, timeout=120
                    )
                    report_lines.append(r2.stdout.strip()[:2000])
                    if r2.stderr.strip():
                        report_lines.append("--- stderr ---")
                        report_lines.append(r2.stderr.strip()[:500])
                    test_passed = (r2.returncode == 0)
                else:
                    report_lines.append("⚠️ tests/ не найден ни в контейнере, ни на хосте")
                    test_passed = False
            else:
                report_lines.append(output[:2000])
                if r.stderr.strip():
                    report_lines.append("--- stderr ---")
                    report_lines.append(r.stderr.strip()[:500])
                test_passed = (r.returncode == 0)
        else:
            report_lines.append(f"⚠️ Контейнер приложения не найден (сервис: {app_service or '—'})")
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
            if not name.startswith("task_") and name != "REPORT.md":
                print(f"     {name}")

    # ── Создать Pull Request ────────────────────────────────────
    pr_url = None
    if status == "✅ Успешно":
        pr_url = create_pr_from_run(run_dir, task, timestamp, metrics, deploy_report)


def create_pr_from_run(run_dir: Path, task: str, timestamp: str,
                       metrics: dict | None = None, deploy_report: str = "") -> str | None:
    """Создать ветку, запушить код и открыть PR."""
    import subprocess
    import shutil

    branch = f"ai-team/{timestamp}"
    title = task[:80] + ("..." if len(task) > 80 else "")

    # Собираем статистику
    metrics = metrics or {}
    code_lines = _count_code_lines(run_dir)
    file_list = _list_code_files(run_dir)
    test_status = "❌" if "❌" in deploy_report else ("✅" if deploy_report else "—")
    deploy_ok = "✅" if deploy_report and "❌" not in deploy_report else ("❌" if deploy_report else "—")

    try:
        # 0. Сохраняем текущие изменения перед переключением
        subprocess.run(["git", "stash", "--include-untracked"], capture_output=True, timeout=10)

        # 1. Создаём ветку от master
        subprocess.run(["git", "checkout", "master"], capture_output=True, timeout=10)
        subprocess.run(["git", "checkout", "-b", branch], capture_output=True, timeout=10)

        # 2. Копируем сгенерированный код (только код, не отчёты)
        code_files = [
            f for f in run_dir.rglob("*")
            if f.is_file()
            and not f.name.startswith("task_")
            and f.name != "REPORT.md"
            and f.name not in (".env", ".env.example", ".gitignore")
            and "__pycache__" not in str(f)
            and ".venv" not in str(f)
        ]
        for src in code_files:
            rel = src.relative_to(run_dir)
            dst = Path.cwd() / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

        # 3. Коммитим
        subprocess.run(["git", "add", "-A"], capture_output=True, timeout=10)
        commit_msg = f"🤖 AI-команда: {title}"
        r = subprocess.run(
            ["git", "commit", "-m", commit_msg],
            capture_output=True, text=True, timeout=10
        )
        if "nothing to commit" in r.stdout + r.stderr:
            print(f"\n⚠️ Нет изменений для PR")
            subprocess.run(["git", "checkout", "master"], capture_output=True, timeout=10)
            subprocess.run(["git", "branch", "-D", branch], capture_output=True, timeout=10)
            subprocess.run(["git", "stash", "pop"], capture_output=True, timeout=10)
            return None

        # 4. Пушим
        push_result = subprocess.run(
            ["git", "push", "-u", "origin", branch],
            capture_output=True, text=True, timeout=30
        )
        if push_result.returncode != 0:
            print(f"\n⚠️ Push failed: {push_result.stderr[:200]}")

        # 5. Создаём PR с богатым описанием
        from gh_pr import create_pr
        body = f"""## 🤖 AI-команда

**Задача:** {task}

### 📊 Результаты

| Параметр | Значение |
|----------|----------|
| ⏱️ Время | {metrics.get('duration', 0):.1f} сек |
| 💰 Цена | ${metrics.get('cost', 0):.4f} |
| 📝 Токенов | {metrics.get('tokens_in', 0):,} → {metrics.get('tokens_out', 0):,} |
| 📁 Файлов | {len(file_list)} |
| 📄 Строк кода | {code_lines} |
| 🧪 Тесты | {test_status} |
| 🐳 Деплой | {deploy_ok} |

### 🏗️ Модели

{metrics.get('models', '—')}

### 📁 Сгенерированные файлы

{file_list}

---
*Ветка `{branch}` • Отчёт `{run_dir}/REPORT.md`*
"""
        pr_url = create_pr(branch, f"🤖 {title}", body)
        if pr_url:
            print(f"\n🔀 PR создан: {pr_url}")

        # Возвращаемся на master и восстанавливаем stash
        subprocess.run(["git", "checkout", "master"], capture_output=True, timeout=10)
        subprocess.run(["git", "stash", "pop"], capture_output=True, timeout=10)
        return pr_url

    except Exception as e:
        print(f"\n⚠️ Ошибка создания PR: {e}")
        subprocess.run(["git", "checkout", "master"], capture_output=True, timeout=10)
        subprocess.run(["git", "branch", "-D", branch], capture_output=True, timeout=10)
        subprocess.run(["git", "stash", "pop"], capture_output=True, timeout=10)
        return None


def _count_code_lines(run_dir: Path) -> int:
    """Посчитать строки в сгенерированном коде."""
    total = 0
    for f in run_dir.rglob("*"):
        if f.is_file() and f.suffix in (".py", ".js", ".ts", ".sql", ".yaml", ".yml", ".toml"):
            if "__pycache__" not in str(f) and ".venv" not in str(f):
                try:
                    total += len(f.read_text().splitlines())
                except Exception:
                    pass
    return total


def _list_code_files(run_dir: Path) -> str:
    """Список файлов для PR description."""
    files = []
    for f in sorted(run_dir.rglob("*")):
        if f.is_file() and not f.name.startswith("task_") and f.name != "REPORT.md":
            if "__pycache__" not in str(f) and ".venv" not in str(f):
                rel = f.relative_to(run_dir)
                ext = f.suffix.lstrip(".") or "file"
                files.append(f"`{rel}`")
    if not files:
        return "—"
    return "\n".join(files[:30]) + ("\n..." if len(files) > 30 else "")


if __name__ == "__main__":
    main()
