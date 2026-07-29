export async function api(path, options = {}) {
  const timeoutMs = options.timeoutMs ?? 120000;
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
      data = {
        ok: false,
        error: 'Réponse non JSON',
        raw: text
      };
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

    return {
      online: true,
      ...data
    };
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

export function safeValue(value) {
  if (value === undefined || value === null || value === '') return '—';
  if (typeof value === 'object') return JSON.stringify(value);
  return value;
}

export function shortText(value, max = 180) {
  const text = String(value ?? '—');
  if (text.length <= max) return text;
  return text.slice(0, max - 1) + '…';
}
