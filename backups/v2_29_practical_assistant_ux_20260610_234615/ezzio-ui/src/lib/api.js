export async function api(path, options = {}) {
  const timeoutMs = options.timeoutMs ?? 180000;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(path, {
      ...options,
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...(options.headers || {})
      }
    });

    const text = await response.text();

    let data;
    try {
      data = text ? JSON.parse(text) : {};
    } catch {
      data = { ok: false, error: 'Réponse non JSON', raw: text };
    }

    if (!response.ok) {
      return {
        ok: false,
        online: false,
        status: response.status,
        error: data?.error || data?.detail || response.statusText,
        data
      };
    }

    return { online: true, ...data };
  } catch (error) {
    return {
      ok: false,
      online: false,
      error: error?.name === 'AbortError' ? 'Timeout' : String(error)
    };
  } finally {
    clearTimeout(timer);
  }
}

export function pretty(value) {
  return JSON.stringify(value ?? {}, null, 2);
}

export function pickReply(value) {
  if (!value) return '—';

  return (
    value.reply ||
    value.message ||
    value.summary ||
    value.answer ||
    value.result?.reply ||
    value.result?.summary ||
    value.action_result?.summary ||
    value.proposal?.summary ||
    value.description ||
    'Réponse reçue. Détails disponibles.'
  );
}

export function statusText(value) {
  if (value?.ok === true || value?.online === true) return 'OK';
  if (value?.online === false) return 'OFF';
  return '—';
}

export function shortText(value, max = 240) {
  const text = String(value ?? '—');
  if (text.length <= max) return text;
  return text.slice(0, max - 1) + '…';
}
