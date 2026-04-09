'use client';

import { useState, useCallback, type FormEvent } from 'react';
import { useAuth } from '@/context/AuthContext';
import { Loader2, LogIn, X } from 'lucide-react';

export default function SessionExpiredModal() {
  const { isSessionExpired, dismissSessionExpired, reauth, logout, user } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = useCallback(async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      await reauth(email || user?.email || '', password);
      setPassword('');
      setEmail('');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setSubmitting(false);
    }
  }, [email, password, reauth, user?.email]);

  const handleLogout = useCallback(() => {
    dismissSessionExpired();
    logout();
  }, [dismissSessionExpired, logout]);

  if (!isSessionExpired) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="w-full max-w-sm mx-4 rounded-xl border border-border/50 bg-background shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-5 pt-5 pb-3">
          <div className="flex items-center gap-2">
            <LogIn className="w-4 h-4 text-primary" />
            <h2 className="text-sm font-semibold text-foreground">Session Expired</h2>
          </div>
          <button
            onClick={handleLogout}
            className="w-7 h-7 flex items-center justify-center rounded-[var(--radius)] text-muted-foreground hover:text-primary hover:bg-primary/10 transition-colors"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>

        <p className="px-5 text-[13px] text-muted-foreground">
          Your session has expired. Sign in again to continue without losing your work.
        </p>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-5 space-y-3">
          <div className="space-y-1">
            <label className="text-[11.5px] font-bold uppercase tracking-widest text-muted-foreground/50">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder={user?.email || 'email@example.com'}
              className="w-full border border-border/50 rounded-[var(--radius)] px-3 py-2 text-[13px] focus:outline-none focus:border-primary/40 focus:ring-2 focus:ring-primary/15 text-foreground bg-background transition-all placeholder:text-muted-foreground/40"
              autoFocus
            />
          </div>
          <div className="space-y-1">
            <label className="text-[11.5px] font-bold uppercase tracking-widest text-muted-foreground/50">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter password"
              className="w-full border border-border/50 rounded-[var(--radius)] px-3 py-2 text-[13px] focus:outline-none focus:border-primary/40 focus:ring-2 focus:ring-primary/15 text-foreground bg-background transition-all placeholder:text-muted-foreground/40"
              required
            />
          </div>

          {error && (
            <p role="alert" className="text-[12.5px] text-destructive font-medium">{error}</p>
          )}

          <div className="flex items-center gap-2 pt-1">
            <button
              type="submit"
              disabled={submitting || !password}
              className="flex-1 h-9 rounded-[var(--radius)] bg-primary text-primary-foreground text-[13px] font-medium hover:opacity-90 disabled:opacity-40 transition-all flex items-center justify-center gap-2"
            >
              {submitting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : null}
              Sign In
            </button>
            <button
              type="button"
              onClick={handleLogout}
              className="h-9 px-4 rounded-[var(--radius)] border border-border/40 text-[13px] text-muted-foreground hover:text-foreground hover:bg-primary/[0.04] transition-colors"
            >
              Logout
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
