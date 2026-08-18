"""status.py — живой STATUS.md прогона (Ralph loop)."""
from pathlib import Path


# ─── STATUS.md — живой статус прогона (Ralph loop) ─────────────
# Короткие итерации держат на диске актуальный «план/статус», который
# следующие фазы читают вместо перечитывания всего накопленного контекста.
# fix/арбитр/D2 получают только хвост STATUS.md — сжатую сводку «что уже было».


def _status_append(run_dir: Path | None, text: str) -> None:
    """Дописать строку в живой STATUS.md прогона. Идемпотентно и безопасно."""
    if run_dir is None:
        return
    try:
        with (run_dir / "STATUS.md").open("a", encoding="utf-8") as f:
            f.write(text.rstrip() + "\n")
    except OSError:
        pass


def _status_context(run_dir: Path) -> str:
    """Хвост STATUS.md для инъекции в промпты правок (fix/арбитр/D2).

    Возвращает пустую строку, если статуса нет — тогда контекст не меняется.
    """
    sp = run_dir / "STATUS.md"
    if not sp.is_file():
        return ""
    text = sp.read_text(encoding="utf-8", errors="ignore").strip()
    if not text:
        return ""
    # Только хвост: полный журнал раздул бы промпт без пользы для решения.
    return "=== СТАТУС ПРОГОНА (что уже было сделано) ===\n" + text[-3000:] + "\n\n"


