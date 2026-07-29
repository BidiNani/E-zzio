<script>
  import { onMount, tick } from 'svelte';
  import { api, apiUpload, pretty, pickReply, statusText, shortText } from '$lib/api.js';

  let text = $state('');
  let attachments = $state([]);
  let dragging = $state(false);
  let busy = $state(false);
  let advanced = $state(false);
  let lastRefresh = $state('—');

  let root = $state(null);
  let maintenance = $state(null);
  let safeActions = $state(null);
  let vision = $state(null);
  let cloud = $state(null);
  let knowledge = $state(null);

  let messages = $state([
    {
      id: crypto.randomUUID(),
      role: 'assistant',
      text:
        "Salut Enrik. Écris ta demande ici, ou glisse une image dans la zone de chat. Je choisirai automatiquement entre chat, recherche, analyse image ou système.",
      kind: 'welcome',
      at: new Date().toLocaleTimeString(),
      raw: null
    }
  ]);

  let fileInput;

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

  function isImage(file) {
    return file?.type?.startsWith('image/');
  }

  function classifyIntent(prompt, hasImage) {
    const t = (prompt || '').toLowerCase();

    if (hasImage) return 'vision';

    if (
      t.includes('cherche') ||
      t.includes('recherche') ||
      t.includes('documente') ||
      t.includes('source') ||
      t.includes('documentation') ||
      t.includes('trouve des infos') ||
      t.includes('internet')
    ) {
      return 'research';
    }

    if (
      t.includes('audit') ||
      t.includes('maintenance') ||
      t.includes('safe action') ||
      t.includes('confirme') ||
      t.includes('annule') ||
      t.includes('système') ||
      t.includes('etat') ||
      t.includes('état')
    ) {
      return 'system';
    }

    return 'chat';
  }

  function addMessage(role, messageText, kind = 'chat', raw = null, files = []) {
    messages = [
      ...messages,
      {
        id: crypto.randomUUID(),
        role,
        text: messageText || '—',
        kind,
        raw,
        files,
        at: new Date().toLocaleTimeString()
      }
    ];

    try {
      localStorage.setItem('ezzio_unified_messages', JSON.stringify(messages.slice(-30)));
    } catch {}

    tick().then(() => {
      const el = document.querySelector('.messages');
      if (el) el.scrollTop = el.scrollHeight;
    });
  }

  function attachFiles(fileList) {
    const files = Array.from(fileList || []).filter((f) => isImage(f));
    const mapped = files.map((file) => ({
      id: crypto.randomUUID(),
      file,
      name: file.name,
      type: file.type,
      url: URL.createObjectURL(file)
    }));

    attachments = [...attachments, ...mapped].slice(0, 4);
  }

  function removeAttachment(id) {
    const item = attachments.find((a) => a.id === id);
    if (item?.url) URL.revokeObjectURL(item.url);
    attachments = attachments.filter((a) => a.id !== id);
  }

  function clearAttachments() {
    for (const item of attachments) {
      if (item.url) URL.revokeObjectURL(item.url);
    }
    attachments = [];
  }

  function onDrop(event) {
    event.preventDefault();
    dragging = false;
    attachFiles(event.dataTransfer?.files);
  }

  function onPaste(event) {
    const items = Array.from(event.clipboardData?.items || []);
    const files = [];

    for (const item of items) {
      if (item.kind === 'file') {
        const file = item.getAsFile();
        if (file && isImage(file)) files.push(file);
      }
    }

    if (files.length) {
      attachFiles(files);
      event.preventDefault();
    }
  }

  async function refreshStatus() {
    const [rootRes, maintRes, safeRes, visionRes, cloudRes, knowledgeRes] = await Promise.all([
      api('/status', { timeoutMs: 15000 }),
      api('/maintenance/audit', { timeoutMs: 180000 }),
      api('/safe-actions/status', { timeoutMs: 30000 }),
      api('/vision/status', { timeoutMs: 30000 }),
      api('/cloud-brain/status', { timeoutMs: 30000 }),
      api('/knowledge/status', { timeoutMs: 30000 })
    ]);

    root = rootRes;
    maintenance = maintRes;
    safeActions = safeRes;
    vision = visionRes;
    cloud = cloudRes;
    knowledge = knowledgeRes;
    lastRefresh = new Date().toLocaleTimeString();
  }

  async function runVision(prompt) {
    const first = attachments[0];

    if (first?.file) {
      const form = new FormData();
      form.append('file', first.file);
      form.append(
        'prompt',
        prompt ||
          "Analyse cette image précisément. Dis ce que tu vois, puis l'action utile suivante."
      );

      return await apiUpload('/vision/analyze', form, 300000);
    }

    return {
      ok: false,
      reply: "Aucune image attachée. Glisse une image ou colle une capture dans la zone de chat."
    };
  }

  async function runResearch(prompt) {
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
          text: `Recherche/documentation demandée : ${prompt}. Réponds clairement. Si tu n'as pas de sources, dis-le.`,
          provider: 'auto',
          force_cloud: false
        })
      });
    }

    return output;
  }

  async function runCommander(prompt) {
    return await api('/api/chat/commander', {
      method: 'POST',
      timeoutMs: 240000,
      body: JSON.stringify({
        text: prompt,
        session: 'unified-chat'
      })
    });
  }

  async function send() {
    const prompt = text.trim();
    const hasImage = attachments.length > 0;

    if (!prompt && !hasImage) return;

    const intent = classifyIntent(prompt, hasImage);
    const filesForMessage = attachments.map((a) => ({
      name: a.name,
      type: a.type,
      url: a.url
    }));

    addMessage('user', prompt || 'Analyse cette image.', intent, null, filesForMessage);

    busy = true;

    try {
      let output;

      if (intent === 'vision') {
        output = await runVision(prompt);
      } else if (intent === 'research') {
        output = await runResearch(prompt);
      } else {
        output = await runCommander(prompt);
      }

      addMessage('assistant', pickReply(output), intent, output);
      text = '';
      clearAttachments();
    } finally {
      busy = false;
      await refreshStatus();
    }
  }

  async function quick(prompt) {
    text = prompt;
    await send();
  }

  function onKeydown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      send();
    }
  }

  onMount(() => {
    try {
      const saved = JSON.parse(localStorage.getItem('ezzio_unified_messages') || '[]');
      if (saved.length) messages = saved;
    } catch {}

    refreshStatus();
    const timer = setInterval(refreshStatus, 15000);
    return () => clearInterval(timer);
  });
</script>

<svelte:head>
  <title>E-ZZIO — Chat unifié</title>
</svelte:head>

<header class="topbar">
  <div class="topbar-inner">
    <div class="brand">
      <div class="orb"></div>
      <div>
        <h1>E-ZZIO</h1>
        <p>Chat unique : écris, colle ou glisse une image. E-ZZIO choisit l’action.</p>
      </div>
    </div>

    <div class="badges">
      <span class={clsStatus(root)}>API {statusText(root)}</span>
      <span class={clsStatus(vision)}>Vision {statusText(vision)}</span>
      <span class={clsStatus(knowledge)}>Recherche {statusText(knowledge)}</span>
      <span class="badge ok">No ads</span>
      <span class="badge">refresh {lastRefresh}</span>
      <button class="soft" onclick={() => (advanced = !advanced)}>
        {advanced ? 'Masquer détails' : 'Détails'}
      </button>
    </div>
  </div>
</header>

<main class="container">
  <section class="hero">
    <h2>Que veux-tu faire ?</h2>
    <p>
      Parle naturellement. Pour une image, glisse-la dans la zone de chat ou colle une capture écran.
      E-ZZIO route automatiquement vers chat, recherche, vision ou système.
    </p>

    <div class="quick-row">
      <button onclick={() => quick('E-ZZIO, fais un état rapide de ton système.')} disabled={busy}>État rapide</button>
      <button onclick={() => quick('E-ZZIO, prépare la prochaine optimisation PC sans rien casser.')} disabled={busy}>Optimiser sans risque</button>
      <button onclick={() => quick('Recherche : bonnes pratiques SvelteKit pour une interface assistant IA locale.')} disabled={busy}>Recherche SvelteKit</button>
      <button onclick={() => quick('E-ZZIO, résume les actions en attente.')} disabled={busy}>Actions en attente</button>
      <button class="primary" onclick={() => quick('CONFIRME')} disabled={busy}>CONFIRME</button>
    </div>
  </section>

  <section class="chat-panel">
    <div class="messages">
      {#each messages as message}
        <div class:message={true} class:user={message.role === 'user'}>
          {#if message.role !== 'user'}
            <div class="avatar">E</div>
          {/if}

          <div class="bubble">
            {#if message.files?.length}
              <div class="attachments" style="margin-bottom:0.6rem;">
                {#each message.files as file}
                  <div class="attachment">
                    <img src={file.url} alt={file.name} />
                    <div class="attachment-name">{file.name}</div>
                  </div>
                {/each}
              </div>
            {/if}

            <div>{message.text}</div>
            <div class="meta">{message.kind} · {message.at}</div>

            {#if advanced && message.raw}
              <div class="details">
                <pre>{pretty(message.raw)}</pre>
              </div>
            {/if}
          </div>

          {#if message.role === 'user'}
            <div class="avatar">T</div>
          {/if}
        </div>
      {/each}

      {#if busy}
        <div class="message">
          <div class="avatar">E</div>
          <div class="bubble">
            E-ZZIO travaille…
            <div class="meta">analyse en cours</div>
          </div>
        </div>
      {/if}
    </div>

    <div class="composer-wrap">
      <div
        class:dropzone={true}
        class:dragging={dragging}
        role="button"
        tabindex="0"
        ondragenter={(event) => {
          event.preventDefault();
          dragging = true;
        }}
        ondragover={(event) => {
          event.preventDefault();
          dragging = true;
        }}
        ondragleave={() => (dragging = false)}
        ondrop={onDrop}
        onpaste={onPaste}
      >
        {#if attachments.length}
          <div class="attachments">
            {#each attachments as item}
              <div class="attachment">
                <img src={item.url} alt={item.name} />
                <div class="attachment-name">{item.name}</div>
                <button class="soft" onclick={() => removeAttachment(item.id)}>×</button>
              </div>
            {/each}
          </div>
        {/if}

        <textarea
          bind:value={text}
          onkeydown={onKeydown}
          placeholder="Écris à E-ZZIO… ou glisse une image ici."
          disabled={busy}
        ></textarea>

        <div class="composer-actions">
          <div class="left-actions">
            <input
              class="file-input"
              bind:this={fileInput}
              type="file"
              accept="image/*"
              multiple
              onchange={(event) => attachFiles(event.target.files)}
            />
            <button class="soft" onclick={() => fileInput?.click()} disabled={busy}>Ajouter image</button>
            <button class="soft" onclick={clearAttachments} disabled={busy || !attachments.length}>Retirer images</button>
          </div>

          <div class="right-actions">
            <span class="badge">
              {attachments.length ? `${attachments.length} image(s)` : 'texte seul'}
            </span>
            <button class="primary" onclick={send} disabled={busy}>Envoyer</button>
          </div>
        </div>
      </div>
    </div>
  </section>

  {#if advanced}
    <div class="panel-row">
      <section class="card">
        <div class="card-head">
          <strong>Santé système</strong>
          <span class="badge">debug</span>
        </div>
        <div class="card-body kv">
          <div class="kv-row"><span class="key">Maintenance</span><span>{valueOf(maintenance, 'bad_count')} souci(s)</span></div>
          <div class="kv-row"><span class="key">Safe Actions</span><span>{valueOf(safeActions, 'pending_count')} attente(s)</span></div>
          <div class="kv-row"><span class="key">Cloud</span><span>send={valueOf(cloud, 'allow_send')}</span></div>
        </div>
      </section>

      <section class="card">
        <div class="card-head">
          <strong>État brut</strong>
          <span class="badge">local</span>
        </div>
        <div class="card-body">
          <pre>{pretty({ root, maintenance, safeActions, vision, cloud, knowledge })}</pre>
        </div>
      </section>
    </div>
  {/if}
</main>
