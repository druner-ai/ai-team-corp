"""Инструменты для AI-агентов."""
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from crewai.tools import tool

from observability import log_event

_UV = shutil.which("uv") or "/home/deploy/.local/bin/uv"


def _read_ci_recipe(code_dir: Path) -> str:
    """Собрать текст всех CI-воркфлоу проекта.

    Рецепт CI — единственное место, где выразимы внешние рантаймы
    (браузеры, системные пакеты), которых нет в requirements.txt.
    Читаем как текст: нам нужны только известные команды, а не структура.
    """
    recipe = []
    wf_dir = code_dir / ".github" / "workflows"
    if wf_dir.is_dir():
        for wf in sorted(wf_dir.glob("*.y*ml")):
            try:
                recipe.append(wf.read_text(errors="replace"))
            except OSError:
                continue
    return "\n".join(recipe)


def _read_requirements(code_dir: Path) -> str:
    """Собрать текст всех файлов зависимостей проекта."""
    chunks = []
    for name in ("requirements.txt", "requirements-dev.txt"):
        f = code_dir / name
        if f.exists():
            try:
                chunks.append(f.read_text(errors="replace"))
            except OSError:
                continue
    return "\n".join(chunks)


# Каталог с системными библиотеками, распакованными без root
# (playwright install --with-deps требует apt и root, поэтому .deb
# распакованы вручную в ~/.local/pwdeps).
_LOCAL_DEPS = Path.home() / ".local" / "pwdeps"


def runtime_env() -> dict[str, str]:
    """Окружение для процесса тестов: локальные системные библиотеки."""
    env = dict(os.environ)
    if not _LOCAL_DEPS.is_dir():
        return env
    lib_dirs = [str(p) for p in sorted((_LOCAL_DEPS / "usr" / "lib").glob("*-linux-gnu")) if p.is_dir()]
    if not lib_dirs:
        return env
    existing = env.get("LD_LIBRARY_PATH", "")
    env["LD_LIBRARY_PATH"] = ":".join(lib_dirs + ([existing] if existing else []))
    return env


def prepare_external_runtimes(code_dir: Path, venv_bin: Path) -> list[str]:
    """Установить внешние рантаймы, которые нельзя объявить в requirements.

    Источник истины — рецепт CI от DevOps-агента. Из него берутся только
    команды из белого списка ниже; произвольные шаги CI не исполняются,
    потому что их пишет LLM.

    Возвращает список строк-заметок для лога прогона.
    """
    notes: list[str] = []
    recipe = _read_ci_recipe(code_dir)
    reqs = _read_requirements(code_dir).lower()

    # ── playwright: пакет ставится через pip, браузер — отдельной командой ──
    wants_playwright = bool(re.search(r"playwright\s+install", recipe)) or "playwright" in reqs
    if wants_playwright:
        pw = venv_bin / "playwright"
        if not pw.exists():
            notes.append("playwright: бинарь не найден в venv — установка браузера пропущена")
        else:
            # --with-deps не используем: требует apt и root.
            r = subprocess.run(
                [str(pw), "install", "chromium"],
                capture_output=True, text=True, timeout=900, env=runtime_env(),
            )
            if r.returncode == 0:
                notes.append("playwright install chromium: ок")
            else:
                tail = (r.stderr or r.stdout or "")[-300:]
                notes.append(f"playwright install chromium: НЕ УДАЛОСЬ — {tail}")

    return notes


@tool("run_tests")
def run_tests(code_directory: str = "") -> str:
    """Запустить pytest в текущем прогоне. Путь не нужен — он берётся автоматически.

    Args:
        code_directory: ИГНОРИРУЕТСЯ. Оставлен для совместимости: модель всё равно
            иногда передаёт путь, и выдуманный путь не должен ломать запуск.

    Returns:
        Результат запуска тестов: stdout + stderr. Ищи строки "passed", "failed", "error".
    """
    # Путь — факт окружения, не аргумент из LLM. Ревью показало: модель
    # подставляла "./output", "/app", "текущая директория" — и получала ERROR.
    env_dir = os.environ.get("AI_TEAM_RUN_DIR", "")
    if not env_dir:
        return ("ERROR: AI_TEAM_RUN_DIR не выставлен. Инструмент вызван вне прогона "
                "— это дефект оркестратора, не твоя ошибка.")

    code_dir = Path(env_dir).resolve()
    if code_directory and Path(code_directory).resolve() != code_dir:
        log_event({
            "event": "tool_arg_ignored",
            "tool": "run_tests",
            "passed": code_directory,
            "used": str(code_dir),
        })

    if not code_dir.exists():
        return f"ERROR: Directory {code_dir} does not exist"

    tests_dir = code_dir / "tests"
    if not tests_dir.exists():
        existing = sorted(p.name for p in code_dir.iterdir())[:20]
        log_event({"event": "tool_call", "tool": "run_tests", "result": "no_tests_dir",
                   "dir": str(code_dir), "contents": existing})
        return (f"ERROR: No tests/ directory found in {code_dir}. "
                f"Содержимое каталога: {existing}")

    req_file = code_dir / "requirements.txt"
    req_dev_file = code_dir / "requirements-dev.txt"

    output_lines = []

    with tempfile.TemporaryDirectory() as tmpdir:
        venv_path = Path(tmpdir) / "venv"
        output_lines.append(f"Creating venv at {venv_path} (via uv)...")

        # uv venv — быстро и не требует python3-venv/ensurepip
        result = subprocess.run(
            [_UV, "venv", str(venv_path)],
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode != 0:
            return f"ERROR creating venv:\n{result.stderr}"

        python = venv_path / "bin" / "python"
        pytest = venv_path / "bin" / "pytest"

        # Устанавливаем зависимости через uv pip (с кэшем — 5-10 сек)
        output_lines.append("Installing dependencies (uv pip)...")
        install_cmd = [_UV, "pip", "install", "--python", str(python), "-q"]
        if req_file.exists():
            install_cmd.extend(["-r", str(req_file)])
        if req_dev_file.exists():
            install_cmd.extend(["-r", str(req_dev_file)])

        result = subprocess.run(
            install_cmd,
            capture_output=True,
            text=True,
            timeout=180,
            cwd=str(code_dir)
        )
        if result.returncode != 0:
            output_lines.append(f"WARNING: uv pip install returned {result.returncode}")
            output_lines.append(result.stderr[:500])

        # Внешние рантаймы по рецепту CI (браузеры и прочее вне pip)
        for note in prepare_external_runtimes(code_dir, venv_path / "bin"):
            output_lines.append(note)

        # Запускаем pytest
        output_lines.append("\nRunning pytest...")
        result = subprocess.run(
            [str(pytest), str(tests_dir), "-v", "--tb=short"],
            capture_output=True,
            text=True,
            timeout=300,
            cwd=str(code_dir),
            env=runtime_env()
        )

        output_lines.append(f"\nExit code: {result.returncode}")
        output_lines.append("\n=== STDOUT ===")
        output_lines.append(result.stdout)
        output_lines.append("\n=== STDERR ===")
        output_lines.append(result.stderr)

        if result.returncode == 0:
            output_lines.append("\n✅ ALL TESTS PASSED")
        else:
            output_lines.append(f"\n❌ TESTS FAILED (exit code {result.returncode})")

        log_event({"event": "tool_call", "tool": "run_tests", "dir": str(code_dir),
                   "exit_code": result.returncode})

    return "\n".join(output_lines)


def run_tests_quiet(code_directory: str) -> tuple[bool, str]:
    """Программный запуск тестов без LLM-агента. Возвращает (passed, summary).

    Используется оркестратором как гейт: PR создаётся только при passed=True.
    """
    code_dir = Path(code_directory).resolve()
    if not code_dir.exists():
        return False, f"Directory {code_directory} does not exist"

    tests_dir = code_dir / "tests"
    if not tests_dir.exists():
        return False, "No tests/ directory found"

    req_file = code_dir / "requirements.txt"
    req_dev_file = code_dir / "requirements-dev.txt"

    with tempfile.TemporaryDirectory() as tmpdir:
        venv_path = Path(tmpdir) / "venv"
        result = subprocess.run(
            [_UV, "venv", str(venv_path)],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode != 0:
            return False, f"venv creation failed: {result.stderr[:300]}"

        python = venv_path / "bin" / "python"
        pytest = venv_path / "bin" / "pytest"

        install_cmd = [_UV, "pip", "install", "--python", str(python), "-q"]
        if req_file.exists():
            install_cmd.extend(["-r", str(req_file)])
        if req_dev_file.exists():
            install_cmd.extend(["-r", str(req_dev_file)])

        result = subprocess.run(
            install_cmd, capture_output=True, text=True,
            timeout=180, cwd=str(code_dir)
        )
        if result.returncode != 0:
            return False, f"pip install failed: {result.stderr[:300]}"

        # Внешние рантаймы по рецепту CI (браузеры и прочее вне pip)
        runtime_notes = prepare_external_runtimes(code_dir, venv_path / "bin")

        result = subprocess.run(
            [str(pytest), str(tests_dir), "-v", "--tb=short"],
            capture_output=True, text=True, timeout=300, cwd=str(code_dir),
            env=runtime_env()
        )

        passed = result.returncode == 0
        full = result.stdout + result.stderr
        if runtime_notes:
            full = "=== подготовка окружения ===\n" + "\n".join(runtime_notes) + "\n\n" + full
        # Полный вывод — рядом с прогоном: срез в 30 строк съедали баннеры
        try:
            (code_dir / "tests_full_output.txt").write_text(full)
        except OSError:
            pass
        lines = full.strip().split("\n")
        summary = "\n".join(lines[-100:])
        return passed, summary
