'use client';

import AppShell from '@/components/AppShell';
import NewsFeed from '@/components/NewsFeed';
import { useAuth } from '@/context/AuthContext';
import { apiFetch, apiFetchJson } from '@/lib/api';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Radio, RefreshCw, Check, AlertTriangle, Activity } from 'lucide-react';
import { useState, useCallback, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface ProcessInfo {
  id: string;
  name: string;
  status: 'running' | 'completed' | 'failed';
  start_time: string;
  end_time?: string;
  message?: string;
  progress?: string;
}

export default function IntelPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [syncing, setSyncing] = useState(false);
  const [syncMsg, setSyncMsg] = useState('');
  const [toast, setToast] = useState<{ msg: string; type: 'success' | 'error'; sticky?: boolean } | null>(null);
  const lastTelegramProcessIdRef = useRef<string | null>(null);
  const toastTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (toastTimerRef.current) clearTimeout(toastTimerRef.current);
    };
  }, []);

  const flash = useCallback((
    msg: string,
    type: 'success' | 'error',
    opts?: { sticky?: boolean; durationMs?: number }
  ) => {
    if (toastTimerRef.current) {
      clearTimeout(toastTimerRef.current);
      toastTimerRef.current = null;
    }
    const sticky = !!opts?.sticky;
    setToast({ msg, type, sticky });
    if (!sticky) {
      toastTimerRef.current = setTimeout(() => setToast(null), opts?.durationMs ?? 4000);
    }
  }, []);

  const { data: allProcesses = [] } = useQuery({
    queryKey: ['task-processes'],
    queryFn: () => apiFetchJson<ProcessInfo[]>('/api/task/processes'),
    refetchInterval: (query) => {
      const data = (query.state.data as ProcessInfo[] | undefined) ?? [];
      const hasRunning = data.some((p) => p.status === 'running');
      return hasRunning ? 2500 : 15000;
    },
    refetchIntervalInBackground: false,
    staleTime: 3000,
    enabled: !!user?.is_admin,
  });

  const latestTelegram = allProcesses.find((p) => p.name.startsWith('Telegram Sync'));

  useEffect(() => {
    if (!latestTelegram) return;

    setSyncMsg(latestTelegram.message || (latestTelegram.status === 'running' ? 'Syncing...' : 'Idle'));
    setSyncing(latestTelegram.status === 'running');

    if (
      latestTelegram.id !== lastTelegramProcessIdRef.current &&
      latestTelegram.status !== 'running'
    ) {
      if (latestTelegram.status === 'completed') {
        flash('Channel sync completed!', 'success', { sticky: true });
        queryClient.invalidateQueries({ queryKey: ['telegram-news'] });
      } else if (latestTelegram.status === 'failed') {
        flash(latestTelegram.message || 'Channel sync failed', 'error', { sticky: true });
      }
    }
    lastTelegramProcessIdRef.current = latestTelegram.id;
  }, [latestTelegram, flash, queryClient]);

  const handleScrape = async () => {
    if (syncing) return;
    setSyncMsg('Starting sync...');
    
    try {
      const res = await apiFetch('/api/task/telegram', { method: 'POST' });
      
      if (!res.ok) {
        const err = await res.json();
        if (res.status !== 400 || err.detail !== "Telegram sync is already running") {
             throw new Error(err.detail || 'Scrape failed');
        }
      }
      queryClient.invalidateQueries({ queryKey: ['task-processes'] });
      setSyncing(true);

    } catch (err: any) {
      flash(err.message, 'error');
      setSyncing(false);
    }
  };

  return (
    <AppShell>
        <div className="p-4 md:p-8 lg:p-12 max-w-[1600px] mx-auto">

          {/* Header */}
          <div className="mb-6 rounded-2xl border border-border/60 bg-card/20 backdrop-blur-sm p-4 md:p-5">
            <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4">
              <div className="flex items-start gap-3">
                <div className="w-9 h-9 rounded-lg bg-sky-500/15 border border-sky-500/30 flex items-center justify-center">
                  <Radio className="w-4 h-4 text-sky-400" />
                </div>
                <div>
                  <h1 className="text-xl md:text-2xl font-semibold text-foreground tracking-tight">Intel Feed</h1>
                  <p className="text-[11px] text-muted-foreground font-mono tracking-wider uppercase">Telegram Channel Aggregator</p>
                </div>
              </div>

              <div className="flex items-center gap-2.5 text-[11px] font-mono">
                <div className={`inline-flex items-center gap-1.5 px-2.5 h-8 rounded-lg border ${
                  syncing
                    ? 'text-sky-300 border-sky-500/40 bg-sky-500/10'
                    : 'text-emerald-300 border-emerald-500/40 bg-emerald-500/10'
                }`}>
                  <Activity className={`w-3.5 h-3.5 ${syncing ? 'animate-pulse' : ''}`} />
                  <span>{syncing ? 'LIVE SYNC' : 'IDLE'}</span>
                </div>
                {latestTelegram?.progress && (
                  <div className="inline-flex items-center px-2.5 h-8 rounded-lg border border-border/60 bg-background/40 text-foreground/80">
                    {latestTelegram.progress}
                  </div>
                )}
              </div>
            </div>

            {/* Admin-only scrape button */}
            {user?.is_admin && (
              <div className="mt-4 pt-4 border-t border-border/40">
                <button
                  onClick={handleScrape}
                  disabled={syncing}
                  className="inline-flex items-center gap-2 px-4 h-9 bg-sky-500 hover:bg-sky-400 text-black rounded-lg text-sm font-semibold transition-all disabled:opacity-50"
                >
                  <RefreshCw className={`w-4 h-4 ${syncing ? 'animate-spin' : ''}`} />
                  {syncing ? (syncMsg || 'Syncing...') : 'Update Channels'}
                </button>
              </div>
            )}
          </div>

          <div className="mb-6 text-[11px] font-mono text-muted-foreground border border-border/40 rounded-xl px-3 py-2.5 bg-background/30">
            Live intelligence stream with task-aware sync state and rolling Telegram ingestion.
          </div>

          {/* Feed */}
          <NewsFeed />

        </div>

        {/* Animated Toast */}
        <AnimatePresence>
          {toast && (
            <motion.div
              initial={{ opacity: 0, y: 20, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 10, scale: 0.95 }}
              transition={{ duration: 0.2 }}
              className={`fixed bottom-6 right-6 z-[60] flex items-center gap-3 px-5 py-3 rounded-2xl shadow-2xl backdrop-blur-md border ${
                toast.type === 'success'
                  ? 'bg-emerald-500/15 border-emerald-500/20 text-emerald-300'
                  : 'bg-rose-500/15 border-rose-500/20 text-rose-300'
              }`}
            >
              {toast.type === 'success' ? <Check className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
              <div className="flex items-center gap-3">
                <span className="text-sm font-medium">{toast.msg}</span>
                {toast.sticky && (
                  <button
                    onClick={() => setToast(null)}
                    className="px-2 py-1 rounded-lg border border-current/30 text-[11px] font-semibold hover:bg-white/10 transition-colors"
                  >
                    OK
                  </button>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </AppShell>
  );
}
