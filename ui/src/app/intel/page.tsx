'use client';

import AppShell from '@/components/AppShell';
import NewsFeed from '@/components/NewsFeed';
import YouTubeIntelFeed from '@/components/YouTubeIntelFeed';
import { useAuth } from '@/context/AuthContext';
import { useTheme } from '@/context/ThemeContext';
import { apiFetch, apiFetchJson } from '@/lib/api';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Radio, RefreshCw, Check, AlertTriangle } from 'lucide-react';
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
      <div className="flex h-[calc(100vh-40px)] relative bg-background overflow-hidden">
        <main className="flex-1 min-w-0 h-full flex flex-col bg-background">
          {/* Inner header bar */}
          <div className="h-11 flex items-center justify-between px-4 border-b border-border/60 shrink-0">
            <div className="flex items-center gap-2.5">
              <Radio className="w-3.5 h-3.5 text-muted-foreground/50 shrink-0" />
              <span className="text-sm font-semibold text-foreground">Intel Feed</span>
              <span className="text-muted-foreground/30 text-[11px]">·</span>
              <span className="text-[11px] text-muted-foreground/60">YouTube + Telegram</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
                <span className={`w-1.5 h-1.5 rounded-full ${syncing ? 'bg-sky-400 animate-pulse' : 'bg-emerald-500'}`} />
                <span>{syncing ? (syncMsg || 'Syncing…') : 'Live'}</span>
              </div>
              {isAdmin && (
                <>
                  <div className="w-px h-4 bg-border/60 mx-1" />
                  <button
                    onClick={handleScrape}
                    disabled={syncing}
                    className="p-1.5 rounded-md text-muted-foreground/40 hover:text-muted-foreground hover:bg-foreground/[0.06] transition-colors disabled:opacity-40"
                    title="Sync Telegram"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${syncing ? 'animate-spin' : ''}`} />
                  </button>
                  <button
                    onClick={handleYouTubeSync}
                    disabled={syncingYoutube}
                    className="p-1.5 rounded-md text-muted-foreground/40 hover:text-muted-foreground hover:bg-foreground/[0.06] transition-colors disabled:opacity-40"
                    title="Sync YouTube"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${syncingYoutube ? 'animate-spin' : ''}`} />
                  </button>
                </>
              )}
            </div>
          </div>

          {/* Scrollable feed content */}
          <div className="flex-1 overflow-y-auto custom-scrollbar">
            <div className="p-4 md:p-6 space-y-4">
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
            className={`fixed bottom-6 right-6 z-[60] flex items-center gap-3 px-4 py-2.5 rounded-xl shadow-xl border border-border/60 bg-background ${
              toast.type === 'success' ? 'text-emerald-500' : 'text-rose-400'
            }`}
          >
            {toast.type === 'success' ? <Check className="w-3.5 h-3.5 shrink-0" /> : <AlertTriangle className="w-3.5 h-3.5 shrink-0" />}
            <span className="text-[13px] font-medium text-foreground">{toast.msg}</span>
            {toast.sticky && (
              <button
                onClick={() => setToast(null)}
                className="ml-1 px-2 py-0.5 rounded-md border border-border/60 text-[10px] text-muted-foreground hover:text-foreground hover:bg-foreground/[0.06] transition-colors"
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
