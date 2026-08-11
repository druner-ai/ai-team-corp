"""Инструменты для AI-агентов."""
import shutil
import subprocess
import tempfile
from pathlib import Path

from crewai.tools import tool

_UV = shutil.which("uv") or "/home/deploy/.local/bin/uv"


@tool("run_tests")
def run_tests(code_directory: str) -> str:
    """Запустить pytest в указанной директории с кодом.

    Args:
        code_directory: Путь к директории с кодом и тестами (где лежат tests/ и app/).

    Returns:
        Результат запуска тестов: stdout + stderr. Ищи строки "passed", "failed", "error".
    """
    code_dir = Path(code_directory).resolve()
    if not code_dir.exists():
        return f"ERROR: Directory {code_directory} does not exist"

    tests_dir = code_dir / "tests"
    if not tests_dir.exists():
        return f"ERROR: No tests/ directory found in {code_directory}"

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

        # Запускаем pytest
        output_lines.append("\nRunning pytest...")
        result = subprocess.run(
            [str(pytest), str(tests_dir), "-v", "--tb=short"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(code_dir)
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

        result = subprocess.run(
            [str(pytest), str(tests_dir), "-v", "--tb=short"],
            capture_output=True, text=True, timeout=120, cwd=str(code_dir)
        )

        passed = result.returncode == 0
        # Берём последние строки вывода как summary
        lines = (result.stdout + result.stderr).strip().split("\n")
        summary = "\n".join(lines[-30:])
        return passed, summary
