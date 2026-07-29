export async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
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
      status: response.status,
      error: data?.error || data?.detail || response.statusText,
      data
    };
  }

  return data;
}

export function pretty(value) {
  return JSON.stringify(value, null, 2);
}

export function safeValue(value) {
  if (value === undefined || value === null || value === '') return '—';
  return value;
}
