'use client';

import AuthGuard from '@/components/AuthGuard';
import AppShell from '@/components/AppShell';
import NewsFeed from '@/components/NewsFeed';
import { useAuth } from '@/context/AuthContext';
import { Radio, RefreshCw, Check, AlertTriangle } from 'lucide-react';
import { useState } from 'react';

export default function IntelPage() {
  const { user, token } = useAuth();
  const [syncing, setSyncing] = useState(false);
  const [toast, setToast] = useState<{ msg: string; type: 'success' | 'error' } | null>(null);

  const flash = (msg: string, type: 'success' | 'error') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 4000);
  };

  const handleScrape = async () => {
    setSyncing(true);
    try {
      const res = await fetch('/api/task/telegram', {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Scrape failed');
      }
      flash('Telegram scrape triggered — data will refresh shortly.', 'success');
    } catch (err: any) {
      flash(err.message, 'error');
    } finally {
      setSyncing(false);
    }
  };

  return (
    <AppShell>
        <div className="p-4 md:p-8 lg:p-12 max-w-[1600px] mx-auto">

          {/* Header */}
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 mb-8">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-sky-600 flex items-center justify-center shadow-lg shadow-cyan-500/20">
                <Radio className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-white tracking-tight">Intelligence Feed</h1>
                <p className="text-xs text-slate-500 font-mono tracking-wider uppercase">Telegram Channel Aggregator • Real-time</p>
              </div>
            </div>

            {/* Admin-only scrape button */}
            {user?.is_admin && (
              <button
                onClick={handleScrape}
                disabled={syncing}
                className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-sky-500 to-indigo-500 hover:from-sky-400 hover:to-indigo-400 text-white rounded-xl text-sm font-semibold transition-all shadow-lg shadow-sky-500/20 hover:shadow-sky-500/30 disabled:opacity-50"
              >
                <RefreshCw className={`w-4 h-4 ${syncing ? 'animate-spin' : ''}`} />
                {syncing ? 'Syncing...' : 'Update Channels'}
              </button>
            )}
          </div>

          {/* Feed */}
          <NewsFeed />

        </div>

        {/* Toast */}
        {toast && (
          <div className={`fixed bottom-6 right-6 z-[60] flex items-center gap-3 px-5 py-3 rounded-2xl shadow-2xl backdrop-blur-md border transition-all ${
            toast.type === 'success'
              ? 'bg-emerald-500/15 border-emerald-500/20 text-emerald-300'
              : 'bg-rose-500/15 border-rose-500/20 text-rose-300'
          }`}>
            {toast.type === 'success' ? <Check className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
            <span className="text-sm font-medium">{toast.msg}</span>
          </div>
        )}
      </AppShell>
  );
}
