/**
 * Shared fetch wrapper that auto-injects the auth token.
 * Centralizes header management and error handling for all API calls.
 */
export async function apiFetch(
  url: string,
  options: RequestInit = {},
): Promise<Response> {
  const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;

  const headers = new Headers(options.headers);
  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  return fetch(url, { 
    ...options, 
    headers,
    credentials: 'include', // CRITICAL: Send HttpOnly cookies to the server
    cache: 'no-store'
  });
}

/**
 * Convenience wrapper that auto-parses JSON and throws on non-ok responses.
 */
export async function apiFetchJson<T = any>(
  url: string,
  options: RequestInit = {},
): Promise<T> {
  const res = await apiFetch(url, options);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${res.status})`);
  }
  return res.json();
}
