"""Web-интерфейс управления AI-командой — скелет.

Живёт в ai-team-corp/web/. Читает реальный config.py (модели/бюджет) и
output/ (история прогонов), пишет оверрайды в team_config.json.
"""

import json
import re
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

# ai-team-corp — на два уровня выше web/backend/
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import config  # noqa: E402  (модели, бюджет — дефолты)

WEB_DIR = Path(__file__).resolve().parents[1]
FRONTEND = WEB_DIR / "frontend"
CONFIG_FILE = Path(__file__).resolve().parent / "team_config.json"

ROLE_LABELS = {
    "architect": "Архитектор",
    "developer": "Разработчик",
    "qa": "QA ревьюер",
    "devops": "DevOps",
    "fallback": "Fallback (после soft-порога)",
}

REPOS = [
    ("ai-team-corp", "пайплайн команды"),
    ("cardputer-panel", "панель Cardputer"),
    ("hermes-stick-server", "голосовой гейтвей"),
    ("internet-radio", "интернет-радио"),
]

app = FastAPI(title="AI Team Control")


# ── Конфиг-оверрайды ───────────────────────────────────────────
def _load_overrides() -> dict:
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text())
        except Exception:
            return {}
    return {}


def _save_overrides(data: dict) -> None:
    CONFIG_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def _effective_models() -> dict:
    """config.MODELS + оверрайды из team_config.json."""
    overrides = _load_overrides().get("models", {})
    out = {}
    for role, cfg in config.MODELS.items():
        o = overrides.get(role, {})
        out[role] = {
            "name": o.get("name", cfg["name"]),
            "temperature": o.get("temperature", cfg["temperature"]),
            "timeout": o.get("timeout", cfg["timeout"]),
            "price_per_1m": cfg.get("price_per_1m"),
        }
    return out


class ModelPatch(BaseModel):
    name: str | None = None
    temperature: float | None = None
    timeout: int | None = None


# ── Роуты ─────────────────────────────────────────────────────
@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/models")
def list_models():
    models = _effective_models()
    return [
        {"role": role, "label": ROLE_LABELS.get(role, role), **cfg}
        for role, cfg in models.items()
    ]


@app.put("/api/models/{role}")
def update_model(role: str, patch: ModelPatch):
    if role not in config.MODELS:
        raise HTTPException(404, f"Нет роли '{role}'")
    data = _load_overrides()
    data.setdefault("models", {}).setdefault(role, {})
    for field in ("name", "temperature", "timeout"):
        val = getattr(patch, field)
        if val is not None:
            data["models"][role][field] = val
    _save_overrides(data)
    return {"ok": True, "role": role}


@app.get("/api/config")
def get_config():
    return {
        "soft_budget": config.SOFT_BUDGET_USD,
        "hard_budget": config.HARD_BUDGET_USD,
        "max_fix_attempts": config.MAX_FIX_ATTEMPTS,
        "max_arbiter_fix_attempts": config.MAX_ARBITER_FIX_ATTEMPTS,
    }


# ── История прогонов (парсинг output/) ────────────────────────
def _parse_report(path: Path) -> dict:
    """Достать ключевые метрики из REPORT.md (markdown-таблица)."""
    txt = path.read_text(errors="ignore") if path.exists() else ""
    def grab(pat):
        m = re.search(pat, txt)
        return m.group(1).strip() if m else None
    return {
        "status": grab(r"\|\s*Статус\s*\|\s*(.+?)\s*\|"),
        "time": grab(r"\|\s*Время выполнения\s*\|\s*([\d.]+)"),
        "cost": grab(r"\|\s*Цена\s*\|\s*\$?([\d.]+)"),
        "tokens_in": grab(r"\|\s*Токенов \(вход\)\s*\|\s*([\d,]+)"),
        "tokens_out": grab(r"\|\s*Токенов \(выход\)\s*\|\s*([\d,]+)"),
    }


@app.get("/api/runs")
def list_runs():
    out = ROOT / "output"
    if not out.is_dir():
        return []
    runs = []
    for d in sorted(out.iterdir(), reverse=True):
        if not d.is_dir():
            continue
        report = d / "REPORT.md"
        metrics = _parse_report(report)
        runs.append({
            "id": d.name,
            "has_report": report.exists(),
            **metrics,
        })
    return runs


@app.get("/api/runs/{run_id}")
def get_run(run_id: str):
    d = ROOT / "output" / run_id
    if not d.is_dir():
        raise HTTPException(404, f"Прогон {run_id} не найден")
    report = (d / "REPORT.md").read_text(errors="ignore") if (d / "REPORT.md").exists() else ""
    gates = {}
    for g in d.glob("gate_*.txt"):
        gates[g.name] = g.read_text(errors="ignore")[-3000:]
    return {"id": run_id, "report": report, "gates": gates}


@app.get("/api/repos")
def list_repos():
    return [{"name": n, "desc": d, "url": f"https://github.com/druner-ai/{n}"}
            for n, d in REPOS]


# ── Фронт ─────────────────────────────────────────────────────
app.mount("/static", StaticFiles(directory=str(FRONTEND)), name="static")


@app.get("/")
def index():
    return FileResponse(str(FRONTEND / "index.html"))
