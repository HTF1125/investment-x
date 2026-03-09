import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { apiFetch, apiFetchJson, ApiError } from '../api'

// ── Helpers ──

function mockResponse(status: number, body?: any, ok?: boolean): Response {
  const isOk = ok ?? (status >= 200 && status < 300)
  return {
    ok: isOk,
    status,
    text: () => Promise.resolve(body != null ? JSON.stringify(body) : ''),
    json: () => Promise.resolve(body),
    headers: new Headers(),
    redirected: false,
    statusText: '',
    type: 'basic' as ResponseType,
    url: '',
    clone: () => mockResponse(status, body, ok),
    body: null,
    bodyUsed: false,
    arrayBuffer: () => Promise.resolve(new ArrayBuffer(0)),
    blob: () => Promise.resolve(new Blob()),
    formData: () => Promise.resolve(new FormData()),
    bytes: () => Promise.resolve(new Uint8Array()),
  } as Response
}

// ── Setup / Teardown ──

let fetchSpy: ReturnType<typeof vi.fn>

beforeEach(() => {
  fetchSpy = vi.fn()
  vi.stubGlobal('fetch', fetchSpy)

  // Default: no token in localStorage
  localStorage.clear()

  // Reset window.location to a non-login page
  Object.defineProperty(window, 'location', {
    writable: true,
    value: { href: '/', pathname: '/', startsWith: undefined },
  })
})

afterEach(() => {
  vi.restoreAllMocks()
})

// ── Tests ──

describe('apiFetch', () => {
  it('injects Authorization header from localStorage when token exists', async () => {
    localStorage.setItem('token', 'test-jwt-token')
    fetchSpy.mockResolvedValue(mockResponse(200, { ok: true }))

    await apiFetch('/api/test')

    const callArgs = fetchSpy.mock.calls[0]
    const headers = callArgs[1].headers as Headers
    expect(headers.get('Authorization')).toBe('Bearer test-jwt-token')
  })

  it('does not inject Authorization header when no token in localStorage', async () => {
    fetchSpy.mockResolvedValue(mockResponse(200, { ok: true }))

    await apiFetch('/api/test')

    const callArgs = fetchSpy.mock.calls[0]
    const headers = callArgs[1].headers as Headers
    expect(headers.has('Authorization')).toBe(false)
  })

  it('does not overwrite an existing Authorization header', async () => {
    localStorage.setItem('token', 'stored-token')
    fetchSpy.mockResolvedValue(mockResponse(200, { ok: true }))

    await apiFetch('/api/test', {
      headers: { Authorization: 'Bearer custom-token' },
    })

    const callArgs = fetchSpy.mock.calls[0]
    const headers = callArgs[1].headers as Headers
    expect(headers.get('Authorization')).toBe('Bearer custom-token')
  })

  it('always sends credentials: "include"', async () => {
    fetchSpy.mockResolvedValue(mockResponse(200, { ok: true }))

    await apiFetch('/api/test')

    const callArgs = fetchSpy.mock.calls[0]
    expect(callArgs[1].credentials).toBe('include')
  })

  it('redirects to login on 401 when token existed (session expired)', async () => {
    localStorage.setItem('token', 'expired-token')
    fetchSpy.mockResolvedValue(mockResponse(401, { detail: 'Not authenticated' }))

    await apiFetch('/api/protected')

    // Token should be removed
    expect(localStorage.getItem('token')).toBeNull()
    // Should redirect to login with expired param
    expect(window.location.href).toBe('/login?expired=true')
  })

  it('does not redirect on 401 when no token existed (unauthenticated request)', async () => {
    fetchSpy.mockResolvedValue(mockResponse(401, { detail: 'Not authenticated' }))

    await apiFetch('/api/protected')

    // No redirect since there was no token
    expect(window.location.href).toBe('/')
  })

  it('does not redirect on 401 when skipAuthRedirect is true', async () => {
    localStorage.setItem('token', 'some-token')
    fetchSpy.mockResolvedValue(mockResponse(401, { detail: 'Not authenticated' }))

    await apiFetch('/api/protected', { skipAuthRedirect: true })

    // Token should still be present
    expect(localStorage.getItem('token')).toBe('some-token')
    expect(window.location.href).toBe('/')
  })

  it('does not redirect on 401 if already on /login page', async () => {
    localStorage.setItem('token', 'some-token')
    Object.defineProperty(window, 'location', {
      writable: true,
      value: { href: '/login', pathname: '/login' },
    })
    fetchSpy.mockResolvedValue(mockResponse(401, { detail: 'Not authenticated' }))

    await apiFetch('/api/auth/me')

    // Token removed but no redirect (already on login)
    expect(localStorage.getItem('token')).toBeNull()
    expect(window.location.href).toBe('/login')
  })

  it('throws on network failure', async () => {
    fetchSpy.mockRejectedValue(new TypeError('Failed to fetch'))

    await expect(apiFetch('/api/test')).rejects.toThrow('Failed to fetch')
  })

  it('throws timeout error when request exceeds timeoutMs', async () => {
    vi.useFakeTimers()
    fetchSpy.mockImplementation(
      (_url: string, init: RequestInit) =>
        new Promise((_resolve, reject) => {
          init.signal?.addEventListener('abort', () => {
            reject(new DOMException('The operation was aborted', 'AbortError'))
          })
        }),
    )

    const promise = apiFetch('/api/slow', { timeoutMs: 100 })
    vi.advanceTimersByTime(150)

    await expect(promise).rejects.toThrow('Request timed out after 100ms')
    vi.useRealTimers()
  })

  it('sets cache to "default" for GET requests', async () => {
    fetchSpy.mockResolvedValue(mockResponse(200, {}))

    await apiFetch('/api/test')

    const callArgs = fetchSpy.mock.calls[0]
    expect(callArgs[1].cache).toBe('default')
  })

  it('sets cache to "no-store" for POST requests', async () => {
    fetchSpy.mockResolvedValue(mockResponse(200, {}))

    await apiFetch('/api/test', { method: 'POST' })

    const callArgs = fetchSpy.mock.calls[0]
    expect(callArgs[1].cache).toBe('no-store')
  })
})

describe('apiFetchJson', () => {
  it('returns parsed JSON body on success', async () => {
    const data = { id: 1, name: 'test' }
    fetchSpy.mockResolvedValue(mockResponse(200, data))

    const result = await apiFetchJson('/api/test')

    expect(result).toEqual(data)
  })

  it('returns empty object when response body is empty', async () => {
    fetchSpy.mockResolvedValue(mockResponse(200, null))

    const result = await apiFetchJson('/api/test')

    expect(result).toEqual({})
  })

  it('throws ApiError with detail message on non-ok response', async () => {
    fetchSpy.mockResolvedValue(mockResponse(400, { detail: 'Bad request' }))

    try {
      await apiFetchJson('/api/test')
      expect.fail('Should have thrown')
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError)
      const apiErr = err as ApiError
      expect(apiErr.message).toBe('Bad request')
      expect(apiErr.status).toBe(400)
      expect(apiErr.url).toBe('/api/test')
    }
  })

  it('throws ApiError with nested detail.message on non-ok response', async () => {
    fetchSpy.mockResolvedValue(
      mockResponse(422, { detail: { message: 'Validation failed' } }),
    )

    try {
      await apiFetchJson('/api/test')
      expect.fail('Should have thrown')
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError)
      expect((err as ApiError).message).toBe('Validation failed')
    }
  })

  it('throws ApiError with generic message when no detail in body', async () => {
    fetchSpy.mockResolvedValue(mockResponse(500, { error: 'internal' }))

    try {
      await apiFetchJson('/api/test')
      expect.fail('Should have thrown')
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError)
      expect((err as ApiError).message).toBe('Request failed (500)')
    }
  })

  it('throws ApiError when response is text instead of JSON', async () => {
    // Simulate text response by returning a response whose text() returns non-JSON
    const res = {
      ...mockResponse(200),
      ok: true,
      status: 200,
      text: () => Promise.resolve('plain text response'),
    } as Response
    fetchSpy.mockResolvedValue(res)

    try {
      await apiFetchJson('/api/test')
      expect.fail('Should have thrown')
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError)
      expect((err as ApiError).message).toContain('Expected JSON response')
    }
  })
})
