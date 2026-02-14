'use client';

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
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
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, firstName?: string, lastName?: string) => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
  token: string | null;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  // Helper to get token
  const getToken = () => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('token');
    }
    return null;
  };

  useEffect(() => {
    // Check for existing token on mount
    const initAuth = async () => {
      const token = getToken();
      if (token) {
        try {
          const res = await fetch('/api/auth/me', {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          });
          
          if (res.ok) {
            const userData = await res.json();
            setUser(userData);
          } else {
            // Invalid token
            localStorage.removeItem('token');
            setUser(null);
          }
        } catch (err) {
          console.error('Auth initialization error:', err);
          localStorage.removeItem('token');
          setUser(null);
        }
      }
      setLoading(false);
    };

    initAuth();
  }, []);

  const login = async (email: string, password: string) => {
    setLoading(true);
    try {
      const res = await fetch('/api/auth/login/json', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password }),
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || 'Login failed');
      }

      const data = await res.json();
      localStorage.setItem('token', data.access_token);
      
      // Fetch user details immediately
      const meRes = await fetch('/api/auth/me', {
        headers: {
          'Authorization': `Bearer ${data.access_token}`
        }
      });
      
      if (meRes.ok) {
        const userData = await meRes.json();
        setUser(userData);
        router.push('/'); // Redirect to dashboard
      }
    } catch (err) {
      console.error('Login error:', err);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const register = async (email: string, password: string, firstName?: string, lastName?: string) => {
    setLoading(true);
    try {
      const res = await fetch('/api/auth/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          email, 
          password,
          first_name: firstName,
          last_name: lastName
        }),
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || 'Registration failed');
      }

      // Automatically login after register? Or redirect to login?
      // Let's auto-login for better UX
      await login(email, password);
    } catch (err) {
      console.error('Registration error:', err);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    setUser(null);
    router.push('/login');
  };

  return (
    <AuthContext.Provider value={{ 
      user, 
      loading, 
      login, 
      register, 
      logout,
      isAuthenticated: !!user,
      token: typeof window !== 'undefined' ? localStorage.getItem('token') : null
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
