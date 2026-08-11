"""Загрузчик паттернов для AI-агентов."""
from pathlib import Path

PATTERNS_DIR = Path(__file__).parent / "patterns"


def load_patterns() -> dict[str, str]:
    """Загрузить все паттерны из каталога patterns/.

    Returns:
        dict: {"fastapi": "...", "docker": "...", "pytest": "...", "architecture": "..."}
    """
    patterns = {}
    for file in PATTERNS_DIR.glob("*.md"):
        if file.name == "README.md":
            continue
        key = file.stem.replace("-agents", "")
        patterns[key] = file.read_text()
    return patterns


def get_pattern(name: str) -> str:
    """Получить конкретный паттерн по имени."""
    patterns = load_patterns()
    return patterns.get(name, "")
