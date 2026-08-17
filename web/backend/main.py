"""Web-интерфейс управления AI-командой — скелет.

Живёт в ai-team-corp/web/. Читает реальный config.py (модели/бюджет) и
output/ (история прогонов), пишет оверрайды в team_config.json.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import time as time_mod
import signal
import threading
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

# ai-team-corp — на два уровня выше web/backend/
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import config  # noqa: E402  (модели, бюджет — дефолты)

try:
    from dotenv import load_dotenv
    load_dotenv("/home/deploy/hermes/data/.env")
except Exception:
    pass

import urllib.request

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

# Каталог моделей для дропдауна (OpenRouter ID → подпись)
MODEL_CATALOG = [
    ("z-ai/glm-5.2", "GLM-5.2 (архитектор)"),
    ("deepseek/deepseek-v4-pro", "DeepSeek V4 Pro"),
    ("deepseek/deepseek-v4-flash", "DeepSeek V4 Flash (дешёвый)"),
    ("moonshotai/kimi-k2.7-code", "Kimi K2.7 Code (планирование)"),
    ("mistralai/codestral-2508", "Codestral 2508"),
    ("qwen/qwen3-coder", "Qwen3 Coder"),
]

# Схема фаз пайплайна (описание для UI; оркестрация живёт в main.py)
PIPELINE_STAGES = [
    {"phase": "A0", "actor": "Test Designer", "desc": "Baseline-тесты на текущее поведение (если в репо нет tests/)", "gate": "G_base"},
    {"phase": "A1", "actor": "Архитектор", "desc": "Архитектурный документ — единственный источник правды", "gate": None},
    {"phase": "A2", "actor": "Test Designer → Разработчик → QA", "desc": "Тесты по спеке → код под тесты → ревью", "gate": "G1 (связь тесты↔спека)"},
    {"phase": "B", "actor": "Разработчик / Test Designer", "desc": "Fix-цикл: ошибки сбора → Test Designer, assert-падения → Разработчик", "gate": "G2 (pytest)"},
    {"phase": "C", "actor": "DevOps", "desc": "Dockerfile, docker-compose, CI", "gate": "G3 (тесты после упаковки)"},
    {"phase": "D", "actor": "Арбитр", "desc": "Разрешает спор тест↔код↔спека; единственный, кто может менять tests/", "gate": "G2_arb"},
    {"phase": "D2", "actor": "Разработчик", "desc": "Доводка кода арбитра, если он сам не прошёл тесты", "gate": "G2_arbfix"},
    {"phase": "→", "actor": "Оркестратор", "desc": "Зелёные тесты → Pull Request (или publish-стадия)", "gate": None},
]

app = FastAPI(title="AI Team Control")

UV = shutil.which("uv") or "/home/deploy/.local/bin/uv"
_active_run: dict = {}
ACTIVE_RUN_FILE = Path(__file__).resolve().parent / "active_run.json"


def _save_active_run():
    try:
        ACTIVE_RUN_FILE.write_text(json.dumps(_active_run, ensure_ascii=False))
    except Exception:
        pass


def _load_active_run():
    try:
        if ACTIVE_RUN_FILE.exists():
            _active_run.update(json.loads(ACTIVE_RUN_FILE.read_text()))
    except Exception:
        pass


_load_active_run()


def _pid_alive(pid: int) -> bool:
    """Жив ли процесс (не зомби). Зомби (uv после завершения ребёнка) считается мёртвым."""
    try:
        with open(f"/proc/{pid}/stat") as f:
            data = f.read()
        state = data.split(") ", 1)[1][0] if ") " in data else "?"
        return state != "Z"
    except (OSError, IndexError):
        return False


def _gen_slug(task: str) -> str:
    """ASCII-slug из первых латинских слов задачи + короткий timestamp-суффикс."""
    words = re.findall(r"[A-Za-z][A-Za-z0-9_-]{1,}", task)
    base = re.sub(r"[^a-z0-9_-]+", "-", "-".join(w.lower() for w in words[:3])).strip("-")[:40]
    if not base:
        base = "ai"
    return f"{base}-{time_mod.strftime('%m%d%H%M')}"


class RunRequest(BaseModel):
    task: str
    mode: str = "greenfield"  # "greenfield" | "enhance"
    repo: str | None = None


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


@app.get("/api/models/catalog")
def model_catalog():
    return [{"id": mid, "label": label} for mid, label in MODEL_CATALOG]


@app.get("/api/models/catalog/live")
def model_catalog_live():
    """Живой список моделей из OpenRouter API (через SOCKS5-прокси из env)."""
    import httpx
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise HTTPException(503, "OPENROUTER_API_KEY не задан")
    try:
        r = httpx.get("https://openrouter.ai/api/v1/models",
                      headers={"Authorization": f"Bearer {key}"}, timeout=20)
        r.raise_for_status()
    except Exception as e:
        raise HTTPException(502, f"OpenRouter недоступен: {e}")
    return [
        {"id": m["id"], "label": m.get("name") or m["id"]}
        for m in r.json().get("data", [])
        if m.get("id")
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


def _run_id_is_active(run_id: str) -> bool:
    """run_id (YYYYMMDD_HHMMSS) близок к started_at активного прогона (±3с)."""
    try:
        t = time_mod.mktime(time_mod.strptime(run_id, "%Y%m%d_%H%M%S"))
        # run-директория создаётся уже внутри main.py, ПОСЛЕ старта uv run (зазор 5–20с)
        return -3 <= (t - _active_run.get("started_at", 0)) <= 60
    except (ValueError, TypeError):
        return False


@app.get("/api/runs")
def list_runs():
    out = ROOT / "output"
    if not out.is_dir():
        return []
    active_pid = _active_run.get("pid")
    alive = bool(active_pid) and _pid_alive(active_pid)
    runs = []
    for d in sorted(out.iterdir(), reverse=True):
        if not d.is_dir():
            continue
        report = d / "REPORT.md"
        metrics = _parse_report(report)
        runs.append({
            "id": d.name,
            "has_report": report.exists(),
            "running": alive and _run_id_is_active(d.name),
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
    repos = {n: {"name": n, "desc": d, "url": f"https://github.com/druner-ai/{n}"}
             for n, d in REPOS}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        try:
            req = urllib.request.Request(
                "https://api.github.com/user/repos?per_page=100&affiliation=owner",
                headers={"Authorization": f"Bearer {token}", "User-Agent": "aitc/1.0"})
            data = json.loads(urllib.request.urlopen(req, timeout=15).read().decode())
            for x in data:
                repos[x["name"]] = {"name": x["name"],
                                    "desc": x.get("description") or "",
                                    "url": x.get("html_url") or f"https://github.com/druner-ai/{x['name']}"}
        except Exception:
            pass
    return list(repos.values())


@app.get("/api/roles")
def list_roles():
    """Роли команды: goal/backstory из agents.py + привязанная модель."""
    import agents
    result = []
    for key, a in agents.AGENTS.items():
        model = ""
        if getattr(a, "llm", None) is not None:
            model = (getattr(a.llm, "model", "") or "").replace("openai/", "", 1)
        result.append({
            "key": key,
            "role": a.role,
            "goal": a.goal,
            "backstory": a.backstory,
            "model": model,
        })
    return result


@app.get("/api/pipeline")
def pipeline():
    """Схема фаз пайплайна + настроенные лимиты."""
    return {
        "stages": PIPELINE_STAGES,
        "config": {
            "max_fix_attempts": config.MAX_FIX_ATTEMPTS,
            "max_arbiter_fix_attempts": config.MAX_ARBITER_FIX_ATTEMPTS,
            "soft_budget": config.SOFT_BUDGET_USD,
            "hard_budget": config.HARD_BUDGET_USD,
        },
    }


@app.post("/api/run")
def start_run(payload: RunRequest):
    """Запустить прогон команды фоновым subprocess (uv run python main.py ...)."""
    if _active_run.get("pid") and _pid_alive(_active_run["pid"]):
        raise HTTPException(409, "Прогон уже запущен")
    task = payload.task.strip()
    if not task:
        raise HTTPException(422, "Пустая задача")
    if payload.mode == "enhance" and not payload.repo:
        raise HTTPException(422, "Для enhance укажи репо (owner/name)")

    cmd = [UV, "run", "python", "main.py"]
    if payload.mode == "enhance":
        cmd += ["--enhance", (payload.repo or "").strip()]
    cmd += [task]

    ts = time_mod.strftime("%Y%m%d_%H%M%S")
    log_path = f"/tmp/aitc-run-{ts}.log"
    log_file = open(log_path, "w")
    env = os.environ.copy()
    slug = None
    if payload.mode == "greenfield":
        slug = _gen_slug(task)
        env["AI_TEAM_PUBLISH"] = "1"
        env["AI_TEAM_PUBLISH_SLUG"] = slug
    proc = subprocess.Popen(
        cmd, cwd=str(ROOT), stdout=log_file, stderr=subprocess.STDOUT,
        start_new_session=True, env=env,
    )
    log_file.close()  # закрываем родительскую копию — fd остаётся у ребёнка

    _active_run.update({
        "pid": proc.pid,
        "started_at": time_mod.time(),
        "task": task,
        "mode": payload.mode,
        "repo": payload.repo,
        "slug": slug,
        "log_path": log_path,
    })
    _save_active_run()
    return {"ok": True, "pid": proc.pid, "started_at": _active_run["started_at"]}


PHASE_LABELS = {
    "A0": "Baseline-тесты", "A1": "Архитектор", "A1f": "Архитектор (fallback)",
    "A1d": "UX/UI-дизайнер", "A2": "Test Designer", "B1": "Разработчик",
    "B2": "Fix-цикл", "D": "Арбитр", "D2": "Доводка арбитра", "C": "DevOps",
}
PHASES_ORDER = ["A1", "A1d", "A2", "B1", "B2", "D", "D2", "C"]
GATE_LABELS = {
    "G0": "спека: есть проверяемые утверждения",
    "G_base": "baseline-тесты репо",
    "G1": "тесты собираются и проходят",
    "G1a": "покрытие спеки тестами",
    "G2_1": "код проходит тесты",
    "G2_2": "код после фикса",
    "G2_arb": "тесты после арбитра",
    "G2_arbfix1": "после правки арбитра",
    "G2_arbfix2": "после правки арбитра",
    "G3_tests": "упаковка не сломала тесты",
    "G1a_final": "итоговое покрытие спеки",
}


def _gate_label(gid):
    if gid in GATE_LABELS:
        return GATE_LABELS[gid]
    if gid and gid.startswith("G2_"):
        return "код проходит тесты (итерация)"
    return gid


def _phase_label(pid):
    if pid in PHASE_LABELS:
        return PHASE_LABELS[pid]
    if pid.startswith("B"):
        return f"Fix-цикл {pid[1:]}"
    return pid


def _latest_run_dir():
    out = ROOT / "output"
    if not out.exists():
        return None
    dirs = [d for d in out.iterdir() if d.is_dir() and d.name[:8].isdigit()]
    return max(dirs, key=lambda d: d.name) if dirs else None


def _parse_run_phases(run_dir):
    jl = run_dir / "run.jsonl"
    if not jl.exists():
        return [], [], 0.0
    phases, order, gates = {}, [], []
    total_cost = 0.0
    for line in jl.read_text(errors="ignore").splitlines():
        try:
            e = json.loads(line)
        except Exception:
            continue
        ev = e.get("event")
        if ev == "phase_start":
            pid = e.get("phase")
            if pid and pid not in phases:
                phases[pid] = {"id": pid, "label": _phase_label(pid), "status": "running"}
                order.append(pid)
        elif ev == "phase_end":
            pid = e.get("phase")
            if pid and pid in phases:
                phases[pid]["status"] = "failed" if e.get("error") else "done"
                phases[pid]["cost"] = e.get("cost")
                phases[pid]["tokens_in"] = e.get("tokens_in")
                phases[pid]["tokens_out"] = e.get("tokens_out")
                phases[pid]["duration"] = e.get("duration")
                if e.get("cost"):
                    total_cost += float(e["cost"])
        elif ev == "phase_skipped":
            pid = e.get("phase")
            if pid and pid not in phases:
                phases[pid] = {"id": pid, "label": _phase_label(pid), "status": "skipped"}
                order.append(pid)
        elif ev == "gate":
            gates.append({"id": e.get("gate"), "label": _gate_label(e.get("gate")),
                          "green": e.get("green"),
                          "asserts": e.get("asserts"), "problems": e.get("problems")})
    seen = set(phases)
    for pid in PHASES_ORDER:
        if pid not in seen:
            phases[pid] = {"id": pid, "label": _phase_label(pid), "status": "pending"}
            order.append(pid)
    return [phases[p] for p in order], gates, round(total_cost, 4)


@app.get("/api/run/status")
def run_status():
    """Живой статус активного прогона: жив ли процесс, elapsed, хвост лога."""
    r = _active_run
    if not r.get("pid"):
        return {"running": False}
    running = _pid_alive(r["pid"])
    if not running:
        try:
            os.waitpid(r["pid"], os.WNOHANG)
        except (ChildProcessError, OSError):
            pass
    elapsed = int(time_mod.time() - r["started_at"]) if r.get("started_at") else 0
    log_tail = []
    if r.get("log_path"):
        try:
            with open(r["log_path"], "r", errors="ignore") as f:
                log_tail = f.readlines()[-30:]
        except OSError:
            pass
    phases, gates, total_cost = [], [], 0.0
    _rd = _latest_run_dir()
    if _rd:
        phases, gates, total_cost = _parse_run_phases(_rd)
    return {
        "running": running,
        "pid": r.get("pid"),
        "elapsed": elapsed,
        "task": r.get("task"),
        "mode": r.get("mode"),
        "repo": r.get("repo"),
        "slug": r.get("slug"),
        "log_tail": [ln.rstrip() for ln in log_tail],
        "phases": phases,
        "gates": gates,
        "total_cost": total_cost,
    }


@app.post("/api/run/stop")
def stop_run():
    """Аварийная остановка активного прогона: убить группу процессов + сбросить состояние."""
    r = _active_run
    if not r.get("pid"):
        return {"ok": True, "stopped": False, "reason": "нет активного прогона"}
    pid = r["pid"]
    stopped = False
    try:
        os.killpg(pid, signal.SIGTERM)
        stopped = True
    except (ProcessLookupError, OSError):
        pass

    def _force_kill():
        time_mod.sleep(1.5)
        try:
            os.killpg(pid, signal.SIGKILL)
        except (ProcessLookupError, OSError):
            pass

    threading.Thread(target=_force_kill, daemon=True).start()
    _active_run.clear()
    _save_active_run()
    return {"ok": True, "stopped": stopped, "pid": pid}


# ── Фронт ─────────────────────────────────────────────────────
app.mount("/static", StaticFiles(directory=str(FRONTEND)), name="static")


@app.get("/")
def index():
    return FileResponse(str(FRONTEND / "index.html"))
