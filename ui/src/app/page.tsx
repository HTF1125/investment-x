'use client';

import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import dynamic from 'next/dynamic';
import AppShell from '@/components/layout/AppShell';
import Briefing from '@/components/intel/Briefing';
import { X } from 'lucide-react';
import { motion } from 'framer-motion';
import { useQueryClient } from '@tanstack/react-query';
import { apiFetchJson } from '@/lib/api';

const ChartGrid = dynamic(() => import('@/components/dashboard/ChartGrid'), {
  ssr: false,
  loading: () => (
    <div className="h-full flex items-center justify-center">
      <div className="w-3.5 h-3.5 border-2 border-border/50 border-t-foreground/60 rounded-full animate-spin" />
    </div>
  ),
});

export default function Home() {
  useEffect(() => { document.title = 'Dashboard | Investment-X'; }, []);

  const [briefingOpen, setBriefingOpen] = useState(false);
  const queryClient = useQueryClient();

  // Prefetch briefing data
  useEffect(() => {
    const prefetch = async () => {
      try {
        const dates = await queryClient.fetchQuery({
          queryKey: ['briefings'],
          queryFn: () => apiFetchJson<{ date: string }[]>('/api/briefings').catch(() => apiFetchJson<{ date: string }[]>('/api/news/reports')),
          staleTime: 120_000,
        });
        if (dates?.[0]?.date) {
          queryClient.prefetchQuery({
            queryKey: ['briefing', dates[0].date],
            queryFn: () => apiFetchJson(`/api/briefings/${dates[0].date}`).catch(() => apiFetchJson(`/api/news/reports/${dates[0].date}`)),
            staleTime: 300_000,
          });
        }
      } catch { /* silent */ }
    };
    prefetch();
  }, [queryClient]);

  // Close briefing on Escape
  useEffect(() => {
    if (!briefingOpen) return;
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') setBriefingOpen(false); };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [briefingOpen]);

  return (
    <AppShell hideFooter>
      <div className="page-shell">
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.4, delay: 0.1 }}
          className="flex-1 min-h-0 flex flex-col"
        >
          <ChartGrid onOpenBriefing={() => setBriefingOpen(true)} />
        </motion.div>
      </div>

      {briefingOpen && typeof document !== 'undefined' && createPortal(
        <div className="fixed inset-0 z-[9000] flex items-center justify-center">
          <div className="absolute inset-0 bg-background/60" onClick={() => setBriefingOpen(false)} />
          <div className="relative w-[95vw] max-w-2xl h-[85vh] rounded-[var(--radius)] border border-border/40 bg-card shadow-2xl flex flex-col overflow-hidden animate-fade-in">
            <div className="flex items-center justify-between px-4 py-2.5 border-b border-border/20 bg-foreground/[0.02] shrink-0">
              <span className="text-[12.5px] font-semibold uppercase tracking-[0.08em] text-foreground">Briefing</span>
              <button onClick={() => setBriefingOpen(false)} className="btn-icon text-muted-foreground/40 hover:text-foreground" title="Close (Esc)">
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
            <div className="flex-1 min-h-0 overflow-hidden">
              <Briefing />
            </div>
          </div>
        </div>,
        document.body,
      )}
    </AppShell>
  );
}
