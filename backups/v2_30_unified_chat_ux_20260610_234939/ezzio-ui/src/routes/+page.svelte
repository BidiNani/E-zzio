<script>
  import { onMount } from 'svelte';
  import { api, apiUpload, pretty, pickReply, statusText, shortText } from '$lib/api.js';

  let mode = $state('chat');
  let busy = $state(false);
  let advanced = $state(false);
  let lastRefresh = $state('—');

  let root = $state(null);
  let maintenance = $state(null);
  let safeActions = $state(null);
  let vision = $state(null);
  let forge = $state(null);
  let cloud = $state(null);
  let knowledge = $state(null);

  let prompt = $state('E-ZZIO, fais un état rapide de ton système.');
  let imagePath = $state('G:\\AI\\E-zzio\\forge\\vision\\inbox\\ezzio_test_vision.png');
  let imagePrompt = $state('Analyse cette image clairement. Dis ce que tu vois, puis l’action utile suivante.');
  let selectedFile = $state(null);

  let result = $state({ ok: true, reply: 'Bienvenue. Choisis une action à gauche, écris ta demande, puis lance E-ZZIO.' });
  let history = $state([]);

  const modes = [
    {
      id: 'chat',
      name: 'Chat',
      desc: 'Parler avec E-ZZIO',
      placeholder: 'Demande quelque chose à E-ZZIO…'
    },
    {
      id: 'research',
      name: 'Recherche',
      desc: 'Trouver / documenter',
      placeholder: 'Sujet à rechercher ou documenter…'
    },
    {
      id: 'vision',
      name: 'Image',
      desc: 'Analyser une image',
      placeholder: 'Chemin image ou upload…'
    },
    {
      id: 'system',
      name: 'Système',
      desc: 'État / audit / actions',
      placeholder: 'Demande système…'
    }
  ];

  function currentMode() {
    return modes.find((m) => m.id === mode) ?? modes[0];
  }

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

  function sourceItems() {
    return result?.results || result?.items || result?.sources || [];
  }

  function setMode(nextMode) {
    mode = nextMode;

    if (nextMode === 'chat') {
      prompt = 'E-ZZIO, fais un état rapide de ton système.';
    } else if (nextMode === 'research') {
      prompt = 'optimisation Ollama CPU Ryzen 9 5900X';
    } else if (nextMode === 'vision') {
      prompt = imagePrompt;
    } else if (nextMode === 'system') {
      prompt = 'E-ZZIO, lance un audit et résume seulement ce qui mérite mon attention.';
    }
  }

  function addHistory(kind, text, output) {
    const item = {
      id: crypto.randomUUID(),
      at: new Date().toLocaleTimeString(),
      kind,
      text,
      reply: pickReply(output)
    };

    history = [item, ...history].slice(0, 8);

    try {
      localStorage.setItem('ezzio_recent_history', JSON.stringify(history));
    } catch {}
  }

  async function refreshStatus() {
    const [rootRes, maintRes, safeRes, visionRes, forgeRes, cloudRes, knowledgeRes] = await Promise.all([
      api('/status', { timeoutMs: 15000 }),
      api('/maintenance/audit', { timeoutMs: 180000 }),
      api('/safe-actions/status', { timeoutMs: 30000 }),
      api('/vision/status', { timeoutMs: 30000 }),
      api('/forge/status', { timeoutMs: 30000 }),
      api('/cloud-brain/status', { timeoutMs: 30000 }),
      api('/knowledge/status', { timeoutMs: 30000 })
    ]);

    root = rootRes;
    maintenance = maintRes;
    safeActions = safeRes;
    vision = visionRes;
    forge = forgeRes;
    cloud = cloudRes;
    knowledge = knowledgeRes;

    lastRefresh = new Date().toLocaleTimeString();
  }

  async function runChat() {
    return await api('/api/chat/commander', {
      method: 'POST',
      timeoutMs: 240000,
      body: JSON.stringify({
        text: prompt,
        session: 'practical-assistant'
      })
    });
  }

  async function runResearch() {
    let output = await api('/knowledge/search', {
      method: 'POST',
      timeoutMs: 180000,
      body: JSON.stringify({
        query: prompt,
        limit: 8
      })
    });

    if (output?.ok === false || output?.status === 404 || output?.error) {
      output = await api('/api/chat/hybrid', {
        method: 'POST',
        timeoutMs: 240000,
        body: JSON.stringify({
          text: `Recherche/documentation : ${prompt}. Réponds clairement. Si tu n'as pas de sources, dis-le.`,
          provider: 'auto',
          force_cloud: false
        })
      });
    }

    return output;
  }

  async function runVision() {
    if (selectedFile) {
      const form = new FormData();
      form.append('file', selectedFile);
      form.append('prompt', imagePrompt || prompt);
      const uploaded = await apiUpload('/vision/analyze', form, 300000);

      if (uploaded?.ok !== false && !uploaded?.error) {
        return uploaded;
      }

      return {
        ...uploaded,
        reply:
          "L'upload direct n'a pas répondu correctement. Utilise l'analyse par chemin local si l'image est sur G:\\."
      };
    }

    return await api('/vision/analyze-path', {
      method: 'POST',
      timeoutMs: 300000,
      body: JSON.stringify({
        path: imagePath,
        prompt: imagePrompt || prompt
      })
    });
  }

  async function runSystem() {
    return await api('/api/chat/commander', {
      method: 'POST',
      timeoutMs: 240000,
      body: JSON.stringify({
        text: prompt,
        session: 'practical-system'
      })
    });
  }

  async function runMain() {
    busy = true;

    try {
      let output;

      if (mode === 'chat') output = await runChat();
      else if (mode === 'research') output = await runResearch();
      else if (mode === 'vision') output = await runVision();
      else output = await runSystem();

      result = output;
      addHistory(currentMode().name, mode === 'vision' ? imagePath || selectedFile?.name : prompt, output);
    } finally {
      busy = false;
      await refreshStatus();
    }
  }

  async function quick(text, targetMode = null) {
    if (targetMode) mode = targetMode;
    prompt = text;
    await runMain();
  }

  function onFileChange(event) {
    const files = event?.target?.files;
    selectedFile = files && files.length ? files[0] : null;
  }

  onMount(() => {
    try {
      history = JSON.parse(localStorage.getItem('ezzio_recent_history') || '[]');
    } catch {
      history = [];
    }

    refreshStatus();
    const timer = setInterval(refreshStatus, 15000);
    return () => clearInterval(timer);
  });
</script>

<svelte:head>
  <title>E-ZZIO — Assistant pratique</title>
</svelte:head>

<header class="topbar">
  <div class="topbar-inner">
    <div class="brand">
      <div class="orb"></div>
      <div>
        <h1>E-ZZIO Assistant</h1>
        <p>Simple : discuter, chercher, analyser une image, vérifier le système.</p>
      </div>
    </div>

    <div class="badges">
      <span class={clsStatus(root)}>API {statusText(root)}</span>
      <span class={clsStatus(vision)}>Vision {statusText(vision)}</span>
      <span class={clsStatus(knowledge)}>Recherche {statusText(knowledge)}</span>
      <span class="badge ok">No ads</span>
      <span class="badge">refresh {lastRefresh}</span>
      <button class="soft" onclick={() => (advanced = !advanced)}>{advanced ? 'Masquer détails' : 'Détails'}</button>
    </div>
  </div>
</header>

<main class="container">
  <div class="layout">
    <aside class="side">
      <div class="side-title">Actions principales</div>

      <div class="mode-list">
        {#each modes as item}
          <button class:active={mode === item.id} class="mode-btn" onclick={() => setMode(item.id)}>
            <span class="mode-name">{item.name}</span>
            <span class="mode-desc">{item.desc}</span>
          </button>
        {/each}
      </div>

      <div class="side-title">Santé rapide</div>

      <div class="health-grid">
        <div class="health-row">
          <span class="health-name">Audit</span>
          <span>{valueOf(maintenance, 'bad_count')} souci(s)</span>
        </div>
        <div class="health-row">
          <span class="health-name">Actions</span>
          <span>{valueOf(safeActions, 'pending_count')} attente(s)</span>
        </div>
        <div class="health-row">
          <span class="health-name">Cloud</span>
          <span>send={valueOf(cloud, 'allow_send')}</span>
        </div>
        <div class="health-row">
          <span class="health-name">Forge</span>
          <span>{statusText(forge)}</span>
        </div>
      </div>

      <div class="side-title">Raccourcis</div>

      <div class="mode-list">
        <button class="mode-btn" onclick={() => quick('E-ZZIO, fais un état rapide de ton système.', 'chat')} disabled={busy}>
          <span class="mode-name">État rapide</span>
          <span class="mode-desc">Résumé clair</span>
        </button>

        <button class="mode-btn" onclick={() => quick('E-ZZIO, prépare la prochaine optimisation PC sans rien casser.', 'system')} disabled={busy}>
          <span class="mode-name">Optimiser</span>
          <span class="mode-desc">Préparer sans risque</span>
        </button>

        <button class="mode-btn" onclick={() => quick('E-ZZIO, lance un audit et résume ce qui mérite mon attention.', 'system')} disabled={busy}>
          <span class="mode-name">Audit</span>
          <span class="mode-desc">Contrôle projet</span>
        </button>

        <button class="mode-btn" onclick={() => quick('CONFIRME', 'system')} disabled={busy}>
          <span class="mode-name">CONFIRME</span>
          <span class="mode-desc">Valider action en attente</span>
        </button>
      </div>
    </aside>

    <section class="main">
      <div class="hero">
        <h2>{currentMode().name}</h2>
        <p>{currentMode().desc}. Écris ta demande, ou utilise un raccourci.</p>
      </div>

      <div class="section">
        <div class="composer">
          {#if mode === 'vision'}
            <div class="two-col">
              <div>
                <label>Chemin image local</label>
                <input bind:value={imagePath} placeholder="G:\AI\E-zzio\image.png" />
              </div>

              <div class="file-box">
                <strong>Ou choisir une image</strong>
                <div class="mode-desc">L’upload direct dépend de l’endpoint vision. Le chemin local reste le plus fiable.</div>
                <input type="file" accept="image/*" onchange={onFileChange} />
                {#if selectedFile}
                  <div class="mode-desc">Sélection : {selectedFile.name}</div>
                {/if}
              </div>
            </div>

            <textarea bind:value={imagePrompt} placeholder="Que veux-tu savoir sur cette image ?"></textarea>
          {:else}
            <textarea bind:value={prompt} placeholder={currentMode().placeholder}></textarea>
          {/if}

          <div class="prompt-row">
            <button class="primary" onclick={runMain} disabled={busy}>
              {busy ? 'E-ZZIO travaille...' : 'Lancer'}
            </button>

            {#if mode === 'chat'}
              <button onclick={() => (prompt = 'Explique-moi clairement ce que tu peux faire maintenant.')} disabled={busy}>Capacités</button>
              <button onclick={() => (prompt = 'Aide-moi à organiser la prochaine étape du projet E-ZZIO.')} disabled={busy}>Prochaine étape</button>
            {/if}

            {#if mode === 'research'}
              <button onclick={() => (prompt = 'documentation FastAPI APIRouter bonnes pratiques')} disabled={busy}>FastAPI</button>
              <button onclick={() => (prompt = 'optimisation Ollama CPU Ryzen 9 5900X')} disabled={busy}>Ollama CPU</button>
              <button onclick={() => (prompt = 'SvelteKit dashboard local-first UX')} disabled={busy}>SvelteKit UX</button>
            {/if}

            {#if mode === 'vision'}
              <button onclick={() => (imagePrompt = 'Décris précisément cette image et indique l’action utile suivante.')} disabled={busy}>Décrire</button>
              <button onclick={() => (imagePrompt = 'Analyse cette capture d’écran comme un assistant technique Windows.')} disabled={busy}>Capture écran</button>
              <button onclick={() => (imagePath = 'G:\\AI\\E-zzio\\forge\\vision\\inbox\\ezzio_test_vision.png')} disabled={busy}>Image test</button>
            {/if}

            {#if mode === 'system'}
              <button onclick={() => (prompt = 'E-ZZIO, annule les actions pendantes inutiles.')} disabled={busy}>Annuler attentes</button>
              <button onclick={() => (prompt = 'E-ZZIO, résume les Safe Actions en attente.')} disabled={busy}>Actions en attente</button>
            {/if}
          </div>
        </div>

        <div class="result">
          <div class="result-head">
            <strong>Réponse</strong>
            <span class={busy ? 'badge warn' : 'badge ok'}>{busy ? 'en cours' : 'prêt'}</span>
          </div>

          <div class="result-body">{pickReply(result)}</div>
        </div>

        {#if sourceItems().length}
          <div class="sources">
            {#each sourceItems() as source}
              <div class="source">
                <div class="source-title">{source.title || source.label || source.name || 'Source'}</div>
                <div class="source-meta">{shortText(source.url || source.source || source.summary || source.description, 420)}</div>
              </div>
            {/each}
          </div>
        {/if}

        {#if advanced}
          <div class="details">
            <pre>{pretty(result)}</pre>
          </div>
        {/if}
      </div>

      <div class="section">
        <div class="hero" style="border-radius:1.2rem; border:1px solid var(--line);">
          <h2>Historique récent</h2>
          <p>Les dernières actions utiles, stockées localement dans ton navigateur.</p>
        </div>

        <div class="history" style="margin-top:1rem;">
          {#each history as item}
            <div class="history-item">
              <div class="history-top">
                <span>{item.kind}</span>
                <span class="badge">{item.at}</span>
              </div>
              <div class="history-text">{shortText(item.text, 160)}</div>
              <div class="history-text">{shortText(item.reply, 220)}</div>
            </div>
          {/each}

          {#if !history.length}
            <div class="history-item">
              <div class="history-text">Aucun historique pour l’instant.</div>
            </div>
          {/if}
        </div>
      </div>
    </section>
  </div>
</main>
