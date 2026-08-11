"""Инструменты для AI-агентов."""
import subprocess
import tempfile
from pathlib import Path

from crewai.tools import tool


@tool("run_tests")
def run_tests(code_directory: str) -> str:
    """Запустить pytest в указанной директории с кодом.

    Args:
        code_directory: Путь к директории с кодом и тестами (где лежат tests/ и app/).

    Returns:
        Результат запуска тестов: stdout + stderr. Ищи строки "passed", "failed", "error".
    """
    code_dir = Path(code_directory)
    if not code_dir.exists():
        return f"ERROR: Directory {code_directory} does not exist"

    # Проверяем наличие тестов
    tests_dir = code_dir / "tests"
    if not tests_dir.exists():
        return f"ERROR: No tests/ directory found in {code_directory}"

    # Проверяем наличие requirements
    req_file = code_dir / "requirements.txt"
    req_dev_file = code_dir / "requirements-dev.txt"

    output_lines = []

    # Создаём временное окружение для установки зависимостей
    with tempfile.TemporaryDirectory() as tmpdir:
        venv_path = Path(tmpdir) / "venv"
        output_lines.append(f"Creating venv at {venv_path}...")

        # Создаём venv
        result = subprocess.run(
            ["python3", "-m", "venv", str(venv_path)],
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode != 0:
            return f"ERROR creating venv:\n{result.stderr}"

        pip = venv_path / "bin" / "pip"
        pytest = venv_path / "bin" / "pytest"

        # Устанавливаем зависимости
        output_lines.append("Installing dependencies...")
        install_cmd = [str(pip), "install", "-q"]
        if req_file.exists():
            install_cmd.extend(["-r", str(req_file)])
        if req_dev_file.exists():
            install_cmd.extend(["-r", str(req_dev_file)])

        result = subprocess.run(
            install_cmd,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(code_dir)
        )
        if result.returncode != 0:
            output_lines.append(f"WARNING: pip install returned {result.returncode}")
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

        # Анализируем результат
        if result.returncode == 0:
            output_lines.append("\n✅ ALL TESTS PASSED")
        else:
            output_lines.append(f"\n❌ TESTS FAILED (exit code {result.returncode})")

    return "\n".join(output_lines)
