'use client';

import AppShell from '@/components/AppShell';
import NavigatorShell from '@/components/NavigatorShell';
import NewsFeed from '@/components/NewsFeed';
import YouTubeIntelFeed from '@/components/YouTubeIntelFeed';
import TelegramFeed from '@/components/TelegramFeed';
import { useAuth } from '@/context/AuthContext';
import { apiFetch, apiFetchJson } from '@/lib/api';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Radio, RefreshCw, Check, AlertTriangle, Youtube, MessageSquare } from 'lucide-react';
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
  const [sidebarOpen, setSidebarOpen] = useState(true);
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const syncSidebarForViewport = () => {
      if (window.innerWidth < 1024) setSidebarOpen(false);
    };

    syncSidebarForViewport();
    window.addEventListener('resize', syncSidebarForViewport);
    return () => window.removeEventListener('resize', syncSidebarForViewport);
  }, []);
  const queryClient = useQueryClient();
  const [syncing, setSyncing] = useState(false);
  const [syncingYoutube, setSyncingYoutube] = useState(false);
  const [intelTab, setIntelTab] = useState<'youtube' | 'telegram'>('youtube');
  const [syncMsg, setSyncMsg] = useState('');
  const [toast, setToast] = useState<{ msg: string; type: 'success' | 'error'; sticky?: boolean } | null>(null);
  const youtubeRef = useRef<HTMLDivElement>(null);
  const newsRef = useRef<HTMLDivElement>(null);
  const telegramRef = useRef<HTMLDivElement>(null);
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

  const sidebarContent = (
    <div className="min-h-0 flex-1 overflow-y-auto py-1 custom-scrollbar">
      <button
        onClick={() => youtubeRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })}
        className="w-full text-left px-2.5 py-1.5 transition-colors border-l-2 border-l-transparent hover:bg-foreground/5 text-muted-foreground hover:text-foreground"
      >
        <div className="font-medium text-[12px] truncate leading-tight">YouTube Intel</div>
      </button>
      <button
        onClick={() => newsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })}
        className="w-full text-left px-2.5 py-1.5 transition-colors border-l-2 border-l-transparent hover:bg-foreground/5 text-muted-foreground hover:text-foreground"
      >
        <div className="font-medium text-[12px] truncate leading-tight">Recent News</div>
      </button>
      <button
        onClick={() => telegramRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })}
        className="w-full text-left px-2.5 py-1.5 transition-colors border-l-2 border-l-transparent hover:bg-foreground/5 text-muted-foreground hover:text-foreground"
      >
        <div className="font-medium text-[12px] truncate leading-tight">Telegram</div>
      </button>
    </div>
  );

  return (
    <AppShell hideFooter>
      <NavigatorShell
        sidebarOpen={sidebarOpen}
        onSidebarToggle={() => setSidebarOpen((o) => !o)}
        sidebarIcon={<Radio className="w-3.5 h-3.5 text-sky-400" />}
        sidebarLabel="Intel"
        sidebarContent={sidebarContent}
        topBarLeft={
          <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
            <span className="text-sm font-semibold text-foreground">Intel Feed</span>
            <span className="text-muted-foreground/30 hidden lg:inline">·</span>
            <span className="hidden lg:inline">YouTube + News + Telegram</span>
            <span className={`w-1.5 h-1.5 rounded-full ${syncing ? 'bg-sky-400 animate-pulse' : 'bg-emerald-500'}`} />
            <span>{syncing ? (syncMsg || 'Syncing…') : 'Live'}</span>
          </div>
        }
        topBarRight={
          <>
            {isAdmin && (
              <>
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
          </>
        }
        mainClassName="overflow-hidden"
      >
        <div className="h-full p-3 md:p-4 overflow-hidden">
          <div className="h-full min-h-0 grid grid-cols-1 lg:grid-cols-[1.7fr_1fr] gap-3">
            <div ref={newsRef} className="min-h-0 h-full">
              <NewsFeed />
            </div>
            <div className="min-h-0 h-full border border-border/60 rounded-xl bg-background overflow-hidden flex flex-col">
              <div className="h-10 border-b border-border/60 px-2.5 flex items-center gap-1.5 shrink-0">
                <button
                  onClick={() => setIntelTab('youtube')}
                  className={`h-7 px-2 rounded-md text-[11px] inline-flex items-center gap-1.5 border transition-colors ${
                    intelTab === 'youtube'
                      ? 'border-border bg-foreground/[0.06] text-foreground'
                      : 'border-transparent text-muted-foreground hover:text-foreground hover:bg-foreground/[0.04]'
                  }`}
                >
                  <Youtube className="w-3.5 h-3.5" />
                  YouTube
                </button>
                <button
                  onClick={() => setIntelTab('telegram')}
                  className={`h-7 px-2 rounded-md text-[11px] inline-flex items-center gap-1.5 border transition-colors ${
                    intelTab === 'telegram'
                      ? 'border-border bg-foreground/[0.06] text-foreground'
                      : 'border-transparent text-muted-foreground hover:text-foreground hover:bg-foreground/[0.04]'
                  }`}
                >
                  <MessageSquare className="w-3.5 h-3.5" />
                  Telegram
                </button>
              </div>
              <div className="min-h-0 flex-1 p-2">
                {intelTab === 'youtube' ? (
                  <div ref={youtubeRef} className="min-h-0 h-full">
                    <YouTubeIntelFeed />
                  </div>
                ) : (
                  <div ref={telegramRef} className="min-h-0 h-full">
                    <TelegramFeed />
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </NavigatorShell>

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

