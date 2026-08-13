// AI Team Control — скелет дашборда.

const $ = (sel) => document.querySelector(sel);

// ── Табы ──────────────────────────────────────────────────────
document.querySelectorAll('#tabs button').forEach((btn) => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('#tabs button').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    btn.classList.add('active');
    $('#' + btn.dataset.tab).classList.add('active');
    loadTab(btn.dataset.tab);
  });
});

function loadTab(name) {
  if (name === 'dashboard') loadDashboard();
  if (name === 'models') loadModels();
  if (name === 'runs') loadRuns();
  if (name === 'repos') loadRepos();
  if (name === 'config') loadConfig();
  if (name === 'roles') loadRoles();
  if (name === 'pipeline') loadPipeline();
  if (name === 'run') loadRun();
}

async function api(path, opts) {
  const res = await fetch('/api' + path, opts);
  if (!res.ok) throw new Error(res.status);
  return res.json();
}

function esc(s) {
  const d = document.createElement('div');
  d.textContent = s ?? '';
  return d.innerHTML;
}

// ── Дашборд ───────────────────────────────────────────────────
async function loadDashboard() {
  const [runs, models, cfg] = await Promise.all([
    api('/runs'), api('/models'), api('/config'),
  ]);
  const total = runs.length;
  const green = runs.filter(r => /успешно|passed|✅/.test(r.status || '')).length;
  const cost = runs.reduce((s, r) => s + (parseFloat(r.cost) || 0), 0).toFixed(2);
  $('#dashboard').innerHTML = `
    <div class="cards">
      <div class="card"><div class="num">${total}</div><div class="lbl">прогонов</div></div>
      <div class="card"><div class="num">${green}</div><div class="lbl">зелёных</div></div>
      <div class="card"><div class="num">$${cost}</div><div class="lbl">суммарно</div></div>
      <div class="card"><div class="num">${models.length}</div><div class="lbl">ролей</div></div>
    </div>
    <h3>Модели команды</h3>
    <table><tr><th>Роль</th><th>Модель</th></tr>
      ${models.map(m => `<tr><td>${esc(m.label)}</td><td><code>${esc(m.name)}</code></td></tr>`).join('')}
    </table>
    <h3>Бюджет</h3>
    <p>soft <b>$${cfg.soft_budget}</b> · hard <b>$${cfg.hard_budget}</b> · fix-попыток <b>${cfg.max_fix_attempts}</b></p>`;
}

// ── Модели ────────────────────────────────────────────────────
async function loadModels() {
  const models = await api('/models');
  let catalog = [];
  try { catalog = await api('/models/catalog/live'); }
  catch (e) { catalog = await api('/models/catalog'); }
  catalog.sort((a, b) => (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
  $('#models').innerHTML = `
    <table><tr><th>Роль</th><th>Модель</th><th>temp</th><th>timeout</th><th></th></tr>
    ${models.map(m => {
      const currentInCatalog = catalog.some(c => c.id === m.name);
      const opts = (currentInCatalog ? '' : `<option value="${esc(m.name)}" selected>${esc(m.name)} (текущая)</option>`)
        + catalog.map(c => `<option value="${esc(c.id)}" ${c.id === m.name ? 'selected' : ''}>${esc(c.id)}</option>`).join('');
      return `
      <tr>
        <td>${esc(m.label)}</td>
        <td><select class="m-name" data-role="${m.role}">${opts}</select></td>
        <td><input class="m-temp" data-role="${m.role}" type="number" step="0.1" value="${m.temperature}"></td>
        <td><input class="m-timeout" data-role="${m.role}" type="number" value="${m.timeout}"></td>
        <td><button data-role="${m.role}" class="save-model">💾</button></td>
      </tr>`;
    }).join('')}
    </table>
    <p class="hint">Модель — из каталога OpenRouter. Применится со следующего прогона.</p>`;

  document.querySelectorAll('.save-model').forEach(btn => {
    btn.addEventListener('click', async () => {
      const role = btn.dataset.role;
      const body = {
        name: $(`.m-name[data-role="${role}"]`).value,
        temperature: parseFloat($(`.m-temp[data-role="${role}"]`).value),
        timeout: parseInt($(`.m-timeout[data-role="${role}"]`).value),
      };
      await api(`/models/${role}`, {
        method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body),
      });
      btn.textContent = '✅';
      setTimeout(() => btn.textContent = '💾', 1200);
    });
  });
}

// ── Прогоны ───────────────────────────────────────────────────
async function loadRuns() {
  const runs = await api('/runs');
  if (!runs.length) { $('#runs').innerHTML = '<p>Прогонов пока нет.</p>'; return; }
  $('#runs').innerHTML = `
    <div id="run-detail"></div>
    <table><tr><th>Прогон</th><th>Статус</th><th>Цена</th><th>Время</th><th></th></tr>
    ${runs.map(r => `
      <tr>
        <td><code>${esc(r.id)}</code></td>
        <td>${esc(r.status || '—')}</td>
        <td>$${esc(r.cost || '—')}</td>
        <td>${esc(r.time || '—')}с</td>
        <td><button class="view-run" data-id="${r.id}">открыть</button></td>
      </tr>`).join('')}
    </table>`;

  document.querySelectorAll('.view-run').forEach(btn => {
    btn.addEventListener('click', async () => {
      const detail = $('#run-detail');
      detail.innerHTML = '<p>Загрузка…</p>';
      try {
        const d = await api('/runs/' + btn.dataset.id);
        const gates = Object.entries(d.gates || {}).map(([k, v]) =>
          `<details><summary>${esc(k)}</summary><pre>${esc(v)}</pre></details>`).join('');
        detail.innerHTML =
          `<h3>Прогон ${esc(d.id)} <button class="close-detail">✕</button></h3>` +
          `${gates}<pre>${esc((d.report || '').slice(0, 4000))}</pre>`;
        detail.scrollIntoView({ behavior: 'smooth', block: 'start' });
        detail.querySelector('.close-detail').addEventListener('click', () => detail.innerHTML = '');
      } catch (e) {
        detail.innerHTML = `<p class="err">Не удалось загрузить: ${esc(e.message)}</p>`;
      }
    });
  });
}

// ── Git ───────────────────────────────────────────────────────
async function loadRepos() {
  const repos = await api('/repos');
  $('#repos').innerHTML = `
    <table><tr><th>Репо</th><th>Что это</th><th>Ссылка</th></tr>
    ${repos.map(r => `
      <tr>
        <td><code>${esc(r.name)}</code></td>
        <td>${esc(r.desc)}</td>
        <td><a href="${esc(r.url)}" target="_blank">${esc(r.url)}</a></td>
      </tr>`).join('')}
    </table>`;
}

// ── Бюджет ────────────────────────────────────────────────────
async function loadConfig() {
  const cfg = await api('/config');
  $('#config').innerHTML = `
    <table>
      <tr><td>Soft budget</td><td><b>$${cfg.soft_budget}</b></td></tr>
      <tr><td>Hard budget</td><td><b>$${cfg.hard_budget}</b></td></tr>
      <tr><td>Fix-попыток (фаза B)</td><td><b>${cfg.max_fix_attempts}</b></td></tr>
      <tr><td>Доводка после арбитра (D2)</td><td><b>${cfg.max_arbiter_fix_attempts}</b></td></tr>
    </table>
    <p class="hint">Правки бюджета/лимитов — следующим шагом (пишутся в team_config.json + env).</p>`;
}

// ── Роли ──────────────────────────────────────────────────────
async function loadRoles() {
  const roles = await api('/roles');
  $('#roles').innerHTML = roles.map(r => `
    <div class="role-card">
      <h3>${esc(r.role)} ${r.model ? `<code>${esc(r.model)}</code>` : ''}</h3>
      <p class="role-goal"><b>Цель:</b> ${esc(r.goal)}</p>
      <details><summary>Backstory</summary><p>${esc(r.backstory)}</p></details>
    </div>`).join('');
}

// ── Пайплайн ──────────────────────────────────────────────────
async function loadPipeline() {
  const d = await api('/pipeline');
  const c = d.config;
  $('#pipeline').innerHTML = `
    <p class="hint">fix-попыток <b>${c.max_fix_attempts}</b> · доводка после арбитра <b>${c.max_arbiter_fix_attempts}</b> · бюджет soft/hard <b>$${c.soft_budget}</b>/<b>$${c.hard_budget}</b></p>
    <table><tr><th>Фаза</th><th>Исполнитель</th><th>Что делает</th><th>Гейт</th></tr>
    ${d.stages.map(s => `
      <tr>
        <td><b>${esc(s.phase)}</b></td>
        <td>${esc(s.actor)}</td>
        <td>${esc(s.desc)}</td>
        <td><code>${esc(s.gate || '—')}</code></td>
      </tr>`).join('')}
    </table>`;
}

// ── Запуск ────────────────────────────────────────────────────
let runPoller = null;

function loadRun() {
  renderRunForm();
  refreshRunStatus();
}

function renderRunForm() {
  $('#run').innerHTML = `
    <div class="run-form">
      <h3>Запустить прогон</h3>
      <label>Режим
        <select id="run-mode">
          <option value="greenfield">greenfield — проект с нуля</option>
          <option value="enhance">enhance — доработка репо</option>
        </select>
      </label>
      <label id="repo-field" style="display:none">Репо (owner/name)
        <input id="run-repo" placeholder="druner-ai/cardputer-panel">
      </label>
      <label>Задача
        <textarea id="run-task" rows="4" placeholder="Что сделать команде…"></textarea>
      </label>
      <button id="run-start">▶ Запустить</button>
      <span id="run-msg"></span>
    </div>
    <div id="run-progress"></div>`;

  $('#run-mode').addEventListener('change', (e) => {
    $('#repo-field').style.display = e.target.value === 'enhance' ? 'block' : 'none';
  });
  $('#run-start').addEventListener('click', async () => {
    const body = {
      task: $('#run-task').value,
      mode: $('#run-mode').value,
      repo: $('#run-repo').value.trim() || null,
    };
    const msg = $('#run-msg');
    msg.textContent = 'Запускаю…';
    msg.className = 'hint';
    try {
      await api('/run', {
        method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body),
      });
      msg.textContent = '✅ Запущен';
      msg.className = 'ok';
      startRunPoller();
      refreshRunStatus();
    } catch (e) {
      msg.textContent = '❌ ' + e.message;
      msg.className = 'err';
    }
  });
}

function startRunPoller() {
  if (runPoller) return;
  runPoller = setInterval(refreshRunStatus, 4000);
}

function stopRunPoller() {
  if (runPoller) { clearInterval(runPoller); runPoller = null; }
}

async function refreshRunStatus() {
  let st;
  try { st = await api('/run/status'); } catch (e) { return; }
  const el = $('#run-progress');
  if (!st.pid) { el.innerHTML = ''; return; }
  const mm = Math.floor(st.elapsed / 60);
  const ss = String(st.elapsed % 60).padStart(2, '0');
  const log = (st.log_tail || []).join('\n');
  el.innerHTML = `
    <div class="role-card">
      <h3>${st.running ? '🟢 Прогон идёт' : '🏁 Прогон завершён'} <code>pid ${st.pid}</code></h3>
      <p>${esc(st.mode)}${st.repo ? ' · ' + esc(st.repo) : ''} · прошло <b>${mm}:${ss}</b></p>
      <p class="hint">${esc(st.task)}</p>
      <pre>${esc(log) || '…'}</pre>
    </div>`;
  if (st.running) { startRunPoller(); }
  else {
    stopRunPoller();
    el.innerHTML += '<p class="hint">Готово — результат во вкладке «Прогоны».</p>';
  }
}

loadDashboard();
