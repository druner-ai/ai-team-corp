"""Права записи по ролям — первые собственные тесты оркестратора.

Проверяются на настоящем `_write_file_safe`: то, что роль не может записать
файл, должно быть фактом файловой системы, а не текстом в промпте.
"""
import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("OPENROUTER_API_KEY", "test")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import main  # noqa: E402


@pytest.fixture
def run_dir(tmp_path: Path) -> Path:
    (tmp_path / "tests").mkdir()
    return tmp_path


def w(run_dir: Path, role: str, path: str, protect: bool = False):
    return main._write_file_safe(run_dir, path, "x = 1\n",
                                overwrite=True, protect_tests=protect, role=role)


# ─── по три случая на роль: разрешено, запрещено, выход за run_dir ───

@pytest.mark.parametrize("role,allowed,denied", [
    ("Test Designer",  "tests/test_a.py",        "src/app.py"),
    ("Test Designer",  "pytest.ini",             "Dockerfile"),
    ("Разработчик",    "src/app.py",             "tests/test_a.py"),
    ("Разработчик",    "pyproject.toml",         "tests/conftest.py"),
    ("DevOps",         "Dockerfile",             "src/app.py"),
    ("DevOps",         ".github/workflows/ci.yml", "tests/test_a.py"),
    ("Архитектор",     "docs/SPEC.md",           "[build-system]"),
    ("Архитектор",     "ARCHITECTURE.md",        "src/app.py"),
    ("Арбитр контракта", "tests/test_a.py",      None),
    ("Арбитр контракта", "src/app.py",           None),
])
def test_allow_and_deny(run_dir: Path, role: str, allowed: str, denied: str | None):
    assert w(run_dir, role, allowed) is not None, f"{role} должен писать в {allowed}"
    if denied is not None:
        assert w(run_dir, role, denied) is None, f"{role} не должен писать в {denied}"


@pytest.mark.parametrize("role", [
    "Test Designer", "Разработчик", "DevOps", "Архитектор", "Арбитр контракта", "QA ревьюер",
])
def test_traversal_denied(run_dir: Path, role: str):
    """Выход за каталог прогона запрещён всем ролям."""
    for path in ("../escaped.py", "../../etc/passwd", "/etc/passwd"):
        assert w(run_dir, role, path) is None, f"{role}: {path} не отклонён"
        assert not (run_dir.parent / "escaped.py").exists()


@pytest.mark.parametrize("path", ["report.md", "src/app.py", "tests/test_a.py"])
def test_qa_writes_nothing(run_dir: Path, path: str):
    """QA — роль наблюдения: не пишет в проект ничего, включая отчёты."""
    assert w(run_dir, "QA ревьюер", path) is None


def test_unknown_role_denied(run_dir: Path):
    """Роль вне таблицы не получает доступ по умолчанию.

    Раньше права были цепочкой if/elif, и роль, не попавшая ни в одну ветку,
    писала куда угодно: так Архитектор насорил файлами "[build-system]".
    """
    assert w(run_dir, "Аналитик", "src/app.py") is None
    assert w(run_dir, "", "src/app.py") is None


def test_protect_tests_overrides_role(run_dir: Path):
    """На этапе fix тесты неприкосновенны даже для роли с правом на tests/."""
    assert w(run_dir, "Арбитр контракта", "tests/test_a.py", protect=True) is None
    assert w(run_dir, "Арбитр контракта", "tests/test_a.py", protect=False) is not None


def test_dockerfile_case_insensitive(run_dir: Path):
    """Агент пишет имя по конвенции Docker, регистр не должен решать."""
    assert w(run_dir, "DevOps", "dockerfile") is not None
    assert w(run_dir, "DevOps", "DOCKER-COMPOSE.YML") is not None


def test_deny_beats_allow(run_dir: Path):
    """Разработчику разрешено всё, но deny на tests/ проверяется раньше."""
    rules = main.WRITE_RULES["разработ"]
    assert "*" in rules["allow"] and "tests/" in rules["deny"]
    assert w(run_dir, "Разработчик", "tests/nested/deep/test_b.py") is None


def test_every_agent_role_is_covered():
    """Каждая роль из agents.py описана в таблице прав.

    Без этой проверки добавление роли снова даёт молчаливый полный доступ.
    """
    import agents
    roles = [getattr(agents, n).role for n in
             ("architect", "test_designer", "developer", "qa_gate", "devops")]
    for role in roles:
        ok, reason = main._write_allowed(role, "docs/x.md")
        covered = "не описана в WRITE_RULES" not in reason
        assert covered, f"роль '{role}' отсутствует в WRITE_RULES"
