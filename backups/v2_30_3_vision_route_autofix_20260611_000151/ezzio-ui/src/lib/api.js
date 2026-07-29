export async function api(path, options = {}) {
  const timeoutMs = options.timeoutMs ?? 240000;
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

export async function apiUpload(path, formData, timeoutMs = 300000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(path, {
      method: 'POST',
      body: formData,
      signal: controller.signal
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
  if (typeof value === 'string') return value;

  return (
    value.reply ||
    value.message ||
    value.summary ||
    value.answer ||
    value.analysis ||
    value.description ||
    value.result?.reply ||
    value.result?.summary ||
    value.result?.analysis ||
    value.action_result?.summary ||
    value.proposal?.summary ||
    value.data?.reply ||
    value.data?.summary ||
    value.error ||
    'Réponse reçue.'
  );
}

export function statusText(value) {
  if (value?.ok === true || value?.online === true) return 'OK';
  if (value?.online === false || value?.ok === false) return 'OFF';
  return '—';
}

export function shortText(value, max = 220) {
  const text = String(value ?? '—');
  if (text.length <= max) return text;
  return text.slice(0, max - 1) + '…';
}
