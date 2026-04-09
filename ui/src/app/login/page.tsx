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
    <div className="w-full max-w-[400px] relative z-10">
      <button
        type="button"
        onClick={() => router.back()}
        className="absolute -top-12 right-0 p-1.5 rounded-[var(--radius)] text-muted-foreground/25 hover:text-muted-foreground hover:bg-foreground/[0.06] transition-all"
        title="Go back"
        aria-label="Go back"
      >
        <X className="w-4 h-4" />
      </button>

      <div className="mb-10">
        <div className="text-[11.5px] font-mono uppercase tracking-[0.14em] text-primary/70 mb-3">Investment-X</div>
        <h1 className="text-[2.25rem] font-bold text-foreground tracking-[-0.03em] leading-[1.1]">Welcome back</h1>
        <p className="text-muted-foreground/50 text-[13px] mt-2.5 tracking-wide">Sign in to your research account</p>
      </div>

      {isExpired && !error && (
        <div className="mb-6 px-3.5 py-3 bg-primary/[0.06] border border-primary/20 rounded-[var(--radius)] text-primary text-[13px] flex items-center gap-2.5">
          <AlertCircle className="w-3.5 h-3.5 shrink-0" />
          <span>Session expired — please sign in again.</span>
        </div>
      )}

      {error && (
        <div role="alert" aria-live="polite" className="mb-6 px-3.5 py-3 bg-destructive/[0.06] border border-destructive/20 rounded-[var(--radius)] text-destructive text-[13px] flex items-center gap-2.5">
          <AlertCircle className="w-3.5 h-3.5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-1.5">
          <label className="text-[11.5px] font-mono uppercase tracking-[0.12em] text-muted-foreground/40 pl-0.5">Email</label>
          <div className="relative group">
            <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground/25 group-focus-within:text-primary/70 transition-colors" />
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full pl-9 pr-4 py-3 bg-card border border-border/40 rounded-[var(--radius)] text-[13px] text-foreground focus:outline-none focus:border-primary/50 focus:ring-2 focus:ring-primary/20 transition-all placeholder:text-muted-foreground/20 hover:border-border/60"
              placeholder="analyst@investment-x.com"
            />
          </div>
        </div>

        <div className="space-y-1.5">
          <div className="flex items-center justify-between pl-0.5">
            <label className="text-[11.5px] font-mono uppercase tracking-[0.12em] text-muted-foreground/40">Password</label>
            <a href="#" className="text-[11.5px] font-mono tracking-[0.04em] text-muted-foreground/35 hover:text-primary/80 transition-colors">Forgot?</a>
          </div>
          <div className="relative group">
            <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground/25 group-focus-within:text-primary/70 transition-colors" />
            <input
              type={showPassword ? "text" : "password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full pl-9 pr-10 py-3 bg-card border border-border/40 rounded-[var(--radius)] text-[13px] text-foreground focus:outline-none focus:border-primary/50 focus:ring-2 focus:ring-primary/20 transition-all placeholder:text-muted-foreground/20 hover:border-border/60"
              placeholder="••••••••"
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-muted-foreground/25 hover:text-muted-foreground/60 rounded transition-colors"
              title={showPassword ? "Hide password" : "Show password"}
            >
              {showPassword ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
            </button>
          </div>
        </div>

        <div className="flex items-center gap-2 pl-0.5 pt-0.5">
           <input
             type="checkbox"
             id="remember-me"
             checked={rememberMe}
             onChange={(e) => setRememberMe(e.target.checked)}
             className="w-3.5 h-3.5 rounded border-border/50 bg-card text-primary focus:ring-primary/30 focus:ring-offset-0 transition-colors accent-primary cursor-pointer"
           />
           <label htmlFor="remember-me" className="text-[12.5px] text-muted-foreground/40 select-none cursor-pointer hover:text-muted-foreground/70 transition-colors">
             Keep me signed in
           </label>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full mt-2 py-3 px-4 bg-foreground text-background rounded-[var(--radius)] font-semibold text-[13px] uppercase tracking-[0.08em] transition-all hover:opacity-85 active:opacity-75 flex items-center justify-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed group active:scale-[0.99]"
        >
          {loading ? (
            <>
              <div className="w-4 h-4 border-2 border-background/30 border-t-background rounded-full animate-spin" />
              <span>Signing in...</span>
            </>
          ) : (
            <>
              Sign In
              <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
            </>
          )}
        </button>
      </form>

      <div className="mt-8 pt-6 border-t border-border/15 text-center text-[12.5px] text-muted-foreground/35 tracking-wide">
        No account?{' '}
        <Link href="/register" className="text-muted-foreground/60 hover:text-foreground font-semibold transition-colors underline underline-offset-2 decoration-border/40">
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
      <Suspense fallback={<div className="text-muted-foreground/40 animate-pulse text-[13px] font-mono relative z-10">Loading...</div>}>
        <LoginForm />
      </Suspense>
    </div>
  );
}
