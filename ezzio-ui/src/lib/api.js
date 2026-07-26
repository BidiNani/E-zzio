export async function message(text, file = null) {
  const form = new FormData();
  form.append('text', text || '');
  if (file) form.append('file', file);

  const res = await fetch('/api/ezzio/message', {
    method: 'POST',
    body: form
  });

  const raw = await res.text();
  let data;
  try { data = raw ? JSON.parse(raw) : {}; }
  catch { data = { ok:false, reply: raw || 'Réponse non JSON' }; }

  if (!res.ok) {
    return { ok:false, reply: data.detail || data.error || 'Erreur API', raw:data };
  }
  return data;
}

export async function status() {
  try {
    const res = await fetch('/api/ezzio/status');
    return await res.json();
  } catch {
    return { ok:false };
  }
}

export function pickReply(x) {
  return x?.reply || x?.analysis || x?.message || x?.error || 'Réponse vide.';
}

export function pretty(x) {
  return JSON.stringify(x ?? {}, null, 2);
}
