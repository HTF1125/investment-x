'use client';

import React, { useState, Suspense } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { Mail, Lock, ArrowRight, Eye, EyeOff, X, AlertCircle } from 'lucide-react';

function LoginForm() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(false);
  const [error, setError] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const { login, loading } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const isExpired = searchParams.get('expired') === 'true';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!email || !password) {
      setError('Please fill in all fields');
      return;
    }

    try {
      await login(email, password, rememberMe);
    } catch (err: any) {
      setError(err.message || 'Failed to login');
    }
  };

  return (
    <div className="w-full max-w-[380px] relative z-10">
      <button
        type="button"
        onClick={() => router.back()}
        className="absolute -top-12 right-0 p-1.5 rounded-[var(--radius)] text-muted-foreground/30 hover:text-primary hover:bg-primary/10 transition-all"
        title="Go back"
        aria-label="Go back"
      >
        <X className="w-4 h-4" />
      </button>

      <div className="mb-10">
        <h1 className="text-3xl font-bold text-foreground tracking-tight leading-tight">Welcome back</h1>
        <p className="text-muted-foreground/50 text-sm mt-2">Sign in to continue</p>
      </div>

      {isExpired && !error && (
        <div className="mb-6 p-3 bg-primary/5 border border-primary/15 rounded-[var(--radius)] text-primary text-sm flex items-center gap-2.5">
          <AlertCircle className="w-3.5 h-3.5 shrink-0" />
          <span>Session expired. Sign in again.</span>
        </div>
      )}

      {error && (
        <div role="alert" aria-live="polite" className="mb-6 p-3 bg-destructive/5 border border-destructive/15 rounded-[var(--radius)] text-destructive text-sm flex items-center gap-2.5">
          <AlertCircle className="w-3.5 h-3.5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-5">
        <div className="space-y-1.5">
          <label className="text-[10px] font-mono uppercase tracking-[0.1em] text-muted-foreground/50 pl-0.5">Email</label>
          <div className="relative group">
            <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground/30 group-focus-within:text-primary transition-colors" />
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 bg-card/50 border border-border/50 rounded-[var(--radius)] text-sm text-foreground focus:outline-none focus:border-primary/40 focus:ring-2 focus:ring-primary/15 transition-all placeholder:text-muted-foreground/25"
              placeholder="analyst@investment-x.com"
            />
          </div>
        </div>

        <div className="space-y-1.5">
          <div className="flex items-center justify-between pl-0.5">
            <label className="text-[10px] font-mono uppercase tracking-[0.1em] text-muted-foreground/50">Password</label>
            <a href="#" className="text-[10px] font-medium text-muted-foreground/40 hover:text-primary transition-colors">Forgot?</a>
          </div>
          <div className="relative group">
            <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground/30 group-focus-within:text-primary transition-colors" />
            <input
              type={showPassword ? "text" : "password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full pl-10 pr-10 py-2.5 bg-card/50 border border-border/50 rounded-[var(--radius)] text-sm text-foreground focus:outline-none focus:border-primary/40 focus:ring-2 focus:ring-primary/15 transition-all placeholder:text-muted-foreground/25"
              placeholder="••••••••"
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-muted-foreground/30 hover:text-primary rounded transition-colors"
              title={showPassword ? "Hide password" : "Show password"}
            >
              {showPassword ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
            </button>
          </div>
        </div>

        <div className="flex items-center gap-2 pl-0.5">
           <input
             type="checkbox"
             id="remember-me"
             checked={rememberMe}
             onChange={(e) => setRememberMe(e.target.checked)}
             className="w-3.5 h-3.5 rounded border-border/50 bg-card/50 text-primary focus:ring-primary/30 focus:ring-offset-0 transition-colors accent-primary cursor-pointer"
           />
           <label htmlFor="remember-me" className="text-xs text-muted-foreground/50 select-none cursor-pointer hover:text-foreground transition-colors">
             Remember me
           </label>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full mt-3 py-2.5 px-4 bg-primary text-primary-foreground rounded-[var(--radius)] font-semibold text-sm transition-all hover:opacity-90 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed group active:scale-[0.99]"
        >
          {loading ? (
            <div className="w-4 h-4 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin" />
          ) : (
            <>
              Sign In
              <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
            </>
          )}
        </button>
      </form>

      <div className="mt-8 pt-6 border-t border-border/15 text-center text-xs text-muted-foreground/40">
        No account?{' '}
        <Link href="/register" className="text-primary hover:text-primary/80 font-semibold transition-colors underline underline-offset-2">
          Apply for access
        </Link>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-6 bg-background relative overflow-hidden">
      <div className="auth-grid-bg" />
      <div className="auth-vignette" />
      <Suspense fallback={<div className="text-foreground animate-pulse text-sm relative z-10">Loading...</div>}>
        <LoginForm />
      </Suspense>
    </div>
  );
}
