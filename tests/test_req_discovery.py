"""Поиск requirements*.txt рекурсивно — регресс прогона 20260813_051701."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools import _find_req_files, _read_requirements


def test_root_files_found(tmp_path):
    (tmp_path / "requirements.txt").write_text("fastapi\n")
    (tmp_path / "requirements-dev.txt").write_text("pytest\n")
    names = [f.name for f in _find_req_files(tmp_path)]
    assert names == ["requirements-dev.txt", "requirements.txt"]


def test_subdir_files_found(tmp_path):
    """Кейс прогона 20260813_051701: зависимости в backend/, корень пуст."""
    backend = tmp_path / "backend"
    backend.mkdir()
    (backend / "requirements.txt").write_text("fastapi\n")
    (backend / "requirements-dev.txt").write_text("pytest\n")
    found = _find_req_files(tmp_path)
    assert len(found) == 2
    assert all("backend" in str(f) for f in found)


def test_stage_dirs_excluded(tmp_path):
    stage = tmp_path / "stage_02_dev"
    stage.mkdir()
    (stage / "requirements.txt").write_text("junk\n")
    (tmp_path / "requirements.txt").write_text("fastapi\n")
    found = _find_req_files(tmp_path)
    assert len(found) == 1
    assert "stage_02_dev" not in str(found[0])


def test_hidden_and_service_dirs_excluded(tmp_path):
    for d in (".venv/sub", "node_modules/pkg", "__pycache__"):
        p = tmp_path / d
        p.mkdir(parents=True)
        (p / "requirements.txt").write_text("junk\n")
    assert _find_req_files(tmp_path) == []


def test_empty_project_gives_empty_list(tmp_path):
    """Без requirements список пуст — install_cmd всё равно валиден (ставит pytest)."""
    assert _find_req_files(tmp_path) == []


def test_read_requirements_merges_subdirs(tmp_path):
    backend = tmp_path / "backend"
    backend.mkdir()
    (backend / "requirements.txt").write_text("fastapi\n")
    (tmp_path / "requirements-dev.txt").write_text("pytest\n")
    text = _read_requirements(tmp_path)
    assert "fastapi" in text and "pytest" in text
