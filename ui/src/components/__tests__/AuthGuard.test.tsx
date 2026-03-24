import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import React from 'react'

// ── Mock useAuth ──
const mockUseAuth = vi.fn()
vi.mock('@/context/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}))

// ── Mock next/navigation ──
const mockReplace = vi.fn()
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: mockReplace,
    prefetch: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
    refresh: vi.fn(),
  }),
}))

// Import after mocks are set up
import AuthGuard from '../auth/AuthGuard'

// ── Setup / Teardown ──

beforeEach(() => {
  mockUseAuth.mockReset()
  mockReplace.mockClear()
})

afterEach(() => {
  vi.restoreAllMocks()
})

// ── Tests ──

describe('AuthGuard', () => {
  it('shows loading indicator while auth is initializing', () => {
    mockUseAuth.mockReturnValue({ user: null, loading: true })

    render(
      <AuthGuard>
        <div data-testid="protected">Protected Content</div>
      </AuthGuard>,
    )

    expect(screen.queryByTestId('protected')).not.toBeInTheDocument()
    expect(screen.getByText(/INITIALIZING SECURITY PROTOCOLS/i)).toBeInTheDocument()
  })

  it('renders children when user is authenticated', () => {
    mockUseAuth.mockReturnValue({
      user: { id: '1', email: 'user@test.com', role: 'general' },
      loading: false,
    })

    render(
      <AuthGuard>
        <div data-testid="protected">Protected Content</div>
      </AuthGuard>,
    )

    expect(screen.getByTestId('protected')).toBeInTheDocument()
    expect(screen.getByText('Protected Content')).toBeInTheDocument()
  })

  it('renders nothing and redirects to /login when not authenticated', async () => {
    mockUseAuth.mockReturnValue({ user: null, loading: false })

    const { container } = render(
      <AuthGuard>
        <div data-testid="protected">Protected Content</div>
      </AuthGuard>,
    )

    // Should not render children
    expect(screen.queryByTestId('protected')).not.toBeInTheDocument()
    // Container should be empty (returns null)
    expect(container.innerHTML).toBe('')

    // Should redirect to /login
    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith('/login')
    })
  })

  it('does not redirect while still loading', () => {
    mockUseAuth.mockReturnValue({ user: null, loading: true })

    render(
      <AuthGuard>
        <div>Content</div>
      </AuthGuard>,
    )

    expect(mockReplace).not.toHaveBeenCalled()
  })

  it('redirects only once when auth state settles to unauthenticated', async () => {
    mockUseAuth.mockReturnValue({ user: null, loading: false })

    render(
      <AuthGuard>
        <div>Content</div>
      </AuthGuard>,
    )

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledTimes(1)
    })
  })
})
