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

from config import MODELS, FALLBACK_MODEL, MAX_BUDGET_USD, MAX_REVIEW_CYCLES, MAX_CI_FIX_ATTEMPTS, OUTPUT_DIR, VERSION
from agents import architect, test_designer, developer, qa_gate, devops
from tasks import make_tasks

# ─── global state ─────────────────────────────────────────────

_all_outputs: list[tuple[str, str, str, dict]] = []  # (task_name, agent_role, raw_output, json_dict)


def _estimate_cost(tokens_in: int, tokens_out: int) -> float:
    """Оценка стоимости по усреднённой цене моделей команды.

    CrewAI возвращает суммарные токены без разбивки по агентам,
    поэтому считаем по средневзвешенной цене всех ролей.
    """
    if not tokens_in and not tokens_out:
        return 0.0
    avg_in = sum(m["price_per_1m"][0] for m in MODELS.values()) / len(MODELS)
    avg_out = sum(m["price_per_1m"][1] for m in MODELS.values()) / len(MODELS)
    return (tokens_in / 1_000_000) * avg_in + (tokens_out / 1_000_000) * avg_out


# ─── callback: захват вывода каждой задачи ────────────────────

def on_task_complete(output: TaskOutput):
    """Callback — вызывается после каждой завершённой задачи."""
    task_name = output.name or "unknown"
    agent_role = str(output.agent) if output.agent else "unknown"
    raw_output = str(output.raw) if output.raw else ""
    json_output = output.json_dict or {}

    # Сохраняем вывод
    _all_outputs.append((task_name, agent_role, raw_output, json_output))


def _write_file_safe(run_dir: Path, filepath: str, content: str, overwrite: bool = False, protect_tests: bool = False, role: str = "") -> Path | None:
    """Безопасно записать файл, обрабатывая коллизии имён и path traversal.

    protect_tests=True — отклонять запись в tests/** (используется на fix/ci-fix
    этапах, чтобы модель не перезаписывала тесты, которые определяют контракт).

    role — whitelist путей по ролям:
    - "test designer": только tests/**
    - "devops": только Dockerfile, docker-compose.yml, .dockerignore, .github/**
    - "разработчик" (fix): всё кроме tests/**
    """
    # Нормализуем путь
    if filepath.startswith("path/to/"):
        filepath = filepath.replace("path/to/", "", 1)
    filepath = filepath.strip("`*\"'")

    # Path traversal guard — отклоняем абсолютные пути и выход за run_dir
    p = Path(filepath)
    if p.is_absolute():
        return None
    full_path = (run_dir / filepath).resolve()
    try:
        full_path.relative_to(run_dir.resolve())
    except ValueError:
        return None

    # Whitelist по ролям
    role_lower = role.lower()
    if "test designer" in role_lower:
        # Test Designer пишет в tests/ + pytest.ini (конфиг для тестов)
        if not (p.parts[0] == "tests" or p.parts[0] == "test" or p.name == "pytest.ini"):
            return None
    elif "devops" in role_lower:
        allowed = {"dockerfile", "docker-compose.yml", ".dockerignore", ".github", ".env.example", "readme.md"}
        if p.parts[0] not in allowed:
            return None
    elif "разработ" in role_lower and protect_tests:
        # fix/ci-fix: не трогаем тесты
        if p.parts[0] == "tests" or p.parts[0] == "test":
            return None

    # Защита тестов: fix/ci-fix не имеют права менять tests/**
    if protect_tests and (p.parts[0] == "tests" or p.parts[0] == "test"):
        return None

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


def _extract_files_json(raw_output: str, run_dir: Path, protect_tests: bool = False, role: str = "") -> dict[str, Path]:
    """Извлечь файлы из JSON-вывода (output_pydantic). Возвращает {} если не JSON.

    Поддерживает два формата:
    1. Чистый JSON в raw_output
    2. JSON, вложенный в markdown (после ## Результат)
    """
    saved = {}
    data = None

    # Пробуем прямой парсинг (чистый JSON)
    try:
        data = json.loads(raw_output)
    except (json.JSONDecodeError, TypeError):
        pass

    # Если не получилось — ищем JSON в тексте
    if data is None:
        import re
        # Сначала пробуем после "## Результат" (если есть)
        result_marker = raw_output.find("## Результат")
        search_text = raw_output[result_marker:] if result_marker != -1 else raw_output

        # Ищем JSON-блок
        match = re.search(r'\{.*\}', search_text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
            except json.JSONDecodeError:
                # Пробуем найти следующий JSON-блок
                remaining = search_text[match.end():]
                match2 = re.search(r'\{.*\}', remaining, re.DOTALL)
                if match2:
                    try:
                        data = json.loads(match2.group())
                    except json.JSONDecodeError:
                        return saved
                else:
                    return saved

    if data is None:
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
        result = _write_file_safe(run_dir, filepath, content, overwrite=True, protect_tests=protect_tests, role=role)
        if result:
            saved[filepath] = result

    return saved

def _extract_files(text: str, run_dir: Path, protect_tests: bool = False, role: str = "", json_dict: dict | None = None) -> dict[str, Path]:
    """Извлечь файлы: сначала пробуем json_dict (если есть), затем JSON в тексте, затем regex."""
    # 1. Если передан json_dict — используем его (самый надёжный источник)
    if json_dict and isinstance(json_dict, dict):
        files = json_dict.get("files", [])
        if isinstance(files, list):
            saved = {}
            for entry in files:
                if not isinstance(entry, dict):
                    continue
                filepath = entry.get("path", "")
                content = entry.get("content", "")
                if not filepath or not content:
                    continue
                result = _write_file_safe(run_dir, filepath, content, overwrite=True, protect_tests=protect_tests, role=role)
                if result:
                    saved[filepath] = result
            if saved:
                return saved

    # 2. Пробуем JSON в тексте
    saved = _extract_files_json(text, run_dir, protect_tests=protect_tests, role=role)
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
    """Извлечь файлы из выводов задач, которые реально производят файлы.

    Каждый этап пишет в собственный подкаталог (stage_02_dev/, stage_04_fix/ и т.д.).
    Финальная сборка — копия последней успешной волны, без объединения с предыдущими.
    Это устраняет проблему наслоения: два conftest.py, мёртвый груз от старых волн.
    """
    all_files = {}
    # Роли, которые реально производят файлы (не Архитектор, не QA)
    FILE_PRODUCING_ROLES = {"test designer", "разработ", "devops"}

    # Маппинг индекса задачи на stage-директорию
    # 0=архитектор, 1=test_designer, 2=разработчик, 3=QA, 4=fix, 5=devops
    STAGE_DIRS = {
        1: "stage_01_tests",
        2: "stage_02_dev",
        4: "stage_04_fix",
        5: "stage_05_devops",
    }

    # Отслеживаем последнюю успешную волну для финальной сборки
    last_wave_dir = None

    for i, (task_name, agent_role, raw_output, json_dict) in enumerate(_all_outputs):
        role_lower = agent_role.lower()
        if not any(role in role_lower for role in FILE_PRODUCING_ROLES):
            # Сохраняем сырой вывод, но не извлекаем файлы
            task_file = run_dir / f"task_{i:02d}_{agent_role.replace(' ', '_')}.md"
            task_file.write_text(f"# {agent_role}\n\n## Задача\n{task_name}\n\n## Результат\n\n{raw_output}")
            all_files[f"task_{i:02d}_{agent_role}.md"] = task_file
            continue

        # Определяем stage-директорию
        stage_name = STAGE_DIRS.get(i, f"stage_{i:02d}_{agent_role.replace(' ', '_')}")
        stage_dir = run_dir / stage_name
        stage_dir.mkdir(parents=True, exist_ok=True)

        # fix_task — защищаем тесты (только index 4, не "fix" в task_name — это срабатывает на "fixtures")
        is_fix_stage = i == 4
        extracted = _extract_files(raw_output, stage_dir, protect_tests=is_fix_stage, role=agent_role, json_dict=json_dict)
        all_files.update(extracted)

        # Запоминаем последнюю волну, которая произвела файлы
        if extracted:
            last_wave_dir = stage_dir

        # Также сохраняем сырой вывод каждой задачи
        task_file = run_dir / f"task_{i:02d}_{agent_role.replace(' ', '_')}.md"
        task_file.write_text(f"# {agent_role}\n\n## Задача\n{task_name}\n\n## Результат\n\n{raw_output}")
        all_files[f"task_{i:02d}_{agent_role}.md"] = task_file

    # Финальная сборка: собираем из ключевых этапов, а не только последней волны.
    # Код (stage_02_dev или stage_04_fix если fix был) + тесты (stage_01_tests) + DevOps (stage_05_devops).
    # Это устраняет проблему наслоения: два conftest.py, мёртвый груз от старых волн.
    final_stages = []

    # Определяем, какой этап содержит код (fix перезаписывает dev)
    code_stage = run_dir / "stage_04_fix" if (run_dir / "stage_04_fix").exists() and any((run_dir / "stage_04_fix").iterdir()) else run_dir / "stage_02_dev"
    if code_stage.exists():
        final_stages.append(code_stage)

    tests_stage = run_dir / "stage_01_tests"
    if tests_stage.exists() and any(tests_stage.iterdir()):
        final_stages.append(tests_stage)

    devops_stage = run_dir / "stage_05_devops"
    if devops_stage.exists():
        final_stages.append(devops_stage)

    for stage in final_stages:
        for item in stage.rglob("*"):
            if item.is_file():
                rel = item.relative_to(stage)
                dest = run_dir / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                import shutil
                shutil.copy2(item, dest)
                all_files[str(rel)] = dest

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

            # Сохраняем логи контейнеров для диагностики
            logs = subprocess.run(
                "docker compose logs --tail 50 2>&1",
                shell=True, cwd=str(project_dir),
                capture_output=True, text=True, timeout=15
            )
            if logs.stdout.strip():
                report_lines.append("\n### 📋 Логи контейнера (последние 50 строк)\n```")
                report_lines.append(logs.stdout.strip()[:3000])
                report_lines.append("```")

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

    tasks = make_tasks(task, run_dir=str(run_dir.resolve()))

    crew = Crew(
        agents=[architect, test_designer, developer, qa_gate, devops],
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

    # ── Реальные метрики от CrewAI (UsageMetrics от провайдеров) ──
    usage = getattr(result, "token_usage", None)
    if usage is not None:
        tokens_in = usage.prompt_tokens or 0
        tokens_out = usage.completion_tokens or 0
    else:
        tokens_in = tokens_out = 0
    cost = _estimate_cost(tokens_in, tokens_out)

    # ── Сохраняем артефакты ДО деплоя ──────────────────────────
    saved_files = save_all_artifacts(run_dir)
    # Финальная сборка: извлекаем из результата Crew (DevOps), передаём json_dict если есть
    final_json = getattr(result, "json_dict", None) or {}
    final_extracted = _extract_files(result_str, run_dir, json_dict=final_json)
    saved_files.update(final_extracted)

    # ── ГЕЙТ: программный запуск тестов перед PR ───────────────
    # Ревью показало: QA-агент 17 прогонов не вызвал run_tests ни разу.
    # Гейт должен быть кодом, не агентом.
    from tools import run_tests_quiet
    tests_green, tests_summary = run_tests_quiet(str(run_dir))
    if not tests_green:
        print(f"\n🔴 ЛОКАЛЬНЫЕ ТЕСТЫ НЕ ПРОШЛИ — PR НЕ СОЗДАЁТСЯ")
        print(f"   См. {run_dir}/tests_output.txt")
        (run_dir / "tests_output.txt").write_text(tests_summary)
        status = "❌ Tests failed"
    else:
        print(f"\n✅ Локальные тесты пройдены")

    # ── Деплой и верификация (DevOps phase 2) ──────────────────
    # Бюджет-гейт: если уже перерасход — пропускаем деплой (экономим ресурсы)
    deploy_report = ""
    if status == "✅ Успешно":
        if cost > MAX_BUDGET_USD:
            deploy_report = f"⚠️ Деплой пропущен: бюджет превышен (${cost:.4f} > ${MAX_BUDGET_USD:.2f})"
            print(f"\n⚠️ Бюджет превышен — деплой пропущен")
        else:
            deploy_report = deploy_and_verify(run_dir)

    metrics = {
        "duration": duration,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "cost": cost,
        "models": ", ".join(f"{k}={v['name'].split('/')[1]}" for k, v in MODELS.items()),
        "status": status,
        "tests_green": tests_green,
    }

    report_path = save_report(run_dir, metrics, deploy_report)

    print(f"\n{'─' * 54}")
    print(f"📊 Метрики выполнения")
    print(f"{'─' * 54}")
    print(f"  Статус:         {status}")
    print(f"  Время:          {duration:.1f} сек")
    print(f"  Токенов вход:   {tokens_in:,}")
    print(f"  Токенов выход:  {tokens_out:,}")
    print(f"  Цена:           ${cost:.4f}")
    if cost > MAX_BUDGET_USD:
        print(f"  ⚠️ БЮДЖЕТ ПРЕВЫШЕН: ${cost:.4f} > ${MAX_BUDGET_USD:.2f}")
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

    # ── CI fix loop: ждём CI, при падении — доработка ──────────
    if pr_url:
        ci_fix_loop(pr_url, run_dir, task, timestamp)


def _wait_for_ci_run(branch: str, timeout: int = 600) -> dict | None:
    """Ждать появления и завершения CI run для ветки. Возвращает run dict или None."""
    import requests

    token = os.getenv("GITHUB_TOKEN")
    if not token:
        return None
    user = os.getenv("GITHUB_USER", "druner-ai")
    repo = os.getenv("GITHUB_REPO", "ai-team-corp")
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}
    api = f"https://api.github.com/repos/{user}/{repo}"

    deadline = time.time() + timeout
    run_id = None

    # Фаза 1: ждём появления run для ветки (до 2 мин)
    while time.time() < deadline and run_id is None:
        try:
            r = requests.get(f"{api}/actions/runs?branch={branch}&per_page=5",
                             headers=headers, timeout=10)
            if r.status_code == 200:
                runs = r.json().get("workflow_runs", [])
                if runs:
                    run_id = runs[0]["id"]
                    print(f"  🔄 CI run {run_id} найден, статус: {runs[0]['status']}")
                    break
        except Exception:
            pass
        time.sleep(10)

    if run_id is None:
        print(f"  ⚠️ CI run для {branch} не появился за 2 мин")
        return None

    # Фаза 2: ждём завершения run
    while time.time() < deadline:
        try:
            r = requests.get(f"{api}/actions/runs/{run_id}", headers=headers, timeout=10)
            if r.status_code == 200:
                run = r.json()
                if run["status"] == "completed":
                    return run
        except Exception:
            pass
        time.sleep(15)

    print(f"  ⚠️ CI run {run_id} не завершился за {timeout} сек")
    return None


def _get_ci_failure_logs(run_id: int, max_chars: int = 6000) -> str:
    """Скачать логи failed-джобов CI run. Возвращает хвост лога (самое важное)."""
    import requests

    token = os.getenv("GITHUB_TOKEN")
    user = os.getenv("GITHUB_USER", "druner-ai")
    repo = os.getenv("GITHUB_REPO", "ai-team-corp")
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}
    api = f"https://api.github.com/repos/{user}/{repo}"

    try:
        # Получаем джобы run-а
        r = requests.get(f"{api}/actions/runs/{run_id}/jobs", headers=headers, timeout=10)
        if r.status_code != 200:
            return ""
        failed_jobs = [j for j in r.json().get("jobs", []) if j.get("conclusion") == "failure"]
        if not failed_jobs:
            return ""

        # Берём лог первой failed-джобы
        job_id = failed_jobs[0]["id"]
        log_r = requests.get(f"{api}/actions/jobs/{job_id}/logs",
                             headers=headers, timeout=20, allow_redirects=True)
        if log_r.status_code != 200:
            return ""

        # Хвост лога — там ошибки
        return log_r.text[-max_chars:]
    except Exception:
        return ""


def _run_ci_fix(arch_doc: str, ci_logs: str, run_dir: Path) -> int:
    """Запустить Разработчика для исправления CI-ошибок. Возвращает кол-во новых файлов.

    Вместо arch_doc[:2000] передаём файлы, упомянутые в traceback + весь tests/.
    Это дешевле полной базы и точнее — убирает шум.
    """
    from crewai import Task, Crew, Process
    from output_models import CodeOutput
    from tasks import make_tasks

    # Извлекаем файлы из traceback (строки вида File "path/to/file.py")
    import re
    traceback_files = set()
    for match in re.finditer(r'File "([^"]+\.py)"', ci_logs):
        path = match.group(1)
        # Нормализуем: убираем абсолютный префикс CI-раннера
        if "/ai-team-corp/" in path:
            path = path.split("/ai-team-corp/")[-1]
        elif "/home/runner/work/" in path:
            parts = path.split("/")
            # Берём путь после repo-name
            if len(parts) > 5:
                path = "/".join(parts[5:])
        traceback_files.add(path)

    # Читаем содержимое файлов из traceback
    file_contents = []
    for tf in sorted(traceback_files):
        tf_path = run_dir / tf
        if tf_path.exists() and tf_path.is_file():
            content = tf_path.read_text()
            file_contents.append(f"### {tf}\n```python\n{content}\n```")

    # Добавляем весь tests/ (контракт, который не трогаем)
    tests_dir = run_dir / "tests"
    if tests_dir.exists():
        for tf in sorted(tests_dir.rglob("*.py")):
            content = tf.read_text()
            file_contents.append(f"### {tf.relative_to(run_dir)}\n```python\n{content}\n```")

    context = "\n\n".join(file_contents) if file_contents else arch_doc[:2000]

    # Создаём fix-задачу с CI-логами и файлами из traceback
    fix_task = Task(
        description=f"""
        CI/CD пайплайн упал. Исправь код, чтобы тесты прошли.

        КОНТЕКСТ — файлы, упомянутые в traceback, и весь tests/:
        {context}

        ЛОГИ ОШИБОК CI (последние строки — самое важное):
        ```
        {ci_logs}
        ```

        ПРАВИЛА ДЛЯ ФИКСА:
        - Исправь ТОЛЬКО то, что падает в CI (логические ошибки, инициализация БД, фикстуры)
        - Верни ТОЛЬКО изменённые файлы (не всю базу)
        - В поле content первого файла добавь комментарий: что исправлено и почему
        - НЕ меняй архитектуру без крайней необходимости
        - Убедись, что conftest.py инициализирует БД для тестов (fixture, lifespan и т.д.)
        - КРИТИЧНО: тестовые файлы должны содержать РЕАЛЬНЫЙ КОД тестов, не только комментарии
        - КРИТИЧНО: каждый файл должен иметь правильное расширение и содержать валидный Python-код
        - КРИТИЧНО: НЕ изменяй тесты, НЕ добавляй новые тесты, НЕ удаляй существующие
        """,
        expected_output="JSON с полем files — изменённые файлы с исправлениями.",
        agent=developer,
        output_pydantic=CodeOutput,
    )

    crew = Crew(
        agents=[developer],
        tasks=[fix_task],
        process=Process.sequential,
        verbose=False,
    )

    try:
        result = crew.kickoff()
        # Извлекаем файлы: сериализуем pydantic в JSON, затем парсим
        result_str = ""
        if hasattr(result, "json_dict") and result.json_dict:
            result_str = json.dumps(result.json_dict, ensure_ascii=False)
        elif hasattr(result, "pydantic") and result.pydantic:
            result_str = result.pydantic.model_dump_json()
        else:
            result_str = str(result) if result else ""
        new_files = _extract_files(result_str, run_dir, protect_tests=True)
        return len(new_files)
    except Exception as e:
        print(f"  ⚠️ CI fix failed: {e}")
        return 0


def _push_fix_to_pr(branch: str, run_dir: Path) -> bool:
    """Запушить исправленные файлы в существующую ветку PR. True = успех."""
    import subprocess
    import shutil

    worktree_dir = Path(f"/tmp/ai-team-fix-{branch.split('/')[-1]}")
    try:
        r = subprocess.run(
            ["git", "worktree", "add", str(worktree_dir), branch],
            capture_output=True, text=True, timeout=15
        )
        if r.returncode != 0:
            return False

        code_files = [
            f for f in run_dir.rglob("*")
            if f.is_file()
            and not f.name.startswith("task_")
            and f.name != "REPORT.md"
            and f.name not in (".env", ".env.example", ".gitignore")
            and "__pycache__" not in str(f)
            and ".venv" not in str(f)
            and ".collision" not in f.suffix
        ]
        for src in code_files:
            rel = src.relative_to(run_dir)
            dst = worktree_dir / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

        subprocess.run(["git", "add", "-A"], cwd=str(worktree_dir), capture_output=True, timeout=10)
        r = subprocess.run(
            ["git", "commit", "-m", "fix: исправление ошибок CI"],
            cwd=str(worktree_dir), capture_output=True, text=True, timeout=10
        )
        if "nothing to commit" in r.stdout + r.stderr:
            return False

        r = subprocess.run(["git", "push"], cwd=str(worktree_dir),
                           capture_output=True, text=True, timeout=30)
        return r.returncode == 0
    except Exception:
        return False
    finally:
        subprocess.run(["git", "worktree", "remove", str(worktree_dir), "--force"],
                      capture_output=True, timeout=15)


def ci_fix_loop(pr_url: str, run_dir: Path, task: str, timestamp: str) -> None:
    """Ждать CI → при падении запускать доработку → пушить фикс → повторять."""
    branch = f"ai-team/{timestamp}"

    # Извлекаем архитектурный документ для контекста fix-задачи
    arch_doc = ""
    for name, role, raw, _ in _all_outputs:
        if "архитект" in role.lower():
            arch_doc = raw
            break

    for attempt in range(1, MAX_CI_FIX_ATTEMPTS + 1):
        print(f"\n⏳ Ожидание CI для {branch} (попытка {attempt}/{MAX_CI_FIX_ATTEMPTS})...")
        run = _wait_for_ci_run(branch, timeout=600)

        if run is None:
            print(f"  ⚠️ CI run не найден — feedback loop пропущен")
            return

        conclusion = run.get("conclusion")
        print(f"  CI результат: {conclusion}")

        if conclusion == "success":
            print(f"\n🎉 CI ЗЕЛЁНЫЙ! PR готов к ревью: {pr_url}")
            return

        if conclusion != "failure":
            print(f"  ⚠️ CI завершился со статусом {conclusion} — пропускаем")
            return

        # CI упал — получаем логи и запускаем фикс
        print(f"\n🔴 CI упал (попытка {attempt}). Получаю логи...")
        ci_logs = _get_ci_failure_logs(run["id"])
        if not ci_logs:
            print(f"  ⚠️ Не удалось получить логи CI")
            return

        print(f"  🔧 Запускаю Разработчика для исправления...")
        new_files = _run_ci_fix(arch_doc, ci_logs, run_dir)
        if new_files == 0:
            print(f"  ⚠️ Разработчик не внёс изменений — прекращаю loop")
            return

        print(f"  📦 Запушиваю фикс в {branch}...")
        if not _push_fix_to_pr(branch, run_dir):
            print(f"  ⚠️ Не удалось запушить фикс — прекращаю loop")
            return

        print(f"  ✅ Фикс запушен. Жду новый CI run...")
        time.sleep(10)  # даём GitHub время создать новый run

    print(f"\n⚠️ CI не стал зелёным за {MAX_CI_FIX_ATTEMPTS} попыток. PR требует ручного ревью: {pr_url}")


def create_pr_from_run(run_dir: Path, task: str, timestamp: str,
                       metrics: dict | None = None, deploy_report: str = "") -> str | None:
    """Создать ветку через git worktree, запушить код и открыть PR.

    Использует git worktree вместо stash — не трогает текущее состояние репо.
    Закрывает старые PR той же задачи (дедупликация).
    """
    import subprocess
    import shutil

    branch = f"ai-team/{timestamp}"
    title = task[:80] + ("..." if len(task) > 80 else "")
    worktree_dir = Path(f"/tmp/ai-team-wt-{timestamp}")

    # Собираем статистику
    metrics = metrics or {}
    code_lines = _count_code_lines(run_dir)
    file_list = _list_code_files(run_dir)
    test_status = "❌" if "❌" in deploy_report else ("✅" if deploy_report else "—")
    deploy_ok = "✅" if deploy_report and "❌" not in deploy_report else ("❌" if deploy_report else "—")

    # Закрываем старые PR для этой же задачи (дедупликация)
    _close_stale_prs(task)

    try:
        # 1. Создаём worktree от master (не трогает текущий checkout)
        r = subprocess.run(
            ["git", "worktree", "add", "-b", branch, str(worktree_dir), "master"],
            capture_output=True, text=True, timeout=15
        )
        if r.returncode != 0:
            print(f"\n⚠️ git worktree failed: {r.stderr[:200]}")
            return None

        # 2. Копируем сгенерированный код в worktree (только код, не отчёты)
        code_files = [
            f for f in run_dir.rglob("*")
            if f.is_file()
            and not f.name.startswith("task_")
            and f.name != "REPORT.md"
            and f.name not in (".env", ".env.example", ".gitignore")
            and "__pycache__" not in str(f)
            and ".venv" not in str(f)
            and ".collision" not in f.suffix  # пропускаем дубликаты-коллизии
        ]
        for src in code_files:
            rel = src.relative_to(run_dir)
            dst = worktree_dir / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

        # 3. Коммитим в worktree
        subprocess.run(["git", "add", "-A"], cwd=str(worktree_dir), capture_output=True, timeout=10)
        commit_msg = f"🤖 AI-команда: {title}"
        r = subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=str(worktree_dir), capture_output=True, text=True, timeout=10
        )
        if "nothing to commit" in r.stdout + r.stderr:
            print(f"\n⚠️ Нет изменений для PR")
            return None

        # 4. Пушим
        push_result = subprocess.run(
            ["git", "push", "-u", "origin", branch],
            cwd=str(worktree_dir), capture_output=True, text=True, timeout=30
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
        return pr_url

    except Exception as e:
        print(f"\n⚠️ Ошибка создания PR: {e}")
        return None
    finally:
        # Всегда чистим worktree
        subprocess.run(["git", "worktree", "remove", str(worktree_dir), "--force"],
                      capture_output=True, timeout=15)
        # Удаляем локальную ветку (remote остаётся для PR)
        subprocess.run(["git", "branch", "-D", branch], capture_output=True, timeout=10)


def _close_stale_prs(task: str) -> None:
    """Закрыть открытые PR с тем же заголовком задачи (дедупликация)."""
    import os
    import requests

    token = os.getenv("GITHUB_TOKEN")
    if not token:
        return
    user = os.getenv("GITHUB_USER", "druner-ai")
    repo = os.getenv("GITHUB_REPO", "ai-team-corp")
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}
    api = f"https://api.github.com/repos/{user}/{repo}"

    # Нормализуем задачу для сравнения (первые 60 символов без эмодзи)
    task_prefix = task[:60].strip().lower()

    try:
        r = requests.get(f"{api}/pulls?state=open&per_page=50", headers=headers, timeout=10)
        if r.status_code != 200:
            return
        for pr in r.json():
            pr_title = pr["title"].replace("🤖 ", "").strip().lower()
            # Если заголовок PR начинается с тех же 60 символов — это дубль
            if pr_title.startswith(task_prefix[:40]):
                pr_number = pr["number"]
                close_r = requests.patch(
                    f"{api}/pulls/{pr_number}",
                    headers=headers,
                    json={"state": "closed"},
                    timeout=10
                )
                if close_r.status_code == 200:
                    print(f"🔒 Закрыт дубль PR #{pr_number}: {pr['title'][:50]}")
                # Удаляем remote-ветку
                branch_name = pr["head"]["ref"]
                requests.delete(f"{api}/git/refs/heads/{branch_name}", headers=headers, timeout=10)
    except Exception:
        pass  # Не критично, продолжаем


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
