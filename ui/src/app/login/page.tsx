'use client';

import React, { useState, Suspense } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { Mail, Lock, LogIn, ArrowRight, Eye, EyeOff, X, AlertCircle } from 'lucide-react';

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
      // Redirect handled in AuthContext after successful login
    } catch (err: any) {
      setError(err.message || 'Failed to login');
    }
  };

  return (
    <div className="w-full max-w-md glass-card p-8 relative z-10 shadow-2xl shadow-sky-500/5 border-sky-500/20">
      <button
        type="button"
        onClick={() => router.back()}
        className="absolute top-4 right-4 p-1.5 rounded-lg text-muted-foreground/70 hover:text-foreground hover:bg-foreground/5 transition-all"
        title="Go back"
        aria-label="Go back"
      >
        <X className="w-4 h-4" />
      </button>
      <div className="mb-8 text-center mt-2">
        <div className="w-12 h-12 rounded-2xl bg-sky-500/10 flex items-center justify-center mx-auto mb-5 border border-sky-500/20 shadow-inner">
          <LogIn className="w-6 h-6 text-sky-500" />
        </div>
        <h1 className="text-2xl font-bold text-foreground mb-2 tracking-tight">Welcome Back</h1>
        <p className="text-muted-foreground text-sm">Sign in to access quantitative intelligence</p>
      </div>

      {isExpired && !error && (
        <div className="mb-6 p-4 bg-sky-500/10 border border-sky-500/20 rounded-xl text-sky-500 text-sm flex items-center gap-3">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>Your session has expired. Please sign in again.</span>
        </div>
      )}

      {error && (
        <div role="alert" aria-live="polite" className="mb-6 p-4 bg-rose-500/10 border border-rose-500/20 rounded-xl text-rose-500 text-sm flex items-center gap-3 shadow-sm">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-5">
        <div className="space-y-1.5">
          <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider pl-1">Email Address</label>
          <div className="relative group">
            <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground/60 group-focus-within:text-sky-500 transition-colors" />
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full pl-10 pr-4 py-3 bg-background/50 border border-border/60 rounded-xl text-sm text-foreground focus:outline-none focus:border-sky-500/50 focus:ring-1 focus:ring-sky-500/50 transition-all placeholder:text-muted-foreground/40 shadow-sm"
              placeholder="analyst@investment-x.com"
            />
          </div>
        </div>

        <div className="space-y-1.5">
          <div className="flex items-center justify-between pl-1">
            <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Password</label>
            <a href="#" className="text-[11px] font-medium text-sky-500 hover:text-sky-400 transition-colors">Forgot password?</a>
          </div>
          <div className="relative group">
            <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground/60 group-focus-within:text-sky-500 transition-colors" />
            <input
              type={showPassword ? "text" : "password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full pl-10 pr-10 py-3 bg-background/50 border border-border/60 rounded-xl text-sm text-foreground focus:outline-none focus:border-sky-500/50 focus:ring-1 focus:ring-sky-500/50 transition-all placeholder:text-muted-foreground/40 shadow-sm"
              placeholder="••••••••"
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 top-1/2 -translate-y-1/2 p-1.5 text-muted-foreground/60 hover:text-foreground hover:bg-foreground/5 rounded-md transition-colors"
              title={showPassword ? "Hide password" : "Show password"}
            >
              {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>
        </div>

        <div className="flex items-center gap-2 pt-1 pl-1">
           <input 
             type="checkbox" 
             id="remember-me"
             checked={rememberMe}
             onChange={(e) => setRememberMe(e.target.checked)}
             className="w-4 h-4 rounded border-border/60 bg-background/50 text-sky-500 focus:ring-sky-500/50 focus:ring-offset-0 transition-colors accent-sky-500 cursor-pointer"
           />
           <label htmlFor="remember-me" className="text-sm text-muted-foreground select-none cursor-pointer hover:text-foreground transition-colors">
             Remember me
           </label>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full mt-2 py-3.5 px-4 bg-sky-500 hover:bg-sky-400 text-white rounded-xl font-semibold transition-all shadow-lg shadow-sky-500/20 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed group active:scale-[0.98]"
        >
          {loading ? (
            <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
          ) : (
            <>
              Sign In
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </>
          )}
        </button>
      </form>

      <div className="mt-8 pt-6 border-t border-border/40 text-center text-sm text-muted-foreground">
        Don&apos;t have an account?{' '}
        <Link href="/register" className="text-sky-500 hover:text-sky-400 font-semibold transition-colors">
          Apply for access
        </Link>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-4 bg-background relative overflow-hidden">
      {/* Dynamic Background */}
      <div className="absolute inset-0 bg-[url('/grid.svg')] bg-center opacity-40 [mask-image:linear-gradient(180deg,black,rgba(0,0,0,0))]" />
      <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] bg-sky-500/10 blur-[120px] rounded-full pointer-events-none" />
      <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] bg-purple-500/10 blur-[120px] rounded-full pointer-events-none" />

      <div className="absolute top-6 right-6 z-20">
         {/* Theme Toggle placeholder, could be useful if they want it on login */}
      </div>

      <Suspense fallback={<div className="text-foreground animate-pulse">Loading...</div>}>
        <LoginForm />
      </Suspense>
    </div>
  );
}
