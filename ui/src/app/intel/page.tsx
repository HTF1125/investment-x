'use client';

import AppShell from '@/components/AppShell';
import NewsFeed from '@/components/NewsFeed';
import YouTubeIntelFeed from '@/components/YouTubeIntelFeed';
import { useAuth } from '@/context/AuthContext';
import { useTheme } from '@/context/ThemeContext';
import { apiFetch, apiFetchJson } from '@/lib/api';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Radio, RefreshCw, Check, AlertTriangle, Activity, BellRing, ScanLine, LayoutGrid } from 'lucide-react';
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
  const isAdmin = !!user && (user.role === 'owner' || user.role === 'admin' || user.is_admin);
  const { theme } = useTheme();
  const isLight = theme === 'light';
  const queryClient = useQueryClient();
  const [syncing, setSyncing] = useState(false);
  const [syncingYoutube, setSyncingYoutube] = useState(false);
  const [syncMsg, setSyncMsg] = useState('');
  const [toast, setToast] = useState<{ msg: string; type: 'success' | 'error'; sticky?: boolean } | null>(null);
  const lastTelegramProcessIdRef = useRef<string | null>(null);
  const lastYoutubeProcessIdRef = useRef<string | null>(null);
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
    enabled: isAdmin,
  });

  const latestTelegram = allProcesses.find((p) => p.name.startsWith('Telegram Sync'));
  const latestYoutube = allProcesses.find((p) => p.name.startsWith('YouTube Sync'));

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
        queryClient.invalidateQueries({ queryKey: ['news-feed'] });
        queryClient.invalidateQueries({ queryKey: ['youtube-intel'] });
      } else if (latestTelegram.status === 'failed') {
        flash(latestTelegram.message || 'Channel sync failed', 'error', { sticky: true });
      }
    }
    lastTelegramProcessIdRef.current = latestTelegram.id;
  }, [latestTelegram, flash, queryClient]);

  useEffect(() => {
    if (!latestYoutube) return;
    setSyncingYoutube(latestYoutube.status === 'running');

    if (
      latestYoutube.id !== lastYoutubeProcessIdRef.current &&
      latestYoutube.status !== 'running'
    ) {
      if (latestYoutube.status === 'completed') {
        flash('YouTube sync completed!', 'success', { sticky: true });
        queryClient.invalidateQueries({ queryKey: ['youtube-intel'] });
        queryClient.invalidateQueries({ queryKey: ['news-feed'] });
      } else if (latestYoutube.status === 'failed') {
        flash(latestYoutube.message || 'YouTube sync failed', 'error', { sticky: true });
      }
    }
    lastYoutubeProcessIdRef.current = latestYoutube.id;
  }, [latestYoutube, flash, queryClient]);

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

  const handleYouTubeSync = async () => {
    if (syncingYoutube) return;
    setSyncingYoutube(true);
    try {
      const res = await apiFetch('/api/task/youtube', { method: 'POST' });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(body.detail || 'YouTube sync failed');
      queryClient.invalidateQueries({ queryKey: ['task-processes'] });
      flash('YouTube sync started.', 'success');
    } catch (err: any) {
      flash(err.message || 'YouTube sync failed', 'error');
      setSyncingYoutube(false);
    } finally {
      // Keep running state controlled by task polling effect.
    }
  };

  return (
    <AppShell>
      <div className="relative overflow-hidden">
        <div className={`absolute inset-0 pointer-events-none ${
          isLight
            ? 'bg-[radial-gradient(circle_at_20%_0%,rgba(14,165,233,0.07),transparent_38%),radial-gradient(circle_at_80%_0%,rgba(16,185,129,0.05),transparent_34%)]'
            : 'bg-[radial-gradient(circle_at_20%_0%,rgba(14,165,233,0.14),transparent_38%),radial-gradient(circle_at_80%_0%,rgba(16,185,129,0.08),transparent_34%)]'
        }`} />

        <div className="relative p-4 md:p-8 lg:p-10 max-w-[1680px] mx-auto space-y-6">
          <section className="rounded-3xl border border-border/60 bg-card/[0.28] backdrop-blur-xl p-5 md:p-7 overflow-hidden">
            <div className="flex flex-col xl:flex-row xl:items-end xl:justify-between gap-5">
              <div className="space-y-3">
                <div className="inline-flex items-center gap-2 rounded-full border border-primary/35 bg-primary/10 px-3 py-1 text-[10px] font-mono tracking-[0.18em] uppercase text-primary">
                  <ScanLine className="w-3.5 h-3.5" />
                  Multi-Source Signal Desk
                </div>
                <div className="flex items-start gap-3">
                  <div className="w-10 h-10 md:w-11 md:h-11 rounded-xl bg-primary/15 border border-primary/30 flex items-center justify-center mt-0.5">
                    <Radio className="w-4.5 h-4.5 text-primary" />
                  </div>
                  <div>
                    <h1 className="text-2xl md:text-3xl font-semibold tracking-tight">Intel Feed</h1>
                    <p className="text-[12px] md:text-[13px] text-muted-foreground font-mono tracking-wider uppercase mt-1">
                      YouTube + Telegram Channel Aggregator
                    </p>
                  </div>
                </div>
                <p className="text-sm text-foreground/70 max-w-3xl leading-relaxed">
                  Central stream for macro, market, and thematic intelligence. Unsummarized and new videos are prioritized,
                  and Telegram items are rolled from the latest 24 hours.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 w-full xl:w-auto xl:min-w-[340px]">
                <div className={`rounded-xl border px-3 py-2.5 ${
                  syncing
                    ? 'border-sky-500/40 bg-sky-500/10'
                    : 'border-emerald-500/40 bg-emerald-500/10'
                }`}>
                  <div className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">Sync Status</div>
                  <div className="mt-1 flex items-center gap-1.5 text-xs font-semibold">
                    <Activity className={`w-3.5 h-3.5 ${syncing ? 'animate-pulse text-primary' : 'text-emerald-500 dark:text-emerald-300'}`} />
                    <span className={syncing ? 'text-primary' : 'text-emerald-600 dark:text-emerald-200'}>{syncing ? 'Live Sync' : 'Idle'}</span>
                  </div>
                </div>
                <div className="rounded-xl border border-border/60 bg-background/40 px-3 py-2.5">
                  <div className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">Progress</div>
                  <div className="mt-1 text-xs font-semibold text-foreground/85">
                    {latestTelegram?.progress || 'n/a'}
                  </div>
                </div>
                <div className="rounded-xl border border-border/60 bg-background/40 px-3 py-2.5">
                  <div className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">Pipeline</div>
                  <div className="mt-1 flex items-center gap-1.5 text-xs font-semibold text-foreground/85">
                    <LayoutGrid className="w-3.5 h-3.5 text-primary" />
                    Video + Text
                  </div>
                </div>
              </div>
            </div>

            <div className="mt-5 pt-4 border-t border-border/40 flex flex-col md:flex-row md:items-center md:justify-between gap-3">
              <div className="text-[11px] font-mono text-muted-foreground inline-flex items-center gap-2">
                <BellRing className="w-3.5 h-3.5 text-primary" />
                {syncing ? (syncMsg || 'Background sync running...') : 'System standing by for next sync event.'}
              </div>
              {isAdmin && (
                <div className="flex flex-col sm:flex-row sm:items-center gap-2 w-full sm:w-auto">
                  <button
                    onClick={handleScrape}
                    disabled={syncing}
                    className="inline-flex items-center justify-center gap-2 px-4 h-10 rounded-xl border border-sky-500/45 bg-sky-500/15 text-sky-200 hover:bg-sky-500/25 transition-colors disabled:opacity-50 text-sm font-semibold w-full sm:w-auto"
                  >
                    <RefreshCw className={`w-4 h-4 ${syncing ? 'animate-spin' : ''}`} />
                    {syncing ? 'Syncing Telegram...' : 'Sync Telegram'}
                  </button>
                  <button
                    onClick={handleYouTubeSync}
                    disabled={syncingYoutube}
                    className="inline-flex items-center justify-center gap-2 px-4 h-10 rounded-xl border border-primary/45 bg-primary/15 text-primary hover:bg-primary/25 transition-colors disabled:opacity-50 text-sm font-semibold w-full sm:w-auto"
                  >
                    <RefreshCw className={`w-4 h-4 ${syncingYoutube ? 'animate-spin' : ''}`} />
                    {syncingYoutube ? 'Syncing YouTube...' : 'Sync YouTube'}
                  </button>
                </div>
              )}
            </div>
          </section>

          <section className="grid grid-cols-1 gap-6">
            <YouTubeIntelFeed />
            <NewsFeed />
          </section>
        </div>
      </div>

        {/* Animated Toast */}
        <AnimatePresence>
          {toast && (
            <motion.div
              initial={{ opacity: 0, y: 20, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 10, scale: 0.95 }}
              transition={{ duration: 0.2 }}
              className={`fixed bottom-4 left-4 right-4 sm:left-auto sm:right-6 sm:bottom-6 z-[60] flex items-start sm:items-center gap-3 px-4 sm:px-5 py-3 rounded-2xl shadow-2xl backdrop-blur-md border ${
                toast.type === 'success'
                  ? 'bg-emerald-500/15 border-emerald-500/20 text-emerald-300'
                  : 'bg-rose-500/15 border-rose-500/20 text-rose-300'
              }`}
            >
              {toast.type === 'success' ? <Check className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
              <div className="flex items-start sm:items-center gap-2 sm:gap-3 min-w-0">
                <span className="text-sm font-medium break-words">{toast.msg}</span>
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
