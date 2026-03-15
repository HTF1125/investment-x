'use client';

import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { useRouter } from 'next/navigation';

// Types
export interface User {
  id: string;
  email: string;
  first_name?: string;
  last_name?: string;
  role?: 'owner' | 'admin' | 'general' | string;
  is_admin: boolean;
  disabled: boolean;
  created_at?: string;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string, rememberMe?: boolean) => Promise<void>;
  register: (email: string, password: string, firstName?: string, lastName?: string) => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
  token: string | null;
  viewAsUser: boolean;
  toggleViewAsUser: () => void;
  isSessionExpired: boolean;
  dismissSessionExpired: () => void;
  reauth: (email: string, password: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  // Opaque auth marker for components that check !!token — actual auth uses HttpOnly cookies
  const [token, setToken] = useState<string | null>(null);
  const [viewAsUser, setViewAsUser] = useState(false);
  const [isSessionExpired, setIsSessionExpired] = useState(false);
  const router = useRouter();

  useEffect(() => {
    if (localStorage.getItem('viewAsUser') === 'true') setViewAsUser(true);
  }, []);

  const toggleViewAsUser = useCallback(() => {
    setViewAsUser(v => {
      const next = !v;
      localStorage.setItem('viewAsUser', String(next));
      return next;
    });
  }, []);

  const normalizeUser = useCallback((raw: any): User => {
    const roleRaw = String(raw?.role || '').toLowerCase();
    const role = roleRaw === 'owner' || roleRaw === 'admin' || roleRaw === 'general'
      ? roleRaw
      : 'general';
    const isAdmin = role === 'owner' || role === 'admin' || !!raw?.is_admin;
    return {
      ...raw,
      role,
      is_admin: isAdmin,
    } as User;
  }, []);


  useEffect(() => {
    const initAuth = async () => {
      try {
        const res = await fetch('/api/auth/me', {
          credentials: 'include',
        });

        if (res.ok) {
          const userData = await res.json();
          setUser(normalizeUser(userData));
          setToken('cookie'); // Opaque marker so !!token works for auth checks
        } else {
          setToken(null);
          setUser(null);
        }
      } catch {
        setToken(null);
        setUser(null);
      }
      setLoading(false);
    };

    initAuth();
  }, [normalizeUser]);

  // Listen for 401 session-expired events dispatched by apiFetch
  useEffect(() => {
    const handler = () => setIsSessionExpired(true);
    window.addEventListener('ix:session-expired', handler);
    return () => window.removeEventListener('ix:session-expired', handler);
  }, []);

  const dismissSessionExpired = useCallback(() => setIsSessionExpired(false), []);

  // Re-authenticate without losing page state
  const reauth = useCallback(async (email: string, password: string) => {
    const res = await fetch('/api/auth/login/json', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || 'Login failed');
    }
    await res.json(); // consume response body
    setToken('cookie');
    const meRes = await fetch('/api/auth/me', {
      credentials: 'include',
    });
    if (meRes.ok) {
      const userData = await meRes.json();
      setUser(normalizeUser(userData));
    }
    setIsSessionExpired(false);
  }, [normalizeUser]);

  const login = useCallback(async (email: string, password: string, rememberMe: boolean = false) => {
    setLoading(true);
    try {
      const res = await fetch('/api/auth/login/json', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include', // Ensure cookies are received
        body: JSON.stringify({ email, password, remember_me: rememberMe }),
      });

      if (!res.ok) {
        let errorMessage = 'Login failed';
        try {
          const errorData = await res.json();
          errorMessage = errorData.detail || errorData.error || errorMessage;
        } catch (e) {
          const text = await res.text().catch(() => '');
          errorMessage = text || `Request failed with status ${res.status}`;
        }
        throw new Error(errorMessage);
      }

      await res.json(); // consume response body; cookie is set by the server
      setToken('cookie');

      // Fetch user details — cookie is sent automatically
      const meRes = await fetch('/api/auth/me', {
        credentials: 'include',
      });
      
      if (meRes.ok) {
        const userData = await meRes.json();
        setUser(normalizeUser(userData));
      }
      // Redirect to dashboard without full page reload
      router.push('/');
    } catch (err) {
      throw err;
    } finally {
      setLoading(false);
    }
  }, [normalizeUser, router]);

  const register = useCallback(async (email: string, password: string, firstName?: string, lastName?: string) => {
    setLoading(true);
    try {
      const res = await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ 
          email, 
          password,
          first_name: firstName,
          last_name: lastName,
        }),
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || 'Registration failed');
      }

      // Auto-login after successful registration
      await login(email, password);
    } catch (err) {
      throw err;
    } finally {
      setLoading(false);
    }
  }, [login]);

  const logout = useCallback(async () => {
    try {
      await fetch('/api/auth/logout', { 
        method: 'POST',
        credentials: 'include' 
      });
    } catch (err) {
      console.warn('Logout request failed', err);
    } finally {
      setToken(null);
      setUser(null);
      router.push('/login');
    }
  }, [router]);

  return (
    <AuthContext.Provider value={{
      user,
      loading,
      login,
      register,
      logout,
      isAuthenticated: !!user,
      token,
      viewAsUser,
      toggleViewAsUser,
      isSessionExpired,
      dismissSessionExpired,
      reauth,
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
