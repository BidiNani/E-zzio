<script>
  import { onMount, tick } from 'svelte';
  import { message, status, pickReply, pretty } from '$lib/api.js';

  let text = $state('');
  let file = $state(null);
  let preview = $state('');
  let busy = $state(false);
  let drag = $state(false);
  let sys = $state({ ok:false });
  let inputFile;
  let messages = $state([
    { role:'assistant', text:'Salut Enrik. Écris, colle une capture, ou glisse une image. Je décide quoi faire.', intent:'ready', raw:null }
  ]);

  function add(role, text, intent='chat', raw=null, img=null) {
    messages = [...messages, { role, text, intent, raw, img, at:new Date().toLocaleTimeString() }];
    tick().then(() => {
      const el = document.querySelector('.chat');
      if (el) el.scrollTop = el.scrollHeight;
    });
  }

  function setFile(f) {
    if (!f || !f.type?.startsWith('image/')) return;
    if (preview) URL.revokeObjectURL(preview);
    file = f;
    preview = URL.createObjectURL(f);
  }

  function clearFile() {
    if (preview) URL.revokeObjectURL(preview);
    file = null; preview = '';
  }

  async function send() {
    if (!text.trim() && !file) return;
    const img = preview;
    add('user', text || 'Analyse cette image.', file ? 'vision' : 'text', null, img);
    busy = true;
    try {
      const r = await message(text, file);
      add('assistant', pickReply(r), r.intent || 'reply', r);
      text = ''; clearFile();
    } finally { busy = false; sys = await status(); }
  }

  function onDrop(e){ e.preventDefault(); drag=false; const f=e.dataTransfer?.files?.[0]; setFile(f); }
  function onPaste(e){ const items=[...(e.clipboardData?.items||[])]; for(const it of items){ if(it.kind==='file'){ const f=it.getAsFile(); if(f?.type?.startsWith('image/')){ setFile(f); e.preventDefault(); return; } } } }
  function key(e){ if(e.key==='Enter' && !e.shiftKey){ e.preventDefault(); send(); } }
  async function quick(t){ text=t; await tick(); send(); }

  onMount(async()=>{ sys = await status(); });
</script>

<header class="top">
  <div class="brand">
    <div class="orb"></div>
    <div><h1>E-ZZIO</h1><p>Chat unique : texte + image + recherche</p></div>
  </div>
  <div class="pills">
    <span class:ok={sys.ok} class="pill">{sys.ok ? 'Prêt' : 'API ?'}</span>
    <span class="pill ok">Local</span>
    <span class="pill ok">No ads</span>
  </div>
</header>

<main class="wrap">
  <div class="quick">
    <button onclick={() => quick('Fais un état rapide de ton système.')}>État</button>
    <button onclick={() => quick('Recherche : optimiser Ollama CPU Ryzen 9 5900X')}>Recherche</button>
    <button onclick={() => quick('Prépare la prochaine optimisation PC sans rien casser.')}>Optimiser</button>
    <button class="primary" onclick={() => quick('CONFIRME')}>CONFIRME</button>
  </div>

  <section class="chat">
    {#each messages as m}
      <div class:msg={true} class:user={m.role==='user'}>
        <div class="bubble">
          {#if m.img}<img class="thumb" src={m.img} alt="image jointe" />{/if}
          {m.text}
          <div class="meta">{m.intent} {m.at ? '· ' + m.at : ''}</div>
          {#if m.raw}
            <details><summary>Détails</summary><pre>{pretty(m.raw)}</pre></details>
          {/if}
        </div>
      </div>
    {/each}
    {#if busy}
      <div class="msg"><div class="bubble">E-ZZIO réfléchit…<div class="meta">en cours</div></div></div>
    {/if}
  </section>

  <section class:composer={true} class:drag={drag}
    ondragenter={(e)=>{e.preventDefault();drag=true}}
    ondragover={(e)=>{e.preventDefault();drag=true}}
    ondragleave={()=>drag=false}
    ondrop={onDrop}
    onpaste={onPaste}
  >
    {#if file}
      <div class="preview">
        <img src={preview} alt={file.name} />
        <span>{file.name}</span>
        <button onclick={clearFile}>Retirer</button>
      </div>
    {/if}

    <textarea bind:value={text} onkeydown={key} disabled={busy}
      placeholder="Écris ici… ou glisse/colle une image. Entrée pour envoyer, Shift+Entrée pour une ligne."></textarea>

    <div class="row">
      <div>
        <input class="hidden" bind:this={inputFile} type="file" accept="image/*" onchange={(e)=>setFile(e.target.files?.[0])} />
        <button onclick={()=>inputFile?.click()} disabled={busy}>Image</button>
      </div>
      <button class="primary" onclick={send} disabled={busy}>Envoyer</button>
    </div>
  </section>
</main>
