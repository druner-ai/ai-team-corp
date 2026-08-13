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
    <table><tr><th>Прогон</th><th>Статус</th><th>Цена</th><th>Время</th><th></th></tr>
    ${runs.map(r => `
      <tr>
        <td><code>${esc(r.id)}</code></td>
        <td>${esc(r.status || '—')}</td>
        <td>$${esc(r.cost || '—')}</td>
        <td>${esc(r.time || '—')}с</td>
        <td><button class="view-run" data-id="${r.id}">открыть</button></td>
      </tr>`).join('')}
    </table>
    <div id="run-detail"></div>`;

  document.querySelectorAll('.view-run').forEach(btn => {
    btn.addEventListener('click', async () => {
      const d = await api('/runs/' + btn.dataset.id);
      const gates = Object.entries(d.gates).map(([k, v]) =>
        `<details><summary>${esc(k)}</summary><pre>${esc(v)}</pre></details>`).join('');
      $('#run-detail').innerHTML = `<h3>${esc(d.id)}</h3>${gates}<pre>${esc(d.report.slice(0, 4000))}</pre>`;
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

loadDashboard();
