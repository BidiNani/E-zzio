<script>
  import { onMount } from 'svelte';
  import { api, pretty, safeValue, shortText } from '$lib/api.js';

  let root = $state(null);
  let maintenance = $state(null);
  let safeActions = $state(null);
  let queue = $state(null);
  let cloud = $state(null);
  let routers = $state(null);
  let human = $state(null);
  let journal = $state(null);
  let supervisor = $state(null);
  let performance = $state(null);
  let forge = $state(null);
  let vision = $state(null);

  let activePanel = $state('timeline');
  let commanderText = $state('E-ZZIO, fais un état rapide de ton système.');
  let commanderOutput = $state({ ok: true, reply: 'Prêt.' });
  let busy = $state(false);
  let lastRefresh = $state('—');
  let autoRefresh = $state(true);

  const panels = [
    ['timeline', 'Timeline'],
    ['journal', 'Journal'],
    ['modules', 'Modules'],
    ['ledger', 'Ledger'],
    ['routers', 'Routeurs'],
    ['raw', 'Raw']
  ];

  function valueOf(obj, path, fallback = '—') {
    try {
      const value = path.split('.').reduce((acc, key) => acc?.[key], obj);
      return safeValue(value ?? fallback);
    } catch {
      return fallback;
    }
  }

  function okish(obj) {
    return obj?.ok === true || obj?.online === true;
  }

  function badgeClass(value) {
    if (value === true || value === 0 || value === 'ok') return 'badge ok';
    if (value === false || value === null || value === undefined) return 'badge warn';
    return 'badge';
  }

  function moduleState(obj) {
    if (okish(obj)) return 'OK';
    if (obj?.online === false) return 'OFF';
    return '—';
  }

  function moduleBadge(obj) {
    if (okish(obj)) return 'badge ok';
    if (obj?.online === false) return 'badge warn';
    return 'badge';
  }

  function livingMood() {
    let score = 100;
    const warnings = [];

    if (!okish(root)) {
      score -= 25;
      warnings.push('API incertaine');
    }

    const badCount = Number(maintenance?.bad_count ?? 0);
    if (badCount > 0) {
      score -= Math.min(35, badCount * 10);
      warnings.push(`${badCount} problème(s) audit`);
    }

    const pending = Number(safeActions?.pending_count ?? 0);
    if (pending > 0) {
      score -= Math.min(20, pending * 4);
      warnings.push(`${pending} action(s) en attente`);
    }

    if (cloud?.ok === false && cloud?.online === true) {
      score -= 5;
      warnings.push('cloud verrouillé ou indisponible');
    }

    score = Math.max(0, Math.min(100, score));

    let label = 'Calme et opérationnel';
    if (score < 85) label = 'Attentif';
    if (score < 65) label = 'À surveiller';
    if (score < 45) label = 'Besoin de maintenance';

    return {
      score,
      label,
      warnings: warnings.length ? warnings : ['Aucun signal critique'],
      focus: pending > 0 ? 'attente confirmation' : badCount > 0 ? 'audit' : 'assistance PC'
    };
  }

  function timelineItems() {
    const items = [];

    for (const q of queue?.items ?? queue?.queue ?? []) {
      items.push({
        kind: q.executed ? 'executed' : q.cancelled ? 'cancelled' : 'pending',
        title: q.action_id || q.action || 'safe-action',
        at: q.executed_at || q.cancelled_at || q.created_at || '—',
        text: q.summary || q.reason || q.description || q.proposal_id || '—'
      });
    }

    for (const e of journal?.events ?? journal?.items ?? journal?.recent_events ?? []) {
      items.push({
        kind: 'journal',
        title: e.type || e.event || 'journal',
        at: e.created_at || e.at || '—',
        text: e.summary || e.note || e.text || JSON.stringify(e).slice(0, 240)
      });
    }

    return items
      .filter(Boolean)
      .sort((a, b) => String(b.at).localeCompare(String(a.at)))
      .slice(0, 18);
  }

  function modules() {
    return [
      ['Backend', root, valueOf(root, 'version')],
      ['Maintenance', maintenance, `bad=${valueOf(maintenance, 'bad_count')}`],
      ['Safe Actions', safeActions, `pending=${valueOf(safeActions, 'pending_count')}`],
      ['Human Loop', human, valueOf(human, 'version')],
      ['Supervisor', supervisor, valueOf(supervisor, 'version')],
      ['Performance', performance, valueOf(performance, 'version')],
      ['Cloud Brain', cloud, `allow=${valueOf(cloud, 'allow_send')}`],
      ['Forge', forge, valueOf(forge, 'version')],
      ['Vision', vision, valueOf(vision, 'model')]
    ];
  }

  async function refreshAll() {
    const [
      rootRes,
      maintRes,
      safeRes,
      queueRes,
      cloudRes,
      routerRes,
      humanRes,
      journalRes,
      supervisorRes,
      performanceRes,
      forgeRes,
      visionRes
    ] = await Promise.all([
      api('/status', { timeoutMs: 15000 }),
      api('/maintenance/audit', { timeoutMs: 180000 }),
      api('/safe-actions/status', { timeoutMs: 30000 }),
      api('/safe-actions/queue?limit=30', { timeoutMs: 30000 }),
      api('/cloud-brain/status', { timeoutMs: 30000 }),
      api('/router-status', { timeoutMs: 30000 }),
      api('/human/status', { timeoutMs: 30000 }),
      api('/human/journal?limit=12', { timeoutMs: 30000 }),
      api('/supervisor/status', { timeoutMs: 30000 }),
      api('/performance/status', { timeoutMs: 30000 }),
      api('/forge/status', { timeoutMs: 30000 }),
      api('/vision/status', { timeoutMs: 30000 })
    ]);

    root = rootRes;
    maintenance = maintRes;
    safeActions = safeRes;
    queue = queueRes;
    cloud = cloudRes;
    routers = routerRes;
    human = humanRes;
    journal = journalRes;
    supervisor = supervisorRes;
    performance = performanceRes;
    forge = forgeRes;
    vision = visionRes;

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
        timeoutMs: 240000,
        body: JSON.stringify({
          text: payload,
          session: 'living-cockpit'
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

  $effect(() => {
    const mood = livingMood();
    document.documentElement.style.setProperty('--living-score', `${mood.score}%`);
  });

  onMount(() => {
    refreshAll();

    const timer = setInterval(() => {
      if (autoRefresh) refreshAll();
    }, 12000);

    return () => clearInterval(timer);
  });
</script>

<svelte:head>
  <title>E-ZZIO — Living Cockpit</title>
</svelte:head>

<header class="topbar">
  <div class="topbar-inner">
    <div class="brand">
      <div class="orb"></div>
      <div>
        <h1>E-ZZIO Living Cockpit</h1>
        <p>Ami IA local d’Enrik — vivant, prudent, utile, sans pub, CPU/RAM only.</p>
      </div>
    </div>

    <div class="badges">
      <span class={badgeClass(root?.ok)}>API {root?.ok ? 'OK' : '—'}</span>
      <span class="badge ok">GPU untouched</span>
      <span class="badge ok">No ads</span>
      <span class={safeActions?.pending_count > 0 ? 'badge warn' : 'badge ok'}>
        pending {valueOf(safeActions, 'pending_count')}
      </span>
      <span class="badge">refresh {lastRefresh}</span>
    </div>
  </div>
</header>

<main class="container">
  <div class="grid">
    <section class="card glow span-4">
      <div class="card-head">
        <div>
          <h2>État vivant</h2>
          <div class="hint">Synthèse locale de santé et priorité</div>
        </div>
        <span class={livingMood().score >= 85 ? 'badge ok' : livingMood().score >= 65 ? 'badge warn' : 'badge bad'}>
          {livingMood().score}%
        </span>
      </div>

      <div class="card-body mood">
        <div class="kv">
          <div class="kv-row"><span class="key">Humeur</span><span class="value">{livingMood().label}</span></div>
          <div class="kv-row"><span class="key">Focus</span><span class="value">{livingMood().focus}</span></div>
          <div class="kv-row"><span class="key">Signaux</span><span class="value">{livingMood().warnings.join(' · ')}</span></div>
        </div>
        <div class="mood-line">
          <div class="mood-fill" style={`--w:${livingMood().score}%`}></div>
        </div>
      </div>
    </section>

    <section class="card span-2">
      <div class="card-head">
        <div>
          <h2>Maintenance</h2>
          <div class="hint">Audit</div>
        </div>
      </div>
      <div class="card-body kv">
        <div class="kv-row"><span class="key">OK</span><span class="value">{valueOf(maintenance, 'ok')}</span></div>
        <div class="kv-row"><span class="key">Bad</span><span class="value">{valueOf(maintenance, 'bad_count')}</span></div>
        <div class="kv-row"><span class="key">Dust</span><span class="value">{valueOf(maintenance, 'dust_candidate_count')}</span></div>
      </div>
    </section>

    <section class="card span-2">
      <div class="card-head">
        <div>
          <h2>Actions</h2>
          <div class="hint">Ledger</div>
        </div>
      </div>
      <div class="card-body kv">
        <div class="kv-row"><span class="key">Queued</span><span class="value">{valueOf(safeActions, 'queued_count')}</span></div>
        <div class="kv-row"><span class="key">Done</span><span class="value">{valueOf(safeActions, 'executed_count')}</span></div>
        <div class="kv-row"><span class="key">Pending</span><span class="value">{valueOf(safeActions, 'pending_count')}</span></div>
      </div>
    </section>

    <section class="card span-2">
      <div class="card-head">
        <div>
          <h2>Cloud</h2>
          <div class="hint">Optionnel</div>
        </div>
      </div>
      <div class="card-body kv">
        <div class="kv-row"><span class="key">OK</span><span class="value">{valueOf(cloud, 'ok')}</span></div>
        <div class="kv-row"><span class="key">Send</span><span class="value">{valueOf(cloud, 'allow_send')}</span></div>
        <div class="kv-row"><span class="key">Usage</span><span class="value">{valueOf(cloud, 'usage.total_today')}</span></div>
      </div>
    </section>

    <section class="card span-2">
      <div class="card-head">
        <div>
          <h2>Vision/Forge</h2>
          <div class="hint">Créatif</div>
        </div>
      </div>
      <div class="card-body kv">
        <div class="kv-row"><span class="key">Vision</span><span class="value">{moduleState(vision)}</span></div>
        <div class="kv-row"><span class="key">Forge</span><span class="value">{moduleState(forge)}</span></div>
        <div class="kv-row"><span class="key">Comfy</span><span class="value">{valueOf(forge, 'comfyui_online')}</span></div>
      </div>
    </section>

    <section class="card span-7">
      <div class="card-head">
        <div>
          <h2>Commander</h2>
          <div class="hint">Dialogue central → proposition → confirmation → exécution sûre</div>
        </div>
        <span class={busy ? 'badge warn' : 'badge ok'}>{busy ? 'Travail...' : 'Prêt'}</span>
      </div>

      <div class="card-body">
        <textarea bind:value={commanderText}></textarea>

        <div class="actions">
          <button class="primary" onclick={() => sendCommander()} disabled={busy}>Envoyer</button>
          <button onclick={() => quick('E-ZZIO, fais un état rapide de ton système.')} disabled={busy}>État</button>
          <button onclick={() => quick('E-ZZIO, lance un audit.')} disabled={busy}>Audit</button>
          <button onclick={() => quick('E-ZZIO, prépare la prochaine optimisation PC sans rien casser.')} disabled={busy}>Optimisation sûre</button>
          <button onclick={() => quick('E-ZZIO, résume ton journal récent.')} disabled={busy}>Journal</button>
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
          <h2>Modules</h2>
          <div class="hint">Présence des organes E-ZZIO</div>
        </div>
      </div>

      <div class="card-body">
        <div class="module-grid">
          {#each modules() as mod}
            <div class="module">
              <div class="item-title">
                <span class="module-name">{mod[0]}</span>
                <span class={moduleBadge(mod[1])}>{moduleState(mod[1])}</span>
              </div>
              <div class="module-detail">{shortText(mod[2], 80)}</div>
            </div>
          {/each}
        </div>
      </div>
    </section>

    <section class="card span-12">
      <div class="card-head">
        <div>
          <h2>Observatoire vivant</h2>
          <div class="hint">Timeline, journal, modules, ledger et routeurs</div>
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
        {#if activePanel === 'timeline'}
          <div class="timeline">
            {#each timelineItems() as item}
              <div class="timeline-item">
                <div class="timeline-top">
                  <span>{item.title}</span>
                  <span class={item.kind === 'executed' ? 'badge ok' : item.kind === 'cancelled' ? 'badge bad' : 'badge warn'}>
                    {item.kind}
                  </span>
                </div>
                <div class="timeline-text">{item.at}</div>
                <div class="timeline-text">{shortText(item.text, 260)}</div>
              </div>
            {/each}
          </div>
        {:else if activePanel === 'journal'}
          <pre>{pretty(journal)}</pre>
        {:else if activePanel === 'modules'}
          <pre>{pretty({
            root,
            maintenance,
            safeActions,
            human,
            supervisor,
            performance,
            cloud,
            forge,
            vision
          })}</pre>
        {:else if activePanel === 'ledger'}
          <pre>{pretty(queue)}</pre>
        {:else if activePanel === 'routers'}
          <pre>{pretty(routers)}</pre>
        {:else}
          <pre>{pretty({
            root,
            maintenance,
            safeActions,
            queue,
            human,
            journal,
            supervisor,
            performance,
            cloud,
            forge,
            vision
          })}</pre>
        {/if}
      </div>
    </section>
  </div>
</main>
