'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { Mail, Lock, User, ArrowRight, AlertTriangle, X } from 'lucide-react';

export default function RegisterPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');

  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const { register } = useAuth();
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    if (!email || !password || !firstName || !lastName) {
      setError('Please fill in all fields');
      setLoading(false);
      return;
    }

    if (password.length < 8) {
      setError('Password must be at least 8 characters');
      setLoading(false);
      return;
    }

    try {
      await register(email, password, firstName, lastName);
      router.push('/');
    } catch (err: any) {
      setError(err.message || 'Failed to register account');
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-6 bg-background relative overflow-hidden">
      <div className="auth-grid-bg" />
      <div className="auth-vignette" />

      <div className="w-full max-w-md relative z-10">
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
          <h1 className="text-3xl font-bold text-foreground tracking-tight leading-tight">Request access</h1>
          <p className="text-muted-foreground/50 text-sm mt-2">Join the research network</p>
        </div>

        {error && (
          <div role="alert" aria-live="polite" className="mb-6 p-3 bg-destructive/5 border border-destructive/15 rounded-[var(--radius)] text-destructive text-sm flex items-center gap-2.5">
            <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-[10px] font-mono uppercase tracking-[0.1em] text-muted-foreground/50 pl-0.5">First Name</label>
              <div className="relative group">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground/30 group-focus-within:text-primary transition-colors" />
                <input
                  type="text"
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  className="w-full pl-10 pr-4 py-2.5 bg-card/50 border border-border/50 rounded-[var(--radius)] text-sm text-foreground focus:outline-none focus:border-primary/40 focus:ring-2 focus:ring-primary/15 transition-all placeholder:text-muted-foreground/25"
                  placeholder="Jane"
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="text-[10px] font-mono uppercase tracking-[0.1em] text-muted-foreground/50 pl-0.5">Last Name</label>
              <input
                type="text"
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                className="w-full px-4 py-2.5 bg-card/50 border border-border/50 rounded-[var(--radius)] text-sm text-foreground focus:outline-none focus:border-primary/40 focus:ring-2 focus:ring-primary/15 transition-all placeholder:text-muted-foreground/25"
                placeholder="Doe"
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-[10px] font-mono uppercase tracking-[0.1em] text-muted-foreground/50 pl-0.5">Work Email</label>
            <div className="relative group">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground/30 group-focus-within:text-primary transition-colors" />
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 bg-card/50 border border-border/50 rounded-[var(--radius)] text-sm text-foreground focus:outline-none focus:border-primary/40 focus:ring-2 focus:ring-primary/15 transition-all placeholder:text-muted-foreground/25"
                placeholder="analyst@firm.com"
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-[10px] font-mono uppercase tracking-[0.1em] text-muted-foreground/50 pl-0.5">Password</label>
            <div className="relative group">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground/30 group-focus-within:text-primary transition-colors" />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 bg-card/50 border border-border/50 rounded-[var(--radius)] text-sm text-foreground focus:outline-none focus:border-primary/40 focus:ring-2 focus:ring-primary/15 transition-all placeholder:text-muted-foreground/25"
                placeholder="Min. 8 characters"
              />
            </div>
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
                Create Account
                <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
              </>
            )}
          </button>
        </form>

        <div className="mt-8 pt-6 border-t border-border/15 text-center text-xs text-muted-foreground/40">
          Already have credentials?{' '}
          <Link href="/login" className="text-primary hover:text-primary/80 font-semibold transition-colors underline underline-offset-2">
            Login here
          </Link>
        </div>
      </div>
    </div>
  );
}
