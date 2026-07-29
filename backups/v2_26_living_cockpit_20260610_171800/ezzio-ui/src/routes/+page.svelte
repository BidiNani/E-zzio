<script>
  import { onMount } from 'svelte';
  import { api, pretty, safeValue } from '$lib/api.js';

  let root = $state(null);
  let maintenance = $state(null);
  let safeActions = $state(null);
  let queue = $state(null);
  let cloud = $state(null);
  let routers = $state(null);

  let activePanel = $state('ledger');
  let commanderText = $state('E-ZZIO, fais un état rapide de ton système.');
  let commanderOutput = $state({ ok: true, reply: 'Prêt.' });
  let busy = $state(false);
  let lastRefresh = $state('—');
  let autoRefresh = $state(true);

  const panels = [
    ['ledger', 'Ledger'],
    ['routers', 'Routeurs'],
    ['cloud', 'Cloud'],
    ['raw', 'Raw']
  ];

  function badgeClass(value) {
    if (value === true || value === 0 || value === 'ok') return 'badge ok';
    if (value === false || value === null || value === undefined) return 'badge warn';
    return 'badge';
  }

  async function refreshAll() {
    const [rootRes, maintRes, safeRes, queueRes, cloudRes, routerRes] = await Promise.all([
      api('/status'),
      api('/maintenance/audit'),
      api('/safe-actions/status'),
      api('/safe-actions/queue?limit=25'),
      api('/cloud-brain/status'),
      api('/router-status')
    ]);

    root = rootRes;
    maintenance = maintRes;
    safeActions = safeRes;
    queue = queueRes;
    cloud = cloudRes;
    routers = routerRes;
    lastRefresh = new Date().toLocaleTimeString();
  }

  async function sendCommander(text = null) {
    const payload = text ?? commanderText;
    if (!payload.trim()) return;

    commanderText = payload;
    busy = true;

    try {
      commanderOutput = await api('/api/chat/commander', {
        method: 'POST',
        body: JSON.stringify({
          text: payload,
          session: 'svelte-ui'
        })
      });
    } finally {
      busy = false;
      await refreshAll();
    }
  }

  async function quick(text) {
    commanderText = text;
    await sendCommander(text);
  }

  function valueOf(obj, path, fallback = '—') {
    try {
      const value = path.split('.').reduce((acc, key) => acc?.[key], obj);
      return safeValue(value ?? fallback);
    } catch {
      return fallback;
    }
  }

  onMount(() => {
    refreshAll();

    const timer = setInterval(() => {
      if (autoRefresh) refreshAll();
    }, 12000);

    return () => clearInterval(timer);
  });
</script>

<svelte:head>
  <title>E-ZZIO — Cockpit Local</title>
</svelte:head>

<header class="topbar">
  <div class="topbar-inner">
    <div class="brand">
      <div class="orb"></div>
      <div>
        <h1>E-ZZIO Cockpit Local</h1>
        <p>Ami IA local d’Enrik — Commander, Safe Actions, Maintenance, Cloud Brain.</p>
      </div>
    </div>

    <div class="badges">
      <span class={badgeClass(root?.ok)}>API {root?.ok ? 'OK' : '—'}</span>
      <span class="badge ok">CPU/RAM only</span>
      <span class="badge ok">GPU untouched</span>
      <span class="badge ok">No ads</span>
      <span class="badge">Refresh {lastRefresh}</span>
    </div>
  </div>
</header>

<main class="container">
  <div class="grid">
    <section class="card span-3">
      <div class="card-head">
        <div>
          <h2>Système</h2>
          <div class="hint">État général FastAPI</div>
        </div>
      </div>
      <div class="card-body kv">
        <div class="kv-row"><span class="key">OK</span><span class="value">{valueOf(root, 'ok')}</span></div>
        <div class="kv-row"><span class="key">Version</span><span class="value">{valueOf(root, 'version')}</span></div>
        <div class="kv-row"><span class="key">GPU</span><span class="value">{valueOf(root, 'policy.ezzio_gpu_policy')}</span></div>
        <div class="kv-row"><span class="key">No ads</span><span class="value">{valueOf(root, 'policy.no_ads')}</span></div>
      </div>
    </section>

    <section class="card span-3">
      <div class="card-head">
        <div>
          <h2>Maintenance</h2>
          <div class="hint">Audit projet</div>
        </div>
      </div>
      <div class="card-body kv">
        <div class="kv-row"><span class="key">OK</span><span class="value">{valueOf(maintenance, 'ok')}</span></div>
        <div class="kv-row"><span class="key">Fichiers</span><span class="value">{valueOf(maintenance, 'checked_count')}</span></div>
        <div class="kv-row"><span class="key">Bad</span><span class="value">{valueOf(maintenance, 'bad_count')}</span></div>
        <div class="kv-row"><span class="key">Dust</span><span class="value">{valueOf(maintenance, 'dust_candidate_count')}</span></div>
      </div>
    </section>

    <section class="card span-3">
      <div class="card-head">
        <div>
          <h2>Safe Actions</h2>
          <div class="hint">Ledger append-only</div>
        </div>
      </div>
      <div class="card-body kv">
        <div class="kv-row"><span class="key">Queued</span><span class="value">{valueOf(safeActions, 'queued_count')}</span></div>
        <div class="kv-row"><span class="key">Executed</span><span class="value">{valueOf(safeActions, 'executed_count')}</span></div>
        <div class="kv-row"><span class="key">Cancelled</span><span class="value">{valueOf(safeActions, 'cancelled_count')}</span></div>
        <div class="kv-row"><span class="key">Pending</span><span class="value">{valueOf(safeActions, 'pending_count')}</span></div>
      </div>
    </section>

    <section class="card span-3">
      <div class="card-head">
        <div>
          <h2>Cloud Brain</h2>
          <div class="hint">Optionnel, redacted</div>
        </div>
      </div>
      <div class="card-body kv">
        <div class="kv-row"><span class="key">OK</span><span class="value">{valueOf(cloud, 'ok')}</span></div>
        <div class="kv-row"><span class="key">Allow send</span><span class="value">{valueOf(cloud, 'allow_send')}</span></div>
        <div class="kv-row"><span class="key">Mode</span><span class="value">{valueOf(cloud, 'mode')}</span></div>
        <div class="kv-row"><span class="key">Usage</span><span class="value">{valueOf(cloud, 'usage.total_today')}</span></div>
      </div>
    </section>

    <section class="card span-7">
      <div class="card-head">
        <div>
          <h2>Commander</h2>
          <div class="hint">Dialogue local → intention → action sûre → confirmation</div>
        </div>
        <span class={busy ? 'badge warn' : 'badge ok'}>{busy ? 'Travail...' : 'Prêt'}</span>
      </div>

      <div class="card-body">
        <textarea bind:value={commanderText}></textarea>

        <div class="actions">
          <button class="primary" onclick={() => sendCommander()} disabled={busy}>Envoyer</button>
          <button onclick={() => quick('E-ZZIO, fais un état rapide de ton système.')} disabled={busy}>État rapide</button>
          <button onclick={() => quick('E-ZZIO, lance un audit.')} disabled={busy}>Audit</button>
          <button onclick={() => quick('E-ZZIO, prépare la prochaine optimisation PC sans rien casser.')} disabled={busy}>Préparer optimisation</button>
          <button class="primary" onclick={() => quick('CONFIRME')} disabled={busy}>CONFIRME</button>
          <button class="danger" onclick={() => quick('annule')} disabled={busy}>Annule</button>
        </div>

        <div class="reply">
          <pre>{pretty(commanderOutput)}</pre>
        </div>
      </div>
    </section>

    <section class="card span-5">
      <div class="card-head">
        <div>
          <h2>Cloud Providers</h2>
          <div class="hint">Les clés ne sont jamais affichées</div>
        </div>
      </div>

      <div class="card-body">
        <div class="list">
          {#each cloud?.providers ?? [] as provider}
            <div class="item">
              <div class="item-title">
                <span>{provider.provider}</span>
                <span class={provider.usable ? 'badge ok' : 'badge warn'}>{provider.usable ? 'usable' : 'locked'}</span>
              </div>
              <div class="item-sub">
                configured={provider.configured} · model={provider.model || '—'} · remaining={provider.remaining}
              </div>
            </div>
          {/each}
        </div>

        <div class="footer-note">
          Cloud = optionnel. E-ZZIO local garde les actions, confirmations et journaux.
        </div>
      </div>
    </section>

    <section class="card span-12">
      <div class="card-head">
        <div>
          <h2>Observatoire</h2>
          <div class="hint">Ledger, routeurs, cloud et raw state</div>
        </div>

        <div class="tabs">
          {#each panels as panel}
            <button
              class:active={activePanel === panel[0]}
              class="tab"
              onclick={() => (activePanel = panel[0])}
            >
              {panel[1]}
            </button>
          {/each}
          <button class="tab" onclick={refreshAll}>Rafraîchir</button>
          <button class="tab" onclick={() => (autoRefresh = !autoRefresh)}>
            Auto {autoRefresh ? 'ON' : 'OFF'}
          </button>
        </div>
      </div>

      <div class="card-body">
        {#if activePanel === 'ledger'}
          <pre>{pretty(queue)}</pre>
        {:else if activePanel === 'routers'}
          <pre>{pretty(routers)}</pre>
        {:else if activePanel === 'cloud'}
          <pre>{pretty(cloud)}</pre>
        {:else}
          <pre>{pretty({ root, maintenance, safeActions, cloud })}</pre>
        {/if}
      </div>
    </section>
  </div>
</main>
