'use client';

import React, { useMemo } from 'react';
import { useAuth } from '@/context/AuthContext';
import { useQuery } from '@tanstack/react-query';
import { apiFetchJson } from '@/lib/api';
import DashboardWorkspace from '@/components/dashboard/DashboardWorkspace';
import AppShell from '@/components/AppShell';
import { RefreshCw, WifiOff, Activity } from 'lucide-react';

const INITIAL_DASHBOARD_FIGURE_BATCH_SIZE = 9;

interface DashboardFigureBatchResponse {
  charts: Record<string, { figure?: any; chart_style?: string | null }>;
}

export default function DashboardContainer({ initialData }: { initialData?: any }) {
  const { token } = useAuth();

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['dashboard-summary'],
    queryFn: () => apiFetchJson('/api/v1/dashboard/summary?include_figures=false'),
    initialData: initialData || undefined,
    staleTime: 1000 * 60 * 2,
    refetchOnWindowFocus: false,
  });

  const initialFigureIds = useMemo(() => {
    const chartsByCategory = data?.charts_by_category as Record<string, any[]> | undefined;
    if (!chartsByCategory) return [] as string[];

    const uniqueCharts = new Map<string, any>();
    Object.values(chartsByCategory).forEach((charts) => {
      charts.forEach((chart) => {
        if (chart?.id) uniqueCharts.set(chart.id, chart);
      });
    });

    return Array.from(uniqueCharts.values())
      .sort((a, b) => (a.rank ?? 0) - (b.rank ?? 0))
      .slice(0, INITIAL_DASHBOARD_FIGURE_BATCH_SIZE)
      .map((chart) => String(chart.id));
  }, [data]);

  const initialFigureQuery = useQuery({
    queryKey: ['dashboard-initial-figures', initialFigureIds],
    queryFn: () => {
      const params = new URLSearchParams();
      initialFigureIds.forEach((id) => params.append('ids', id));
      return apiFetchJson<DashboardFigureBatchResponse>(
        `/api/v1/dashboard/charts/figures?${params.toString()}`
      );
    },
    enabled: initialFigureIds.length > 0,
    staleTime: 1000 * 60 * 5,
    gcTime: 1000 * 60 * 10,
    refetchOnWindowFocus: false,
  });

  const hydratedChartsByCategory = useMemo(() => {
    const chartsByCategory = data?.charts_by_category as Record<string, any[]> | undefined;
    if (!chartsByCategory) return null;

    const prefetchedFigures = initialFigureQuery.data?.charts ?? {};
    if (Object.keys(prefetchedFigures).length === 0) return chartsByCategory;

    return Object.fromEntries(
      Object.entries(chartsByCategory).map(([category, charts]) => [
        category,
        (charts as any[]).map((chart) => {
          const prefetched = prefetchedFigures[String(chart.id)];
          if (!prefetched?.figure) return chart;
          return {
            ...chart,
            figure: prefetched.figure,
            chart_style: prefetched.chart_style ?? chart.chart_style ?? null,
          };
        }),
      ])
    );
  }, [data, initialFigureQuery.data]);


  if (isError) {
    return (
      <AppShell>
        <div className="flex flex-col items-center justify-center min-h-[70vh] space-y-5 px-4">
          <div className="w-14 h-14 rounded-lg bg-rose-500/10 border border-rose-500/20 flex items-center justify-center">
            <WifiOff className="w-6 h-6 text-rose-400" />
          </div>
          <div className="text-center space-y-1">
            <p className="text-sm font-medium text-foreground">Connection failed</p>
            <p className="text-xs text-muted-foreground max-w-sm">
              {error instanceof Error ? error.message : 'Unable to reach the data pipeline.'}
            </p>
          </div>
          <button
            onClick={() => refetch()}
            className="flex items-center gap-2 px-5 py-2 border border-rose-500/30 text-rose-400 rounded-lg text-xs font-medium hover:bg-rose-500/10 transition-all"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Retry
          </button>
        </div>
      </AppShell>
    );
  }

  const waitingForInitialFigures =
    !!data?.charts_by_category &&
    initialFigureIds.length > 0 &&
    initialFigureQuery.isLoading &&
    !initialFigureQuery.isError;
  const showLoading = (!data && isLoading) || waitingForInitialFigures;

  if (showLoading) {
    return (
      <AppShell>
        <div className="flex flex-col items-center justify-center min-h-[75vh] space-y-6 animate-in fade-in duration-500">
            <div className="w-10 h-10 border-2 border-border/40 border-t-foreground/60 rounded-full animate-spin" />
            <div className="text-center space-y-1.5">
              <p className="text-sm font-medium text-foreground">Loading dashboard</p>
              <p className="text-[10px] font-mono text-muted-foreground/50 uppercase tracking-wider">
                Syncing data pipelines...
              </p>
            </div>
            {!token && (
              <a
                href="/login"
                className="mt-2 px-5 py-2 border border-border/50 rounded-lg text-[11px] font-medium text-muted-foreground hover:text-foreground hover:bg-primary/[0.06] transition-all"
              >
                Return to Login
              </a>
            )}
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
      {hydratedChartsByCategory ? (
        <DashboardWorkspace
          chartsByCategory={hydratedChartsByCategory}
        />
      ) : (
        <div className="text-center py-20 text-muted-foreground">
          Loading Data Dictionary...
        </div>
      )}
    </AppShell>
  );
}
