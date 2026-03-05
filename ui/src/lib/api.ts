/**
 * Shared fetch wrapper that auto-injects the auth token.
 * Centralizes header management and error handling for all API calls.
 */
const DEFAULT_REQUEST_TIMEOUT_MS = 30000;

export interface ApiRequestOptions extends RequestInit {
  timeoutMs?: number;
  skipAuthRedirect?: boolean;
}

export class ApiError extends Error {
  status: number;
  body: unknown;
  url: string;

  constructor(message: string, status: number, url: string, body: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
    this.url = url;
  }
}

function createRequestSignal(
  timeoutMs: number,
  upstreamSignal?: AbortSignal | null,
): { signal: AbortSignal | undefined; cleanup: () => void; didTimeout: () => boolean } {
  if (timeoutMs <= 0 && !upstreamSignal) {
    return {
      signal: undefined,
      cleanup: () => {},
      didTimeout: () => false,
    };
  }

  const controller = new AbortController();
  let timeoutId: ReturnType<typeof setTimeout> | null = null;
  let timedOut = false;

  const abortFromUpstream = () => controller.abort(upstreamSignal?.reason);

  if (upstreamSignal) {
    if (upstreamSignal.aborted) {
      abortFromUpstream();
    } else {
      upstreamSignal.addEventListener("abort", abortFromUpstream, { once: true });
    }
  }

  if (timeoutMs > 0) {
    timeoutId = setTimeout(() => {
      timedOut = true;
      controller.abort(new DOMException("Request timed out", "TimeoutError"));
    }, timeoutMs);
  }

  return {
    signal: controller.signal,
    cleanup: () => {
      if (timeoutId) {
        clearTimeout(timeoutId);
      }
      if (upstreamSignal) {
        upstreamSignal.removeEventListener("abort", abortFromUpstream);
      }
    },
    didTimeout: () => timedOut,
  };
}

export async function apiFetch(
  url: string,
  options: ApiRequestOptions = {},
): Promise<Response> {
  const {
    timeoutMs = DEFAULT_REQUEST_TIMEOUT_MS,
    skipAuthRedirect = false,
    signal: upstreamSignal,
    ...requestInit
  } = options;
  const token =
    typeof window !== "undefined" ? localStorage.getItem("token") : null;
  const method = String(requestInit.method || "GET").toUpperCase();

  const headers = new Headers(requestInit.headers);
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const { signal, cleanup, didTimeout } = createRequestSignal(
    timeoutMs,
    upstreamSignal,
  );

  let res: Response;
  try {
    res = await fetch(url, {
      ...requestInit,
      headers,
      signal,
      credentials: "include",
      cache:
        requestInit.cache ??
        (method === "GET" || method === "HEAD" ? "default" : "no-store"),
    });
  } catch (error) {
    cleanup();
    if (didTimeout()) {
      throw new Error(`Request timed out after ${timeoutMs}ms`);
    }
    throw error;
  }
  cleanup();

  // Global handler for 401 Unauthorized (Session Expired)
  if (res.status === 401 && !skipAuthRedirect && typeof window !== "undefined") {
    // Only redirect if we thought we were logged in
    if (localStorage.getItem("token")) {
      console.warn("Session expired, redirecting to login...");
      localStorage.removeItem("token");
      // Use window.location for a hard redirect to clear state
      if (!window.location.pathname.startsWith("/login")) {
        window.location.href = "/login?expired=true";
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
  options: ApiRequestOptions = {},
): Promise<T> {
  const res = await apiFetch(url, options);
  const body = await parseResponseBody(res);

  if (!res.ok) {
    if (typeof body === 'string') {
      throw new ApiError(
        body || `Request failed (${res.status})`,
        res.status,
        url,
        body,
      );
    }
    const detail = body?.detail;
    if (typeof detail === 'string') {
      throw new ApiError(detail, res.status, url, body);
    }
    if (detail && typeof detail === 'object' && typeof detail.message === 'string') {
      throw new ApiError(detail.message, res.status, url, body);
    }
    if (typeof body?.message === 'string') {
      throw new ApiError(body.message, res.status, url, body);
    }
    throw new ApiError(`Request failed (${res.status})`, res.status, url, body);
  }

  if (typeof body === 'string') {
    throw new ApiError(
      `Expected JSON response from ${url}, received text response.`,
      res.status,
      url,
      body,
    );
  }

  return (body ?? {}) as T;
}
