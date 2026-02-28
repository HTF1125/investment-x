'use client';

import AppShell from '@/components/AppShell';
import NavigatorShell from '@/components/NavigatorShell';
import NewsFeed from '@/components/NewsFeed';
import YouTubeIntelFeed from '@/components/YouTubeIntelFeed';
import TelegramFeed from '@/components/TelegramFeed';
import { useAuth } from '@/context/AuthContext';
import { apiFetch, apiFetchJson } from '@/lib/api';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Radio, RefreshCw, Check, AlertTriangle, Youtube, MessageSquare, Newspaper } from 'lucide-react';
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

type IntelTab = 'news' | 'youtube' | 'telegram';

const TABS: { id: IntelTab; label: string; icon: React.ReactNode }[] = [
  { id: 'news', label: 'News', icon: <Newspaper className="w-3.5 h-3.5" /> },
  { id: 'youtube', label: 'YouTube', icon: <Youtube className="w-3.5 h-3.5" /> },
  { id: 'telegram', label: 'Telegram', icon: <MessageSquare className="w-3.5 h-3.5" /> },
];

export default function IntelPage() {
  const { user } = useAuth();
  const isAdmin = !!user && (user.role === 'owner' || user.role === 'admin' || user.is_admin);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [intelTab, setIntelTab] = useState<IntelTab>('news');

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const sync = () => { if (window.innerWidth < 1024) setSidebarOpen(false); };
    sync();
    window.addEventListener('resize', sync);
    return () => window.removeEventListener('resize', sync);
  }, []);

  const queryClient = useQueryClient();
  const [syncingNews, setSyncingNews] = useState(false);
  const [syncingYoutube, setSyncingYoutube] = useState(false);
  const [syncingTelegram, setSyncingTelegram] = useState(false);
  const [toast, setToast] = useState<{ msg: string; type: 'success' | 'error'; sticky?: boolean } | null>(null);

  const lastNewsIdRef = useRef<string | null>(null);
  const lastYoutubeIdRef = useRef<string | null>(null);
  const lastTelegramIdRef = useRef<string | null>(null);
  const toastTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => () => { if (toastTimerRef.current) clearTimeout(toastTimerRef.current); }, []);

  const flash = useCallback((msg: string, type: 'success' | 'error', opts?: { sticky?: boolean }) => {
    if (toastTimerRef.current) { clearTimeout(toastTimerRef.current); toastTimerRef.current = null; }
    setToast({ msg, type, sticky: !!opts?.sticky });
    if (!opts?.sticky) toastTimerRef.current = setTimeout(() => setToast(null), 4000);
  }, []);

  const { data: allProcesses = [] } = useQuery({
    queryKey: ['task-processes'],
    queryFn: () => apiFetchJson<ProcessInfo[]>('/api/task/processes'),
    refetchInterval: (query) => {
      const data = (query.state.data as ProcessInfo[] | undefined) ?? [];
      return data.some((p) => p.status === 'running') ? 2500 : 15000;
    },
    refetchIntervalInBackground: false,
    staleTime: 3000,
    enabled: isAdmin,
  });

  const latestNews = allProcesses.find((p) => p.name.startsWith('News Scraping'));
  const latestYoutube = allProcesses.find((p) => p.name.startsWith('YouTube Sync'));
  const latestTelegram = allProcesses.find((p) => p.name.startsWith('Telegram Sync'));

  useEffect(() => {
    if (!latestNews) return;
    setSyncingNews(latestNews.status === 'running');
    if (latestNews.id !== lastNewsIdRef.current && latestNews.status !== 'running') {
      if (latestNews.status === 'completed') {
        flash('News crawl completed!', 'success', { sticky: true });
        queryClient.invalidateQueries({ queryKey: ['news-feed'] });
      } else if (latestNews.status === 'failed') {
        flash(latestNews.message || 'News crawl failed', 'error', { sticky: true });
      }
    }
    lastNewsIdRef.current = latestNews.id;
  }, [latestNews, flash, queryClient]);

  useEffect(() => {
    if (!latestYoutube) return;
    setSyncingYoutube(latestYoutube.status === 'running');
    if (latestYoutube.id !== lastYoutubeIdRef.current && latestYoutube.status !== 'running') {
      if (latestYoutube.status === 'completed') {
        flash('YouTube sync completed!', 'success', { sticky: true });
        queryClient.invalidateQueries({ queryKey: ['youtube-intel'] });
      } else if (latestYoutube.status === 'failed') {
        flash(latestYoutube.message || 'YouTube sync failed', 'error', { sticky: true });
      }
    }
    lastYoutubeIdRef.current = latestYoutube.id;
  }, [latestYoutube, flash, queryClient]);

  useEffect(() => {
    if (!latestTelegram) return;
    setSyncingTelegram(latestTelegram.status === 'running');
    if (latestTelegram.id !== lastTelegramIdRef.current && latestTelegram.status !== 'running') {
      if (latestTelegram.status === 'completed') {
        flash('Telegram sync completed!', 'success', { sticky: true });
        queryClient.invalidateQueries({ queryKey: ['news-feed'] });
      } else if (latestTelegram.status === 'failed') {
        flash(latestTelegram.message || 'Telegram sync failed', 'error', { sticky: true });
      }
    }
    lastTelegramIdRef.current = latestTelegram.id;
  }, [latestTelegram, flash, queryClient]);

  const triggerSync = async (endpoint: string, setSyncing: (v: boolean) => void, label: string) => {
    setSyncing(true);
    try {
      const res = await apiFetch(endpoint, { method: 'POST' });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(body.detail || `${label} failed`);
      queryClient.invalidateQueries({ queryKey: ['task-processes'] });
    } catch (err: any) {
      flash(err.message || `${label} failed`, 'error');
      setSyncing(false);
    }
  };

  const handleActiveSync = () => {
    if (intelTab === 'news') triggerSync('/api/task/news', setSyncingNews, 'News crawl');
    else if (intelTab === 'youtube') triggerSync('/api/task/youtube', setSyncingYoutube, 'YouTube sync');
    else triggerSync('/api/task/telegram', setSyncingTelegram, 'Telegram sync');
  };

  const activeIsSyncing = intelTab === 'news' ? syncingNews : intelTab === 'youtube' ? syncingYoutube : syncingTelegram;
  const anySyncing = syncingNews || syncingYoutube || syncingTelegram;

  return (
    <AppShell hideFooter>
      <NavigatorShell
        sidebarOpen={sidebarOpen}
        onSidebarToggle={() => setSidebarOpen((o) => !o)}
        sidebarIcon={<Radio className="w-3.5 h-3.5 text-sky-400" />}
        sidebarLabel="Intel"
        sidebarContent={
          <div className="min-h-0 flex-1 overflow-y-auto py-1 custom-scrollbar">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setIntelTab(tab.id)}
                className={`w-full text-left px-2.5 py-1.5 transition-colors border-l-2 hover:bg-foreground/5 ${
                  intelTab === tab.id
                    ? 'border-l-sky-400 text-foreground'
                    : 'border-l-transparent text-muted-foreground hover:text-foreground'
                }`}
              >
                <div className="font-medium text-[12px] truncate leading-tight">{tab.label}</div>
              </button>
            ))}
          </div>
        }
        topBarLeft={
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-foreground">Intel Feed</span>
            <span className="text-muted-foreground/30">·</span>
            {TABS.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setIntelTab(tab.id)}
                className={`h-6 px-2 rounded-md text-[11px] inline-flex items-center gap-1.5 border transition-colors ${
                  intelTab === tab.id
                    ? 'border-border bg-foreground/[0.06] text-foreground'
                    : 'border-transparent text-muted-foreground hover:text-foreground hover:bg-foreground/[0.04]'
                }`}
              >
                {tab.icon}
                {tab.label}
              </button>
            ))}
          </div>
        }
        topBarRight={
          <div className="flex items-center gap-1.5">
            <span className={`w-1.5 h-1.5 rounded-full ${anySyncing ? 'bg-sky-400 animate-pulse' : 'bg-emerald-500'}`} />
            {isAdmin && (
              <button
                onClick={handleActiveSync}
                disabled={activeIsSyncing}
                title={`Sync ${TABS.find((t) => t.id === intelTab)?.label}`}
                className="p-1.5 rounded-md text-muted-foreground/40 hover:text-muted-foreground hover:bg-foreground/[0.06] transition-colors disabled:opacity-40"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${activeIsSyncing ? 'animate-spin' : ''}`} />
              </button>
            )}
          </div>
        }
        mainClassName="overflow-hidden"
      >
        <div className="h-full p-3 md:p-4 overflow-hidden max-w-screen-xl mx-auto w-full">
          <div className="h-full min-h-0 border border-border/60 rounded-xl bg-background overflow-hidden">
            <div className="min-h-0 h-full overflow-hidden">
              {intelTab === 'news' && <NewsFeed embedded />}
              {intelTab === 'youtube' && <YouTubeIntelFeed embedded />}
              {intelTab === 'telegram' && <TelegramFeed embedded />}
            </div>
          </div>
        </div>
      </NavigatorShell>

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
