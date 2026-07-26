from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["ui-dashboard"])

HTML = r"""
<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <title>E-ZZIO Local Dashboard</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    :root {
      --bg: #0d1117;
      --panel: #161b22;
      --panel2: #0f1722;
      --text: #e6edf3;
      --muted: #8b949e;
      --ok: #3fb950;
      --warn: #d29922;
      --bad: #f85149;
      --accent: #58a6ff;
      --line: #30363d;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Segoe UI", system-ui, sans-serif;
      background: radial-gradient(circle at top left, #162033 0, var(--bg) 38%);
      color: var(--text);
    }
    header {
      padding: 22px 28px;
      border-bottom: 1px solid var(--line);
      background: rgba(13, 17, 23, 0.84);
      position: sticky;
      top: 0;
      backdrop-filter: blur(12px);
      z-index: 2;
    }
    h1 { margin: 0; font-size: 26px; letter-spacing: .4px; }
    .subtitle { color: var(--muted); margin-top: 6px; }
    main { padding: 24px; max-width: 1400px; margin: 0 auto; }
    .grid {
      display: grid;
      grid-template-columns: repeat(12, 1fr);
      gap: 16px;
    }
    .card {
      background: linear-gradient(180deg, var(--panel), var(--panel2));
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 18px;
      box-shadow: 0 12px 28px rgba(0,0,0,.24);
    }
    .span4 { grid-column: span 4; }
    .span6 { grid-column: span 6; }
    .span8 { grid-column: span 8; }
    .span12 { grid-column: span 12; }
    h2 { margin: 0 0 12px 0; font-size: 17px; color: #c9d1d9; }
    .kv {
      display: grid;
      grid-template-columns: 160px 1fr;
      gap: 8px 12px;
      font-size: 14px;
    }
    .key { color: var(--muted); }
    .value { overflow-wrap: anywhere; }
    .pill {
      display: inline-block;
      padding: 3px 9px;
      border-radius: 999px;
      font-size: 12px;
      border: 1px solid var(--line);
      background: #111827;
    }
    .ok { color: var(--ok); }
    .warn { color: var(--warn); }
    .bad { color: var(--bad); }
    button {
      border: 1px solid var(--line);
      background: #21262d;
      color: var(--text);
      border-radius: 10px;
      padding: 9px 12px;
      cursor: pointer;
      margin-right: 8px;
    }
    button:hover { border-color: var(--accent); }
    textarea {
      width: 100%;
      min-height: 90px;
      border: 1px solid var(--line);
      border-radius: 12px;
      background: #0d1117;
      color: var(--text);
      padding: 12px;
      resize: vertical;
      font-family: inherit;
    }
    pre {
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      background: #0d1117;
      border: 1px solid var(--line);
      padding: 12px;
      border-radius: 12px;
      max-height: 360px;
      overflow: auto;
      color: #c9d1d9;
    }
    .small { font-size: 12px; color: var(--muted); }
    .row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
    @media (max-width: 900px) {
      .span4, .span6, .span8, .span12 { grid-column: span 12; }
      .kv { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
<header>
  <h1>🧠 E-ZZIO Local Dashboard</h1>
  <div class="subtitle">Interface locale — sans pub, sans tracking, CPU/RAM only, GPU untouched.</div>
</header>

<main>
  <div class="grid">
    <section class="card span4">
      <h2>État global</h2>
      <div id="rootStatus" class="kv"></div>
    </section>

    <section class="card span4">
      <h2>Maintenance</h2>
      <div id="maintenance" class="kv"></div>
    </section>

    <section class="card span4">
      <h2>Safe Actions</h2>
      <div id="safeActions" class="kv"></div>
    </section>

    <section class="card span6">
      <h2>Commander</h2>
      <textarea id="cmdText">E-ZZIO, fais un état rapide de ton système.</textarea>
      <div class="row" style="margin-top:10px;">
        <button onclick="sendCommander()">Envoyer</button>
        <button onclick="quick('E-ZZIO, prépare la prochaine optimisation PC sans rien casser.')">Préparer optimisation</button>
        <button onclick="quick('CONFIRME')">CONFIRME</button>
        <button onclick="quick('annule')">Annule</button>
      </div>
      <pre id="cmdOutput">Prêt.</pre>
    </section>

    <section class="card span6">
      <h2>Cloud Brain</h2>
      <div id="cloudBrain" class="kv"></div>
      <div class="small" style="margin-top:10px;">Les clés ne sont jamais affichées. L'envoi cloud dépend de allow_send.</div>
    </section>

    <section class="card span12">
      <h2>Ledger Safe Actions</h2>
      <div class="row">
        <button onclick="refreshAll()">Rafraîchir</button>
        <button onclick="loadJson('/safe-actions/queue?limit=20', 'ledgerRaw')">Voir queue brute</button>
        <button onclick="loadJson('/router-status', 'ledgerRaw')">Voir routeurs</button>
      </div>
      <pre id="ledgerRaw">Chargement...</pre>
    </section>
  </div>
</main>

<script>
async function getJson(url, options) {
  try {
    const res = await fetch(url, options || {});
    const text = await res.text();
    try { return JSON.parse(text); }
    catch { return { ok:false, error:"Non JSON", raw:text }; }
  } catch (e) {
    return { ok:false, error:String(e) };
  }
}

function pill(value) {
  if (value === true || value === "ok" || value === 0) return '<span class="pill ok">' + value + '</span>';
  if (value === false || value === null || value === undefined) return '<span class="pill warn">' + value + '</span>';
  return '<span class="pill">' + String(value) + '</span>';
}

function renderKV(id, data, keys) {
  const el = document.getElementById(id);
  el.innerHTML = "";
  keys.forEach(k => {
    const v = k.split(".").reduce((a, b) => a && a[b], data);
    el.innerHTML += '<div class="key">' + k + '</div><div class="value">' + pill(v) + '</div>';
  });
}

async function refreshAll() {
  const root = await getJson('/status');
  renderKV('rootStatus', root, ['ok', 'version', 'policy.ezzio_gpu_policy', 'policy.no_ads']);

  const maint = await getJson('/maintenance/audit');
  renderKV('maintenance', maint, ['ok', 'checked_count', 'bad_count', 'dust_candidate_count']);

  const safe = await getJson('/safe-actions/status');
  renderKV('safeActions', safe, ['ok', 'version', 'queued_count', 'executed_count', 'cancelled_count', 'pending_count']);

  const cloud = await getJson('/cloud-brain/status');
  renderKV('cloudBrain', cloud, ['ok', 'version', 'allow_send', 'mode', 'usage.total_today', 'cache_count']);

  const queue = await getJson('/safe-actions/queue?limit=20');
  document.getElementById('ledgerRaw').textContent = JSON.stringify(queue, null, 2);
}

async function loadJson(url, target) {
  const data = await getJson(url);
  document.getElementById(target).textContent = JSON.stringify(data, null, 2);
}

async function sendCommander() {
  const text = document.getElementById('cmdText').value;
  const body = JSON.stringify({ text: text, session: "ui" });
  const data = await getJson('/api/chat/commander', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: body
  });
  document.getElementById('cmdOutput').textContent = JSON.stringify(data, null, 2);
  refreshAll();
}

function quick(text) {
  document.getElementById('cmdText').value = text;
  sendCommander();
}

refreshAll();
setInterval(refreshAll, 20000);
</script>
</body>
</html>
"""

@router.get("/ui", response_class=HTMLResponse)
async def get_ui_dashboard():
    return HTML
