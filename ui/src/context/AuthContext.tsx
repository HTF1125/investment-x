'use client';

import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { useRouter } from 'next/navigation';

// Types
export interface User {
  id: string;
  email: string;
  first_name?: string;
  last_name?: string;
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
      const storedToken = localStorage.getItem('token');
      if (storedToken) {
        try {
          const res = await fetch('/api/auth/me', {
            headers: { 'Authorization': `Bearer ${storedToken}` },
          });
          
          if (res.ok) {
            const userData = await res.json();
            setUser(userData);
            setToken(storedToken);
          } else {
            // Invalid token — clear it
            updateToken(null);
            setUser(null);
          }
        } catch {
          updateToken(null);
          setUser(null);
        }
      }
      setLoading(false);
    };

    initAuth();
  }, [updateToken]);

  const login = useCallback(async (email: string, password: string, rememberMe: boolean = false) => {
    setLoading(true);
    try {
      const res = await fetch('/api/auth/login/json', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, remember_me: rememberMe }),
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || 'Login failed');
      }

      const data = await res.json();
      updateToken(data.access_token);
      
      // Fetch user details immediately
      const meRes = await fetch('/api/auth/me', {
        headers: { 'Authorization': `Bearer ${data.access_token}` },
      });
      
      if (meRes.ok) {
        const userData = await meRes.json();
        setUser(userData);
        router.push('/');
      }
    } catch (err) {
      throw err;
    } finally {
      setLoading(false);
    }
  }, [router, updateToken]);

  const register = useCallback(async (email: string, password: string, firstName?: string, lastName?: string) => {
    setLoading(true);
    try {
      const res = await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
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

  const logout = useCallback(() => {
    updateToken(null);
    setUser(null);
    router.push('/login');
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
