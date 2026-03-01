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

  const res = await fetch(url, { 
    ...options, 
    headers,
    credentials: 'include', // CRITICAL: Send HttpOnly cookies to the server
    cache: 'no-store'
  });

  // Global handler for 401 Unauthorized (Session Expired)
  if (res.status === 401 && typeof window !== 'undefined') {
    // Only redirect if we thought we were logged in
    if (localStorage.getItem('token')) {
      console.warn('Session expired, redirecting to login...');
      localStorage.removeItem('token');
      // Use window.location for a hard redirect to clear state
      if (!window.location.pathname.startsWith('/login')) {
        window.location.href = '/login?expired=true';
      }
    }
  }

  return res;
}

async function parseResponseBody(res: Response): Promise<any> {
  const text = await res.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

/**
 * Convenience wrapper that auto-parses JSON and throws on non-ok responses.
 */
export async function apiFetchJson<T = any>(
  url: string,
  options: RequestInit = {},
): Promise<T> {
  const res = await apiFetch(url, options);
  const body = await parseResponseBody(res);

  if (!res.ok) {
    if (typeof body === 'string') {
      throw new Error(body || `Request failed (${res.status})`);
    }
    const detail = body?.detail;
    if (typeof detail === 'string') {
      throw new Error(detail);
    }
    if (detail && typeof detail === 'object' && typeof detail.message === 'string') {
      throw new Error(detail.message);
    }
    if (typeof body?.message === 'string') {
      throw new Error(body.message);
    }
    throw new Error(`Request failed (${res.status})`);
  }

  if (typeof body === 'string') {
    throw new Error(`Expected JSON response from ${url}, received text response.`);
  }

  return (body ?? {}) as T;
}
