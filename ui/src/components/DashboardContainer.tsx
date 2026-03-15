'use client';

import React, { useEffect } from 'react';
import { useSearchParams } from 'next/navigation';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { apiFetchJson } from '@/lib/api';
import Dashboard from '@/components/dashboard/Dashboard';
import ChartDetailView from '@/components/dashboard/ChartDetailView';
import ChartSkeletonGrid from '@/components/dashboard/ChartSkeletonGrid';
import AppShell from '@/components/AppShell';
import { RefreshCw, WifiOff, Activity, Loader2 } from 'lucide-react';
import dynamic from 'next/dynamic';

const CustomChartEditor = dynamic(() => import('@/components/CustomChartEditor'), {
  ssr: false,
  loading: () => (
    <div className="flex-1 flex items-center justify-center">
      <Loader2 className="w-5 h-5 text-muted-foreground animate-spin" />
    </div>
  ),
});

interface DashboardFigureBatchResponse {
  charts: Record<string, { figure?: any; chart_style?: string | null }>;
}

export default function DashboardContainer({ initialData }: { initialData?: any }) {
  const queryClient = useQueryClient();
  const searchParams = useSearchParams();
  const chartId = searchParams.get('chartId');
  const isNewChart = searchParams.get('new') === 'true';

  // All hooks must be called unconditionally
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['dashboard-summary'],
    queryFn: () => apiFetchJson('/api/v1/dashboard/summary?include_figures=false'),
    initialData: initialData || undefined,
    staleTime: 1000 * 60 * 2,
    refetchOnWindowFocus: false,
  });

  // Non-blocking prefetch: seed individual chart figure caches in the background
  useEffect(() => {
    if (chartId || isNewChart) return; // skip when not on gallery
    const chartsByCategory = data?.charts_by_category as Record<string, any[]> | undefined;
    if (!chartsByCategory) return;

    const uniqueCharts = new Map<string, any>();
    Object.values(chartsByCategory).forEach(charts => {
      charts.forEach(chart => {
        if (chart?.id) uniqueCharts.set(chart.id, chart);
      });
    });

    const firstIds = Array.from(uniqueCharts.values())
      .sort((a, b) => (a.rank ?? 0) - (b.rank ?? 0))
      .slice(0, 4) // Only proactively load the top row instead of 20 to save upfront memory on slow connections
      .map(chart => String(chart.id));

    if (firstIds.length === 0) return;

    const params = new URLSearchParams();
    firstIds.forEach(id => params.append('ids', id));

    queryClient.prefetchQuery({
      queryKey: ['dashboard-initial-figures', firstIds],
      queryFn: async () => {
        const batch = await apiFetchJson<DashboardFigureBatchResponse>(
          `/api/v1/dashboard/charts/figures?${params.toString()}`
        );
        for (const [id, entry] of Object.entries(batch.charts)) {
          if (entry.figure) {
            queryClient.setQueryData(['chart-figure', id], entry.figure);
          }
        }
        return batch;
      },
      staleTime: 1000 * 60 * 2,
    });
  }, [data, queryClient, chartId, isNewChart]);

  // ── Route: new chart editor ──
  if (isNewChart) {
    return (
      <div className="fixed inset-0 z-[60] bg-background flex flex-col">
        <CustomChartEditor mode="standalone" initialChartId={null} />
      </div>
    );
  }

  // ── Route: chart detail page ──
  if (chartId) {
    return <ChartDetailView chartId={chartId} />;
  }

  // ── Route: dashboard gallery ──

  if (isError) {
    return (
      <AppShell>
        <div className="flex flex-col items-center justify-center min-h-[70vh] space-y-5 px-4">
          <div className="w-14 h-14 rounded-lg bg-destructive/10 border border-destructive/20 flex items-center justify-center">
            <WifiOff className="w-6 h-6 text-destructive" />
          </div>
          <div className="text-center space-y-1">
            <p className="text-sm font-medium text-foreground">Connection failed</p>
            <p className="text-xs text-muted-foreground max-w-sm">
              {error instanceof Error ? error.message : 'Unable to reach the data pipeline.'}
            </p>
          </div>
          <button
            onClick={() => refetch()}
            className="flex items-center gap-2 px-5 py-2 border border-destructive/30 text-destructive rounded-lg text-xs font-medium hover:bg-destructive/10 transition-all"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Retry
          </button>
        </div>
      </AppShell>
    );
  }

  if (!data && isLoading) {
    return (
      <AppShell hideFooter>
        <div className="h-[calc(100vh-48px)] flex flex-col overflow-hidden">
          <div className="px-4 sm:px-5 lg:px-6 border-b border-border/20 shrink-0 h-11 flex items-center">
            <div className="flex gap-1.5 animate-pulse">
              <div className="h-5 w-8 bg-primary/[0.06] rounded-[var(--radius)]" />
              <div className="h-5 w-16 bg-primary/[0.04] rounded-[var(--radius)]" />
              <div className="h-5 w-14 bg-primary/[0.03] rounded-[var(--radius)]" />
              <div className="h-5 w-12 bg-primary/[0.03] rounded-[var(--radius)]" />
            </div>
          </div>
          <ChartSkeletonGrid />
        </div>
      </AppShell>
    );
  }

  if (!data && !isLoading && !isError) {
    return (
      <AppShell>
        <div className="flex flex-col items-center justify-center min-h-[75vh] space-y-5 animate-in fade-in">
          <div className="w-14 h-14 rounded-lg bg-muted/30 border border-border/50 flex items-center justify-center">
            <Activity className="w-6 h-6 text-muted-foreground/40" />
          </div>
          <div className="text-center space-y-1">
            <p className="text-sm font-medium text-foreground">Connection timed out</p>
            <p className="text-xs text-muted-foreground">Unable to reach the data pipeline</p>
          </div>
          <button
            onClick={() => refetch()}
            className="px-5 py-2 border border-border/50 rounded-lg text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-primary/[0.06] transition-all"
          >
            Retry
          </button>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell hideFooter>
      <Dashboard chartsByCategory={data.charts_by_category || {}} />
    </AppShell>
  );
}
