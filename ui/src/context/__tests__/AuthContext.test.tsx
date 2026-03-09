import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, act, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import React from 'react'
import { AuthProvider, useAuth } from '../AuthContext'

// ── Mock next/navigation ──
const mockPush = vi.fn()
const mockReplace = vi.fn()
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
    replace: mockReplace,
    prefetch: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
    refresh: vi.fn(),
  }),
  usePathname: () => '/',
  useSearchParams: () => new URLSearchParams(),
}))

// ── Test consumer component ──
function AuthConsumer() {
  const { user, loading, isAuthenticated, token, logout, login } = useAuth()
  const [loginError, setLoginError] = React.useState<string | null>(null)

  const handleLogin = async () => {
    setLoginError(null)
    try {
      await login('test@test.com', 'password')
    } catch (err: any) {
      setLoginError(err.message || 'Login failed')
    }
  }

  return (
    <div>
      <div data-testid="loading">{String(loading)}</div>
      <div data-testid="authenticated">{String(isAuthenticated)}</div>
      <div data-testid="user">{user ? JSON.stringify(user) : 'null'}</div>
      <div data-testid="token">{token ?? 'null'}</div>
      <div data-testid="login-error">{loginError ?? ''}</div>
      <button data-testid="logout-btn" onClick={logout}>
        Logout
      </button>
      <button data-testid="login-btn" onClick={handleLogin}>
        Login
      </button>
    </div>
  )
}

// ── Helpers ──

let fetchSpy: ReturnType<typeof vi.fn>

function renderWithAuth() {
  return render(
    <AuthProvider>
      <AuthConsumer />
    </AuthProvider>,
  )
}

// ── Setup / Teardown ──

beforeEach(() => {
  fetchSpy = vi.fn()
  vi.stubGlobal('fetch', fetchSpy)
  localStorage.clear()
  mockPush.mockClear()
  mockReplace.mockClear()
})

afterEach(() => {
  vi.restoreAllMocks()
})

// ── Tests ──

describe('AuthProvider', () => {
  describe('initialization', () => {
    it('starts in loading state', () => {
      // Make fetch hang so we can observe the loading state
      fetchSpy.mockImplementation(() => new Promise(() => {}))

      renderWithAuth()

      expect(screen.getByTestId('loading').textContent).toBe('true')
    })

    it('sets user from /api/auth/me on mount when token exists', async () => {
      localStorage.setItem('token', 'valid-token')
      fetchSpy.mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            id: '1',
            email: 'user@test.com',
            role: 'admin',
            is_admin: true,
            disabled: false,
          }),
      })

      renderWithAuth()

      await waitFor(() => {
        expect(screen.getByTestId('loading').textContent).toBe('false')
      })

      expect(screen.getByTestId('authenticated').textContent).toBe('true')
      const userData = JSON.parse(screen.getByTestId('user').textContent!)
      expect(userData.email).toBe('user@test.com')
      expect(userData.role).toBe('admin')
    })

    it('clears auth state when /api/auth/me returns non-ok', async () => {
      localStorage.setItem('token', 'stale-token')
      fetchSpy.mockResolvedValue({ ok: false, json: () => Promise.resolve({}) })

      renderWithAuth()

      await waitFor(() => {
        expect(screen.getByTestId('loading').textContent).toBe('false')
      })

      expect(screen.getByTestId('authenticated').textContent).toBe('false')
      expect(screen.getByTestId('user').textContent).toBe('null')
      expect(localStorage.getItem('token')).toBeNull()
    })

    it('clears auth state when /api/auth/me fetch throws', async () => {
      localStorage.setItem('token', 'stale-token')
      fetchSpy.mockRejectedValue(new Error('Network error'))

      renderWithAuth()

      await waitFor(() => {
        expect(screen.getByTestId('loading').textContent).toBe('false')
      })

      expect(screen.getByTestId('authenticated').textContent).toBe('false')
      expect(localStorage.getItem('token')).toBeNull()
    })
  })

  describe('normalizeUser', () => {
    it('normalizes role to lowercase and derives is_admin', async () => {
      fetchSpy.mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            id: '1',
            email: 'owner@test.com',
            role: 'Owner',
            is_admin: false,
            disabled: false,
          }),
      })

      renderWithAuth()

      await waitFor(() => {
        expect(screen.getByTestId('loading').textContent).toBe('false')
      })

      const userData = JSON.parse(screen.getByTestId('user').textContent!)
      expect(userData.role).toBe('owner')
      // Owner role should set is_admin to true
      expect(userData.is_admin).toBe(true)
    })

    it('defaults unknown roles to "general"', async () => {
      fetchSpy.mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            id: '1',
            email: 'user@test.com',
            role: 'viewer',
            is_admin: false,
            disabled: false,
          }),
      })

      renderWithAuth()

      await waitFor(() => {
        expect(screen.getByTestId('loading').textContent).toBe('false')
      })

      const userData = JSON.parse(screen.getByTestId('user').textContent!)
      expect(userData.role).toBe('general')
    })
  })

  describe('logout', () => {
    it('clears user state, removes token, and navigates to /login', async () => {
      // Initial mount: authenticated
      localStorage.setItem('token', 'valid-token')
      fetchSpy.mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            id: '1',
            email: 'user@test.com',
            role: 'general',
            is_admin: false,
            disabled: false,
          }),
      })

      renderWithAuth()

      await waitFor(() => {
        expect(screen.getByTestId('authenticated').textContent).toBe('true')
      })

      // Mock the logout POST request
      fetchSpy.mockResolvedValue({ ok: true })

      await act(async () => {
        screen.getByTestId('logout-btn').click()
      })

      await waitFor(() => {
        expect(screen.getByTestId('authenticated').textContent).toBe('false')
      })

      expect(screen.getByTestId('user').textContent).toBe('null')
      expect(screen.getByTestId('token').textContent).toBe('null')
      expect(localStorage.getItem('token')).toBeNull()
      expect(mockPush).toHaveBeenCalledWith('/login')
    })

    it('still clears state even if logout POST fails', async () => {
      localStorage.setItem('token', 'valid-token')
      fetchSpy.mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            id: '1',
            email: 'user@test.com',
            role: 'general',
            is_admin: false,
            disabled: false,
          }),
      })

      renderWithAuth()

      await waitFor(() => {
        expect(screen.getByTestId('authenticated').textContent).toBe('true')
      })

      // Logout POST fails
      fetchSpy.mockRejectedValue(new Error('Network error'))

      await act(async () => {
        screen.getByTestId('logout-btn').click()
      })

      await waitFor(() => {
        expect(screen.getByTestId('authenticated').textContent).toBe('false')
      })

      expect(localStorage.getItem('token')).toBeNull()
      expect(mockPush).toHaveBeenCalledWith('/login')
    })
  })

  describe('login', () => {
    it('sets user and token on successful login', async () => {
      // Initial mount: no auth
      fetchSpy.mockResolvedValue({ ok: false, json: () => Promise.resolve({}) })

      renderWithAuth()

      await waitFor(() => {
        expect(screen.getByTestId('loading').textContent).toBe('false')
      })

      // Login call: first the login endpoint, then /api/auth/me
      fetchSpy
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ access_token: 'new-jwt-token' }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () =>
            Promise.resolve({
              id: '1',
              email: 'test@test.com',
              role: 'general',
              is_admin: false,
              disabled: false,
            }),
        })

      await act(async () => {
        screen.getByTestId('login-btn').click()
      })

      await waitFor(() => {
        expect(screen.getByTestId('authenticated').textContent).toBe('true')
      })

      expect(screen.getByTestId('token').textContent).toBe('new-jwt-token')
      expect(localStorage.getItem('token')).toBe('new-jwt-token')
      expect(mockPush).toHaveBeenCalledWith('/')
    })

    it('surfaces error and does not set auth state on failed login', async () => {
      // Initial mount: no auth
      fetchSpy.mockResolvedValue({ ok: false, json: () => Promise.resolve({}) })

      renderWithAuth()

      await waitFor(() => {
        expect(screen.getByTestId('loading').textContent).toBe('false')
      })

      // Login returns error
      fetchSpy.mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: () => Promise.resolve({ detail: 'Invalid credentials' }),
      })

      await act(async () => {
        screen.getByTestId('login-btn').click()
      })

      // Wait for error to be captured by the consumer
      await waitFor(() => {
        expect(screen.getByTestId('login-error').textContent).toBe(
          'Invalid credentials',
        )
      })

      expect(screen.getByTestId('authenticated').textContent).toBe('false')
    })
  })
})

describe('useAuth', () => {
  it('throws when used outside AuthProvider', () => {
    function BadConsumer() {
      useAuth()
      return null
    }

    // Suppress React error boundary console noise
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    expect(() => render(<BadConsumer />)).toThrow(
      'useAuth must be used within an AuthProvider',
    )

    consoleSpy.mockRestore()
  })
})
