import { config } from './config.js';

export async function authorizeRoom(userId: string, room: string): Promise<boolean> {
  if (room === `user:${userId}`) return true;

  const url = `${config.djangoApiBase}/internal/realtime/authorize/`;
  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Internal-Token': config.internalToken,
      },
      body: JSON.stringify({ user_id: userId, room }),
    });
    if (!res.ok) return false;
    const data = (await res.json()) as { allowed?: boolean };
    return Boolean(data.allowed);
  } catch (err) {
    console.warn('authorizeRoom failed', err);
    return false;
  }
}

export async function proxyJobPost(
  path: string,
  token: string,
  body: Record<string, unknown>,
): Promise<{ ok: boolean; status: number; data: unknown }> {
  const url = `${config.djangoApiBase}${path}`;
  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(body),
    });
    const data = await res.json().catch(() => ({}));
    return { ok: res.ok, status: res.status, data };
  } catch (err) {
    return { ok: false, status: 502, data: { detail: String(err) } };
  }
}
