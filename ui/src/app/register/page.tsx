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
          <h1 className="text-[2.25rem] font-bold text-foreground tracking-[-0.03em] leading-[1.1]">Request access</h1>
          <p className="text-muted-foreground/50 text-[13px] mt-2.5 tracking-wide">Join the macro research network</p>
        </div>

        {error && (
          <div role="alert" aria-live="polite" className="mb-6 px-3.5 py-3 bg-destructive/[0.06] border border-destructive/20 rounded-[var(--radius)] text-destructive text-[13px] flex items-center gap-2.5">
            <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <label className="text-[11.5px] font-mono uppercase tracking-[0.12em] text-muted-foreground/40 pl-0.5">First Name</label>
              <div className="relative group">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground/25 group-focus-within:text-primary/70 transition-colors" />
                <input
                  type="text"
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  className="w-full pl-9 pr-4 py-3 bg-card border border-border/40 rounded-[var(--radius)] text-[13px] text-foreground focus:outline-none focus:border-primary/50 focus:ring-2 focus:ring-primary/20 transition-all placeholder:text-muted-foreground/20 hover:border-border/60"
                  placeholder="Jane"
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="text-[11.5px] font-mono uppercase tracking-[0.12em] text-muted-foreground/40 pl-0.5">Last Name</label>
              <div className="relative group">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground/25 group-focus-within:text-primary/70 transition-colors" />
                <input
                  type="text"
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                  className="w-full pl-9 pr-4 py-3 bg-card border border-border/40 rounded-[var(--radius)] text-[13px] text-foreground focus:outline-none focus:border-primary/50 focus:ring-2 focus:ring-primary/20 transition-all placeholder:text-muted-foreground/20 hover:border-border/60"
                  placeholder="Doe"
                />
              </div>
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-[11.5px] font-mono uppercase tracking-[0.12em] text-muted-foreground/40 pl-0.5">Work Email</label>
            <div className="relative group">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground/25 group-focus-within:text-primary/70 transition-colors" />
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full pl-9 pr-4 py-3 bg-card border border-border/40 rounded-[var(--radius)] text-[13px] text-foreground focus:outline-none focus:border-primary/50 focus:ring-2 focus:ring-primary/20 transition-all placeholder:text-muted-foreground/20 hover:border-border/60"
                placeholder="analyst@firm.com"
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-[11.5px] font-mono uppercase tracking-[0.12em] text-muted-foreground/40 pl-0.5">Password</label>
            <div className="relative group">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground/25 group-focus-within:text-primary/70 transition-colors" />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full pl-9 pr-4 py-3 bg-card border border-border/40 rounded-[var(--radius)] text-[13px] text-foreground focus:outline-none focus:border-primary/50 focus:ring-2 focus:ring-primary/20 transition-all placeholder:text-muted-foreground/20 hover:border-border/60"
                placeholder="Min. 8 characters"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full mt-2 py-3 px-4 bg-foreground text-background rounded-[var(--radius)] font-semibold text-[13px] uppercase tracking-[0.08em] transition-all hover:opacity-85 active:opacity-75 flex items-center justify-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed group active:scale-[0.99]"
          >
            {loading ? (
              <>
                <div className="w-4 h-4 border-2 border-background/30 border-t-background rounded-full animate-spin" />
                <span>Creating account...</span>
              </>
            ) : (
              <>
                Request Access
                <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
              </>
            )}
          </button>
        </form>

        <div className="mt-8 pt-6 border-t border-border/15 text-center text-[12.5px] text-muted-foreground/35 tracking-wide">
          Already have credentials?{' '}
          <Link href="/login" className="text-muted-foreground/60 hover:text-foreground font-semibold transition-colors underline underline-offset-2 decoration-border/40">
            Sign in here
          </Link>
        </div>
      </div>
    </div>
  );
}
