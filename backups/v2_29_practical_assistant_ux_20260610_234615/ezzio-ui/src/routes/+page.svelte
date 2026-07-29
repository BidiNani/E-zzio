<script>
  import { onMount } from 'svelte';
  import { api, pretty, pickReply, statusText, shortText } from '$lib/api.js';

  let root = $state(null);
  let maintenance = $state(null);
  let safeActions = $state(null);
  let cloud = $state(null);
  let vision = $state(null);
  let forge = $state(null);
  let researchStatus = $state(null);

  let tab = $state('chat');
  let busy = $state(false);
  let lastRefresh = $state('—');
  let advanced = $state(false);

  let chatText = $state('E-ZZIO, fais un état rapide de ton système.');
  let chatResult = $state({ ok: true, reply: 'Prêt.' });

  let researchText = $state('optimiser Ollama CPU Ryzen 9 5900X');
  let researchResult = $state({ ok: true, reply: 'Recherche prête. Lance une requête.' });

  let imagePath = $state('G:\\AI\\E-zzio\\forge\\vision\\inbox\\ezzio_test_vision.png');
  let visionPrompt = $state('Analyse cette image précisément. Décris ce que tu vois et indique l’action utile suivante.');
  let visionResult = $state({ ok: true, reply: 'Vision prête. Colle un chemin image puis clique Analyser.' });

  function clsStatus(obj) {
    if (obj?.ok === true || obj?.online === true) return 'badge ok';
    if (obj?.online === false || obj?.ok === false) return 'badge warn';
    return 'badge';
  }

  function valueOf(obj, path, fallback = '—') {
    try {
      const value = path.split('.').reduce((acc, key) => acc?.[key], obj);
      if (value === undefined || value === null || value === '') return fallback;
      if (typeof value === 'object') return JSON.stringify(value);
      return value;
    } catch {
      return fallback;
    }
  }

  async function refreshStatus() {
    const [rootRes, maintRes, safeRes, cloudRes, visionRes, forgeRes, researchRes] = await Promise.all([
      api('/status', { timeoutMs: 15000 }),
      api('/maintenance/audit', { timeoutMs: 180000 }),
      api('/safe-actions/status', { timeoutMs: 30000 }),
      api('/cloud-brain/status', { timeoutMs: 30000 }),
      api('/vision/status', { timeoutMs: 30000 }),
      api('/forge/status', { timeoutMs: 30000 }),
      api('/knowledge/status', { timeoutMs: 30000 })
    ]);

    root = rootRes;
    maintenance = maintRes;
    safeActions = safeRes;
    cloud = cloudRes;
    vision = visionRes;
    forge = forgeRes;
    researchStatus = researchRes;
    lastRefresh = new Date().toLocaleTimeString();
  }

  async function sendChat(text = null) {
    const payload = text ?? chatText;
    if (!payload.trim()) return;

    chatText = payload;
    busy = true;
    try {
      chatResult = await api('/api/chat/commander', {
        method: 'POST',
        timeoutMs: 240000,
        body: JSON.stringify({
          text: payload,
          session: 'functional-cockpit'
        })
      });
    } finally {
      busy = false;
      await refreshStatus();
    }
  }

  async function sendResearch() {
    if (!researchText.trim()) return;

    busy = true;
    try {
      let result = await api('/knowledge/search', {
        method: 'POST',
        timeoutMs: 180000,
        body: JSON.stringify({
          query: researchText,
          limit: 8
        })
      });

      if (result?.ok === false || result?.status === 404 || result?.error) {
        result = await api('/api/chat/hybrid', {
          method: 'POST',
          timeoutMs: 240000,
          body: JSON.stringify({
            text: `Recherche/documentation demandée : ${researchText}. Réponds prudemment, cite les limites si tu n’as pas de source.`,
            provider: 'auto',
            force_cloud: false
          })
        });
      }

      researchResult = result;
    } finally {
      busy = false;
      await refreshStatus();
    }
  }

  async function analyzeImage() {
    if (!imagePath.trim()) return;

    busy = true;
    try {
      visionResult = await api('/vision/analyze-path', {
        method: 'POST',
        timeoutMs: 300000,
        body: JSON.stringify({
          path: imagePath,
          prompt: visionPrompt
        })
      });
    } finally {
      busy = false;
      await refreshStatus();
    }
  }

  function researchItems() {
    return researchResult?.results || researchResult?.items || researchResult?.sources || [];
  }

  onMount(() => {
    refreshStatus();
    const timer = setInterval(refreshStatus, 15000);
    return () => clearInterval(timer);
  });
</script>

<svelte:head>
  <title>E-ZZIO — Fonctionnel</title>
</svelte:head>

<header class="topbar">
  <div class="topbar-inner">
    <div class="brand">
      <div class="orb"></div>
      <div>
        <h1>E-ZZIO Functional Cockpit</h1>
        <p>Chat, recherche, analyse image, état système — local-first, sans pub, GPU untouched.</p>
      </div>
    </div>

    <div class="badges">
      <span class={clsStatus(root)}>API {statusText(root)}</span>
      <span class={clsStatus(vision)}>Vision {statusText(vision)}</span>
      <span class={clsStatus(forge)}>Forge {statusText(forge)}</span>
      <span class={clsStatus(cloud)}>Cloud {statusText(cloud)}</span>
      <span class="badge ok">No ads</span>
      <span class="badge">refresh {lastRefresh}</span>
      <button onclick={() => (advanced = !advanced)}>{advanced ? 'Simple' : 'Avancé'}</button>
    </div>
  </div>
</header>

<main class="container">
  <div class="grid">
    <section class="card span-12">
      <div class="card-body status-grid">
        <div class="status-tile">
          <div class="status-name">Maintenance</div>
          <div class="status-value">{valueOf(maintenance, 'bad_count')} problème(s)</div>
        </div>
        <div class="status-tile">
          <div class="status-name">Safe Actions</div>
          <div class="status-value">{valueOf(safeActions, 'pending_count')} attente(s)</div>
        </div>
        <div class="status-tile">
          <div class="status-name">Vision</div>
          <div class="status-value">{valueOf(vision, 'model')}</div>
        </div>
        <div class="status-tile">
          <div class="status-name">Recherche</div>
          <div class="status-value">{statusText(researchStatus)}</div>
        </div>
      </div>
    </section>

    <section class="card span-12">
      <div class="card-head">
        <div>
          <h2>Mode de travail</h2>
          <div class="hint">Choisis ce que tu veux faire maintenant.</div>
        </div>
      </div>

      <div class="card-body">
        <div class="tabs">
          <button class:active={tab === 'chat'} onclick={() => (tab = 'chat')}>Chat</button>
          <button class:active={tab === 'research'} onclick={() => (tab = 'research')}>Recherche</button>
          <button class:active={tab === 'vision'} onclick={() => (tab = 'vision')}>Analyse image</button>
          <button class:active={tab === 'system'} onclick={() => (tab = 'system')}>Système</button>
        </div>
      </div>
    </section>

    {#if tab === 'chat'}
      <section class="card span-12">
        <div class="card-head">
          <div>
            <h2>Chat E-ZZIO</h2>
            <div class="hint">Dialogue principal. Les actions réelles passent par confirmation.</div>
          </div>
          <span class={busy ? 'badge warn' : 'badge ok'}>{busy ? 'Travail...' : 'Prêt'}</span>
        </div>

        <div class="card-body">
          <textarea bind:value={chatText}></textarea>

          <div class="actions">
            <button class="primary" onclick={() => sendChat()} disabled={busy}>Envoyer</button>
            <button onclick={() => sendChat('E-ZZIO, fais un état rapide de ton système.')} disabled={busy}>État rapide</button>
            <button onclick={() => sendChat('E-ZZIO, prépare la prochaine optimisation PC sans rien casser.')} disabled={busy}>Optimisation sûre</button>
            <button onclick={() => sendChat('E-ZZIO, lance un audit.')} disabled={busy}>Audit</button>
            <button class="primary" onclick={() => sendChat('CONFIRME')} disabled={busy}>CONFIRME</button>
            <button class="danger" onclick={() => sendChat('annule')} disabled={busy}>Annule</button>
          </div>

          <div class="reply">
            <div class="clean-reply">{pickReply(chatResult)}</div>
            {#if advanced}
              <div class="details"><pre>{pretty(chatResult)}</pre></div>
            {/if}
          </div>
        </div>
      </section>
    {/if}

    {#if tab === 'research'}
      <section class="card span-12">
        <div class="card-head">
          <div>
            <h2>Recherche / documentation</h2>
            <div class="hint">Sources ouvertes si disponibles. Sinon réponse prudente via fallback local/hybrid.</div>
          </div>
          <span class={busy ? 'badge warn' : 'badge ok'}>{busy ? 'Recherche...' : 'Prêt'}</span>
        </div>

        <div class="card-body">
          <input bind:value={researchText} placeholder="Sujet de recherche..." />

          <div class="actions">
            <button class="primary" onclick={sendResearch} disabled={busy}>Rechercher</button>
            <button onclick={() => (researchText = 'documentation FastAPI APIRouter bonnes pratiques')} disabled={busy}>FastAPI</button>
            <button onclick={() => (researchText = 'optimisation Ollama CPU Ryzen 9 5900X')} disabled={busy}>Ollama CPU</button>
            <button onclick={() => (researchText = 'SvelteKit local-first dashboard architecture')} disabled={busy}>SvelteKit</button>
          </div>

          <div class="reply">
            <div class="clean-reply">{pickReply(researchResult)}</div>

            {#if researchItems().length}
              <div class="result-list details">
                {#each researchItems() as item}
                  <div class="result-item">
                    <div class="result-title">{item.title || item.label || item.name || 'Source'}</div>
                    <div class="result-meta">{shortText(item.url || item.source || item.summary || item.description, 360)}</div>
                  </div>
                {/each}
              </div>
            {/if}

            {#if advanced}
              <div class="details"><pre>{pretty(researchResult)}</pre></div>
            {/if}
          </div>
        </div>
      </section>
    {/if}

    {#if tab === 'vision'}
      <section class="card span-12">
        <div class="card-head">
          <div>
            <h2>Analyse image</h2>
            <div class="hint">Colle un chemin Windows vers une image. Exemple : G:\AI\E-zzio\forge\vision\inbox\image.png</div>
          </div>
          <span class={busy ? 'badge warn' : 'badge ok'}>{busy ? 'Analyse...' : 'Prêt'}</span>
        </div>

        <div class="card-body">
          <input bind:value={imagePath} placeholder="Chemin image local..." style="margin-bottom:0.8rem;" />
          <textarea bind:value={visionPrompt}></textarea>

          <div class="actions">
            <button class="primary" onclick={analyzeImage} disabled={busy}>Analyser image</button>
            <button onclick={() => (visionPrompt = 'Décris précisément cette image et indique les problèmes visibles.')} disabled={busy}>Décrire</button>
            <button onclick={() => (visionPrompt = 'Analyse cette capture d’écran comme un assistant technique Windows.')} disabled={busy}>Capture écran</button>
            <button onclick={() => (imagePath = 'G:\\AI\\E-zzio\\forge\\vision\\inbox\\ezzio_test_vision.png')} disabled={busy}>Image test</button>
          </div>

          <div class="reply">
            <div class="clean-reply">{pickReply(visionResult)}</div>
            {#if advanced}
              <div class="details"><pre>{pretty(visionResult)}</pre></div>
            {/if}
          </div>
        </div>
      </section>
    {/if}

    {#if tab === 'system'}
      <section class="card span-6">
        <div class="card-head">
          <div>
            <h2>Système</h2>
            <div class="hint">État résumé</div>
          </div>
        </div>
        <div class="card-body kv">
          <div class="kv-row"><span class="key">API</span><span class="value">{valueOf(root, 'version')}</span></div>
          <div class="kv-row"><span class="key">GPU</span><span class="value">{valueOf(root, 'policy.ezzio_gpu_policy')}</span></div>
          <div class="kv-row"><span class="key">No ads</span><span class="value">{valueOf(root, 'policy.no_ads')}</span></div>
          <div class="kv-row"><span class="key">Audit</span><span class="value">{valueOf(maintenance, 'bad_count')} problème(s)</span></div>
        </div>
      </section>

      <section class="card span-6">
        <div class="card-head">
          <div>
            <h2>Modules</h2>
            <div class="hint">Fonctionnalités prêtes</div>
          </div>
        </div>
        <div class="card-body kv">
          <div class="kv-row"><span class="key">Vision</span><span class="value">{statusText(vision)}</span></div>
          <div class="kv-row"><span class="key">Forge</span><span class="value">{statusText(forge)}</span></div>
          <div class="kv-row"><span class="key">Cloud</span><span class="value">send={valueOf(cloud, 'allow_send')}</span></div>
          <div class="kv-row"><span class="key">Recherche</span><span class="value">{statusText(researchStatus)}</span></div>
        </div>
      </section>

      {#if advanced}
        <section class="card span-12">
          <div class="card-head">
            <div>
              <h2>Détails techniques</h2>
              <div class="hint">Visible uniquement en mode avancé</div>
            </div>
          </div>
          <div class="card-body">
            <pre>{pretty({ root, maintenance, safeActions, cloud, vision, forge, researchStatus })}</pre>
          </div>
        </section>
      {/if}
    {/if}
  </div>
</main>
