"""memory.py — cross-run память проекта: memory/<owner>__<repo>.md."""
from pathlib import Path


# ─── Cross-run память (Loop Engineering: Memory = источник правды) ──
# Каждый прогон в режиме --enhance читает историю проекта и дописывает в неё
# свой итог. Архитектор следующего прогона видит «что уже решали и как» —
# вместо того чтобы стартовать с нуля и повторять старые ошибки.

MEMORY_DIR = Path(__file__).resolve().parent / "memory"


def _memory_path(repo: str) -> Path:
    """Файл памяти проекта: memory/<owner>__<repo>.md."""
    return MEMORY_DIR / (repo.replace("/", "__") + ".md")


def _memory_read(repo: str) -> str:
    """Прочитать историю проекта для инъекции в промпт Архитектора."""
    p = _memory_path(repo)
    if not p.is_file():
        return ""
    text = p.read_text(encoding="utf-8", errors="ignore").strip()
    return text if text else ""


def _memory_append(repo: str, entry: str) -> None:
    """Дописать запись в память проекта."""
    p = _memory_path(repo)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(entry.rstrip() + "\n\n")
    except OSError:
        pass


