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
    <AppShell hideFooter>
      <div className="flex h-[calc(100vh-48px)] relative bg-background overflow-hidden">
        {/* Main Content Area */}
        <main className="flex-1 min-w-0 h-full overflow-y-auto custom-scrollbar relative flex flex-col bg-background">
          <div className="p-4 md:p-6 lg:p-8 space-y-6">
            {/* Header Card */}
            <div className="glass-card p-4 md:p-5 border border-border/50">
              <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
                <div className="flex items-center gap-3 min-w-0">
                  <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400 shrink-0">
                    <Radio className="w-5 h-5" />
                  </div>
                  <div className="min-w-0">
                    <h1 className="text-lg font-bold text-foreground">Intel Feed</h1>
                    <p className="text-[10px] font-mono text-muted-foreground/60 uppercase tracking-wider">
                      YouTube + Telegram Aggregator
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <div className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border text-[10px] font-mono ${
                    syncing
                      ? 'border-sky-500/40 bg-sky-500/10 text-sky-400'
                      : 'border-emerald-500/40 bg-emerald-500/10 text-emerald-400'
                  }`}>
                    <Activity className={`w-3 h-3 ${syncing ? 'animate-pulse' : ''}`} />
                    <span className="font-bold">{syncing ? 'SYNCING' : 'IDLE'}</span>
                  </div>

                  {isAdmin && (
                    <>
                      <button
                        onClick={handleScrape}
                        disabled={syncing}
                        className="p-2 rounded-lg border border-sky-500/30 bg-sky-500/10 text-sky-400 hover:bg-sky-500/20 transition-all disabled:opacity-50"
                        title="Sync Telegram"
                      >
                        <RefreshCw className={`w-4 h-4 ${syncing ? 'animate-spin' : ''}`} />
                      </button>
                      <button
                        onClick={handleYouTubeSync}
                        disabled={syncingYoutube}
                        className="p-2 rounded-lg border border-primary/30 bg-primary/10 text-primary hover:bg-primary/20 transition-all disabled:opacity-50"
                        title="Sync YouTube"
                      >
                        <RefreshCw className={`w-4 h-4 ${syncingYoutube ? 'animate-spin' : ''}`} />
                      </button>
                    </>
                  )}
                </div>
              </div>

              {syncing && syncMsg && (
                <div className="mt-3 pt-3 border-t border-border/30 flex items-center gap-2 text-[10px] font-mono text-muted-foreground">
                  <BellRing className="w-3 h-3 text-primary" />
                  {syncMsg}
                </div>
              )}
            </div>

            {/* Feed Content */}
            <div className="space-y-6">
              <YouTubeIntelFeed />
              <NewsFeed />
            </div>
          </div>
        </main>
      </div>

      {/* Toast Notification */}
      <AnimatePresence>
        {toast && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 10, scale: 0.95 }}
            transition={{ duration: 0.2 }}
            className={`fixed bottom-6 right-6 z-[60] flex items-center gap-3 px-4 py-3 rounded-xl shadow-2xl backdrop-blur-md border ${
              toast.type === 'success'
                ? 'bg-emerald-500/15 border-emerald-500/20 text-emerald-300'
                : 'bg-rose-500/15 border-rose-500/20 text-rose-300'
            }`}
          >
            {toast.type === 'success' ? <Check className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
            <span className="text-sm font-medium">{toast.msg}</span>
            {toast.sticky && (
              <button
                onClick={() => setToast(null)}
                className="px-2 py-1 rounded-lg border border-current/30 text-[10px] font-bold hover:bg-white/10 transition-colors"
              >
                OK
              </button>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </AppShell>
  );
}
