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
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  // Store token in state to avoid direct localStorage reads during render (SSR hydration safety)
  const [token, setToken] = useState<string | null>(null);
  const router = useRouter();

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

  // Sync token from localStorage on mount only (client-side)
  useEffect(() => {
    const stored = localStorage.getItem('token');
    if (stored) setToken(stored);
  }, []);

  // Persist token changes to localStorage
  const updateToken = useCallback((newToken: string | null) => {
    setToken(newToken);
    if (newToken) {
      localStorage.setItem('token', newToken);
    } else {
      localStorage.removeItem('token');
    }
  }, []);

  useEffect(() => {
    const initAuth = async () => {
      // With cookies, we don't strictly need to check localStorage, 
      // but we do it for cross-tab session persistence if cookies are volatile
      const storedToken = localStorage.getItem('token');
      
      try {
        const res = await fetch('/api/auth/me', {
          credentials: 'include', // Use browser cookies
          headers: storedToken ? { 'Authorization': `Bearer ${storedToken}` } : {},
        });
        
        if (res.ok) {
          const userData = await res.json();
          setUser(normalizeUser(userData));
          if (storedToken) setToken(storedToken);
        } else {
          updateToken(null);
          setUser(null);
        }
      } catch {
        updateToken(null);
        setUser(null);
      }
      setLoading(false);
    };

    initAuth();
  }, [normalizeUser, updateToken]);

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

      const data = await res.json();
      // Token is now set in cookie, but we still update localStorage for legacy CSR components
      updateToken(data.access_token);
      
      // Fetch user details immediately with the token we just received
      const meRes = await fetch('/api/auth/me', {
        credentials: 'include',
        headers: { 'Authorization': `Bearer ${data.access_token}` },
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
  }, [normalizeUser, router, updateToken]);

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
      updateToken(null);
      setUser(null);
      router.push('/login');
    }
  }, [router, updateToken]);

  return (
    <AuthContext.Provider value={{ 
      user, 
      loading, 
      login, 
      register, 
      logout,
      isAuthenticated: !!user,
      token,
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
