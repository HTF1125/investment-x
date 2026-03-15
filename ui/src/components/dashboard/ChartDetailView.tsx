'use client';

import React, { useState, useCallback, useEffect, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { apiFetchJson } from '@/lib/api';
import {
  ArrowLeft, Pencil, RefreshCw, Copy,
  Trash2, Loader2, ChevronLeft, ChevronRight,
} from 'lucide-react';
import { motion } from 'framer-motion';
import dynamic from 'next/dynamic';
import Chart from '../Chart';
import { useDashboardActions } from '@/hooks/useDashboardActions';
import { useDashboardPermissions } from '@/hooks/useDashboardPermissions';

const CustomChartEditor = dynamic(() => import('../CustomChartEditor'), {
  ssr: false,
  loading: () => (
    <div className="flex-1 flex items-center justify-center">
      <Loader2 className="w-5 h-5 text-muted-foreground animate-spin" />
    </div>
  ),
});

interface ChartDetail {
  id: string;
  name: string;
  category?: string;
  public?: boolean;
  figure?: any;
  code?: string;
  chart_style?: string | null;
  created_by?: string;
  created_by_name?: string;
  created_by_email?: string;
  updated_at?: string;
}

export default function ChartDetailView({ chartId }: { chartId: string }) {
  const router = useRouter();
  const perms = useDashboardPermissions();
  const [editing, setEditing] = useState(false);
  const [copied, setCopied] = useState(false);
  const [copySignal, setCopySignal] = useState(0);

  // Fetch current chart
  const { data: chart, isLoading, error } = useQuery<ChartDetail>({
    queryKey: ['chart-detail', chartId],
    queryFn: () => apiFetchJson(`/api/custom/${chartId}`),
  });

  // Fetch dashboard summary for prev/next navigation
  const { data: summary } = useQuery({
    queryKey: ['dashboard-summary'],
    queryFn: () => apiFetchJson('/api/v1/dashboard/summary?include_figures=false'),
    staleTime: 1000 * 60 * 5,
  });

  // Build flat ordered chart list matching dashboard display order
  const chartList = useMemo(() => {
    const cats = (summary as any)?.charts_by_category as Record<string, any[]> | undefined;
    if (!cats) return [];
    const uniqueMap = new Map<string, any>();
    Object.values(cats).forEach(charts => {
      if (Array.isArray(charts)) {
        charts.forEach((c: any) => { if (c?.id) uniqueMap.set(String(c.id), c); });
      }
    });
    return Array.from(uniqueMap.values())
      .sort((a, b) => (a.rank ?? 0) - (b.rank ?? 0));
  }, [summary]);

  const chartIds = useMemo(() => chartList.map(c => String(c.id)), [chartList]);
  const currentIndex = chartIds.indexOf(chartId);
  const total = chartIds.length;
  const hasPrev = total > 1 && currentIndex > 0;
  const hasNext = total > 1 && currentIndex < total - 1;

  // Peek at next/prev chart names
  const prevChart = hasPrev ? chartList[currentIndex - 1] : null;
  const nextChart = hasNext ? chartList[currentIndex + 1] : null;

  const goPrev = useCallback(() => {
    if (!hasPrev) return;
    router.replace(`/?chartId=${chartIds[currentIndex - 1]}`, { scroll: false });
  }, [hasPrev, chartIds, currentIndex, router]);

  const goNext = useCallback(() => {
    if (!hasNext) return;
    router.replace(`/?chartId=${chartIds[currentIndex + 1]}`, { scroll: false });
  }, [hasNext, chartIds, currentIndex, router]);

  const actions = useDashboardActions({});

  const handleCopy = useCallback(() => {
    setCopySignal(s => s + 1);
    actions.copyChart(chartId);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }, [chartId, actions]);

  // Keyboard: Escape to go back, left/right to navigate
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      if (editing) return;
      switch (e.key) {
        case 'Escape':
          e.preventDefault();
          router.push('/');
          break;
        case 'ArrowLeft':
          e.preventDefault();
          goPrev();
          break;
        case 'ArrowRight':
          e.preventDefault();
          goNext();
          break;
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [router, editing, goPrev, goNext]);

  // Reset editing when chart changes
  useEffect(() => { setEditing(false); }, [chartId]);

  if (isLoading) {
    return (
      <div className="fixed inset-0 z-[60] bg-background flex items-center justify-center">
        <Loader2 className="w-5 h-5 text-muted-foreground animate-spin" />
      </div>
    );
  }

  if (error || !chart) {
    return (
      <div className="fixed inset-0 z-[60] bg-background flex flex-col items-center justify-center gap-3">
        <p className="text-[12px] text-muted-foreground/50">Chart not found</p>
        <button
          onClick={() => router.push('/')}
          className="text-[11px] text-primary hover:underline"
        >
          Back to dashboard
        </button>
      </div>
    );
  }

  const canEdit = perms.canEditChart(chart as any);
  const canRefresh = perms.canRefreshChart(chart as any);
  const canDelete = perms.canDeleteChart(chart as any);

  return (
    <motion.div
      className="fixed inset-0 z-[60] bg-background flex flex-col"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.15 }}
    >
      {/* ── Top bar ── */}
      <div className="h-12 shrink-0 border-b border-border/25 bg-background flex items-center gap-3 px-4 sm:px-6">
        <button
          onClick={() => router.push('/')}
          className="flex items-center gap-1.5 px-2 py-1 rounded-[var(--radius)] text-muted-foreground hover:text-foreground hover:bg-primary/[0.06] transition-colors shrink-0"
          title="Back to dashboard (Esc)"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span className="text-[11px] font-medium hidden sm:inline">Dashboard</span>
        </button>

        <div className="w-px h-4 bg-border/25 hidden sm:block" />

        <div className="flex items-center gap-2 flex-1 min-w-0">
          <h1 className="text-[13px] font-semibold text-foreground truncate">
            {chart.name || 'Untitled'}
          </h1>
          {chart.category && (
            <span className="text-[9px] font-mono text-muted-foreground/40 bg-primary/[0.04] border border-border/20 px-1.5 py-0.5 rounded-[calc(var(--radius)-2px)] shrink-0 hidden sm:inline-block">
              {chart.category}
            </span>
          )}
        </div>

        {/* Navigation */}
        {total > 1 && (
          <div className="flex items-center gap-1 shrink-0 mr-1">
            <button
              onClick={goPrev}
              disabled={!hasPrev}
              className="p-1 rounded-[var(--radius)] text-muted-foreground/40 hover:text-foreground hover:bg-primary/[0.06] transition-colors disabled:opacity-20 disabled:cursor-default"
              title={prevChart ? `Previous: ${prevChart.name}` : 'Previous'}
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="text-[10px] font-mono text-muted-foreground/35 tabular-nums min-w-[3.5ch] text-center">
              {currentIndex + 1}/{total}
            </span>
            <button
              onClick={goNext}
              disabled={!hasNext}
              className="p-1 rounded-[var(--radius)] text-muted-foreground/40 hover:text-foreground hover:bg-primary/[0.06] transition-colors disabled:opacity-20 disabled:cursor-default"
              title={nextChart ? `Next: ${nextChart.name}` : 'Next'}
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        )}

        <div className="w-px h-4 bg-border/25" />

        {/* Actions */}
        <div className="flex items-center gap-0.5 shrink-0">
          <button
            onClick={handleCopy}
            className="p-1.5 rounded-[var(--radius)] text-muted-foreground/40 hover:text-foreground hover:bg-primary/[0.06] transition-colors"
            title="Copy as PNG"
          >
            <Copy className={`w-3.5 h-3.5 ${copied ? 'text-success' : ''}`} />
          </button>
          {canRefresh && (
            <button
              onClick={() => actions.refreshChart(chartId)}
              disabled={!!actions.refreshingChartIds[chartId]}
              className="p-1.5 rounded-[var(--radius)] text-muted-foreground/40 hover:text-foreground hover:bg-primary/[0.06] transition-colors disabled:opacity-40"
              title="Refresh data"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${actions.refreshingChartIds[chartId] ? 'animate-spin' : ''}`} />
            </button>
          )}
          {canEdit && (
            <button
              onClick={() => setEditing(prev => !prev)}
              className={`flex items-center gap-1.5 ml-1 px-2.5 py-1 rounded-[var(--radius)] border text-[10px] font-semibold transition-all ${
                editing
                  ? 'border-primary/40 text-primary bg-primary/10'
                  : 'border-border/30 text-muted-foreground/60 hover:text-foreground hover:border-border/60 hover:bg-primary/[0.04]'
              }`}
              title={editing ? 'Close editor' : 'Edit chart code'}
            >
              <Pencil className="w-3 h-3" />
              <span className="hidden sm:inline">{editing ? 'Close' : 'Edit'}</span>
            </button>
          )}
          {canDelete && (
            <button
              onClick={() => {
                if (confirm(`Delete "${chart.name}"? This cannot be undone.`)) {
                  actions.setDeleteTarget({ id: chartId, name: chart.name || chartId });
                  actions.confirmDelete();
                  router.push('/');
                }
              }}
              className="p-1.5 rounded-[var(--radius)] text-muted-foreground/20 hover:text-destructive hover:bg-destructive/[0.06] transition-colors"
              title="Delete chart"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* ── Content ── */}
      <div className={`flex-1 min-h-0 flex overflow-hidden ${editing ? 'flex-col sm:flex-row' : ''}`}>
        {editing && (
          <div className="w-full sm:w-[60%] sm:min-w-[400px] sm:max-w-[1000px] shrink-0 border-r border-border/30 flex flex-col overflow-hidden">
            <CustomChartEditor
              mode="integrated"
              initialChartId={chart.id}
              onClose={() => setEditing(false)}
            />
          </div>
        )}

        <div className="flex-1 min-w-0 flex items-center justify-center p-4 sm:p-8">
          <motion.div
            key={chart.id}
            className="w-full max-w-[840px] max-h-[480px] h-full overflow-hidden bg-card rounded-[var(--radius)] border border-border/25 shadow-sm"
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.2, ease: 'easeOut' }}
          >
            <Chart
              key={chart.id}
              id={chart.id}
              initialFigure={chart.figure}
              copySignal={copySignal}
              interactive={true}
              scrollZoom={true}
            />
          </motion.div>
        </div>
      </div>

      {/* ── Bottom bar ── */}
      <div className="h-8 px-4 sm:px-6 flex items-center justify-between border-t border-border/20 shrink-0">
        <div className="flex items-center gap-3 text-[10px] font-mono text-muted-foreground/30">
          {(chart.created_by_name || chart.created_by_email) && (
            <span>{chart.created_by_name || chart.created_by_email}</span>
          )}
          {chart.updated_at && (
            <span>{new Date(chart.updated_at).toLocaleDateString()}</span>
          )}
        </div>
        <div className="text-[9px] font-mono text-muted-foreground/20 hidden sm:flex items-center gap-3">
          <span><kbd className="px-1 py-0.5 rounded border border-border/20 text-[8px]">←→</kbd> navigate</span>
          <span><kbd className="px-1 py-0.5 rounded border border-border/20 text-[8px]">Esc</kbd> back</span>
        </div>
      </div>
    </motion.div>
  );
}
