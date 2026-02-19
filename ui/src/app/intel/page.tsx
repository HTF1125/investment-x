'use client';

import AppShell from '@/components/AppShell';
import NewsFeed from '@/components/NewsFeed';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/api';
import { useQueryClient } from '@tanstack/react-query';
import { Radio, RefreshCw, Check, AlertTriangle, FileText } from 'lucide-react';
import { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Link from 'next/link';

export default function IntelPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [syncing, setSyncing] = useState(false);
  const [syncMsg, setSyncMsg] = useState('');
  const [toast, setToast] = useState<{ msg: string; type: 'success' | 'error' } | null>(null);

  const flash = useCallback((msg: string, type: 'success' | 'error') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 4000);
  }, []);

  const handleScrape = async () => {
    if (syncing) return;
    setSyncing(true);
    setSyncMsg('Starting sync...');
    
    try {
      const res = await apiFetch('/api/task/telegram', { method: 'POST' });
      
      if (!res.ok) {
        const err = await res.json();
        if (res.status !== 400 || err.detail !== "Telegram sync is already running") {
             throw new Error(err.detail || 'Scrape failed');
        }
      }
      
      // Poll for status — invalidate query on completion instead of full page reload
      const poll = setInterval(async () => {
         try {
             const sRes = await fetch('/api/task/status');
             if (!sRes.ok) return;
             const status = await sRes.json();
             
             if (status.telegram) {
                 if (status.telegram.running) {
                     setSyncMsg(status.telegram.message || 'Syncing...');
                 } else {
                     setSyncMsg(status.telegram.message || 'Idle');
                     if (status.telegram.message?.includes('Completed')) {
                         flash('Channel sync completed!', 'success');
                         queryClient.invalidateQueries({ queryKey: ['telegram-news'] });
                     } else if (status.telegram.message?.startsWith('Failed')) {
                         flash(status.telegram.message, 'error');
                     }
                     setSyncing(false);
                     clearInterval(poll);
                 }
             }
         } catch {
             // Polling error — silently handled by UI state
         }
      }, 2000);

    } catch (err: any) {
      flash(err.message, 'error');
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

            <div className="flex items-center gap-3">
              <Link 
                href="/intel/research"
                className="flex items-center gap-2 px-5 py-2.5 bg-white/5 hover:bg-white/10 text-white rounded-xl text-sm font-semibold transition-all border border-white/10 group"
              >
                <FileText className="w-4 h-4 text-cyan-400 group-hover:scale-110 transition-transform" />
                Research Library
              </Link>

              {/* Admin-only scrape button */}
              {user?.is_admin && (
                <button
                  onClick={handleScrape}
                  disabled={syncing}
                  className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-sky-500 to-indigo-500 hover:from-sky-400 hover:to-indigo-400 text-white rounded-xl text-sm font-semibold transition-all shadow-lg shadow-sky-500/20 hover:shadow-sky-500/30 disabled:opacity-50"
                >
                  <RefreshCw className={`w-4 h-4 ${syncing ? 'animate-spin' : ''}`} />
                  {syncing ? (syncMsg || 'Syncing...') : 'Update Channels'}
                </button>
              )}
            </div>
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
              <span className="text-sm font-medium">{toast.msg}</span>
            </motion.div>
          )}
        </AnimatePresence>
      </AppShell>
  );
}
