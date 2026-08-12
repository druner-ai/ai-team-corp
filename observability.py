#!/usr/bin/env python3
"""Машиночитаемый лог прогона: output/<ts>/run.jsonl.

Одна строка JSON на событие. Единственный источник для разбора прогонов —
verbose-лог CrewAI с рамками и ANSI-кодами для этого не годится.

Типы событий:
  run_start    — задача, модели, бюджет
  phase_start  — начало фазы
  phase_end    — конец фазы: токены, стоимость, длительность
  artifacts    — какая роль на какой стадии какие файлы записала
  tool_call    — вызов инструмента агентом
  gate         — результат детерминированного гейта
  arbiter      — решение по спору теста и кода
  run_end      — итог прогона
"""

import json
import time
from pathlib import Path

_RUN_LOG: Path | None = None


def init_log(run_dir: Path) -> Path:
    """Создать пустой run.jsonl в каталоге прогона."""
    global _RUN_LOG
    _RUN_LOG = Path(run_dir) / "run.jsonl"
    _RUN_LOG.write_text("")
    return _RUN_LOG


def log_event(payload: dict) -> None:
    """Записать событие. Молча ничего не делает, если лог не инициализирован."""
    if _RUN_LOG is None:
        return
    rec = {"ts": round(time.time(), 3), **payload}
    try:
        with _RUN_LOG.open("a") as f:
            f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
    except Exception as e:
        # Лог не должен ломать прогон
        print(f"⚠️ run.jsonl: не удалось записать событие: {e}")


def log_path() -> Path | None:
    return _RUN_LOG
